"""Integração da calibração (frente B) com um Postgres de verdade. DADOS INVENTADOS.

Precisa de um banco DESCARTÁVEL em TEST_DATABASE_URL (o nome do banco precisa ter "teste"): o teste apaga
tabelas. Sem a variável, é pulado.
"""
import os

import pandas as pd
import pytest

URL = os.environ.get("TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif("teste" not in URL, reason="defina TEST_DATABASE_URL com um banco descartável")

VERSAO_ANTIGA = "2000-01-01T00:00:00Z"


@pytest.fixture()
def conn():
    os.environ["DATABASE_URL"] = URL
    import pipeline as p

    c = p.db()
    for m in sorted((p.ROOT / "migrations").glob("*.sql")):
        c.execute(m.read_text(encoding="utf-8"))
    c.execute("TRUNCATE fatores_harmonizacao, celula_regiao, regioes CASCADE")
    c.execute("INSERT INTO regioes (nome, geom, fonte_poligono) "
              "VALUES ('Teste', ST_Multi(ST_MakeEnvelope(-61, -4, -59, -2, 4326)), 'teste')")
    for chave in ("atualizado_em", "data_version"):
        c.execute("INSERT INTO config (chave, valor) VALUES (%s, %s) "
                  "ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor", (chave, VERSAO_ANTIGA))
    yield c
    c.close()


def versao(c, chave):
    return c.execute("SELECT valor FROM config WHERE chave = %s", (chave,)).fetchone()[0]


def test_gravar_fatores_muda_a_versao_dos_dados_no_mesmo_commit(conn):
    """Bug 3 da revisão do PR #26: os fatores mudavam e a versão não, então o cache da API ficava velho."""
    from harmonizacao import calibrar

    fat = pd.DataFrame([("Teste", 2012, 2, "D", 5.0, 100, None), ("Teste", 2013, 2, "D", 6.0, 120, None)],
                       columns=["regiao", "ano", "mes", "periodo", "fator", "n_focos_origem", "fusao_com"])
    assert calibrar.gravar(fat, [2012, 2013]) == 2
    assert conn.execute("SELECT count(*) FROM fatores_harmonizacao").fetchone()[0] == 2
    # a API usa `atualizado_em` como chave do cache e recarrega os fatores quando `data_version` muda
    assert versao(conn, "atualizado_em") != VERSAO_ANTIGA
    assert versao(conn, "data_version") != VERSAO_ANTIGA
