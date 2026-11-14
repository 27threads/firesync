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
    yield {"conn": conn, "p": p, "job": job_nrt, "hoje": hoje}
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


def test_rodada_repetida_nao_duplica(banco):
    conn, hoje = banco["conn"], banco["hoje"]
    banco["job"].rodada()
    banco["job"].rodada()
    assert conn.execute("SELECT count(*) FROM focos").fetchone()[0] == 2
    assert soma_do_mes(conn, hoje) == 2


def test_falha_no_download_nao_grava_atualizado_em(banco, monkeypatch):
    def curl_falha(url, dest=None):
        raise RuntimeError("curl falhou (22): https://x/api/area/csv/***/...")

    monkeypatch.setattr(banco["p"], "curl", curl_falha)
    with pytest.raises(RuntimeError):
        banco["job"].rodada()
    assert atualizado_em(banco["conn"]) is None
    assert banco["conn"].execute("SELECT count(*) FROM focos").fetchone()[0] == 0


@pytest.mark.xfail(strict=True, reason="bug da issue #15: dados e atualizado_em não estão no mesmo commit")
def test_falha_depois_de_agregar_nao_muda_o_que_a_api_le(banco, monkeypatch):
    """Se a rodada falha depois de agregar, a API não pode ler agregados novos com o atualizado_em velho."""
    conn, hoje = banco["conn"], banco["hoje"]

    def sem_dados_falha():
        raise RuntimeError("missing_data fora do ar")

    monkeypatch.setattr(banco["p"], "sem_dados", sem_dados_falha)
    with pytest.raises(RuntimeError):
        banco["job"].rodada()
    assert atualizado_em(conn) is None
    assert soma_do_mes(conn, hoje) == 0  # hoje falha: os agregados novos já foram gravados
