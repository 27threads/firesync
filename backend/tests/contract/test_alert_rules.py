"""Contrato: o config/alert_rules.json tem o formato que a API vai ler."""
import re


def test_tem_versao(alert_rules):
    assert re.fullmatch(r"\d+\.\d+", alert_rules["version"])


def test_janela_do_normal(alert_rules):
    b = alert_rules["baseline"]
    assert b["window_days"] == 7 and b["neighbor_days"] == 15
    assert b["reference_years_from"] == 2012 and b["satellite"] == "VIIRS"


def test_niveis_do_alerta(alert_rules):
    lv = alert_rules["levels"]
    assert lv["critical"]["min_ratio_to_median"] > 1
    assert lv["critical"]["trend_days"] >= 1
    assert 50 < lv["attention"]["above_percentile"] < 100


def test_decisao_da_issue_59(alert_rules):
    assert alert_rules['version'] == '1.0'
    assert alert_rules['levels']['critical'] == {
        'min_ratio_to_median': 2.0, 'min_detections': 10,
        'trend_days': 3, 'requires_rising_trend': True,
    }
    assert alert_rules['levels']['attention']['above_percentile'] == 75


def test_classe_de_intensidade(alert_rules):
    it = alert_rules["intensity"]
    assert 0 < it["medium_min_mw"] < it["high_min_mw"]
    sat = it["saturated_is_high"]
    assert sat["enabled"] is True and sat["sensors"] == ["VIIRS"]  # no MODIS, confiança alta não é saturação
