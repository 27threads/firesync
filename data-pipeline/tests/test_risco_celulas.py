"""Risco por célula (RFC 0003): o modelo treinado de 'onde vai ter fogo nos próximos 14 dias'. DADOS INVENTADOS.

Nenhum número aqui é dado real. Os testes plantam um padrão conhecido (algumas células pegam fogo todo ano na mesma época)
e conferem que o modelo o aprende, que nenhuma variável olha para o futuro e que o resultado vai para o arquivo e para o banco.
"""
import json
import sys
from datetime import date, timedelta

import h3
import numpy as np
import pandas as pd
import pytest

import risco_celulas as rc

CENTRO = h3.latlng_to_cell(-10.0, -55.0, 4)
CELULAS = [h3.str_to_int(c) for c in sorted(h3.grid_disk(CENTRO, 2))]          # 19 células vizinhas
FOGUENTAS = CELULAS[:3]                                                         # pegam fogo forte em ago a out, todo ano
INICIO, FIM = date(2012, 2, 1), date(2017, 6, 30)
REGRAS = {"version": "t1", "horizon_days": 14, "tiers": [{"tier": "very_high", "min_prob": 0.6}, {"tier": "high", "min_prob": 0.4},
                                                          {"tier": "medium", "min_prob": 0.2}, {"tier": "lower", "min_prob": 0.0}]}


def serie_inventada(semente=0, fim=FIM):
    rng = np.random.default_rng(semente)
    dias = pd.date_range(INICIO, fim)
    linhas = []
    for u in CELULAS:
        base = np.full(len(dias), 0.05)
        if u in FOGUENTAS:
            base = np.where((dias.month >= 8) & (dias.month <= 10), 4.0, 0.2)
        n = rng.poisson(base)
        linhas.append(pd.DataFrame({"unidade": u, "data": dias.strftime("%Y-%m-%d"), "n": n}))
    d = pd.concat(linhas)
    return d[d["n"] > 0].reset_index(drop=True)


def test_faixa_de_usa_os_cortes_do_arquivo_de_regras():
    assert [rc.faixa_de(p, REGRAS) for p in (0.95, 0.6, 0.59, 0.4, 0.2, 0.19, 0.0)] == \
        ["very_high", "very_high", "high", "high", "medium", "lower", "lower"]


def test_arquivo_de_regras_real_tem_os_cortes_e_as_taxas_de_cada_faixa():
    r = rc.carregar_regras()
    assert r["horizon_days"] == 14 and r["version"]
    cortes = [t["min_prob"] for t in r["tiers"]]
    assert cortes == sorted(cortes, reverse=True) and cortes[-1] == 0.0
    taxa = r["historical_share"]
    assert set(taxa) == {t["tier"] for t in r["tiers"]}
    assert taxa["lower"] < taxa["medium"] < taxa["high"] < taxa["very_high"] < 1


def test_serie_preparada_tem_uma_linha_por_celula_e_um_dia_a_mais_ate_o_fim():
    s = rc.preparar_serie(serie_inventada(), FIM)
    assert s["matriz"].shape == (len(CELULAS), (FIM - INICIO).days + 1)
    assert set(s["unidades"]) == set(CELULAS)
    assert s["matriz"].sum() == serie_inventada()["n"].sum()


def test_as_variaveis_sao_so_as_do_modelo_e_nenhuma_olha_o_futuro():
    d = serie_inventada()
    domingo = date(2016, 8, 7)
    antes = rc.montar_pistas(rc.preparar_serie(d, FIM), [domingo])
    assert list(antes) == rc.FEATURES
    futuro = d.copy()
    futuro.loc[pd.to_datetime(futuro["data"]).dt.date > domingo, "n"] = 999        # muda todo o futuro
    depois = rc.montar_pistas(rc.preparar_serie(futuro, FIM), [domingo])
    for nome in antes:
        assert np.array_equal(antes[nome], depois[nome], equal_nan=True), nome


def test_o_modelo_aprende_que_as_celulas_de_fogo_recorrente_tem_mais_chance_na_temporada():
    d = serie_inventada()
    modelo = rc.treinar(d, date(2016, 12, 31))
    r = rc.pontuar(modelo, d, date(2017, 8, 6)).set_index("h3")
    assert r["prob"].between(0, 1).all() and set(r["faixa"]) <= {"very_high", "high", "medium", "lower"}
    assert r.loc[FOGUENTAS, "prob"].min() > 0.5                                    # plantado: fogo forte todo ano em ago a out
    assert r.drop(FOGUENTAS)["prob"].max() < 0.2


def test_o_treino_so_usa_semanas_cujo_gabarito_termina_antes_do_fim_dos_dados():
    """Mudar tudo depois do corte não pode mudar o modelo treinado até o corte."""
    d = serie_inventada()
    corte = date(2016, 6, 30)
    futuro = d.copy()
    futuro.loc[pd.to_datetime(futuro["data"]).dt.date > corte, "n"] = 500
    a = rc.pontuar(rc.treinar(d, corte), d, date(2016, 6, 26))["prob"].to_numpy()
    b = rc.pontuar(rc.treinar(futuro, corte), d, date(2016, 6, 26))["prob"].to_numpy()
    assert np.allclose(a, b)


def test_o_treino_e_reproduzivel_com_a_mesma_semente():
    d = serie_inventada()
    a = rc.pontuar(rc.treinar(d, date(2016, 12, 31), semente=3), d, date(2017, 3, 5))["prob"].to_numpy()
    b = rc.pontuar(rc.treinar(d, date(2016, 12, 31), semente=3), d, date(2017, 3, 5))["prob"].to_numpy()
    assert np.array_equal(a, b)


def test_linha_de_comando_com_arquivo_grava_notas_modelo_e_relatorio(tmp_path, monkeypatch):
    serie_inventada().to_parquet(tmp_path / "serie.parquet", index=False)
    monkeypatch.setattr(sys, "argv", ["risco_celulas.py", "--serie", str(tmp_path / "serie.parquet"), "--data-ref", "2017-08-06",
                                      "--saida", str(tmp_path / "saida")])
    rc.main()
    notas = pd.read_csv(tmp_path / "saida" / "risco_celulas.csv")
    assert list(notas.columns) == ["h3", "h3_texto", "data_ref", "prob", "faixa", "modelo_versao"]
    assert len(notas) == len(CELULAS) and (notas["data_ref"] == "2017-08-06").all()
    assert (tmp_path / "saida" / "modelo_risco.joblib").exists()
    texto = (tmp_path / "saida" / "relatorio_risco.txt").read_text(encoding="utf-8")
    assert "2017-08-06" in texto and "treinado com dados até" in texto


def test_a_nota_de_uma_data_antiga_so_usa_dados_ate_ela(tmp_path, monkeypatch):
    """Para mostrar uma data do passado, o modelo é treinado só com o que existia até ela (nada de olhar o futuro)."""
    serie_inventada().to_parquet(tmp_path / "serie.parquet", index=False)
    monkeypatch.setattr(sys, "argv", ["risco_celulas.py", "--serie", str(tmp_path / "serie.parquet"), "--data-ref", "2015-08-02",
                                      "--saida", str(tmp_path / "saida")])
    rc.main()
    texto = (tmp_path / "saida" / "relatorio_risco.txt").read_text(encoding="utf-8")
    assert "treinado com dados até 2015-07-19" in texto                            # 14 dias antes: o gabarito precisa ter terminado


# ---------------------------------------------------------------- banco (pulados sem TEST_DATABASE_URL)
import os  # noqa: E402

URL = os.environ.get("TEST_DATABASE_URL", "")
banco = pytest.mark.skipif("teste" not in URL, reason="defina TEST_DATABASE_URL com um banco descartável")


@pytest.fixture()
def conn():
    os.environ["DATABASE_URL"] = URL
    import pipeline as p

    c = p.db()
    for m in sorted((p.ROOT / "migrations").glob("*.sql")):
        c.execute(m.read_text(encoding="utf-8"))
    c.execute("TRUNCATE risco_celulas, agregados_diarios, cobertura, celula_regiao, regioes CASCADE")
    yield c
    c.close()


@banco
def test_gravar_e_idempotente_e_atualiza_a_nota_do_mesmo_dia(conn):
    notas = pd.DataFrame({"h3": CELULAS[:2], "prob": [0.7, 0.1], "faixa": ["very_high", "lower"]})
    assert rc.gravar(conn, notas, date(2026, 11, 14), "v1") == 2
    notas.loc[0, "prob"], notas.loc[0, "faixa"] = 0.45, "high"
    assert rc.gravar(conn, notas, date(2026, 11, 14), "v1") == 2                   # de novo: atualiza, não duplica
    linhas = conn.execute("SELECT h3, prob, faixa FROM risco_celulas ORDER BY prob DESC").fetchall()
    assert [(r[2]) for r in linhas] == ["high", "lower"] and len(linhas) == 2
    assert conn.execute("SELECT count(DISTINCT calculado_em) FROM risco_celulas").fetchone()[0] == 1


@banco
def test_a_serie_do_banco_soma_as_celulas_filhas_na_celula_res4_e_a_data_vem_da_cobertura(conn):
    conn.execute("INSERT INTO regioes (nome, geom, fonte_poligono) VALUES ('Teste', ST_Multi(ST_MakeEnvelope(-61,-4,-59,-2,4326)), 'teste')")
    regiao = conn.execute("SELECT id FROM regioes").fetchone()[0]
    filhas = sorted(h3.cell_to_children(CENTRO, 6))[:2]
    for f in filhas:
        conn.execute("INSERT INTO agregados_diarios VALUES (%s,'2026-11-10',%s,'N20','D',3)", (h3.str_to_int(f), regiao))
    conn.execute("INSERT INTO cobertura(regiao_id,satelite,data_inicio,data_fim) VALUES (%s,'N20','2026-11-01','2026-11-20')", (regiao,))
    serie = rc.serie_do_banco(conn)
    assert serie.loc[serie["unidade"] == h3.str_to_int(CENTRO), "n"].sum() == 6    # duas filhas de 3
    from datetime import datetime, UTC
    # a cobertura vai até 20/11, mas a data nunca passa do relógio (15/11), e também não depende de haver focos nesse dia
    assert rc.data_de_referencia(conn, datetime(2026, 11, 15, 12, tzinfo=UTC)) == date(2026, 11, 15)
