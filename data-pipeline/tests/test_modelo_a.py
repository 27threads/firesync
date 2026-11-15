"""Modelo A (RFC 0002): a chance de o MODIS (Aqua) ver um fogo que o VIIRS (S-NPP) viu. DADOS INVENTADOS.

Nenhum número aqui é dado real do FIRMS. Os testes plantam uma chance de detecção conhecida e conferem se o código a
recupera (docs/testes.md, regras 1 e 5).
"""
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

from harmonizacao import modelo_a as m

KM_EM_GRAUS = 1 / 111.0  # INVENTADO para os testes: 1 km de latitude é cerca de 0,009 grau


def aqua_prep(linhas):
    """Fogos do Aqua já limpos e preparados: (lat, lon, data, periodo, minuto, scan, track)."""
    return pd.DataFrame(linhas, columns=["latitude", "longitude", "acq_date", "daynight", "minuto", "scan", "track"])


def snpp_prep(linhas):
    return pd.DataFrame(linhas, columns=["latitude", "longitude", "acq_date", "daynight", "minuto"])


AQUA = aqua_prep([(-10.0, -60.0, "2024-08-01", "D", 1080, 1.0, 1.0)])  # pixel de 1 km


def parear(snpp_linhas, janela=10, aqua=AQUA):
    return m.parear(snpp_prep(snpp_linhas), aqua, janela).iloc[0]


def test_fogo_dentro_do_pixel_do_modis_e_visto():
    # raio de "viu": metade do pixel do MODIS (0,5 km) + metade do pixel do VIIRS (0,19 km)
    r = parear([(-10.0 - 0.4 * KM_EM_GRAUS, -60.0, "2024-08-01", "D", 1085)])
    assert bool(r["olhando"]) and bool(r["viu"])


def test_fogo_a_dez_km_com_o_modis_olhando_nao_e_visto():
    r = parear([(-10.0 - 10 * KM_EM_GRAUS, -60.0, "2024-08-01", "D", 1085)])
    assert bool(r["olhando"]) and not bool(r["viu"])


def test_fogo_a_oitenta_km_nao_estava_sendo_olhado():
    r = parear([(-10.0 - 80 * KM_EM_GRAUS, -60.0, "2024-08-01", "D", 1085)])
    assert not bool(r["olhando"]) and not bool(r["viu"])


def test_janela_de_horario_separa_passagens_diferentes():
    fogo = [(-10.0, -60.0, "2024-08-01", "D", 1080 + 44)]  # o Aqua de 2024 passa ~44 min depois (dado real de 2024)
    assert not bool(parear(fogo, janela=10)["olhando"])
    assert bool(parear(fogo, janela=90)["viu"])


def test_outra_data_ou_outro_periodo_nao_pareia():
    assert not bool(parear([(-10.0, -60.0, "2024-08-02", "D", 1080)])["olhando"])
    assert not bool(parear([(-10.0, -60.0, "2024-08-01", "N", 1080)])["olhando"])


def test_pixel_grande_do_modis_cobre_um_fogo_que_o_pixel_pequeno_nao_cobriria():
    grande = aqua_prep([(-10.0, -60.0, "2024-08-01", "D", 1080, 4.0, 2.0)])  # pixel de borda de faixa
    fogo = [(-10.0 - 1.8 * KM_EM_GRAUS, -60.0, "2024-08-01", "D", 1080)]
    assert bool(parear(fogo, aqua=grande)["viu"])
    assert not bool(parear(fogo)["viu"])


def test_tamanho_mediano_do_pixel_do_modis_na_passagem():
    aqua = aqua_prep([(-10.0, -60.0, "2024-08-01", "D", 1080, 1.0, 1.0),
                      (-10.0, -60.0 + 5 * KM_EM_GRAUS, "2024-08-01", "D", 1080, 3.0, 1.0),
                      (-10.0, -60.0 + 8 * KM_EM_GRAUS, "2024-08-01", "D", 1080, 5.0, 1.0)])
    assert parear([(-10.0, -60.0, "2024-08-01", "D", 1080)], aqua=aqua)["modis_scan_mediano"] == pytest.approx(3.0)


def test_sorteio_de_blocos_mantem_cada_bloco_inteiro_de_um_lado_e_e_reproduzivel():
    rng = np.random.default_rng(0)
    pontos = pd.DataFrame({"latitude": rng.uniform(-12, -2, 3000), "longitude": rng.uniform(-62, -52, 3000)})
    a = m.atribuir_bloco(pontos, 4)
    teste = m.sortear_blocos(a["bloco"], semente=7)
    assert teste == m.sortear_blocos(a["bloco"], semente=7)           # mesma semente, mesmo sorteio
    assert teste != m.sortear_blocos(a["bloco"], semente=8)
    grupo = a["bloco"].isin(teste)
    assert (a.groupby("bloco")["bloco"].apply(lambda b: grupo[b.index].nunique()) == 1).all()  # sem bloco dividido
    assert 0.3 < grupo.mean() < 0.7                                   # cerca de metade dos fogos de cada lado


def dados_com_chance_plantada(n=20000, semente=1):
    """Fogos INVENTADOS: a chance de o MODIS ver cresce com a potência (FRP) e é menor à noite."""
    rng = np.random.default_rng(semente)
    frp = rng.lognormal(mean=1.5, sigma=1.0, size=n)
    noite = rng.random(n) < 0.3
    p_real = 1 / (1 + np.exp(-(1.2 * np.log(frp) - 3.0 - 0.8 * noite)))
    return pd.DataFrame({
        "frp": frp, "bright_ti4": 300 + 10 * np.log(frp), "high_conf": frp > 40, "daynight": np.where(noite, "N", "D"),
        "mes": rng.integers(1, 13, n), "bioma": rng.choice(["Amazônia", "Cerrado"], n),
        "modis_scan_mediano": rng.uniform(1, 3, n), "viu": rng.random(n) < p_real, "p_real": p_real})


def test_tabela_por_faixa_recupera_a_chance_plantada():
    d = dados_com_chance_plantada()
    d["periodo"] = d["daynight"]
    d["faixa"] = m.faixa_frp(d["frp"])
    tabela = m.ajustar_tabela(d, minimo=30)
    p = m.prever_tabela(tabela, d)
    assert abs(p.mean() - d["viu"].mean()) < 0.01                    # calibrada na média
    assert np.corrcoef(p, d["p_real"])[0, 1] > 0.9                   # acompanha a chance verdadeira


def test_tabela_usa_o_nivel_mais_geral_quando_a_combinacao_tem_poucos_fogos():
    d = dados_com_chance_plantada(n=3000)
    d["periodo"] = d["daynight"]
    d["faixa"] = m.faixa_frp(d["frp"])
    tabela = m.ajustar_tabela(d, minimo=30)
    novo = pd.DataFrame({"faixa": m.faixa_frp(pd.Series([3.0])), "periodo": ["D"], "bioma": ["Pampa"]})  # bioma nunca visto
    assert 0 < float(m.prever_tabela(tabela, novo).iloc[0]) < 1


def test_gradient_boosting_separa_e_calibra_nos_blocos_de_teste():
    d = dados_com_chance_plantada(n=30000)
    treino, teste = d.iloc[:20000].copy(), d.iloc[20000:].copy()
    modelo = m.ajustar_boosting(treino, ["Amazônia", "Cerrado"], semente=3)
    p = m.prever_boosting(modelo, teste, ["Amazônia", "Cerrado"])
    med = m.medir(teste["viu"], p)
    teto = m.medir(teste["viu"], teste["p_real"])["auc"]          # o melhor possível: conhece a chance verdadeira
    assert med["auc"] > teto - 0.03                               # o modelo chega perto do teto, que tem sorteio embutido
    assert abs(med["taxa_prevista"] - med["taxa_observada"]) < 0.02


def test_medidas_sem_as_duas_classes_nao_quebram():
    med = m.medir(pd.Series([True, True, True]), pd.Series([0.5, 0.6, 0.7]))
    assert np.isnan(med["auc"]) and med["taxa_observada"] == 1.0


def test_prova_cruzada_recupera_o_fator_conhecido():
    """Se cada fogo do VIIRS tem 25% de chance de ser visto, o fator (VIIRS por foco do MODIS) é 4."""
    n = 4000
    snpp = pd.DataFrame({"bioma": ["X"] * n, "periodo": ["D"] * n, "mes": [8] * n, "p": [0.25] * n})
    aqua = pd.DataFrame({"bioma": ["X"] * (n // 4), "periodo": ["D"] * (n // 4), "mes": [8] * (n // 4)})
    prova = m.prova_cruzada(snpp, aqua, "p", ["bioma", "periodo"], snpp)
    assert prova["fator_modelo"].iloc[0] == pytest.approx(4.0)
    assert prova["fator_contagens"].iloc[0] == pytest.approx(4.0)
    assert prova["razao_modelo_contagens"].iloc[0] == pytest.approx(1.0)


def test_prova_cruzada_conta_o_total_do_viirs_pelas_mesmas_chaves():
    """Bug da revisão do PR 53: o total do VIIRS (com os fogos fora da área olhada) vinha do ano inteiro nas linhas
    mensais e não entrava em nenhuma conta. Aqui há fogos fora da área olhada e dois meses com totais diferentes."""
    olhados = pd.DataFrame({"bioma": ["X"] * 300, "periodo": ["D"] * 300, "mes": [8] * 200 + [9] * 100, "p": [0.5] * 300})
    todos = pd.DataFrame({"bioma": ["X"] * 700, "periodo": ["D"] * 700, "mes": [8] * 400 + [9] * 300})
    aqua = pd.DataFrame({"bioma": ["X"] * 150, "periodo": ["D"] * 150, "mes": [8] * 100 + [9] * 50})
    mensal = m.prova_cruzada(olhados, aqua, "p", ["bioma", "periodo", "mes"], todos).set_index("mes")
    assert mensal.loc[8, "n_viirs_total"] == 400 and mensal.loc[9, "n_viirs_total"] == 300   # o total é do mês
    assert mensal.loc[8, "fator_contagens"] == pytest.approx(2.0)            # só os olhados: 200 / 100
    assert mensal.loc[8, "fator_contagens_total"] == pytest.approx(4.0)      # todos os fogos do VIIRS: 400 / 100
    assert mensal.loc[9, "fator_contagens_total"] == pytest.approx(6.0)      # 300 / 50
    anual = m.prova_cruzada(olhados, aqua, "p", ["bioma", "periodo"], todos)
    assert anual["n_viirs_total"].iloc[0] == 700 and anual["fator_contagens_total"].iloc[0] == pytest.approx(700 / 150)


def test_limpeza_usa_as_regras_da_frente_a():
    """Terra sai, type diferente de 0 sai, FRP zero sai e confiança baixa sai (as mesmas regras do pipeline.py)."""
    def linha(sat, tipo, frp, conf):
        return {"latitude": -10.0, "longitude": -60.0, "brightness": 330.0, "bright_t31": 290.0, "scan": 1.0, "track": 1.0,
                "acq_date": "2024-08-01", "acq_time": "1800", "satellite": sat, "confidence": conf, "version": "61.03",
                "frp": frp, "daynight": "D", "type": tipo}
    df = pd.DataFrame([linha("Aqua", 0, 20.0, "80"), linha("Terra", 0, 20.0, "80"), linha("Aqua", 2, 20.0, "80"),
                       linha("Aqua", 0, 0.0, "80"), linha("Aqua", 0, 20.0, "10")])
    df.loc[1:, "latitude"] += np.arange(1, 5) * 0.01  # evita que a regra de duplicatas esconda o motivo da saída
    assert len(m.limpar_aqua(df)) == 1


def raw_aqua_e_snpp():
    """Arquivos brutos INVENTADOS no formato do Archive Download: o MODIS vê só os fogos fortes do VIIRS."""
    rng = np.random.default_rng(5)
    n = 6000
    frp = rng.lognormal(1.5, 1.0, n)
    lat = rng.uniform(-9.9, -9.1, n)
    lon = rng.uniform(-59.9, -59.1, n)
    dia = rng.integers(1, 20, n)
    visto = rng.random(n) < 1 / (1 + np.exp(-(1.2 * np.log(frp) - 3.0)))
    comum = {"acq_time": "1800", "confidence": "n", "daynight": "D", "type": 0}
    snpp = pd.DataFrame({"latitude": lat, "longitude": lon, "brightness": 330.0, "bright_t31": 290.0, "scan": 0.4,
                         "track": 0.4, "acq_date": [f"2024-08-{d:02d}" for d in dia], "satellite": "N",
                         "version": "2", "frp": frp, **comum})
    aqua = pd.DataFrame({"latitude": lat[visto], "longitude": lon[visto], "brightness": 330.0, "bright_t31": 290.0,
                         "scan": 1.0, "track": 1.0, "acq_date": [f"2024-08-{d:02d}" for d in dia[visto]],
                         "satellite": "Aqua", "version": "61.03", "frp": frp[visto] * 4, **{**comum, "confidence": "80"}})
    return aqua, snpp


def biomas_de_teste():
    return gpd.GeoDataFrame({"CD_Bioma": [1, 3]}, geometry=[box(-60.0, -10.0, -59.5, -9.0), box(-59.5, -10.0, -59.0, -9.0)],
                            crs=4326)


def test_ponta_a_ponta_com_dados_inventados_recupera_que_so_fogo_forte_e_visto():
    aqua, snpp = raw_aqua_e_snpp()
    r = m.executar(aqua, snpp, m.preparar_biomas(biomas_de_teste()), janela=10, semente=2, bloco_res=4)
    curva = r["curva"].query("bioma == 'todos'")
    fraca = curva[curva["faixa"] == "0-2"]["taxa_viu"].mean()
    forte = curva[curva["faixa"] == "25+"]["taxa_viu"].mean()
    # plantado: a chance vai de ~5% (abaixo de 2 MW) a ~75% em média (25 MW ou mais)
    assert 0.65 < forte < 0.85 and fraca < 0.15 and forte > 4 * fraca
    medidas = r["medidas"].set_index("modelo")
    assert medidas.loc["boosting", "auc"] > 0.7                       # os dados inventados têm sorteio, o teto é ~0,77
    assert medidas.loc["boosting", "auc"] > medidas.loc["tabela", "auc"] - 0.02
    assert medidas.loc["tabela", "auc"] > medidas.loc["referencia", "auc"] + 0.15   # a referência é a taxa única (AUC 0,5)
    assert {"treino", "teste"} == set(r["grupos"]["grupo"])
    assert "janela" in r["relatorio"]


def raw_ano(ano, forca=1.0, semente=0, n=5000):
    """Arquivos brutos INVENTADOS de um ano: a chance de o MODIS ver cresce com a potência, vezes `forca` (deriva)."""
    rng = np.random.default_rng(semente + ano)
    frp = rng.lognormal(1.5, 1.0, n)
    lat, lon = rng.uniform(-9.9, -9.1, n), rng.uniform(-59.9, -59.1, n)
    dia = rng.integers(1, 20, n)
    visto = rng.random(n) < forca / (1 + np.exp(-(1.2 * np.log(frp) - 3.0)))
    comum = {"acq_time": "1800", "confidence": "n", "daynight": "D", "type": 0}
    data = [f"{ano}-08-{d:02d}" for d in dia]
    snpp = pd.DataFrame({"latitude": lat, "longitude": lon, "brightness": 330.0, "bright_t31": 290.0, "scan": 0.4,
                         "track": 0.4, "acq_date": data, "satellite": "N", "version": "2", "frp": frp, **comum})
    aqua = pd.DataFrame({"latitude": lat[visto], "longitude": lon[visto], "brightness": 330.0, "bright_t31": 290.0,
                         "scan": 1.0, "track": 1.0, "acq_date": [data[i] for i in np.where(visto)[0]],
                         "satellite": "Aqua", "version": "61.03", "frp": frp[visto] * 4, **{**comum, "confidence": "80"}})
    return aqua, snpp


def pares_por_ano(anos_e_forca, biomas):
    return {ano: m.preparar_ano(*raw_ano(ano, forca), biomas, janela=10) for ano, forca in anos_e_forca.items()}


def test_preparar_ano_guarda_so_os_fogos_olhados_e_os_totais():
    biomas = m.preparar_biomas(biomas_de_teste())
    r = m.preparar_ano(*raw_ano(2019), biomas, janela=10)
    assert r["totais"]["ano"] == 2019 and r["totais"]["snpp"] > 0 and r["totais"]["aqua"] > 0
    assert r["totais"]["olhando"] == len(r["olhados"]) and r["totais"]["janela"] == 10
    assert r["olhados"]["olhando"].all() and {"viu", "frp", "bioma", "bright_ti4"} <= set(r["olhados"].columns)
    assert set(r["olhados"]["acq_date"].str[:4]) == {"2019"}


def test_temporal_treina_so_nos_anos_de_treino_e_mede_cada_ano_de_teste():
    biomas = m.preparar_biomas(biomas_de_teste())
    pares = pares_por_ano({2019: 1.0, 2020: 1.0, 2021: 1.0, 2022: 1.0, 2023: 1.0}, biomas)
    r = m.executar_temporal(pares, [2019, 2020, 2021], [2022, 2023], biomas)
    assert list(r["medidas"]["ano"].unique()) == [2022, 2023]
    assert set(r["medidas"]["modelo"]) == {"referencia", "tabela", "boosting"}
    assert "2019" in r["relatorio"] and "2022" in r["relatorio"]
    boosting = r["medidas"].query("modelo == 'boosting'").set_index("ano")
    assert (boosting["auc"] > 0.7).all()                            # sem deriva, o modelo vale nos anos que não viu
    assert (boosting["taxa_prevista"] - boosting["taxa_observada"]).abs().max() < 0.03


def test_temporal_mostra_a_deriva_quando_o_modis_passa_a_ver_menos():
    """Plantado: em 2023 o MODIS vê só 60% do que via. A chance prevista fica acima da observada naquele ano."""
    biomas = m.preparar_biomas(biomas_de_teste())
    pares = pares_por_ano({2019: 1.0, 2020: 1.0, 2022: 1.0, 2023: 0.6}, biomas)
    r = m.executar_temporal(pares, [2019, 2020], [2022, 2023], biomas)
    b = r["medidas"].query("modelo == 'boosting'").set_index("ano")
    assert abs(b.loc[2022, "taxa_prevista"] - b.loc[2022, "taxa_observada"]) < 0.03
    assert b.loc[2023, "taxa_prevista"] - b.loc[2023, "taxa_observada"] > 0.08
    curva = r["curva_por_ano"].query("bioma == 'todos' and faixa == '25+'").set_index("ano")
    assert curva.loc[2023, "taxa_viu"] < curva.loc[2022, "taxa_viu"] - 0.1


def test_temporal_recusa_ano_de_teste_que_tambem_e_de_treino_ou_sem_dados():
    biomas = m.preparar_biomas(biomas_de_teste())
    pares = pares_por_ano({2019: 1.0, 2020: 1.0}, biomas)
    with pytest.raises(ValueError, match="treino e teste"):
        m.executar_temporal(pares, [2019, 2020], [2020], biomas)
    with pytest.raises(ValueError, match="sem dados"):
        m.executar_temporal(pares, [2019], [2021], biomas)


def csvs_por_ano(pasta, anos):
    for ano in anos:
        aqua, snpp = raw_ano(ano)
        aqua.to_csv(pasta / f"modis_{ano}_Brazil.csv", index=False)
        snpp.to_csv(pasta / f"viirs-snpp_{ano}_Brazil.csv", index=False)
    biomas_de_teste().to_file(pasta / "biomas.geojson", driver="GeoJSON")


def test_linha_de_comando_temporal_le_a_pasta_por_ano_e_grava_os_arquivos(tmp_path, monkeypatch):
    csvs_por_ano(tmp_path, (2019, 2020, 2021))
    monkeypatch.setattr(sys, "argv", ["modelo_a.py", "--pasta", str(tmp_path), "--treino", "2019", "2020", "--teste", "2021",
                                      "--biomas", str(tmp_path / "biomas.geojson"), "--saida", str(tmp_path / "saida"),
                                      "--janela", "10"])
    m.main()
    for nome in ("medidas_por_ano.csv", "curva_por_ano.csv", "totais_por_ano.csv", "relatorio_temporal.txt"):
        assert (tmp_path / "saida" / nome).exists(), nome


def test_linha_de_comando_temporal_reaproveita_o_cache_dos_pares(tmp_path, monkeypatch):
    csvs_por_ano(tmp_path, (2019, 2020))
    monkeypatch.setattr(sys, "argv", ["modelo_a.py", "--pasta", str(tmp_path), "--treino", "2019", "--teste", "2020",
                                      "--biomas", str(tmp_path / "biomas.geojson"), "--saida", str(tmp_path / "saida"),
                                      "--janela", "10", "--cache", str(tmp_path / "cache")])
    m.main()
    assert {p.name for p in (tmp_path / "cache").iterdir()} == {"pares_2019_j10.parquet", "pares_2020_j10.parquet"}
    primeiro = (tmp_path / "saida" / "medidas_por_ano.csv").read_text()
    for ano in (2019, 2020):                                       # sem os CSV, só o cache: o resultado sai igual
        (tmp_path / f"modis_{ano}_Brazil.csv").unlink()
        (tmp_path / f"viirs-snpp_{ano}_Brazil.csv").unlink()
    m.main()
    assert (tmp_path / "saida" / "medidas_por_ano.csv").read_text() == primeiro


def test_pares_do_ano_acha_os_arquivos_com_os_nomes_que_o_pipeline_baixa(tmp_path):
    """Revisão do PR #87: `pipeline.py download` grava modis_{ano}.csv e viirs-snpp_{ano}.csv (data/raw/country/)."""
    aqua, snpp = raw_ano(2019)
    aqua.to_csv(tmp_path / "modis_2019.csv", index=False)
    snpp.to_csv(tmp_path / "viirs-snpp_2019.csv", index=False)
    r = m.pares_do_ano(tmp_path, 2019, m.preparar_biomas(biomas_de_teste()), 10)
    assert r["totais"]["ano"] == 2019 and r["totais"]["olhando"] > 0
    with pytest.raises(FileNotFoundError, match="modis_2020"):
        m.pares_do_ano(tmp_path, 2020, m.preparar_biomas(biomas_de_teste()), 10)


def test_o_cache_dos_pares_e_refeito_quando_os_biomas_ou_a_janela_mudam(tmp_path, monkeypatch):
    """Revisão do PR #87: o cache só vale para os mesmos biomas, a mesma janela e as mesmas regras de limpeza."""
    csvs_por_ano(tmp_path, (2019,))
    chamadas = []
    original = m.preparar_ano
    monkeypatch.setattr(m, "preparar_ano", lambda *a, **k: chamadas.append(1) or original(*a, **k))
    biomas = m.preparar_biomas(biomas_de_teste())
    outros = m.preparar_biomas(gpd.GeoDataFrame({"CD_Bioma": [1, 3]}, geometry=[box(-60.0, -10.0, -59.2, -9.0), box(-59.2, -10.0, -59.0, -9.0)], crs=4326))
    cache = tmp_path / "cache"
    m.pares_do_ano(tmp_path, 2019, biomas, 10, cache)
    m.pares_do_ano(tmp_path, 2019, biomas, 10, cache)
    assert len(chamadas) == 1                                       # mesmos biomas e janela: reaproveita
    m.pares_do_ano(tmp_path, 2019, outros, 10, cache)
    assert len(chamadas) == 2                                       # biomas diferentes: refaz, sem aviso silencioso
    m.pares_do_ano(tmp_path, 2019, outros, 10, cache)
    assert len(chamadas) == 2                                       # e o cache novo passa a valer
    monkeypatch.setattr(m, "OLHANDO_KM", 30.0)                      # uma regra do pareamento mudou
    m.pares_do_ano(tmp_path, 2019, outros, 10, cache)
    assert len(chamadas) == 3


def test_linha_de_comando_grava_os_arquivos(tmp_path, monkeypatch):
    aqua, snpp = raw_aqua_e_snpp()
    aqua.to_csv(tmp_path / "aqua.csv", index=False)
    snpp.to_csv(tmp_path / "snpp.csv", index=False)
    biomas_de_teste().to_file(tmp_path / "biomas.geojson", driver="GeoJSON")
    monkeypatch.setattr(sys, "argv", ["modelo_a.py", "--modis", str(tmp_path / "aqua.csv"), "--viirs", str(tmp_path / "snpp.csv"),
                                      "--biomas", str(tmp_path / "biomas.geojson"), "--saida", str(tmp_path / "saida"),
                                      "--janela", "10"])
    m.main()
    for nome in ("curva_deteccao.csv", "medidas.csv", "calibracao.csv", "prova_cruzada.csv", "relatorio_modelo_a.txt"):
        assert (tmp_path / "saida" / nome).exists(), nome
