"""Integração do job NRT com um Postgres de verdade (PostGIS), com o FIRMS simulado.

Precisa de um banco DESCARTÁVEL em TEST_DATABASE_URL (o nome do banco precisa ter "teste"): os testes
apagam as tabelas. Sem a variável, os testes são pulados.

    TEST_DATABASE_URL=postgresql://postgres:teste@localhost:5434/firesync_teste_job pytest tests/
"""
import gc
import os
from datetime import datetime, timezone

import h3
import pandas as pd
import pytest

URL = os.environ.get("TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif("teste" not in URL, reason="defina TEST_DATABASE_URL com um banco descartável")

COLS = ["latitude", "longitude", "bright_ti4", "scan", "track", "acq_date", "acq_time", "satellite",
        "instrument", "confidence", "version", "bright_ti5", "frp", "daynight"]
FIRMS_SAT = {"SNPP": "N", "N20": "N20"}  # satélite do mês -> código que o FIRMS escreve no CSV
PONTOS = [(-3.1, -60.1), (-3.2, -60.2)]


@pytest.fixture()
def banco(monkeypatch, tmp_path):
    os.environ["DATABASE_URL"] = URL
    monkeypatch.setenv("FIRMS_MAP_KEY", "chave-de-teste")
    import agregar
    import job_nrt
    import pipeline as p

    conn = p.db()
    for m in sorted((p.ROOT / "migrations").glob("*.sql")):
        conn.execute(m.read_text(encoding="utf-8"))
    conn.execute("TRUNCATE focos, agregados, cobertura, celula_regiao, regioes, dias_sem_dados CASCADE")
    conn.execute("DELETE FROM config WHERE chave = 'atualizado_em'")
    rid = conn.execute("""INSERT INTO regioes (nome, geom, fonte_poligono)
                          VALUES ('Teste', ST_Multi(ST_MakeEnvelope(-61, -4, -59, -2, 4326)), 'teste')
                          RETURNING id""").fetchone()[0]
    res = int(p.config(conn, "h3_resolucao"))
    for lat, lon in PONTOS:
        conn.execute("INSERT INTO celula_regiao (h3, regiao_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                     (h3.str_to_int(h3.latlng_to_cell(lat, lon, res)), rid))

    hoje = datetime.now(timezone.utc).date()
    satelite = agregar.janelas(hoje.replace(day=1), agregar.proximo_mes(hoje.replace(day=1)))[0][0]
    csv = pd.DataFrame([[lat, lon, 330, 0.4, 0.4, hoje.isoformat(), "0130", FIRMS_SAT[satelite], "VIIRS", "n",
                         "2.0NRT", 290, 6.0, "N"] for lat, lon in PONTOS], columns=COLS)

    def curl_simulado(url, dest=None):  # o FIRMS devolve o mesmo CSV para as duas fontes
        csv.to_csv(dest, index=False)

    monkeypatch.setattr(p, "curl", curl_simulado)
    monkeypatch.setattr(p, "sem_dados", lambda: None)  # a página missing_data do FIRMS não entra no teste
    monkeypatch.setattr(p, "RAW", tmp_path)
    yield {"conn": conn, "p": p, "job": job_nrt, "hoje": hoje, "csv": csv}
    gc.collect()  # solta conexões presas em tracebacks (e a trava do job)
    conn.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                 "WHERE datname = current_database() AND pid <> pg_backend_pid()")
    conn.close()


def atualizado_em(conn):
    row = conn.execute("SELECT valor FROM config WHERE chave = 'atualizado_em'").fetchone()
    return row[0] if row else None


def soma_do_mes(conn, hoje):
    return conn.execute("SELECT coalesce(sum(focos_brutos), 0) FROM agregados WHERE ano = %s AND mes = %s",
                        (hoje.year, hoje.month)).fetchone()[0]


def test_rodada_grava_focos_agregados_e_atualizado_em(banco):
    conn, hoje = banco["conn"], banco["hoje"]
    banco["job"].rodada()

    qualidade = conn.execute("SELECT qualidade, count(*) FROM focos GROUP BY 1").fetchall()
    assert qualidade == [("NRT", 2)]  # as duas fontes trazem os mesmos focos: o upsert não duplica
    assert soma_do_mes(conn, hoje) == 2
    valor = atualizado_em(conn)
    assert valor is not None and valor.endswith("Z")
    gravado = datetime.strptime(valor, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    assert (datetime.now(timezone.utc) - gravado).total_seconds() < 600


def test_rodada_registra_inicio_fim_e_quantos_focos_entraram(banco, capturar_logs):
    """RNF07: cada rodada registra quantos focos entraram, quanto tempo levou e os erros."""
    banco["job"].rodada()

    [inicio] = capturar_logs.eventos("nrt_run_started")
    [fim] = capturar_logs.eventos("nrt_run_finished")
    assert inicio["run_id"] == fim["run_id"]
    assert fim["detections_inserted"] == 2 and fim["detections_updated"] == 2  # a 2ª fonte traz os mesmos
    assert fim["nrt_replaced_by_sp"] == 0
    assert fim["duration_ms"] >= 0 and fim["updated_at"].endswith("Z")
    importados = capturar_logs.eventos("import_file_done")
    assert len(importados) == 2 and all(e["run_id"] == inicio["run_id"] for e in importados)
    assert importados[0]["kind"] == "viirs" and importados[0]["rows_in_coverage"] == 2
    janelas = capturar_logs.eventos("aggregate_window_done")  # duas quando a janela de 48 h cruza o mês
    assert sum(j["monthly_rows"] for j in janelas) >= 1
    assert sum(j["detections"] for j in janelas) == 2  # focos que entram no calendário, não linhas
    assert all(j["satellite"] in ("SNPP", "N20") for j in janelas)
    [agregacao] = capturar_logs.eventos("aggregate_finished")
    assert agregacao["scope"] == "partial" and agregacao["data_version_changed"] is False


def test_logs_nunca_mostram_a_map_key(banco, capturar_logs):
    banco["job"].rodada()
    assert "chave-de-teste" not in capturar_logs.stream.getvalue()


def test_rodada_com_outra_rodando_registra_que_pulou(banco, capturar_logs):
    outra = banco["p"].db()
    outra.execute("SELECT pg_advisory_lock(%s)", (banco["job"].LOCK,))
    try:
        banco["job"].rodada()
    finally:
        outra.close()

    [pulou] = capturar_logs.eventos("nrt_run_skipped")
    assert pulou["reason"] == "lock_held" and pulou["level"] == "warning"
    assert capturar_logs.eventos("nrt_run_started") == []


def test_falha_registra_a_etapa_e_o_erro(banco, monkeypatch, capturar_logs):
    def curl_falha(url, dest=None):
        raise RuntimeError("curl falhou (22): https://x/api/area/csv/***/...")

    monkeypatch.setattr(banco["p"], "curl", curl_falha)
    with pytest.raises(RuntimeError):
        banco["job"].rodada()

    [falha] = capturar_logs.eventos("nrt_run_failed")
    assert falha["step"] == "download" and falha["error_type"] == "RuntimeError"
    assert falha["duration_ms"] >= 0
    assert capturar_logs.eventos("nrt_run_finished") == []


def test_rodada_repetida_nao_duplica(banco):
    conn, hoje = banco["conn"], banco["hoje"]
    banco["job"].rodada()
    banco["job"].rodada()
    assert conn.execute("SELECT count(*) FROM focos").fetchone()[0] == 2
    assert soma_do_mes(conn, hoje) == 2


def test_linha_urt_entra_como_nrt_e_nao_apaga_o_nrt(banco, monkeypatch, capturar_logs):
    """Bug de 17/11/2026: o FIRMS passou a mandar linhas `2.1URT` junto com as `2.0NRT`. Gravadas como SP, elas
    faziam o `drop_nrt_under_sp` apagar todo o NRT do satélite até o dia delas, e o mapa ficava vazio."""
    conn, hoje = banco["conn"], banco["hoje"]
    csv = banco["csv"].assign(version=["2.0NRT", "2.1URT"])
    monkeypatch.setattr(banco["p"], "curl", lambda url, dest=None: csv.to_csv(dest, index=False))
    banco["job"].rodada()

    assert conn.execute("SELECT qualidade, count(*) FROM focos GROUP BY 1").fetchall() == [("NRT", 2)]
    assert soma_do_mes(conn, hoje) == 2
    [fim] = capturar_logs.eventos("nrt_run_finished")
    assert fim["nrt_replaced_by_sp"] == 0


def test_falha_no_download_nao_grava_atualizado_em(banco, monkeypatch):
    def curl_falha(url, dest=None):
        raise RuntimeError("curl falhou (22): https://x/api/area/csv/***/...")

    monkeypatch.setattr(banco["p"], "curl", curl_falha)
    with pytest.raises(RuntimeError):
        banco["job"].rodada()
    assert atualizado_em(banco["conn"]) is None
    assert banco["conn"].execute("SELECT count(*) FROM focos").fetchone()[0] == 0


def test_falha_no_meio_da_agregacao_nao_muda_o_que_a_api_le(banco, monkeypatch):
    """A API nunca lê agregados novos com o atualizado_em velho (bug da issue #15, corrigido no PR #23)."""
    conn, hoje, agregar = banco["conn"], banco["hoje"], banco["job"].agregar
    janelas = agregar.janelas

    def janelas_que_falham(de, ate):  # falha depois do DELETE, dentro da transação da agregação
        janelas(de, ate)
        raise RuntimeError("falha no meio da agregação")

    monkeypatch.setattr(agregar, "janelas", janelas_que_falham)
    with pytest.raises(RuntimeError):
        banco["job"].rodada()
    assert atualizado_em(conn) is None
    assert soma_do_mes(conn, hoje) == 0  # a agregação e a versão vão no mesmo commit


def test_pagina_de_dias_sem_dados_fora_do_ar_nao_trava_a_agregacao(banco, monkeypatch, capturar_logs):
    """Auditoria, achado 4: a página missing_data do FIRMS é um JSON não documentado. Se ela quebrar, a rodada
    segue com a tabela antiga de dias sem dados, em vez de deixar o site parado."""
    conn, hoje = banco["conn"], banco["hoje"]

    def sem_dados_falha():
        raise RuntimeError("missing_data fora do ar")

    monkeypatch.setattr(banco["p"], "sem_dados", sem_dados_falha)
    banco["job"].rodada()
    assert atualizado_em(conn) is not None
    assert soma_do_mes(conn, hoje) == len(PONTOS)
    assert capturar_logs.eventos("missing_days_failed")
