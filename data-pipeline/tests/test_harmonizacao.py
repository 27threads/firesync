"""Harmonização (frente B): comparação com o INPE e calibração, sem banco. DADOS INVENTADOS em todos os testes.

Os três primeiros testes reproduzem bugs achados na revisão do PR #26 (docs/testes.md, regra 2).
"""
import sys

import pandas as pd
import pytest

from harmonizacao import calibrar, test_calibrar, test_validar_inpe, validar_inpe


def contagens(linhas):
    return pd.DataFrame(linhas, columns=["bioma", "ano", "mes", "satelite", "periodo", "focos"])


def fatores(linhas):
    return pd.DataFrame(linhas, columns=["bioma", "mes", "periodo", "ano_calibracao", "fator"])


def test_faixa_do_ano_soma_por_cenario_e_nao_os_percentis():
    """Bug 1: a faixa anual somava o P5 e o P95 de cada mês. A soma dos percentis não é o percentil da soma."""
    cont = contagens([("X", 2005, m, "Aqua", "D", 1 if m <= 2 else 0) for m in range(1, 13)])
    fat = fatores([("X", 1, "D", 2012, 1.0), ("X", 1, "D", 2013, 10.0),
                   ("X", 2, "D", 2012, 10.0), ("X", 2, "D", 2013, 1.0)])
    ano = validar_inpe.anual(cont, fat, ate=2005).iloc[0]
    # cenário 2012: 1 + 10 = 11; cenário 2013: 10 + 1 = 11. A faixa do ano é 11 a 11.
    assert ano["firesync"] == pytest.approx(11)
    assert ano["band_low"] == pytest.approx(11)
    assert ano["band_high"] == pytest.approx(11)


def test_mes_sem_deteccao_entra_como_zero_e_o_ano_continua_na_comparacao():
    """Bug 2: mês sem linha em `agregados` sumia da série, e o ano inteiro saía da comparação anual."""
    cont = contagens([("X", 2005, m, "Aqua", "D", 100) for m in range(1, 13) if m != 3])
    fat = fatores([("X", m, "D", k, 5.0) for m in range(1, 13) for k in (2012, 2013)])
    inpe = pd.DataFrame([("X", 2005, m, 50) for m in range(1, 13)], columns=["bioma", "ano", "mes", "inpe"])
    serie = validar_inpe.harmonizar(cont, fat)
    marco = serie[(serie["ano"] == 2005) & (serie["mes"] == 3)]
    assert len(marco) == 1 and marco["firesync"].iloc[0] == 0
    medidas = validar_inpe.comparar(serie.merge(inpe, on=["bioma", "ano", "mes"])).iloc[0]
    assert medidas["meses"] == 12 and medidas["anos_completos"] == 1


def test_periodo_com_focos_e_sem_fator_nao_vira_zero_em_silencio():
    """Revisão do PR #26, ponto 5: sem fator para um período com focos, o mês fica sem estimativa (não zero)."""
    cont = contagens([("X", 2005, 1, "Aqua", "D", 10), ("X", 2005, 1, "Aqua", "N", 10)])
    fat = fatores([("X", 1, "D", 2012, 5.0)])
    janeiro = validar_inpe.harmonizar(cont, fat).query("ano == 2005 and mes == 1").iloc[0]
    assert pd.isna(janeiro["firesync"])


def test_mes_observado_nao_tem_faixa_e_usa_a_contagem_do_viirs():
    cont = contagens([("X", 2013, 1, "SNPP", "D", 70), ("X", 2013, 1, "SNPP", "N", 30)])
    fat = fatores([("X", 1, "D", 2012, 5.0)])
    janeiro = validar_inpe.harmonizar(cont, fat).query("ano == 2013 and mes == 1").iloc[0]
    assert janeiro["firesync"] == 100 and janeiro["origem"] == "observado_viirs"
    assert pd.isna(janeiro["band_low"]) and pd.isna(janeiro["band_high"])


@pytest.mark.parametrize("autoteste", [test_calibrar, test_validar_inpe])
def test_autotestes_com_dados_inventados_passam(autoteste):
    """Os autotestes da pasta harmonizacao/ (fatores conhecidos, deriva, degrau em 2012) rodam na esteira."""
    autoteste.main()  # termina com SystemExit(1) se alguma conferência falhar


def test_calibracao_pela_linha_de_comando_gera_relatorio_e_decide_os_anos(tmp_path, monkeypatch):
    test_calibrar.gerar(deriva=False).to_csv(tmp_path / "contagens.csv", index=False)
    monkeypatch.setattr(sys, "argv", ["calibrar.py", "--csv", str(tmp_path / "contagens.csv"),
                                      "--saida", str(tmp_path / "saida")])
    calibrar.main()
    relatorio = (tmp_path / "saida" / "relatorio.txt").read_text(encoding="utf-8")
    assert "anos 2012 a 2024 (13 cenários)" in relatorio
    fat = pd.read_csv(tmp_path / "saida" / "fatores_todos_os_anos.csv")
    assert not ((fat["ano"] == 2012) & (fat["mes"] == 1)).any()  # janeiro de 2012 fora


def test_comparacao_com_o_inpe_pela_linha_de_comando(tmp_path, monkeypatch):
    inpe, cont, fat = test_validar_inpe.gerar(1.0)
    for nome, d in (("inpe", inpe), ("contagens", cont), ("fatores", fat)):
        d.to_csv(tmp_path / f"{nome}.csv", index=False)
    monkeypatch.setattr(sys, "argv", ["validar_inpe.py", "--contagens", str(tmp_path / "contagens.csv"),
                                      "--fatores", str(tmp_path / "fatores.csv"), "--inpe", str(tmp_path / "inpe.csv"),
                                      "--ate", "2024", "--saida", str(tmp_path / "b6")])
    validar_inpe.main()
    medidas = pd.read_csv(tmp_path / "b6" / "metricas_b6.csv").iloc[0]
    assert medidas["anos_completos"] == 22 and abs(medidas["degrau_2012"]) < 0.1
    anual = pd.read_csv(tmp_path / "b6" / "serie_anual_firesync.csv")
    estimados = anual[anual["origem"] == "estimado_modis"]
    assert ((estimados["band_low"] <= estimados["firesync"]) & (estimados["firesync"] <= estimados["band_high"])).all()
