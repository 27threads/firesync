"""Pipeline de dados FIRMS (MODIS + VIIRS).

Uso (nesta ordem; precisa de DATABASE_URL e, para o download, FIRMS_MAP_KEY):
    python pipeline.py cadastrar  # regioes.json -> tabelas regioes (polígono) e celula_regiao
    python pipeline.py download   # arquivos anuais do país da cobertura + API (2026 / NOAA-21 / NRT)
    python pipeline.py stage      # mantém só os focos dentro da cobertura (sem filtros) em data/staged/
    python pipeline.py clean      # aplica os filtros do time de dados e grava parquet em data/processed/
    python pipeline.py sem_dados  # dias sem dado de satélite (FIRMS missing_data) -> dias_sem_dados
    python pipeline.py importar [arquivo.csv|.zip ...]  # focos no banco (upsert) + cobertura; sem arg = data/staged/

Detalhes: docs/pipeline-dados.md e docs/banco.md
"""
import json
import os
import re
import sys
import subprocess
import zipfile
from datetime import date, timedelta
from io import StringIO
from pathlib import Path

import geopandas as gpd
import h3
import pandas as pd
import psycopg
import shapely

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
STAGE = ROOT / "data" / "staged"
OUT = ROOT / "data" / "processed"
COUNTRY_URL = "https://firms.modaps.eosdis.nasa.gov/data/country/{src}/{y}/{src}_{y}_{pais}.csv"
API = "https://firms.modaps.eosdis.nasa.gov/api"

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
              "satellite", "confidence", "version", "frp", "daynight", "type", "provisional"]
VIIRS_COLS = ["latitude", "longitude", "bright_ti4", "bright_ti5", "scan", "track", "acq_date", "acq_time",
              "satellite", "confidence", "version", "frp", "daynight", "type", "provisional", "high_conf"]


def env(name):
    if os.environ.get(name):
        return os.environ[name]
    f = ROOT / ".env"
    for line in f.read_text().splitlines() if f.exists() else []:
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"{name} não definida (variável de ambiente ou data-pipeline/.env)")


def db():
    return psycopg.connect(env("DATABASE_URL"), autocommit=True)


def config(conn, chave):
    row = conn.execute("SELECT valor FROM config WHERE chave = %s", (chave,)).fetchone()
    if row is None:
        raise SystemExit(f"config.{chave} não existe: rode a migration")
    return row[0]


def curl(url, dest=None):
    # curl em vez de urllib: o Python deste Windows falha na cadeia SSL da NASA
    args = ["curl", "-sS", "-f", "--retry", "3", "-m", "600", url]
    if dest:
        tmp = Path(str(dest) + ".part")
        subprocess.run(args + ["-o", str(tmp)], check=True)
        tmp.replace(dest)
        return None
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


# ---------------------------------------------------------------- cadastrar
SIMPLIFY_DEG = 0.001  # ~110 m, bem menor que o lado da célula res 6 (~3,7 km): não muda quais células entram


def region_cells(geom, res, mode):
    # o polígono do IBGE tem centenas de milhares de vértices; simplificar só para achar as células
    shape = h3.geo_to_h3shape(geom.simplify(SIMPLIFY_DEG, preserve_topology=True).__geo_interface__)
    return {h3.str_to_int(c) for c in h3.h3shape_to_cells_experimental(shape, res, contain=mode)}


def assign_cells(centers, overlaps):
    """Cada célula fica em uma região só: a do centro; as de borda (costa, fronteira) que nenhum
    centro pegou vão para a primeira região que encosta nelas. Sem isso, focos na borda somem dos agregados."""
    claimed = set().union(*centers)
    out = []
    for center, overlap in zip(centers, overlaps):
        borda = overlap - claimed
        claimed |= borda
        out.append(center | borda)
    return out


def cadastrar():
    """Única etapa que lê regioes.json. Grava o polígono em `regioes` (upsert por nome) e as células em `celula_regiao`."""
    conn = db()
    res = int(config(conn, "h3_resolucao"))
    regs = json.loads((ROOT / "regioes.json").read_text(encoding="utf-8"))
    geoms = []
    for r in regs:
        src = RAW / r["arquivo"]
        if not src.exists():
            src.parent.mkdir(parents=True, exist_ok=True)
            curl(r["url"], src)
        g = gpd.read_file(f"zip://{src}")
        # SIRGAS2000 ≈ WGS84 (<1 m)
        geoms.append(g[g[r["campo"]] == r["valor"]].set_crs(4326, allow_override=True).union_all())
    cells_by_region = assign_cells([region_cells(g, res, "center") for g in geoms],
                                   [region_cells(g, res, "overlap") for g in geoms])
    for r, geom, cells in zip(regs, geoms, cells_by_region):
        with conn.transaction():
            rid = conn.execute(
                """INSERT INTO regioes (nome, geom, fonte_poligono)
                   VALUES (%s, ST_Multi(ST_GeomFromWKB(%s, 4326)), %s)
                   ON CONFLICT (nome) DO UPDATE SET geom = EXCLUDED.geom, fonte_poligono = EXCLUDED.fonte_poligono
                   RETURNING id""",
                (r["nome"], shapely.to_wkb(geom), r["fonte_poligono"])).fetchone()[0]
            conn.execute("DELETE FROM celula_regiao WHERE regiao_id = %s", (rid,))
            with conn.cursor().copy("COPY celula_regiao (h3, regiao_id) FROM STDIN") as cp:
                for c in cells:
                    cp.write_row((c, rid))
        print(f"cadastrar: {r['nome']} ({len(cells):,} células res {res})", flush=True)


def load_regions(conn):
    """Polígonos da tabela `regioes` (a cobertura é a união deles)."""
    rows = conn.execute("SELECT nome, ST_AsBinary(geom) FROM regioes ORDER BY id").fetchall()
    return gpd.GeoDataFrame({"nome": [r[0] for r in rows]},
                            geometry=shapely.from_wkb([bytes(r[1]) for r in rows]), crs=4326).rename_geometry("geom")


def bbox_of(regions):
    w, s, e, n = regions.total_bounds
    return (w - 0.01, s - 0.01, e + 0.01, n + 0.01)  # oeste, sul, leste, norte; folga pro arredondamento da URL


# ---------------------------------------------------------------- download
def download():
    key = env("FIRMS_MAP_KEY")
    conn = db()
    pais = config(conn, "cobertura_pais")
    regions = load_regions(conn)
    if regions.empty:
        raise SystemExit("tabela regioes vazia: rode `python pipeline.py cadastrar` antes")
    for src, years in COUNTRY_FILES.items():
        for y in years:
            dest = RAW / "country" / f"{src}_{y}.csv"
            if dest.exists():
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            print("país:", dest.name, flush=True)
            curl(COUNTRY_URL.format(src=src, y=y, pais=pais), dest)

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
    src = p
    if str(p).endswith(".zip"):  # ZIP do Archive Download: CSV + Readme.txt
        z = zipfile.ZipFile(p)
        src = z.open(next(n for n in z.namelist() if n.endswith(".csv")))
    df = pd.read_csv(src, dtype={"acq_time": str, "version": str, "confidence": str})
    w, s, e, n = bbox
    return df[df.longitude.between(w, e) & df.latitude.between(s, n)]


def stage():
    """Bruto -> só focos dentro da cobertura (união de `regioes`), colunas normalizadas, sem filtro de qualidade."""
    regions = load_regions(db())
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
            in_coverage(normalize(df, kind), regions).to_parquet(dest, index=False)
            print("stage:", dest.name, flush=True)


def normalize(df, kind):
    df = df.rename(columns={"brightness": "bright_ti4", "bright_t31": "bright_ti5"} if kind == "viirs" else {})
    df["acq_time"] = df.acq_time.str.zfill(4)  # API devolve "14" em vez de "0014" (já é UTC)
    df["version"] = df.version.replace("61.03", "6.03")  # API escreve 61.03, arquivo por país 6.03
    df["provisional"] = df.version.str.contains("NRT")
    if "type" not in df:
        df["type"] = pd.NA
    return df


def in_coverage(df, regions):
    """Mantém os pontos dentro de qualquer região. Não grava a região no foco (isso é da calibração)."""
    pts = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs=4326)
    j = gpd.sjoin(pts, regions[["geom"]], predicate="within", how="inner")
    return df.loc[j.index.unique()]


# ---------------------------------------------------------------- clean
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
        log = {"linhas_na_cobertura": 0, "principal": 0, "baixa_confianca": 0}
        for name in ["main", "lowconf"]:
            shutil.rmtree(OUT / f"{kind}_{name}", ignore_errors=True)
        for p in sorted((STAGE / kind).glob("*.parquet")):
            df = pd.read_parquet(p)
            log["linhas_na_cobertura"] += len(df)
            main, low = fn(df, log)
            log["principal"] += len(main); log["baixa_confianca"] += len(low)
            write(main, OUT / f"{kind}_main", cols)
            write(low, OUT / f"{kind}_lowconf", cols)
        report[kind] = log
        print(kind, json.dumps(log, ensure_ascii=False), flush=True)
    (OUT / "clean_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------- sem_dados
SATELITES_FIRMS = {"Terra (MODIS)": "Terra", "Aqua (MODIS)": "Aqua", "Suomi NPP (VIIRS)": "SNPP",
                   "NOAA-20 (VIIRS)": "N20", "NOAA-21 (VIIRS)": "N21"}


# fonte SP do data_availability para cada satélite (Terra e Aqua estão juntos no MODIS)
SP_SOURCE = {"Terra": "MODIS_SP", "Aqua": "MODIS_SP", "SNPP": "VIIRS_SNPP_SP", "N20": "VIIRS_NOAA20_SP",
             "N21": "VIIRS_NOAA21_SP"}


def parse_missing(html, sp_fim):
    """Tabela da página missing_data do FIRMS -> {(data, satelite)}.

    Cada linha tem data/satélite da coluna SP e data/satélite da coluna NRT. Uma falha do NRT só vale
    depois do último dia SP daquele satélite (regra do próprio FIRMS); antes disso o SP tem o dado.
    """
    tds = [t.strip() for t in re.findall(r"<td>(.*?)</td>", html, re.S)]
    rows = set()
    for i in range(0, len(tds), 4):
        for (data, sat), nrt in ((tds[i:i + 2], False), (tds[i + 2:i + 4], True)):
            if not data:
                continue
            if sat not in SATELITES_FIRMS:
                raise ValueError(f"missing_data: satélite desconhecido {sat!r}")
            d, s = date.fromisoformat(data), SATELITES_FIRMS[sat]
            if nrt and d <= sp_fim[s]:
                continue
            rows.add((d, s))
    return rows


def sem_dados():
    """Dias sem dado de satélite (FIRMS) -> `dias_sem_dados`. Substitui a tabela inteira (foto atual do FIRMS)."""
    key = env("FIRMS_MAP_KEY")
    avail = pd.read_csv(StringIO(curl(f"{API}/data_availability/csv/{key}/ALL"))).set_index("data_id")
    sp_fim = {s: date.fromisoformat(avail.loc[src, "max_date"]) for s, src in SP_SOURCE.items()}
    # shortcut: o FIRMS não documenta um CSV de missing_data; este é o JSON que a própria página
    # /api/missing_data/ carrega. Se mudar de formato, o parse falha (não grava dado errado).
    d = json.loads(curl(f"{API}/missing_data/?action=fetch_data"))
    rows = parse_missing(d["html"], sp_fim)
    conn = db()
    with conn.transaction():
        conn.execute("DELETE FROM dias_sem_dados")
        conn.cursor().executemany("INSERT INTO dias_sem_dados (data, satelite) VALUES (%s, %s)", sorted(rows))
    print(f"sem_dados: {len(rows)} dias × satélite", flush=True)


# ---------------------------------------------------------------- importar
SATELITES = {"Terra": "Terra", "Aqua": "Aqua", "N": "SNPP", "SNPP": "SNPP", "N20": "N20", "N21": "N21"}
VIIRS_CONF = {"l": "baixa", "low": "baixa", "n": "nominal", "nominal": "nominal", "h": "alta", "high": "alta"}
FOCOS_COLS = ["sensor", "satelite", "lat", "lon", "datahora_utc", "confianca", "frp", "periodo", "tipo",
              "qualidade", "scan", "track", "arquivo_origem", "h3"]
FOCOS_KEY = ["satelite", "lat", "lon", "datahora_utc"]


def to_focos(df, kind, origem, res):
    """Frame normalizado (saída de `normalize`) -> colunas da tabela `focos` (docs/importacao-regioes.md)."""
    sat = df.satellite.map(SATELITES)
    if sat.isna().any():
        raise ValueError(f"{origem}: satélite desconhecido {sorted(set(df.satellite[sat.isna()]))}")
    if kind == "modis":
        c = pd.to_numeric(df.confidence)
        conf = pd.Series("alta", index=df.index).mask(c < 80, "nominal").mask(c < 30, "baixa")
    else:
        conf = df.confidence.str.lower().map(VIIRS_CONF)
    if conf.isna().any():
        raise ValueError(f"{origem}: confiança desconhecida {sorted(set(df.confidence[conf.isna()]))}")
    out = pd.DataFrame({
        "sensor": "MODIS" if kind == "modis" else "VIIRS",
        "satelite": sat,
        "lat": df.latitude,
        "lon": df.longitude,
        "datahora_utc": pd.to_datetime(df.acq_date + " " + df.acq_time, format="%Y-%m-%d %H%M", utc=True),
        "confianca": conf,
        "frp": pd.to_numeric(df.frp, errors="coerce"),
        "periodo": df.daynight,
        "tipo": pd.to_numeric(df.type, errors="coerce").astype("Int16"),
        "qualidade": df.provisional.map({True: "NRT", False: "SP"}),
        "scan": df.scan,
        "track": df.track,
        "arquivo_origem": origem,
        "h3": [h3.str_to_int(h3.latlng_to_cell(a, b, res)) for a, b in zip(df.latitude, df.longitude)],
    })
    # o upsert não aceita a mesma chave duas vezes no mesmo comando
    return out.drop_duplicates(FOCOS_KEY)


def kind_of(df):
    # pelo satélite: o ZIP do Archive Download escreve instrument=SNPP e usa brightness/bright_t31 no VIIRS
    return "modis" if df.satellite.isin(["Terra", "Aqua"]).all() else "viirs"


def importar(paths=()):
    """Carrega focos em `focos` (upsert pela chave única) e atualiza `cobertura`.

    Sem argumento: todos os parquet de data/staged/ (saída do `stage`).
    Com argumento: CSVs ou ZIPs do FIRMS, normalizados e recortados pela cobertura aqui mesmo.
    Cada arquivo é uma transação: ou entra inteiro, ou não entra.
    """
    conn = db()
    res = int(config(conn, "h3_resolucao"))
    if paths:
        regions = load_regions(conn)
        bbox = bbox_of(regions)
        jobs = [(Path(p), None) for p in paths]
    else:
        jobs = [(p, p.parent.name) for p in sorted(STAGE.glob("*/*.parquet"))]
    cols = ",".join(FOCOS_COLS)
    upd = ",".join(f"{c} = EXCLUDED.{c}" for c in FOCOS_COLS if c not in FOCOS_KEY)
    for p, kind in jobs:
        if kind is None:  # CSV/ZIP direto do FIRMS
            raw = read_raw(p, bbox)
            kind = kind_of(raw)
            df = in_coverage(normalize(raw, kind), regions)
        else:
            df = pd.read_parquet(p)
        if df.empty:
            continue
        f = to_focos(df, kind, p.name, res)
        buf = StringIO()
        f.to_csv(buf, index=False, header=False)
        with conn.transaction():
            conn.execute(f"CREATE TEMP TABLE focos_tmp (LIKE focos INCLUDING DEFAULTS) ON COMMIT DROP")
            with conn.cursor().copy(f"COPY focos_tmp ({cols}) FROM STDIN WITH (FORMAT csv)") as cp:
                cp.write(buf.getvalue())
            ins, upd_n = conn.execute(f"""
                WITH r AS (
                    INSERT INTO focos ({cols}) SELECT {cols} FROM focos_tmp
                    ON CONFLICT ({",".join(FOCOS_KEY)}) DO UPDATE SET {upd}
                    RETURNING (xmax = 0) AS novo)
                SELECT count(*) FILTER (WHERE novo), count(*) FILTER (WHERE NOT novo) FROM r""").fetchone()
            # a cobertura é o país (unidade de download), não o bioma: o período do arquivo vale para
            # todas as regiões. Usar a data do último foco de cada bioma confundiria "zero focos" com "sem dados".
            conn.execute("""
                INSERT INTO cobertura (regiao_id, satelite, data_inicio, data_fim)
                SELECT r.id, t.satelite, t.ini, t.fim
                FROM (SELECT satelite, min(datahora_utc)::date ini, max(datahora_utc)::date fim
                      FROM focos_tmp GROUP BY satelite) t CROSS JOIN regioes r
                ON CONFLICT (regiao_id, satelite) DO UPDATE
                SET data_inicio = least(cobertura.data_inicio, EXCLUDED.data_inicio),
                    data_fim = greatest(cobertura.data_fim, EXCLUDED.data_fim), atualizado_em = now()""")
        print(f"importar: {p.name}: {ins:,} novos, {upd_n:,} atualizados", flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "importar":
        importar(sys.argv[2:])
    else:
        {"cadastrar": cadastrar, "download": download, "stage": stage, "clean": clean,
         "sem_dados": sem_dados}[cmd]()
