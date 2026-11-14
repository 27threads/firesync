"""Pipeline de dados FIRMS (MODIS + VIIRS), etapa de arquivos (antes do banco).

Uso:
    python pipeline.py download   # polígonos das regiões + arquivos anuais do Brasil + API (2026 / NOAA-21 / NRT)
    python pipeline.py stage      # recorta as regiões de regioes.json (sem filtros) em data/staged/
    python pipeline.py clean      # aplica os filtros do time de dados e grava parquet em data/processed/

Detalhes: docs/pipeline-dados.md
"""
import json
import os
import sys
import subprocess
from datetime import date, timedelta
from io import StringIO
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
STAGE = ROOT / "data" / "staged"
OUT = ROOT / "data" / "processed"
COUNTRY_URL = "https://firms.modaps.eosdis.nasa.gov/data/country/{src}/{y}/{src}_{y}_Brazil.csv"
API = "https://firms.modaps.eosdis.nasa.gov/api"
REGIOES = json.loads((ROOT / "regioes.json").read_text(encoding="utf-8"))  # regiões são dado, não código

# Arquivos anuais por país (versão padrão, com `type`). Último ano completo publicado: 2025.
COUNTRY_FILES = {
    "modis": range(2000, 2026),
    "viirs-snpp": range(2012, 2026),
    "viirs-jpss1": range(2018, 2026),
}
# O que os arquivos por país não cobrem vem da API: (fonte SP, início, fonte NRT)
API_SOURCES = [
    ("MODIS_SP", "2026-01-01", "MODIS_NRT"),
    ("VIIRS_SNPP_SP", "2026-01-01", "VIIRS_SNPP_NRT"),
    ("VIIRS_NOAA20_SP", "2026-01-01", "VIIRS_NOAA20_NRT"),
    ("VIIRS_NOAA21_SP", "2023-03-01", "VIIRS_NOAA21_NRT"),  # NOAA-21 não tem arquivo por país
]

MODIS_COLS = ["latitude", "longitude", "brightness", "bright_t31", "scan", "track", "acq_date", "acq_time",
              "satellite", "confidence", "version", "frp", "daynight", "type", "regiao", "provisional"]
VIIRS_COLS = ["latitude", "longitude", "bright_ti4", "bright_ti5", "scan", "track", "acq_date", "acq_time",
              "satellite", "confidence", "version", "frp", "daynight", "type", "regiao", "provisional", "high_conf"]


def map_key():
    if os.environ.get("FIRMS_MAP_KEY"):
        return os.environ["FIRMS_MAP_KEY"]
    env = ROOT / ".env"
    for line in env.read_text().splitlines() if env.exists() else []:
        if line.startswith("FIRMS_MAP_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("FIRMS_MAP_KEY não definida (variável de ambiente ou data-pipeline/.env)")


def curl(url, dest=None):
    # curl em vez de urllib: o Python deste Windows falha na cadeia SSL da NASA
    args = ["curl", "-sS", "-f", "--retry", "3", "-m", "600", url]
    if dest:
        tmp = Path(str(dest) + ".part")
        subprocess.run(args + ["-o", str(tmp)], check=True)
        tmp.replace(dest)
        return None
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


# ---------------------------------------------------------------- download
def download():
    key = map_key()
    regions = load_regions()
    for src, years in COUNTRY_FILES.items():
        for y in years:
            dest = RAW / "country" / f"{src}_{y}.csv"
            if dest.exists():
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            print("país:", dest.name, flush=True)
            curl(COUNTRY_URL.format(src=src, y=y), dest)

    avail = pd.read_csv(StringIO(curl(f"{API}/data_availability/csv/{key}/ALL"))).set_index("data_id")
    bbox = ",".join(f"{v:.2f}" for v in bbox_of(regions))
    for sp, start, nrt in API_SOURCES:
        sp_end = date.fromisoformat(avail.loc[sp, "max_date"])
        nrt_end = date.fromisoformat(avail.loc[nrt, "max_date"])
        jobs = [(sp, date.fromisoformat(start), sp_end), (nrt, sp_end + timedelta(days=1), nrt_end)]
        for source, d0, d1 in jobs:
            d = d0
            while d <= d1:
                n = min(5, (d1 - d).days + 1)  # API aceita no máximo 5 dias por chamada
                dest = RAW / "api" / source / f"{d}.csv"
                # chunk que alcança o fim da disponibilidade é rebaixado: o NRT ainda está chegando
                if not dest.exists() or d + timedelta(days=n - 1) >= nrt_end:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    print("api:", source, d, flush=True)
                    curl(f"{API}/area/csv/{key}/{source}/{bbox}/{n}/{d}", dest)
                d += timedelta(days=n)


# ---------------------------------------------------------------- stage
# Um arquivo por vez: o histórico inteiro não cabe na RAM.
def raw_files(kind):
    country = sorted((RAW / "country").glob("modis_*.csv" if kind == "modis" else "viirs-*.csv"))
    api = sorted(p for p in (RAW / "api").glob("*/*.csv") if p.parent.name.startswith(kind.upper()))
    return country + api


def read_raw(p, bbox):
    df = pd.read_csv(p, dtype={"acq_time": str, "version": str, "confidence": str})
    w, s, e, n = bbox
    return df[df.longitude.between(w, e) & df.latitude.between(s, n)]


def stage():
    """Bruto -> só as regiões de regioes.json, colunas normalizadas, sem nenhum filtro de qualidade."""
    regions = load_regions()
    bbox = bbox_of(regions)
    for kind in ["modis", "viirs"]:
        for p in raw_files(kind):
            dest = STAGE / kind / f"{p.parent.name}_{p.stem}.parquet"
            if dest.exists() and dest.stat().st_mtime > p.stat().st_mtime:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            df = read_raw(p, bbox)
            if df.empty:
                continue
            add_regiao(normalize(df, kind), regions).to_parquet(dest, index=False)
            print("stage:", dest.name, flush=True)


# ---------------------------------------------------------------- clean


def normalize(df, kind):
    df = df.rename(columns={"brightness": "bright_ti4", "bright_t31": "bright_ti5"} if kind == "viirs" else {})
    df["acq_time"] = df.acq_time.str.zfill(4)  # API devolve "14" em vez de "0014" (já é UTC)
    df["version"] = df.version.replace("61.03", "6.03")  # API escreve 61.03, arquivo por país 6.03
    df["provisional"] = df.version.str.contains("NRT")
    if "type" not in df:
        df["type"] = pd.NA
    return df


def load_regions():
    """Polígonos de regioes.json (baixa o arquivo de origem se faltar). Retorna GeoDataFrame [regiao, geometry]."""
    parts = []
    for r in REGIOES:
        src = RAW / r["arquivo"]
        if not src.exists():
            src.parent.mkdir(parents=True, exist_ok=True)
            curl(r["url"], src)
        g = gpd.read_file(f"zip://{src}")
        g = g[g[r["campo"]] == r["valor"]].set_crs(4326, allow_override=True)  # SIRGAS2000 ≈ WGS84 (<1 m)
        parts.append(gpd.GeoDataFrame({"regiao": [r["nome"]]}, geometry=[g.union_all()], crs=4326))
    return pd.concat(parts, ignore_index=True)


def bbox_of(regions):
    w, s, e, n = regions.total_bounds
    return (w - 0.01, s - 0.01, e + 0.01, n + 0.01)  # oeste, sul, leste, norte; folga pro arredondamento da URL


def add_regiao(df, regions):
    pts = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs=4326)
    j = gpd.sjoin(pts, regions, predicate="within", how="inner")
    j = j[~j.index.duplicated()]  # ponto exatamente na divisa entre regiões
    return pd.DataFrame(j.drop(columns=["geometry", "index_right"]))


def keep(df, mask, log, key):
    """Filtra e soma no log quantas linhas saíram (acumula entre arquivos)."""
    log[key] = log.get(key, 0) + int((~mask).sum())
    return df[mask]


DUP_KEY = ["latitude", "longitude", "acq_date", "acq_time", "satellite"]


def common_filters(df, log):
    # type só existe na versão padrão; linhas NRT (provisional) ficam com type vazio
    df = keep(df, df.provisional | (df.type == 0), log, "type!=0")
    df = keep(df, pd.to_numeric(df.frp, errors="coerce") > 0, log, "frp<=0_ou_vazio")
    return keep(df, ~df.duplicated(DUP_KEY), log, "duplicatas_identicas")


def clean_modis(df, log):
    df = common_filters(df, log)
    conf = pd.to_numeric(df.confidence)
    return df[conf >= 30], df[conf < 30]


def clean_viirs(df, log):
    df = common_filters(df, log)
    df = keep(df, ~((df.confidence == "l") & (df.daynight == "N")), log, "conf_l_noite")
    df = df.assign(high_conf=df.confidence == "h")
    low = df.confidence == "l"  # aqui só sobra baixa confiança diurna
    return df[~low], df[low]


def write(df, path, cols):
    df = df[cols].copy()
    df["year"] = df.acq_date.str[:4]
    # partições separam satélite e dia/noite sem apagar nada; cada chamada acrescenta arquivos novos
    df.to_parquet(path, partition_cols=["satellite", "daynight", "year"], index=False)


def clean():
    import shutil
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    for kind, fn, cols in [("modis", clean_modis, MODIS_COLS), ("viirs", clean_viirs, VIIRS_COLS)]:
        log = {"linhas_amazonia_pantanal": 0, "principal": 0, "baixa_confianca": 0}
        for name in ["main", "lowconf"]:
            shutil.rmtree(OUT / f"{kind}_{name}", ignore_errors=True)
        for p in sorted((STAGE / kind).glob("*.parquet")):
            df = pd.read_parquet(p)
            log["linhas_amazonia_pantanal"] += len(df)
            main, low = fn(df, log)
            log["principal"] += len(main); log["baixa_confianca"] += len(low)
            write(main, OUT / f"{kind}_main", cols)
            write(low, OUT / f"{kind}_lowconf", cols)
        report[kind] = log
        print(kind, json.dumps(log, ensure_ascii=False), flush=True)
    (OUT / "clean_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    {"download": download, "stage": stage, "clean": clean}[sys.argv[1]]()
