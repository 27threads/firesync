"""Modelo de risco (RFC 0003): chance de "muito fogo" nos 14 dias seguintes, por célula H3 res 4. DADOS INVENTADOS.

Nenhum número aqui é dado real. Os testes conferem, acima de tudo, que nenhuma pista usa dias depois do domingo
avaliado e que o treino só usa anos anteriores ao ano de teste (docs/testes.md, regras 1 e 5).
"""
import sys
from datetime import date, timedelta

import h3
import numpy as np
import pandas as pd
import pytest

from validacao import backtest_alerta as bt
from validacao import modelo_risco as mr

N_DIAS = (bt.FIM - bt.INICIO).days + 1
CENTRO = h3.latlng_to_cell(-10.0, -55.0, 4)
UNIDADES = np.array(sorted(h3.str_to_int(c) for c in h3.grid_disk(CENTRO, 1)))   # o centro e os 6 vizinhos
J_CENTRO = int(np.where(UNIDADES == h3.str_to_int(CENTRO))[0][0])
T = date(2020, 8, 2)                                                           # um domingo
SEMANAS = [T]


def dia(d):
    return (d - bt.INICIO).days


def vazia():
    return np.zeros((len(UNIDADES), N_DIAS), np.float32)


def bruto(linhas):
    """CSV INVENTADO no formato do Archive Download do VIIRS: (lat, lon, data, confiança, frp, type)."""
    return pd.DataFrame([{"latitude": la, "longitude": lo, "bright_ti4": 330.0, "bright_ti5": 290.0, "scan": 0.4,
                          "track": 0.4, "acq_date": d, "acq_time": "1700", "satellite": "N", "confidence": c,
                          "version": "2", "frp": f, "daynight": "D", "type": t} for la, lo, d, c, f, t in linhas])


def test_serie_diaria_conta_por_celula_e_dia_com_a_limpeza_da_frente_a():
    la, lo = h3.cell_to_latlng(CENTRO)               # pontos a metros do centro da célula, todos dentro dela
    df = bruto([(la, lo, "2020-08-01", "n", 5.0, 0), (la + 0.001, lo, "2020-08-01", "h", 7.0, 0),
                (la + 0.002, lo, "2020-08-02", "n", 3.0, 0),
                (la + 0.003, lo, "2020-08-01", "l", 9.0, 0),      # confiança baixa: fora
                (la + 0.004, lo, "2020-08-01", "n", 9.0, 2),      # type diferente de 0: fora
                (la + 0.005, lo, "2020-08-01", "n", 0.0, 0)])     # FRP zero: fora
    s = mr.serie_diaria(df).set_index("data")
    assert set(s["unidade"]) == {h3.str_to_int(CENTRO)}
    assert s.loc["2020-08-01", "n"] == 2 and s.loc["2020-08-01", "frp"] == pytest.approx(12.0)
    assert s.loc["2020-08-02", "n"] == 1


def test_matrizes_alinham_contagem_e_potencia_na_mesma_ordem_de_unidades():
    df = pd.DataFrame({"unidade": [UNIDADES[2], UNIDADES[0]], "data": ["2020-08-01", "2020-08-02"],
                       "n": [4, 1], "frp": [40.0, 3.0]})
    unidades, m_n, m_frp = mr.matrizes(df)
    assert list(unidades) == [UNIDADES[0], UNIDADES[2]]
    assert m_n[1, dia(date(2020, 8, 1))] == 4 and m_frp[1, dia(date(2020, 8, 1))] == pytest.approx(40.0)
    assert m_n.shape == (2, N_DIAS) and m_n.sum() == 5


def test_pistas_de_fogo_somam_as_janelas_certas():
    m, frp = vazia(), vazia()
    m[J_CENTRO, dia(T) - 6: dia(T) + 1] = 2          # 7 dias até o domingo: 14 detecções
    m[J_CENTRO, dia(T) - 20] = 5                     # dentro dos 30 dias, fora dos 14
    frp[J_CENTRO, dia(T)] = 80.0
    p = mr.pistas_fogo(m, frp, SEMANAS, mr.vizinhos(UNIDADES))
    assert p["s7"][0, J_CENTRO] == 14 and p["s14"][0, J_CENTRO] == 14 and p["s30"][0, J_CENTRO] == 19
    assert p["frp7"][0, J_CENTRO] == pytest.approx(80.0)
    assert p["tendencia"][0, J_CENTRO] == 0          # 3 dias iguais aos 3 anteriores


def test_vizinhanca_soma_as_celulas_ao_lado_e_nao_a_propria():
    m = vazia()
    m[J_CENTRO, dia(T)] = 100
    vizinha = (J_CENTRO + 1) % len(UNIDADES)
    m[vizinha, dia(T)] = 3
    p = mr.pistas_fogo(m, vazia(), SEMANAS, mr.vizinhos(UNIDADES))
    assert p["viz7"][0, J_CENTRO] == 3               # só a vizinha
    assert p["viz7"][0, vizinha] >= 100              # a vizinha enxerga o centro


def test_nenhuma_pista_de_fogo_usa_dias_depois_do_domingo():
    rng = np.random.default_rng(0)
    m, frp = rng.poisson(1.0, vazia().shape).astype(np.float32), rng.random(vazia().shape).astype(np.float32)
    antes = mr.pistas_fogo(m, frp, SEMANAS, mr.vizinhos(UNIDADES))
    m2, frp2 = m.copy(), frp.copy()
    m2[:, dia(T) + 1:] = 999                         # muda todo o futuro
    frp2[:, dia(T) + 1:] = 999
    depois = mr.pistas_fogo(m2, frp2, SEMANAS, mr.vizinhos(UNIDADES))
    for nome in antes:
        assert np.array_equal(antes[nome], depois[nome], equal_nan=True), nome


def test_normal_passado_e_a_media_dos_14_dias_seguintes_nos_anos_anteriores():
    m = vazia()
    for ano, total in ((2019, 28), (2018, 14)):      # os 14 dias seguintes à mesma data, um e dois anos antes
        fim = dia(T) + 14 - 364 * (2020 - ano)
        m[J_CENTRO, fim - 13: fim + 1] = total / 14
    p = mr.pistas_fogo(m, vazia(), SEMANAS, mr.vizinhos(UNIDADES))
    assert p["ano_anterior"][0, J_CENTRO] == pytest.approx(28)
    assert p["normal_passado"][0, J_CENTRO] == pytest.approx((28 + 14 + 0 * 6) / 8)   # 8 anos anteriores na série


def test_oni_usa_a_estacao_ja_publicada_dois_meses_antes(tmp_path):
    (tmp_path / "oni.txt").write_text(" SEAS  YR   TOTAL   ANOM\n  AMJ 2020  27.0  -0.10\n  MJJ 2020  27.0  -0.30\n"
                                      "  JJA 2020  27.0  -0.90\n  JAS 2020  27.0  -1.50\n", encoding="utf-8")
    oni = mr.ler_oni(tmp_path / "oni.txt")
    # agosto de 2020: a última estação que termina até junho é AMJ. MJJ termina em julho e ainda não vale
    assert mr.pista_oni(oni, [date(2020, 8, 2)])[0] == pytest.approx(-0.10)
    assert mr.pista_oni(oni, [date(2020, 9, 6)])[0] == pytest.approx(-0.30)
    assert np.isnan(mr.pista_oni(oni, [date(2019, 1, 6)])[0])        # sem estação anterior no arquivo


def test_pistas_de_clima_somam_a_chuva_e_contam_os_dias_secos_sem_olhar_o_futuro():
    chuva = np.full((len(UNIDADES), N_DIAS), 2.0, np.float32)
    chuva[J_CENTRO, dia(T) - 9: dia(T) + 1] = 0.0                    # 10 dias secos até o domingo
    chuva[:, dia(T) + 1:] = 500.0                                    # futuro: não pode entrar
    quente = np.full((len(UNIDADES), N_DIAS), 30.0, np.float32)
    p = mr.pistas_clima({"PRECTOTCORR": chuva, "T2M_MAX": quente, "RH2M": quente, "WS2M": quente}, SEMANAS)
    assert p["chuva30"][0, J_CENTRO] == pytest.approx(40.0)          # 20 dias de 2 mm
    assert p["chuva90"][0, J_CENTRO] == pytest.approx(160.0)
    assert p["dias_secos30"][0, J_CENTRO] == 10
    assert p["tmax7"][0, J_CENTRO] == pytest.approx(30.0) and p["umid7"][0, 0] == pytest.approx(30.0)


def test_clima_do_power_vai_para_a_celula_pelo_ponto_da_grade_mais_perto(tmp_path):
    la, lo = h3.cell_to_latlng(CENTRO)
    perto, longe = (round(la * 2) / 2, round(lo / 0.625) * 0.625), (round(la * 2) / 2 + 5.0, round(lo / 0.625) * 0.625)
    pd.DataFrame({"LAT": [perto[0], longe[0], perto[0]], "LON": [perto[1], longe[1], perto[1]], "YEAR": [2020] * 3,
                  "DOY": [215, 215, 216], "PRECTOTCORR": [7.5, 99.0, -999.0]}).to_parquet(
        tmp_path / "PRECTOTCORR_2020.parquet", index=False)        # INVENTADO; 2020-08-02 é o dia 215 do ano
    clima = mr.clima_por_unidade(tmp_path, UNIDADES)
    assert set(clima) == {"PRECTOTCORR"}
    assert clima["PRECTOTCORR"][J_CENTRO, dia(T)] == pytest.approx(7.5)
    assert np.isnan(clima["PRECTOTCORR"][J_CENTRO, dia(T) + 1])    # -999 é dado ausente
    assert np.isnan(clima["PRECTOTCORR"][J_CENTRO, dia(T) - 1])    # dia sem linha


def test_bioma_da_celula_pelo_centro():
    import geopandas as gpd
    from shapely.geometry import box

    la, lo = h3.cell_to_latlng(CENTRO)
    biomas = gpd.GeoDataFrame({"CD_Bioma": [3]}, geometry=[box(lo - 0.05, la - 0.05, lo + 0.05, la + 0.05)], crs=4326)
    b = mr.bioma_das_unidades(UNIDADES, biomas)
    assert b[J_CENTRO] == 3 and np.isnan(np.delete(b, J_CENTRO)).all()      # as vizinhas ficam fora do retângulo


def test_clima_entra_sobre_as_pistas_de_fogo_e_nao_sobre_o_oni(tmp_path, monkeypatch):
    """Decisão de 15/11/2026: o ONI não ajudou e fica só como comparação. O conjunto com clima parte do de fogo."""
    rng = np.random.default_rng(2)
    dias = pd.date_range("2012-02-01", "2024-12-31")
    serie = pd.concat([pd.DataFrame({"unidade": u, "data": dias.strftime("%Y-%m-%d"),
                                     "n": rng.poisson(2.0, len(dias)), "frp": 10.0}) for u in UNIDADES[:3]])
    serie[serie["n"] > 0].to_csv(tmp_path / "serie.csv", index=False)
    (tmp_path / "oni.txt").write_text(" SEAS  YR   TOTAL   ANOM\n" + "".join(
        f"  {s} {a}  27.0  0.10\n" for a in range(2011, 2025) for s in mr.ESTACOES), encoding="utf-8")
    la, lo = h3.cell_to_latlng(CENTRO)
    (tmp_path / "clima").mkdir()
    for ano in range(2012, 2025):
        n = 366 if ano % 4 == 0 else 365
        pd.DataFrame({"LAT": [round(la * 2) / 2] * n, "LON": [round(lo / 0.625) * 0.625] * n, "YEAR": [ano] * n,
                      "DOY": range(1, n + 1), "PRECTOTCORR": rng.random(n) * 5}).to_parquet(
            tmp_path / "clima" / f"PRECTOTCORR_{ano}.parquet", index=False)
    monkeypatch.setattr(sys, "argv", ["modelo_risco.py", "--serie", str(tmp_path / "serie.csv"), "--oni",
                                      str(tmp_path / "oni.txt"), "--clima", str(tmp_path / "clima"),
                                      "--saida", str(tmp_path / "saida"), "--anos-teste", "2023", "--ano-final", "2024"])
    mr.main()
    medidas = pd.read_csv(tmp_path / "saida" / "medidas_por_ano.csv")
    assert set(medidas["conjunto"]) == {"fogo", "fogo+oni", "fogo+clima"}
    imp = pd.read_csv(tmp_path / "saida" / "importancia.csv")
    assert "chuva30" in set(imp["pista"]) and "oni" not in set(imp["pista"])


def test_linha_de_comando_monta_a_serie_dos_arquivos_anuais(tmp_path, monkeypatch):
    la, lo = h3.cell_to_latlng(CENTRO)
    bruto([(la, lo, "2020-08-01", "n", 5.0, 0)]).to_csv(tmp_path / "a.csv", index=False)
    bruto([(la, lo, "2021-08-01", "n", 5.0, 0), (la + 0.001, lo, "2021-08-01", "h", 2.0, 0)]).to_csv(tmp_path / "b.csv", index=False)
    monkeypatch.setattr(sys, "argv", ["modelo_risco.py", "--viirs", str(tmp_path / "a.csv"), str(tmp_path / "b.csv"),
                                      "--gravar-serie", str(tmp_path / "s" / "serie.parquet")])
    mr.main()
    s = pd.read_parquet(tmp_path / "s" / "serie.parquet").set_index("data")
    assert s.loc["2020-08-01", "n"] == 1 and s.loc["2021-08-01", "n"] == 2 and s.loc["2021-08-01", "frp"] == pytest.approx(7.0)


def test_anomalia_e_o_valor_menos_a_media_das_mesmas_semanas_em_anos_anteriores():
    semanas = semanas_de(2015, 2019)
    x = np.zeros((len(semanas), 2), np.float32)
    w = 52 * 2 + 10                                    # uma semana de 2017, com dois anos anteriores na série
    x[w - 52] = [10.0, 0.0]                            # a mesma semana em 2016
    x[w - 104] = [20.0, 0.0]                           # e em 2015
    x[w] = [50.0, 7.0]
    a = mr.anomalia(x)
    assert a[w, 0] == pytest.approx(50.0 - 15.0) and a[w, 1] == pytest.approx(7.0)
    assert np.isnan(a[10, 0])                          # primeiro ano: sem ano anterior, sem anomalia


def test_anomalia_nao_usa_semanas_futuras():
    rng = np.random.default_rng(4)
    x = rng.random((300, 3)).astype(np.float32)
    antes = mr.anomalia(x)
    x2 = x.copy()
    x2[200:] = 999
    depois = mr.anomalia(x2)
    assert np.array_equal(antes[:200], depois[:200], equal_nan=True)


def test_pistas_de_clima_trazem_a_anomalia_da_chuva_e_da_temperatura():
    semanas = semanas_de(2015, 2019)
    forma = (len(UNIDADES), N_DIAS)
    p = mr.pistas_clima({"PRECTOTCORR": np.full(forma, 2.0, np.float32), "T2M_MAX": np.full(forma, 30.0, np.float32),
                         "RH2M": np.full(forma, 50.0, np.float32), "WS2M": np.full(forma, 3.0, np.float32)}, semanas)
    assert {"chuva30_anom", "chuva90_anom", "tmax7_anom", "umid7_anom"} <= set(p)
    ultima = len(semanas) - 1
    assert p["chuva30_anom"][ultima, 0] == pytest.approx(0.0)         # clima constante: nenhuma anomalia


def test_medidas_comparam_modelo_regra_e_ingenua_com_o_mesmo_numero_de_alertas():
    y = np.array([1, 1, 0, 0, 0, 0, 0, 0], bool)
    p = np.array([0.9, 0.8, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1])           # o modelo acerta os dois
    critico = np.array([1, 0, 1, 0, 0, 0, 0, 0], bool)               # a regra dá 2 alertas e acerta 1
    score = np.array([0, 0, 0, 0, 0, 0, 9, 8], float)                # a ingênua erra os dois
    med = mr.medidas_ano(y, p, critico, score)
    assert med["alertas"] == 2
    assert med["acerto_modelo"] == 1.0 and med["acerto_regra"] == 0.5 and med["acerto_ingenua"] == 0.0
    assert med["ganho_sobre_regra"] == pytest.approx(0.5) and med["auc"] == 1.0


def test_medidas_comparam_tambem_com_a_regra_de_piso_continuo_no_numero_de_alertas_dela():
    """A regra do piso contínuo (escolhida em 15/11/2026) dá menos alertas; o modelo e a ingênua usam o mesmo número."""
    y = np.array([1, 1, 1, 0, 0, 0, 0, 0], bool)
    p = np.array([0.9, 0.8, 0.7, 0.1, 0.1, 0.1, 0.1, 0.1])
    critico = np.array([1, 0, 0, 1, 1, 0, 0, 0], bool)               # regra atual: 3 alertas, acerta 1
    continua = np.array([1, 0, 0, 0, 0, 0, 0, 0], bool)              # piso contínuo: 1 alerta, acerta 1
    score = np.array([0, 0, 0, 0, 0, 0, 9, 8], float)
    med = mr.medidas_ano(y, p, critico, score, continua)
    assert med["alertas"] == 3 and med["alertas_continua"] == 1
    assert med["acerto_regra_continua"] == 1.0 and med["acerto_modelo_k_continua"] == 1.0
    assert med["acerto_ingenua_k_continua"] == 0.0
    assert med["ganho_sobre_regra_continua"] == pytest.approx(0.0)
    assert "acerto_regra_continua" not in mr.medidas_ano(y, p, critico, score)   # sem a regra, as colunas não existem


def test_validacao_em_avanco_repassa_a_regra_de_piso_continuo():
    semanas, pistas, gab, critico, score = dados_com_sinal_plantado()
    continua = critico & (score > np.median(score))
    r = mr.validar_em_avanco(pistas, gab, semanas, critico, score, anos_teste=[2019], critico_continuo=continua)
    assert {"acerto_regra_continua", "ganho_sobre_regra_continua"} <= set(r.columns)


def semanas_de(ano_ini, ano_fim):
    t, fim = date(ano_ini, 1, 1), date(ano_fim, 12, 14)
    t += timedelta((6 - t.weekday()) % 7)
    return [t + timedelta(weeks=w) for w in range((fim - t).days // 7 + 1)]


def dados_com_sinal_plantado(semente=3, unidades=40):
    """INVENTADO: o gabarito depende de uma pista (`seca`) que a regra e a ingênua não enxergam."""
    rng = np.random.default_rng(semente)
    semanas = semanas_de(2015, 2020)
    forma = (len(semanas), unidades)
    seca = rng.random(forma).astype(np.float32)
    ruido = rng.random(forma).astype(np.float32)
    gab = rng.random(forma) < 0.02 + 0.5 * (seca > 0.8)
    return semanas, {"seca": seca, "ruido": ruido}, gab, rng.random(forma) < 0.1, rng.random(forma)


def test_validacao_em_avanco_treina_so_com_anos_anteriores(monkeypatch):
    semanas, pistas, gab, critico, score = dados_com_sinal_plantado()
    vistos = []
    original = mr.ajustar

    def espiao(x, y, categoricas, semente):
        vistos.append(len(y))
        return original(x, y, categoricas, semente)

    monkeypatch.setattr(mr, "ajustar", espiao)
    r = mr.validar_em_avanco(pistas, gab, semanas, critico, score, anos_teste=[2018, 2019])
    por_ano = {a: sum(1 for t in semanas if (t + timedelta(bt.JANELA_GABARITO)).year < a) for a in (2018, 2019)}
    assert vistos == [por_ano[2018] * 40, por_ano[2019] * 40]        # só semanas cujo gabarito termina antes do ano
    assert list(r["ano"]) == [2018, 2019]


def test_validacao_em_avanco_acha_o_sinal_plantado_e_ganha_da_regra():
    semanas, pistas, gab, critico, score = dados_com_sinal_plantado()
    r = mr.validar_em_avanco(pistas, gab, semanas, critico, score, anos_teste=[2019, 2020])
    assert (r["acerto_modelo"] > r["acerto_regra"] + 0.2).all()      # plantado: ~52% com a seca, ~7% sem ela
    assert (r["auc"] > 0.7).all()


def test_ponta_a_ponta_pela_linha_de_comando(tmp_path, monkeypatch):
    rng = np.random.default_rng(1)
    dias = pd.date_range("2012-02-01", "2024-12-31")
    linhas = []
    for u in UNIDADES[:4]:
        base = 3 + 3 * np.sin((dias.day_of_year.to_numpy() - 150) / 58.0)      # temporada de fogo no meio do ano
        n = rng.poisson(np.clip(base, 0.05, None))
        linhas.append(pd.DataFrame({"unidade": u, "data": dias.strftime("%Y-%m-%d"), "n": n, "frp": n * 10.0}))
    serie = pd.concat(linhas)
    serie[serie["n"] > 0].to_csv(tmp_path / "serie.csv", index=False)
    (tmp_path / "oni.txt").write_text(" SEAS  YR   TOTAL   ANOM\n" + "".join(
        f"  {s} {a}  27.0  {0.1 * (a - 2018):.2f}\n" for a in range(2011, 2025) for s in mr.ESTACOES), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["modelo_risco.py", "--serie", str(tmp_path / "serie.csv"), "--oni",
                                      str(tmp_path / "oni.txt"), "--saida", str(tmp_path / "saida"),
                                      "--anos-teste", "2022", "2023", "--ano-final", "2024"])
    mr.main()
    medidas = pd.read_csv(tmp_path / "saida" / "medidas_por_ano.csv")
    assert set(medidas["conjunto"]) == {"fogo", "fogo+oni"}
    assert set(medidas["ano"]) == {2022, 2023, 2024}
    assert set(medidas.loc[medidas["ano"] == 2024, "papel"]) == {"final"}
    assert (tmp_path / "saida" / "importancia.csv").exists() and (tmp_path / "saida" / "relatorio.txt").exists()
