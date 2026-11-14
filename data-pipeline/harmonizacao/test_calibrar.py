"""Autoteste do calibrar.py com DADOS INVENTADOS (nada aqui é dado real do FIRMS).

Gera contagens diárias sintéticas com fatores conhecidos (dia 4x, noite 20x), roda a calibração e confere:
  1. os fatores recuperados ficam perto dos verdadeiros onde há foco suficiente;
  2. a fusão acontece onde o Aqua tem poucos focos (bioma inventado "Pampa", à noite);
  3. sem deriva, o critério de 1,5x mantém os 13 anos;
  4. com uma deriva inventada em 2022-2024, o critério escolhe 2012-2021;
  5. janeiro de 2012 não entra;
  6. a noite não se junta ao dia quando o ano inteiro da noite tem foco suficiente.

Uso:  python -I test_calibrar.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrar as c  # noqa: E402

FATOR_VERDADEIRO = {"D": 4.0, "N": 20.0}  # INVENTADO
SAZONAL = [1, 1, 1, 1, 2, 4, 8, 30, 35, 15, 6, 2]  # INVENTADO: pico em setembro


def gerar(deriva=False, seed=1):
    """Contagens diárias INVENTADAS para dois biomas, fev/2012 a dez/2024."""
    rng = np.random.default_rng(seed)
    linhas = []
    for regiao, escala in [("Amazônia", 40.0), ("Pampa", 0.05)]:
        for dia in pd.date_range("2012-01-01", "2024-12-31"):
            base = escala * SAZONAL[dia.month - 1]
            for periodo, frac in [("D", 1.0), ("N", 0.15)]:
                a = rng.poisson(base * frac)
                f = FATOR_VERDADEIRO[periodo] * (0.6 if deriva and dia.year >= 2022 else 1.0)
                s = rng.poisson(a * f + base * frac * 0.5)
                linhas += [(regiao, dia.date(), periodo, "Aqua", a), (regiao, dia.date(), periodo, "SNPP", s)]
    d = pd.DataFrame(linhas, columns=["regiao", "data", "periodo", "satelite", "focos"])
    return d[d["focos"] > 0]


def rodar(diario, minimo=30):
    m = c.mensal(diario)
    fat = c.fatores_por_ano(m, minimo)
    erros = c.erros_por_ano(c.validar(m, fat))
    return m, fat, erros


def main():
    falhas = []

    m, fat, erros = rodar(gerar(deriva=False))
    # 5. janeiro de 2012 fora
    if ((m["ano"] == 2012) & (m["mes"] == 1)).any():
        falhas.append("janeiro de 2012 entrou")
    # 1. fatores recuperados (Amazônia, meses de pico, sem fusão)
    amz = fat[(fat["regiao"] == "Amazônia") & fat["mes"].isin([8, 9]) & fat["fusao_com"].isna()]
    for p, verdade in FATOR_VERDADEIRO.items():
        med = amz[amz["periodo"] == p]["fator"].median()
        esperado = verdade + 0.5  # o gerador soma 0,5x do Aqua esperado como fogo pequeno só do VIIRS
        if abs(med - esperado) / esperado > 0.1:
            falhas.append(f"fator {p} recuperado {med:.2f}, esperado perto de {esperado}")
    # 2. fusão no Pampa à noite
    pampa_n = fat[(fat["regiao"] == "Pampa") & (fat["periodo"] == "N")]
    if pampa_n["fusao_com"].isna().all():
        falhas.append("não houve fusão no Pampa à noite")
    # 6. a noite não se junta ao dia quando o ano inteiro da noite tem foco suficiente
    m_pampa = m[(m["regiao"] == "Pampa") & (m["periodo"] == "N")].groupby("ano")["A"].sum()
    anos_noite_ok = m_pampa[m_pampa >= 30].index
    misturou = pampa_n[pampa_n["ano"].isin(anos_noite_ok) & (pampa_n["fusao_com"] == "ano inteiro, dia e noite")]
    if len(misturou):
        falhas.append(f"{len(misturou)} fatores noturnos juntaram dia e noite sem precisar")
    fundidos_n = pampa_n[pampa_n["fusao_com"].fillna("").str.contains(r"\(N\)")]["fator"].median()
    if not np.isnan(fundidos_n) and abs(fundidos_n - 20.5) / 20.5 > 0.25:
        falhas.append(f"fator noturno fundido {fundidos_n:.2f}, esperado perto de 20,5")
    # 3. sem deriva: 13 anos
    anos, _, _, razao = c.decidir(erros, "erro_ponderado")
    if len(anos) != 13:
        falhas.append(f"sem deriva escolheu {len(anos)} anos (razão {razao:.2f})")

    # 4. com deriva: 10 anos
    _, _, erros_d = rodar(gerar(deriva=True))
    anos_d, _, _, razao_d = c.decidir(erros_d, "erro_ponderado")
    if len(anos_d) != 10:
        falhas.append(f"com deriva escolheu {len(anos_d)} anos (razão {razao_d:.2f})")

    print(f"[dados inventados] sem deriva: razão {razao:.2f} -> {len(anos)} anos | "
          f"com deriva: razão {razao_d:.2f} -> {len(anos_d)} anos")
    print("[dados inventados] fusões:", fat["fusao_com"].value_counts().to_dict())
    print("[dados inventados] cobertura da faixa (Amazônia):",
          round(erros[erros["regiao"] == "Amazônia"]["cobertura_faixa"].mean(), 2))
    if falhas:
        print("FALHOU:\n  " + "\n  ".join(falhas))
        sys.exit(1)
    print("OK: todas as conferências passaram")


if __name__ == "__main__":
    main()
