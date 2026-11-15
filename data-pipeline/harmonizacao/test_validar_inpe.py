"""Autoteste do validar_inpe.py com DADOS INVENTADOS (nada aqui é dado real do FIRMS nem do INPE).

Confere:
  1. a série harmonizada respeita a regra da origem (estimado até jan/2012, observado depois) e a faixa contém
     o valor central;
  2. com fatores corretos, as séries têm a mesma forma (correlação alta, picos iguais) e o degrau em 2012 é pequeno;
  3. com fatores errados pela metade (harmonização ruim, inventada), o teste acusa um degrau grande em 2012.

Uso:  python -I test_validar_inpe.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validar_inpe as v  # noqa: E402

FATOR = {"D": 4.0, "N": 20.0}             # INVENTADO
SAZONAL = [1, 1, 1, 1, 2, 4, 8, 30, 35, 15, 6, 2]  # INVENTADO
FRACAO_NOITE = 0.15                        # INVENTADO


def gerar(escala_fatores=1.0, seed=3):
    rng = np.random.default_rng(seed)
    inpe, cont = [], []
    for ano in range(2003, 2025):
        intensidade = rng.uniform(0.5, 2.0)  # anos fracos e fortes, INVENTADO
        for mes in range(1, 13):
            aqua = 300 * SAZONAL[mes - 1] * intensidade
            inpe.append(("Amazônia", ano, mes, round(aqua * 1.1), "AQUA_M-T", False))  # INPE conta um pouco diferente
            for p, frac in (("D", 1 - FRACAO_NOITE), ("N", FRACAO_NOITE)):
                a = aqua * frac
                if (ano, mes) >= v.INICIO_VIIRS:
                    cont.append(("Amazônia", ano, mes, "SNPP", p, round(a * FATOR[p] * rng.uniform(0.95, 1.05))))
                else:
                    cont.append(("Amazônia", ano, mes, "Aqua", p, round(a)))
    fat = []
    for k in range(2012, 2025):
        for mes in range(1, 13):
            for p in ("D", "N"):
                if (k, mes) == (2012, 1):
                    continue  # janeiro de 2012 fora da calibração
                fat.append(("Amazônia", mes, p, k, FATOR[p] * escala_fatores * rng.uniform(0.9, 1.1)))
    return (pd.DataFrame(inpe, columns=["bioma", "ano", "mes", "focos", "satelite", "parcial"]),
            pd.DataFrame(cont, columns=["bioma", "ano", "mes", "satelite", "periodo", "focos"]),
            pd.DataFrame(fat, columns=["bioma", "mes", "periodo", "ano_calibracao", "fator"]))


def rodar(escala):
    inpe, cont, fat = gerar(escala)
    fs = v.harmonizar(cont, fat)
    i = inpe[["bioma", "ano", "mes", "focos"]].rename(columns={"focos": "inpe"})
    return fs, v.comparar(fs.merge(i, on=["bioma", "ano", "mes"])).iloc[0]


def main():
    falhas = []
    fs, bom = rodar(1.0)
    est = fs[fs["origem"] == "estimado_modis"]
    if est[["ano", "mes"]].apply(tuple, axis=1).max() != (2012, 1):
        falhas.append("o último mês estimado deveria ser jan/2012")
    if not ((est["band_low"] <= est["firesync"]) & (est["firesync"] <= est["band_high"])).all():
        falhas.append("faixa não contém o valor central")
    if fs[fs["origem"] == "observado_viirs"]["band_low"].notna().any():
        falhas.append("mês observado não deveria ter faixa")
    if bom["corr_mensal_pearson"] < 0.95 or bom["pico_igual_tolerancia_1_mes"] < 0.9:
        falhas.append(f"forma não reconhecida: corr {bom['corr_mensal_pearson']:.2f}, "
                      f"picos {bom['pico_igual_tolerancia_1_mes']:.2f}")
    if abs(bom["degrau_2012"]) > 0.1:
        falhas.append(f"degrau com fatores certos deveria ser pequeno: {bom['degrau_2012']:.2f}")

    _, ruim = rodar(0.5)
    if ruim["degrau_2012"] < 0.5:
        falhas.append(f"degrau com fatores errados deveria ser grande: {ruim['degrau_2012']:.2f}")

    print(f"[dados inventados] fatores certos: corr mensal {bom['corr_mensal_pearson']:.3f}, "
          f"picos {bom['pico_igual_tolerancia_1_mes']:.2f}, top5 em comum {bom['top5_em_comum']}, "
          f"degrau 2012 {bom['degrau_2012']:+.1%}")
    print(f"[dados inventados] fatores pela metade: degrau 2012 {ruim['degrau_2012']:+.1%}")
    if falhas:
        print("FALHOU:\n  " + "\n  ".join(falhas))
        sys.exit(1)
    print("OK: todas as conferências passaram")


if __name__ == "__main__":
    main()
