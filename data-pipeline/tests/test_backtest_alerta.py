"""Backtest do alerta (RFC 0001), sem banco. DADOS INVENTADOS em todos os testes."""
import random
from datetime import date, timedelta

import h3
import numpy as np
import pandas as pd
import pytest

from validacao import backtest_alerta as bt

REGRA = {
    "baseline": {"window_days": 7, "neighbor_days": 15, "reference_years_from": 2012},
    "levels": {"critical": {"min_ratio_to_median": 2.0, "min_detections": 10, "trend_days": 3,
                            "requires_rising_trend": True},
               "attention": {"above_percentile": 75}},
}


def dia(d):
    return (d - bt.INICIO).days


def test_celula_mae_res4_pela_conta_de_bits_bate_com_o_h3():
    rnd = random.Random(1)
    for _ in range(200):
        c = h3.latlng_to_cell(rnd.uniform(-33, 5), rnd.uniform(-74, -34), 6)
        i = h3.str_to_int(c)
        assert (i & ~bt.MASCARA_RES) | bt.RES4 | bt.DIGITOS_5_6 == h3.str_to_int(h3.cell_to_parent(c, 4))


def test_matriz_poe_zero_no_dia_sem_linha_e_soma_repetidos():
    df = pd.DataFrame({"unidade": [7, 7, 9], "data": [date(2012, 2, 3), date(2012, 2, 3), date(2012, 2, 5)],
                       "n": [2, 3, 4]})
    unidades, m = bt.matriz(df)
    assert list(unidades) == [7, 9]
    assert m.shape == (2, dia(bt.FIM) + 1)
    assert m[0, 2] == 5 and m[1, 4] == 4 and m.sum() == 9


def test_somas_moveis_e_nan_quando_a_janela_sai_do_comeco():
    s = bt.somas_moveis(np.array([[1, 2, 3, 4]], np.float32), 3)
    assert np.isnan(s[0, :2]).all()
    assert s[0, 2:].tolist() == [6, 9]


def test_normal_deixa_o_proprio_ano_de_fora():
    t = date(2018, 8, 5)
    idx = bt.indices_normal(t, 15, range(2012, 2025), t.year)
    anos = {(bt.INICIO + timedelta(days=int(i))).year for i in idx}
    assert 2018 not in anos and anos == set(range(2012, 2025)) - {2018}
    assert len(idx) == 12 * 31


def test_gabarito_nao_se_sobrepoe_a_semana_avaliada():
    """Pedido do Mateus (PR #42): fogo só em t-6..t e zero depois tem que dar "sem muito fogo"."""
    t = date(2018, 8, 5)  # domingo
    m = np.zeros((1, dia(bt.FIM) + 1), np.float32)
    m[0, dia(t) - 6: dia(t) + 1] = [10, 20, 30, 40, 50, 60, 70]  # sobe nos últimos 3 dias
    semanas, a = bt.avaliar(m, REGRA)
    w = semanas.index(t)
    assert bt.nivel(a, 2.0, True, 75, 10)[w, 0] == 2   # o nível vê o fogo
    assert not bt.gabarito(a, 90, 10)[w, 0]                             # o gabarito não vê
    # e o fogo na semana seguinte entra no gabarito da semana avaliada
    m[0, dia(t) + 1: dia(t) + 8] = 30
    _, a = bt.avaliar(m, REGRA)
    assert bt.gabarito(a, 90, 10)[w, 0]


def test_mediana_zero_usa_o_piso_e_tendencia_desligada_ignora_a_queda():
    a = {"s7": np.array([[9.0, 10.0, 10.0]]), "med7": np.zeros((1, 3)), "p75": np.zeros((1, 3)),
         "p90": np.zeros((1, 3)), "sobe": np.array([[True, True, False]])}
    assert bt.nivel(a, 2.0, True, 75, 10).tolist() == [[1, 2, 1]]
    assert bt.nivel(a, 2.0, False, 75, 10).tolist() == [[1, 2, 2]]


def test_ganho_zero_quando_a_regra_e_a_propria_ingenua():
    rnd = np.random.default_rng(3)
    score = rnd.random((50, 20))
    gab = rnd.random((50, 20)) < 0.3
    niv = np.where(score > np.quantile(score, 0.9), 2, 0)
    anos = np.repeat(np.arange(2013, 2023), 5)[:, None] * np.ones((1, 20), int)
    r = bt.medidas(niv, gab, score, anos)
    assert r["freq_critico"] == pytest.approx(0.1)
    assert r["ganho"] == pytest.approx(0)


def test_ganho_positivo_quando_a_regra_ve_o_que_a_ingenua_nao_ve():
    rnd = np.random.default_rng(4)
    gab = rnd.random((60, 100)) < 0.2
    niv = np.where(gab & (rnd.random(gab.shape) < 0.5), 2, 0)   # Crítico só antes de muito fogo
    score = rnd.random(gab.shape)                               # a ingênua não sabe nada
    anos = np.repeat(np.arange(2013, 2025), 5)[:, None] * np.ones((1, 100), int)
    r = bt.medidas(niv, gab, score, anos)
    assert r["acerto"] == 1 and r["ganho"] > 0.5
    assert r["anos_com_ganho_positivo"] == 12
    assert r["cobertura_critico"] == pytest.approx(0.5, abs=0.15)
    assert r["prevalencia_gabarito"] == pytest.approx(0.2, abs=0.02)


def test_evento_sem_fonte_e_recusado(tmp_path):
    p = tmp_path / "eventos.csv"
    p.write_text("nome,regiao,inicio,fim,fonte_url,fonte_descricao\n"
                 "Com fonte,Pantanal,2020-07-01,2020-10-31,https://exemplo.gov.br,x\n"
                 "Sem fonte,Pantanal,2024-06-01,2024-06-30,,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Sem fonte"):
        bt.ler_eventos(p)


def test_antecedencia_conta_semanas_entre_o_primeiro_alerta_e_o_inicio():
    inicio = date(2020, 7, 5)
    semanas = [inicio + timedelta(weeks=i) for i in range(-8, 4)]
    niv = np.array([[0], [0], [0], [0], [0], [1], [2], [2], [2], [2], [2], [2]])
    a = {"s7": np.ones((12, 1)), "med7": np.ones((12, 1))}
    ev = pd.DataFrame({"nome": ["X"], "regiao": ["Pantanal"], "inicio": [pd.Timestamp(inicio)],
                       "fim": [pd.Timestamp(inicio + timedelta(weeks=3))]})
    linhas = bt.eventos(ev, np.array(["Pantanal"]), semanas, a, niv)
    assert len(linhas) == 12
    assert set(linhas["antecedencia_semanas"]) == {3}


def test_normal_do_gabarito_nao_vaza_em_dezembro():
    """Issue #59, item 1: com t no fim de dezembro, t+14 cai no ano seguinte, e esse ano tem que sair do normal."""
    t = date(2018, 12, 23)
    for i in bt.indices_gabarito(t, 15, range(2012, 2025)):
        assert i < dia(t) + 1 or i - 13 > dia(t) + 14   # janela de 14 dias de referência fora de t+1..t+14


def test_piso_continuo_tira_o_degrau_da_mediana_baixa():
    """Issue #59, item 2: com mediana 1 e razão 2, bastavam 2 detecções; com o piso contínuo, precisa de 10."""
    a = {"s7": np.array([[2.0, 10.0]]), "med7": np.ones((1, 2)), "p75": np.full((1, 2), 99.0),
         "p90": np.full((1, 2), 99.0), "sobe": np.ones((1, 2), bool)}
    assert bt.nivel(a, 2.0, True, 75, 10, piso_continuo=False).tolist() == [[2, 2]]
    assert bt.nivel(a, 2.0, True, 75, 10, piso_continuo=True).tolist() == [[0, 2]]


def test_nivel_da_regra_usa_o_piso_continuo_da_v1():
    """Issue #66, item 5: os eventos conhecidos usavam o piso só na mediana zero, e não a v1 da API."""
    a = {"s7": np.array([[2.0, 10.0]]), "med7": np.ones((1, 2)), "p75": np.full((1, 2), 99.0),
         "p90": np.full((1, 2), 99.0), "sobe": np.ones((1, 2), bool)}
    assert bt.nivel_da_regra(a, REGRA).tolist() == [[0, 2]]
    piso_baixo = {**REGRA, "levels": {**REGRA["levels"],
                                      "critical": {**REGRA["levels"]["critical"], "min_detections": 2}}}
    assert bt.nivel_da_regra(a, piso_baixo).tolist() == [[2, 2]]   # o piso vem do alert_rules.json


def test_regra_atual_da_grade_e_a_variante_com_piso_continuo():
    atuais = [r for r in bt.regras(REGRA) if r["regra_atual"]]
    assert [r["regra"] for r in atuais] == ["razao2.0_tend1_atencao_p75_piso_continuo"]

def test_nivel_da_regra_le_tendencia_e_atencao_do_json():
    """Revisão do PR #71: a tendência e o percentil de Atenção também vêm do alert_rules.json."""
    a = {"s7": np.array([[30.0, 50.0]]), "med7": np.array([[1.0, 100.0]]), "p75": np.full((1, 2), 40.0),
         "p90": np.full((1, 2), 60.0), "sobe": np.zeros((1, 2), bool)}
    assert bt.nivel_da_regra(a, REGRA).tolist() == [[0, 1]]   # sem subir, não é Crítico; 50 > P75
    sem_tendencia = {**REGRA, "levels": {"critical": {**REGRA["levels"]["critical"], "requires_rising_trend": False},
                                         "attention": {"above_percentile": 90}}}
    assert bt.nivel_da_regra(a, sem_tendencia).tolist() == [[2, 0]]   # 50 não passa do P90


def test_grade_usa_o_piso_do_alert_rules_json():
    """Revisão do PR #71: a regra atual do relatório e o eventos.csv usam o mesmo min_detections."""
    a = {k: np.full((1, 1), v, np.float32) for k, v in
         {"s7": 2.0, "med7": 1.0, "p75": 99.0, "p90": 99.0, "score": 0.1, "s14": 0.0,
          "g80": 99.0, "g90": 99.0, "g95": 99.0}.items()}
    a["sobe"] = np.ones((1, 1), bool)
    piso_baixo = {**REGRA, "levels": {**REGRA["levels"],
                                      "critical": {**REGRA["levels"]["critical"], "min_detections": 2}}}
    for regra, freq in ((REGRA, 0.0), (piso_baixo, 1.0)):
        bt_ = bt.tabela([date(2020, 1, 5)], a, regra)
        atual = bt_[bt_["regra_atual"] & (bt_["p_gabarito"] == 90) & (bt_["minimo"] == 10)]
        assert atual["freq_critico"].tolist() == [freq]


def eventos_com(niv):
    inicio = date(2020, 7, 5)
    semanas = [inicio + timedelta(weeks=i) for i in range(-8, 1)]
    a = {"s7": np.ones((9, 1)), "med7": np.ones((9, 1))}
    ev = pd.DataFrame({"nome": ["X"], "regiao": ["Pantanal"], "inicio": [pd.Timestamp(inicio)],
                       "fim": [pd.Timestamp(inicio)]})
    return bt.eventos(ev, np.array(["Pantanal"]), semanas, a, np.array(niv)[:, None]).iloc[0]


def test_antecedencia_avisa_quando_bate_no_limite_da_janela():
    """Revisão do PR #71: alerta já ligado na 1ª semana da janela = a antecedência real pode ser maior."""
    no_limite = eventos_com([1, 1, 1, 1, 1, 1, 1, 1, 2])
    assert no_limite["antecedencia_dias"] == 56 and bool(no_limite["antecedencia_no_limite"])
    assert not eventos_com([0, 0, 0, 0, 0, 1, 2, 2, 2])["antecedencia_no_limite"]


def test_antecedencia_diz_se_o_alerta_ficou_ligado_ate_o_inicio():
    """Revisão do PR #71: um alerta isolado que voltou a Normal não é o mesmo que um alerta contínuo."""
    assert bool(eventos_com([0, 0, 0, 0, 0, 1, 2, 2, 2])["alerta_continuo"])
    blip = eventos_com([0, 1, 0, 0, 0, 0, 0, 1, 2])
    assert blip["antecedencia_dias"] == 49 and not blip["alerta_continuo"]
    assert not eventos_com([0, 0, 1, 1, 0, 0, 0, 0, 2])["alerta_continuo"]   # desligou antes do início


def test_evento_sem_alerta_tem_antecedencia_vazia_e_regiao_errada_avisa_o_evento():
    """Issue #59, item 3: 0 semanas (alerta menos de 7 dias antes) não pode ser igual a "nenhum alerta"."""
    inicio = date(2020, 7, 5)
    semanas = [inicio + timedelta(weeks=i) for i in range(-8, 2)]
    a = {"s7": np.ones((10, 1)), "med7": np.ones((10, 1))}
    ev = pd.DataFrame({"nome": ["X"], "regiao": ["Pantanal"], "inicio": [pd.Timestamp(inicio)],
                       "fim": [pd.Timestamp(inicio + timedelta(weeks=1))]})
    linhas = bt.eventos(ev, np.array(["Pantanal"]), semanas, a, np.zeros((10, 1), int))
    assert linhas["antecedencia_semanas"].isna().all() and linhas["antecedencia_dias"].isna().all()
    niv = np.zeros((10, 1), int)
    niv[7] = 2  # 1 semana antes = 7 dias
    linhas = bt.eventos(ev, np.array(["Pantanal"]), semanas, a, niv)
    assert set(linhas["antecedencia_dias"]) == {7} and set(linhas["antecedencia_semanas"]) == {1}
    with pytest.raises(ValueError, match="X"):
        bt.eventos(ev, np.array(["Cerrado"]), semanas, a, niv)


def linha(regra, p, mn, ganho, anos=12):
    return {"regra": regra, "regra_atual": False, "p_gabarito": p, "minimo": mn, "freq_critico": 0.05,
            "acerto": 0.5, "acerto_ingenua": 0.5 - ganho, "ganho": ganho, "anos_com_ganho_positivo": anos,
            "cobertura_critico": 0.2}


def principal_e_sensibilidade(regra, ganhos_sensibilidade):
    return [linha(regra, *bt.GABARITO, 0.1)] + [linha(regra, p, mn, g)
                                                 for (p, mn), g in zip(bt.SENSIBILIDADE, ganhos_sensibilidade)]


def test_situacao_aplica_o_criterio_completo_com_a_sensibilidade():
    tab = pd.DataFrame(principal_e_sensibilidade("passa_em_tudo", [0.1, 0.1, 0.1, 0.1])
                       + principal_e_sensibilidade("falha_no_minimo_5", [0.1, 0.1, -0.01, 0.1])
                       + [linha("sem_sensibilidade", *bt.GABARITO, 0.1),
                          linha("poucos_anos", *bt.GABARITO, 0.1, anos=6),
                          linha("ingenua_p90", *bt.GABARITO, 0.0)])
    s = bt.situacao(tab).set_index("regra")["situacao"].to_dict()
    assert s == {"passa_em_tudo": "aprovada", "falha_no_minimo_5": "reprovada",
                 "sem_sensibilidade": "sensibilidade não avaliada", "poucos_anos": "reprovada"}


def test_relatorio_so_lista_como_aprovada_a_regra_que_passa_em_todas_as_variacoes():
    tab = pd.DataFrame(principal_e_sensibilidade("passa_em_tudo", [0.1, 0.1, 0.1, 0.1])
                       + principal_e_sensibilidade("falha_no_minimo_5", [0.1, 0.1, -0.01, 0.1])
                       + [linha("sem_sensibilidade", *bt.GABARITO, 0.1)])
    aprovadas, resto = bt.relatorio(tab).split("Passam no gabarito principal")
    assert "passa_em_tudo" in aprovadas
    assert "falha_no_minimo_5" not in aprovadas and "sem_sensibilidade" not in aprovadas
    assert "sem_sensibilidade" in resto


def test_relatorio_sem_regra_aprovada_diz_que_a_tela_nao_mostra_acerto():
    tab = pd.DataFrame(principal_e_sensibilidade("falha_no_minimo_5", [0.1, 0.1, -0.01, 0.1]))
    assert "NENHUMA" in bt.relatorio(tab)


def test_antecedencia_continua_conta_so_o_trecho_ligado_ate_o_inicio():
    """Para a tela (#65): "virou Crítico X dias antes e ficou em Atenção ou Crítico até o início"."""
    e = eventos_com([0, 1, 0, 0, 0, 1, 2, 1, 2])          # semanas -8..-1 e o início
    assert e["antecedencia_continua_dias"] == 21           # trecho ligado desde -3 (1, 2, 1)
    assert e["antecedencia_critico_continuo_dias"] == 14   # primeiro Crítico dentro do trecho, em -2
    assert not e["continua_no_limite"]
    desligado = eventos_com([0, 0, 0, 0, 0, 1, 1, 0, 2])  # voltou a Normal na última semana antes
    assert pd.isna(desligado["antecedencia_continua_dias"])
    assert pd.isna(desligado["antecedencia_critico_continuo_dias"])
    so_atencao = eventos_com([1, 1, 1, 1, 1, 1, 1, 1, 2])  # ligado a janela toda, nunca Crítico antes
    assert so_atencao["antecedencia_continua_dias"] == 56 and bool(so_atencao["continua_no_limite"])
    assert pd.isna(so_atencao["antecedencia_critico_continuo_dias"])


def soma(serie, fim, k):
    """Soma ingênua dos k dias que terminam em `fim`, data por data. None se sai da série."""
    datas = [fim - timedelta(d) for d in range(k)]
    if min(datas) < bt.INICIO or max(datas) > bt.FIM:
        return None
    return sum(serie[(d - bt.INICIO).days] for d in datas)


def normal_ingenuo(serie, centro, k, ano_excluido, pcts):
    vals = []
    for ano in range(2012, 2025):
        if ano == ano_excluido:
            continue
        for d in range(-15, 16):
            s = soma(serie, centro.replace(year=ano) + timedelta(d), k)
            if s is not None:
                vals.append(s)
    return np.percentile(vals, pcts)


@pytest.mark.parametrize("t", [date(2013, 1, 6), date(2016, 6, 12), date(2019, 9, 1), date(2021, 12, 26),
                               date(2024, 12, 15)])
def test_formulas_do_avaliar_batem_com_a_conta_ingenua_data_por_data(t):
    """Qualidade: refaz cada número do avaliar() sem os atalhos de índice (somas acumuladas, índices do normal)."""
    rnd = np.random.default_rng(t.toordinal())
    m = rnd.poisson(rnd.uniform(0, 8, (3, 1)), (3, (bt.FIM - bt.INICIO).days + 1)).astype(np.float32)
    semanas, a = bt.avaliar(m, REGRA)
    w = semanas.index(t)
    fim14 = t + timedelta(14)
    for u in range(3):
        s = m[u]
        assert a["s7"][w, u] == soma(s, t, 7)
        med, p75, p90 = normal_ingenuo(s, t, 7, t.year, [50, 75, 90])
        assert (a["med7"][w, u], a["p75"][w, u], a["p90"][w, u]) == pytest.approx((med, p75, p90), rel=1e-5)
        assert bool(a["sobe"][w, u]) == (soma(s, t, 3) > soma(s, t - timedelta(3), 3))
        assert a["s14"][w, u] == soma(s, fim14, 14)                     # t+1..t+14
        g = normal_ingenuo(s, fim14, 14, fim14.year, [80, 90, 95])     # exclui o ano de t+14
        assert (a["g80"][w, u], a["g90"][w, u], a["g95"][w, u]) == pytest.approx(tuple(g), rel=1e-5)
        crit = a["s7"][w, u] >= max(2 * med, 10) and soma(s, t, 3) > soma(s, t - timedelta(3), 3)
        esperado = 2 if crit else 1 if a["s7"][w, u] > p75 else 0
        assert bt.nivel_da_regra({k: v[w:w + 1, u:u + 1] for k, v in a.items()}, REGRA)[0, 0] == esperado
