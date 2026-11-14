"""Análise exploratória de cada base (antes dos filtros), a partir de data/staged/.

Uso: python eda.py   ->  reports/eda.html
Bases: MODIS Terra, MODIS Aqua, VIIRS SNPP, VIIRS NOAA-20, VIIRS NOAA-21.
"""
import base64
import io
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pipeline import DUP_KEY, STAGE, ROOT

BASES = {"Terra": "MODIS Terra", "Aqua": "MODIS Aqua", "N": "VIIRS SNPP", "N20": "VIIRS NOAA-20", "N21": "VIIRS NOAA-21"}
ORDER = list(BASES.values())
COLORS = dict(zip(ORDER, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]))  # paleta categórica de referência
INK, MUTED = "#0b0b0b", "#52514e"
SAMPLE = 0.03  # fração guardada pra distribuições (frp, scan, hora)

plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6, "figure.dpi": 110})


def accumulate():
    monthly = defaultdict(int)       # (base, ano, mês) -> focos
    counts = defaultdict(lambda: defaultdict(int))  # base -> métrica -> n
    conf = defaultdict(lambda: defaultdict(int))
    samples = []
    for kind in ["modis", "viirs"]:
        for p in sorted((STAGE / kind).glob("*.parquet")):
            df = pd.read_parquet(p)
            df["base"] = df.satellite.map(BASES)
            df["frp_n"] = pd.to_numeric(df.frp, errors="coerce")
            dup = df.duplicated(DUP_KEY)
            for base, g in df.groupby("base"):
                c = counts[base]
                c["total"] += len(g)
                c["noite"] += int((g.daynight == "N").sum())
                c["type!=0"] += int((g.type.notna() & (g.type != 0)).sum())
                c["type_vazio(NRT)"] += int(g.type.isna().sum())
                c["frp<=0_ou_vazio"] += int((~(g.frp_n > 0)).sum())
                c["duplicata_exata"] += int(dup[g.index].sum())
                c["provisorio"] += int(g.provisional.sum())
                if kind == "viirs":
                    c["l_noite"] += int(((g.confidence == "l") & (g.daynight == "N")).sum())
                    for k, v in g.confidence.value_counts().items():
                        conf[base][k] += v
                else:
                    bins = pd.cut(pd.to_numeric(g.confidence), [-1, 29, 49, 79, 100], labels=["0-29", "30-49", "50-79", "80-100"])
                    for k, v in bins.value_counts().items():
                        conf[base][str(k)] += v
                for (y, m), v in g.groupby([g.acq_date.str[:4], g.acq_date.str[5:7]]).size().items():
                    monthly[(base, int(y), int(m))] += v
                c["inicio"] = min(c.get("inicio", "9999"), g.acq_date.min())
                c["fim"] = max(c.get("fim", ""), g.acq_date.max())
            samples.append(df.sample(frac=SAMPLE, random_state=0)[["base", "frp_n", "scan", "track", "acq_time", "daynight"]])
            print("eda:", p.name, flush=True)
    m = pd.Series(monthly).rename_axis(["base", "ano", "mes"]).rename("focos").reset_index()
    return m, counts, conf, pd.concat(samples, ignore_index=True)


def png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return f'<img src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}">'


def calendar(m, base):
    t = m[m.base == base].groupby(["ano", "mes"]).focos.sum().unstack().reindex(columns=range(1, 13))
    fig, ax = plt.subplots(figsize=(6.5, 0.22 * len(t) + 1))
    im = ax.imshow(t.values, cmap="Blues", aspect="auto")  # sequencial: um matiz, claro -> escuro
    ax.set_xticks(range(12), ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
    ax.set_yticks(range(len(t)), t.index)
    ax.grid(False)
    fig.colorbar(im, ax=ax, label="focos/mês")
    ax.set_title(f"{base}: focos por mês (cobertura)", loc="left", color=INK)
    return png(fig)


def dists(s, base):
    g = s[s.base == base]
    fig, axs = plt.subplots(1, 3, figsize=(10, 2.4))
    hour = g.acq_time.str[:2].astype(int)
    axs[0].hist(hour, bins=range(25), color=COLORS[base], rwidth=0.85)
    axs[0].set(title="hora da passagem (UTC)", xlabel="hora")
    axs[1].hist(np.log10(g.frp_n[g.frp_n > 0]), bins=50, color=COLORS[base])
    axs[1].set(title="FRP (log10 MW)", xlabel="log10(frp)")
    axs[2].hist(g.scan, bins=50, color=COLORS[base])
    axs[2].set(title="scan: tamanho do pixel (km)", xlabel="km")
    for a in axs:
        a.title.set_color(INK); a.title.set_ha("left"); a.title.set_x(0)
    return png(fig)


def annual(m):
    t = m.groupby(["ano", "base"]).focos.sum().unstack()
    t = t[t.index < 2026]  # 2026 incompleto
    fig, ax = plt.subplots(figsize=(9, 3.2))
    for b in ORDER:
        if b in t:
            ax.plot(t.index, t[b], color=COLORS[b], lw=2, label=b, marker="o", ms=3)
            last = t[b].dropna()
            ax.annotate(b, (last.index[-1], last.iloc[-1]), xytext=(4, 0), textcoords="offset points", color=INK, va="center")
    ax.set(title="Focos por ano e base (anos completos)", ylabel="focos/ano")
    ax.title.set_ha("left"); ax.title.set_x(0)
    ax.legend(frameon=False, ncol=5, loc="upper left", bbox_to_anchor=(0, -0.12))
    return png(fig)


def ratio(m, num, den):
    t = m.groupby(["base", "ano", "mes"]).focos.sum()
    r = (t[num] / t[den]).unstack().reindex(columns=range(1, 13))
    r = r[r.index < 2026] if num != "VIIRS NOAA-21" else r
    fig, ax = plt.subplots(figsize=(6.5, 0.25 * len(r) + 1))
    im = ax.imshow(r.values, cmap="Oranges", aspect="auto")
    for (i, j), v in np.ndenumerate(r.values):
        if np.isfinite(v):
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7, color="white" if v > np.nanpercentile(r.values, 70) else INK)
    ax.set_xticks(range(12), ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
    ax.set_yticks(range(len(r)), r.index)
    ax.grid(False)
    ax.set_title(f"Razão mensal {num} / {den}", loc="left", color=INK)
    return png(fig), r


def summary(counts, conf, s):
    rows = []
    for b in ORDER:
        c = counts.get(b)
        if not c:
            continue
        g = s[s.base == b]
        pct = lambda k: f"{100 * c[k] / c['total']:.1f}%"
        rows.append({"base": b, "período": f"{c['inicio']} → {c['fim']}", "focos": f"{c['total']:,}".replace(",", "."),
                     "% noite": pct("noite"), "% type≠0": pct("type!=0"), "% sem type (NRT)": pct("type_vazio(NRT)"),
                     "% frp≤0/vazio": pct("frp<=0_ou_vazio"), "% duplicata exata": pct("duplicata_exata"),
                     "% l à noite": pct("l_noite") if "l_noite" in c else "-",
                     "frp mediana / p95 (MW)": f"{g.frp_n.median():.1f} / {g.frp_n.quantile(.95):.0f}",
                     "scan mediana / p95 (km)": f"{g.scan.median():.2f} / {g.scan.quantile(.95):.2f}",
                     "confiança": ", ".join(f"{k}: {100 * v / c['total']:.0f}%" for k, v in sorted(conf[b].items()))})
    return pd.DataFrame(rows).to_html(index=False, border=0)


def main():
    m, counts, conf, s = accumulate()
    out = ROOT / "reports"; out.mkdir(exist_ok=True)
    m.to_csv(out / "focos_mensais_por_base.csv", index=False)  # pra quem quiser mexer no Excel/pandas
    present = set(m.base)
    ratios = []
    for num, den in [("VIIRS SNPP", "MODIS Aqua"), ("VIIRS NOAA-20", "VIIRS SNPP"), ("VIIRS NOAA-21", "VIIRS NOAA-20")]:
        if {num, den} <= present:
            img, r = ratio(m, num, den)
            ratios.append(img)
            r.to_csv(out / f"razao_{num.split()[-1]}_{den.split()[-1]}.csv".lower())
    parts = [f"<h1>Análise exploratória das bases FIRMS: cobertura (Brasil)</h1>",
             "<p>Dados <b>antes</b> dos filtros de limpeza (só recorte pela cobertura, tabela regioes). Distribuições usam amostra de "
             f"{SAMPLE:.0%}. Tabela mensal completa em <code>reports/focos_mensais_por_base.csv</code>.</p>",
             "<h2>Resumo por base</h2>", summary(counts, conf, s),
             "<h2>Comparação entre bases</h2>", annual(m), *ratios]
    for b in ORDER:
        if b in set(m.base):
            parts += [f"<h2>{b}</h2>", calendar(m, b), dists(s, b)]
    css = ("body{font-family:system-ui,sans-serif;max-width:1100px;margin:24px auto;padding:0 16px;color:#0b0b0b;background:#fcfcfb}"
           "table{border-collapse:collapse;font-size:12px}td,th{padding:4px 8px;border-bottom:1px solid #e6e5e0;text-align:left}"
           "img{max-width:100%;display:block;margin:12px 0}h2{margin-top:32px}")
    (out / "eda.html").write_text(f"<!doctype html><meta charset=utf-8><title>EDA FIRMS</title><style>{css}</style>"
                                  + "\n".join(parts), encoding="utf-8")
    print("ok ->", out / "eda.html")


if __name__ == "__main__":
    main()
