"""NRT ou SP pela fonte do arquivo, não só pelo texto da versão (bug de 17/11/2026, linhas `2.1URT`).

O FIRMS muda o texto da versão sem avisar. O que não muda é a fonte que a gente pediu: tudo o que vem de uma
fonte `*_NRT` é provisório. Versão que o código não conhece gera um aviso no log, para a mudança aparecer no dia.
"""
import pandas as pd

from pipeline import normalize

C = ["latitude", "longitude", "acq_date", "acq_time", "satellite", "confidence", "version", "frp", "daynight"]


def frame(versoes):
    return pd.DataFrame([[-3, -60, "2026-11-17", "312", "N20", "n", v, 1.2, "N"] for v in versoes], columns=C)


def test_fonte_nrt_e_provisoria_com_qualquer_versao():
    t = normalize(frame(["2.0NRT", "2.2XYZ", "3"]), "viirs", fonte="VIIRS_NOAA20_NRT_20261117_20261117T1200.csv")
    assert t.provisional.tolist() == [True, True, True]


def test_fonte_sp_usa_a_versao():
    t = normalize(frame(["2", "2.0NRT"]), "viirs", fonte="VIIRS_NOAA20_SP")
    assert t.provisional.tolist() == [False, True]


def test_sem_fonte_usa_a_versao():
    t = normalize(frame(["2.0NRT", "2.1URT", "2", "6.03"]), "viirs")
    assert t.provisional.tolist() == [True, True, False, False]


def test_versao_desconhecida_gera_aviso(capturar_logs):
    normalize(frame(["2.0NRT", "2.2XYZ", "2.2XYZ", "2"]), "viirs", fonte="VIIRS_NOAA20_NRT")
    [aviso] = capturar_logs.eventos("firms_unknown_version")
    assert aviso["level"] == "warning"
    assert aviso["versions"] == ["2.2XYZ"] and aviso["source"] == "VIIRS_NOAA20_NRT"


def test_versoes_conhecidas_nao_geram_aviso(capturar_logs):
    normalize(frame(["2.0NRT", "2.1URT", "2.0RT", "2", "6.03", "61.03"]), "viirs")
    assert capturar_logs.eventos("firms_unknown_version") == []
