"""Contrato: o docs/api-exemplo.json segue as regras do docs/api.md.

O front usa esse arquivo até a API existir. Se o contrato mudar e o exemplo não, estes testes quebram.
Quando a API existir, os mesmos testes rodam contra a resposta real de POST /calendar.
"""
import json
import re
from datetime import date


def months_between(first, last):
    y, m = map(int, first.split("-"))
    out = []
    while f"{y}-{m:02d}" <= last:
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def test_blocos_obrigatorios(api_example):
    for key in ["meta", "area", "coverage", "months", "years", "seasonality", "recent", "indicators"]:
        assert key in api_example, key


def test_meses_sem_buraco_e_ate_o_ultimo_mes(api_example):
    months = [m["month"] for m in api_example["months"]]
    assert months == months_between(months[0], months[-1])
    assert months[-1] == api_example["meta"]["last_month"]


def test_origem_depende_so_da_data(api_example):
    for m in api_example["months"]:
        esperado = "estimated_modis" if m["month"] <= "2012-01" else "observed_viirs"
        assert m["source"] == esperado, m["month"]


def test_faixa_so_nos_meses_estimados_e_em_volta_do_valor(api_example):
    for m in api_example["months"]:
        if m["source"] == "observed_viirs":
            assert m["band_low"] is None and m["band_high"] is None, m["month"]
        else:
            assert m["band_low"] <= m["detections"] <= m["band_high"], m["month"]


def test_mes_incompleto(api_example):
    for m in api_example["months"]:
        if m["missing_days"] >= 3:
            assert m["incomplete"], m["month"]
    assert api_example["months"][-1]["incomplete"]  # o mês atual ainda não acabou


def test_mes_atual_sem_anomalia(api_example):
    atual = api_example["months"][-1]
    assert atual["anomaly"] is None and atual["anomaly_pct"] is None


def test_frp_nao_aparece_na_resposta(api_example):
    texto = json.dumps(api_example)
    assert '"frp' not in texto  # o FRP fica só no pacote de auditoria


def test_ranking_dos_anos(api_example):
    years = api_example["years"]
    valores = [y["detections"] for y in years]
    assert valores == sorted(valores, reverse=True)
    ranks = [y["rank"] for y in years if y["complete"]]
    assert ranks == list(range(1, len(ranks) + 1))
    assert all(y["rank"] is None for y in years if not y["complete"])
    assert {y["year"]: y["source"] for y in years}[2012] == "mixed"


def test_sazonalidade_tem_os_12_meses(api_example):
    assert [s["month_of_year"] for s in api_example["seasonality"]] == list(range(1, 13))


def test_janelas_recentes(api_example):
    recent = api_example["recent"]
    date.fromisoformat(recent["data_through"])
    for nome in ["last_7_days", "month_to_date"]:
        w = recent[nome]
        for campo in ["start", "end", "detections", "typical_median", "typical_p25", "typical_p75",
                      "difference", "difference_pct", "n_years", "n_windows", "n_high", "high_share"]:
            assert campo in w, (nome, campo)
        assert w["typical_p25"] <= w["typical_median"] <= w["typical_p75"]
        assert w["end"] == recent["data_through"]


def test_ids_h3_sao_texto(api_example):
    """Um ID H3 como número perde precisão no JSON.parse do navegador. Se aparecer, tem que ser texto."""
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("h3", "cells"):
                    vals = v if isinstance(v, list) else [v]
                    assert all(isinstance(x, str) and re.fullmatch(r"[0-9a-f]{15}", x) for x in vals), k
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(api_example)
