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
import time
import zipfile
from datetime import date, timedelta
from io import StringIO
from pathlib import Path

import geopandas as gpd
import h3
import pandas as pd
import psycopg
import shapely

import logs

log = logs.logger("pipeline")
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
    # datas sempre em UTC, qualquer que seja o fuso configurado no servidor (::date, extract, limites de mês)
    return psycopg.connect(env("DATABASE_URL"), autocommit=True, options="-c timezone=UTC")


def config(conn, chave):
    row = conn.execute("SELECT valor FROM config WHERE chave = %s", (chave,)).fetchone()
    if row is None:
        raise SystemExit(f"config.{chave} não existe: rode a migration")
    return row[0]


def curl(url, dest=None):
    # curl em vez de urllib: o Python deste Windows falha na cadeia SSL da NASA
    args = ["curl", "-sS", "-f", "--retry", "3", "-m", "600", url]
    inicio = time.monotonic()
    try:
        if dest:
            tmp = Path(str(dest) + ".part")
            subprocess.run(args + ["-o", str(tmp)], check=True)
            tmp.replace(dest)
            out = None
        else:
            out = subprocess.run(args, check=True, capture_output=True, text=True, encoding="utf-8").stdout
    except subprocess.CalledProcessError as e:
        # a MAP_KEY vai na URL (/csv/<chave>/...): nunca deixar ela chegar ao log
        raise RuntimeError(f"curl falhou ({e.returncode}): {mask_key(url)}") from None
    log.debug("http_get", url=mask_key(url), duration_ms=ms_desde(inicio))
    return out


def ms_desde(inicio):
    """Milissegundos desde `inicio` (time.monotonic()), para o `duration_ms` dos logs."""
    return round((time.monotonic() - inicio) * 1000)


def mask_key(url):
    return re.sub(r"/csv/[^/]+/", "/csv/***/", url)


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
            log.info("region_polygon_download", region=r["nome"], file=r["arquivo"])
            curl(r["url"], src)
        g = gpd.read_file(f"zip://{src}")
        # SIRGAS2000 ≈ WGS84 (<1 m)
        geoms.append(g[g[r["campo"]] == r["valor"]].set_crs(4326, allow_override=True).union_all())
    cells_by_region = assign_cells([region_cells(g, res, "center") for g in geoms],
                                   [region_cells(g, res, "overlap") for g in geoms])
    # Uma transação: a tabela vira exatamente o JSON. Região renomeada ou removida sai (o cascade limpa
    # células, agregados e fatores dela); sem isso a célula ficaria em duas regiões.
    with conn.transaction():
        removidas = conn.execute("DELETE FROM regioes WHERE nome <> ALL(%s) RETURNING nome",
                                 ([r["nome"] for r in regs],)).fetchall()
        if removidas:  # o cascade apaga células, agregados e fatores delas
            log.warning("regions_removed", regions=[n for (n,) in removidas])
        conn.execute("DELETE FROM celula_regiao")
        for r, geom, cells in zip(regs, geoms, cells_by_region):
            rid = conn.execute(
                """INSERT INTO regioes (nome, geom, fonte_poligono)
                   VALUES (%s, ST_Multi(ST_GeomFromWKB(%s, 4326)), %s)
                   ON CONFLICT (nome) DO UPDATE SET geom = EXCLUDED.geom, fonte_poligono = EXCLUDED.fonte_poligono
                   RETURNING id""",
                (r["nome"], shapely.to_wkb(geom), r["fonte_poligono"])).fetchone()[0]
            with conn.cursor().copy("COPY celula_regiao (h3, regiao_id) FROM STDIN") as cp:
                for c in cells:
                    cp.write_row((c, rid))
            log.info("region_registered", region=r["nome"], region_id=rid, cells=len(cells), h3_resolution=res)


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
                log.debug("download_skipped", file=dest.name, reason="already_downloaded")
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            log.info("download_country_file", source=src, year=y, country=pais)
            curl(COUNTRY_URL.format(src=src, y=y, pais=pais), dest)

    avail = pd.read_csv(StringIO(curl(f"{API}/data_availability/csv/{key}/ALL"))).set_index("data_id")
    bbox = ",".join(f"{v:.2f}" for v in bbox_of(regions))
    for sp, start, nrt in API_SOURCES:
        sp_end = date.fromisoformat(avail.loc[sp, "max_date"])
        nrt_end = date.fromisoformat(avail.loc[nrt, "max_date"])
        jobs = [(sp, date.fromisoformat(start), sp_end), (nrt, sp_end + timedelta(days=1), nrt_end)]
        log.info("firms_availability", sp_source=sp, sp_end=sp_end, nrt_source=nrt, nrt_end=nrt_end)
        for old in (RAW / "api" / nrt).glob("*.csv"):  # o SP chegou: o NRT desses dias sai (e o staged dele)
            if date.fromisoformat(old.stem) + timedelta(days=4) <= sp_end:
                log.info("nrt_file_superseded_by_sp", file=f"{nrt}/{old.name}", sp_end=sp_end)
                old.unlink()
                (STAGE / ("viirs" if "VIIRS" in nrt else "modis") / f"{nrt}_{old.stem}.parquet").unlink(missing_ok=True)
        for source, d0, d1 in jobs:
            d = d0
            while d <= d1:
                n = min(5, (d1 - d).days + 1)  # API aceita no máximo 5 dias por chamada
                dest = RAW / "api" / source / f"{d}.csv"
                # chunk que alcança o fim da disponibilidade é rebaixado: o NRT ainda está chegando
                if not dest.exists() or d + timedelta(days=n - 1) >= nrt_end:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    log.info("download_api_chunk", source=source, start=d, days=n,
                             reason="near_availability_end" if dest.exists() else "missing")
                    curl(f"{API}/area/csv/{key}/{source}/{bbox}/{n}/{d}", dest)
                else:
                    log.debug("download_skipped", file=f"{source}/{dest.name}", reason="already_downloaded")
                d += timedelta(days=n)


# ---------------------------------------------------------------- stage
# Um arquivo por vez: o histórico inteiro não cabe na RAM.
def raw_files(kind):
    country = sorted((RAW / "country").glob("modis_*.csv" if kind == "modis" else "viirs-*.csv"))
    api = sorted(p for p in (RAW / "api").glob("*/*.csv") if p.parent.name.startswith(kind.upper()))
    return country + api


def read_raw(p, bbox):
    dtype = {"acq_time": str, "version": str, "confidence": str}
    if str(p).endswith(".zip"):  # ZIP do Archive Download: CSV + Readme.txt
        with zipfile.ZipFile(p) as z, z.open(next(n for n in z.namelist() if n.endswith(".csv"))) as f:
            df = pd.read_csv(f, dtype=dtype)
    else:
        df = pd.read_csv(p, dtype=dtype)
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
                log.debug("stage_skipped", file=dest.name, reason="up_to_date")
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            df = read_raw(p, bbox)
            if df.empty:
                log.info("stage_skipped", file=p.name, reason="no_rows_in_bbox")
                continue
            dentro = in_coverage(normalize(df, kind), regions)
            dentro.to_parquet(dest, index=False)
            log.info("stage_file_done", file=dest.name, rows_in_bbox=len(df), rows_in_coverage=len(dentro))


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


# As mesmas regras estão em SQL em agregar.py (o que a API usa). Mudou uma, mude a outra.
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
    eventos = logs.logger("clean")
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
        eventos.info("clean_done", kind=kind, counts=log)
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
    por_satelite = {s: sum(1 for _, x in rows if x == s) for s in sorted({x for _, x in rows})}
    log.info("missing_days_loaded", rows=len(rows), by_satellite=por_satelite, sp_end=sp_fim)


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
    Devolve os totais de todos os arquivos (o job NRT registra quantos focos entraram).
    """
    conn = db()
    res = int(config(conn, "h3_resolucao"))
    if paths:
        regions = load_regions(conn)
        if regions.empty:
            raise SystemExit("tabela regioes vazia: rode `python pipeline.py cadastrar` antes")
        bbox = bbox_of(regions)
        jobs = [(Path(p), None) for p in paths]
    else:
        jobs = [(p, p.parent.name) for p in sorted(STAGE.glob("*/*.parquet"))]
    cols = ",".join(FOCOS_COLS)
    upd = ",".join(f"{c} = EXCLUDED.{c}" for c in FOCOS_COLS if c not in FOCOS_KEY)
    totais = {"detections_inserted": 0, "detections_updated": 0, "nrt_replaced_by_sp": 0}
    for p, kind in jobs:
        inicio = time.monotonic()
        if kind is None:  # CSV/ZIP direto do FIRMS
            raw = read_raw(p, bbox)
            kind = kind_of(raw)
            df = in_coverage(normalize(raw, kind), regions)
            lidas = len(raw)
        else:
            df = pd.read_parquet(p)
            lidas = len(df)
        if df.empty:
            log.info("import_file_skipped", file=p.name, reason="no_rows_in_coverage", rows_read=lidas)
            continue
        f = to_focos(df, kind, p.name, res)
        buf = StringIO()
        f.to_csv(buf, index=False, header=False)
        with conn.transaction():
            conn.execute(f"CREATE TEMP TABLE focos_tmp ON COMMIT DROP AS SELECT {cols} FROM focos WITH NO DATA")
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
            sub = drop_nrt_under_sp(conn, sorted(f.satelite.unique()))
        log.info("import_file_done", file=p.name, kind=kind, rows_read=lidas, rows_in_coverage=len(df),
                 duplicate_keys_dropped=len(df) - len(f), satellites=sorted(f.satelite.unique()),
                 quality=sorted(f.qualidade.unique()), period_start=f.datahora_utc.min(),
                 period_end=f.datahora_utc.max(), inserted=ins, updated=upd_n, nrt_replaced_by_sp=sub,
                 duration_ms=ms_desde(inicio))
        totais["detections_inserted"] += ins
        totais["detections_updated"] += upd_n
        totais["nrt_replaced_by_sp"] += sub
    return totais


def drop_nrt_under_sp(conn, satelites):
    """O NRT só vale depois do último dia SP do satélite: quando o SP chega, ele substitui o NRT daqueles dias.

    As coordenadas mudam um pouco no reprocessamento, então a chave única não junta os dois; sem isto o
    mesmo fogo contaria duas vezes. Roda depois de cada arquivo, então a ordem de importação não importa.
    """
    n = 0
    for sat in satelites:
        apagados = conn.execute("""
            DELETE FROM focos
            WHERE satelite = %(s)s AND qualidade = 'NRT'
              AND datahora_utc < (SELECT date_trunc('day', max(datahora_utc)) + interval '1 day'
                                  FROM focos WHERE satelite = %(s)s AND qualidade = 'SP')""", {"s": sat}).rowcount
        if apagados:
            log.info("nrt_replaced_by_sp", satellite=sat, rows=apagados)
        n += apagados
    return n


# ---------------------------------------------------------------- inpe (A2)
INPE_JSON = "https://data.inpe.br/queimadas/estatisticas/media/estatistica/paises/brasil.json"
INPE_CSV = ROOT / "referencia" / "inpe_mensal_biomas.csv"


def inpe_mensal(d):
    """JSON de estatísticas do INPE (histórico mensal por estado × bioma) -> bioma × ano × mês.

    O INPE troca de satélite de referência (NOAA-12 até 03/07/2002, AQUA_M-T depois): a coluna `satelite`
    evita ler a troca como aumento de fogo. Mês com satélite é o da faixa que contém o dia 15.
    `parcial` marca o mês de `data_limite`, que ainda não acabou.
    """
    rows = [(h["bioma"]["nome_bioma"], h["ano"], int(m), n)
            for h in d["historico_mensal"] for m, n in h["meses"].items() if n is not None]
    df = pd.DataFrame(rows, columns=["bioma", "ano", "mes", "focos"])
    df = df.groupby(["bioma", "ano", "mes"], as_index=False).focos.sum()
    lim = pd.Timestamp(d["meta"]["data_limite"])
    dia15 = pd.to_datetime(dict(year=df.ano, month=df.mes, day=15)).clip(upper=lim)  # mês atual: até o limite
    df["satelite"] = None
    for f in d["meta"]["faixas_de_satelite"]:
        df.loc[dia15.between(pd.Timestamp(f["inicio"]), pd.Timestamp(f["fim"])), "satelite"] = f["satelite"]
    df["parcial"] = (df.ano == lim.year) & (df.mes == lim.month) & (lim.day < lim.days_in_month)
    return df


def inpe():
    """Série mensal de focos do INPE por bioma (satélite de referência AQUA_M-T desde 04/07/2002), para validar (B6)."""
    # shortcut: é o JSON que a página data.inpe.br/queimadas/estatisticas carrega (não documentado);
    # se mudar de formato, a leitura falha em vez de gravar dado errado.
    d = json.loads(curl(INPE_JSON))
    df = inpe_mensal(d)
    INPE_CSV.parent.mkdir(exist_ok=True)
    df.to_csv(INPE_CSV, index=False)
    log.info("inpe_series_saved", rows=len(df), data_limit=d["meta"]["data_limite"], file=INPE_CSV.name,
             satellite_ranges=d["meta"]["faixas_de_satelite"])


def main(argv):
    cmd = argv[0]
    inicio = time.monotonic()
    log.info("command_started", command=cmd)
    try:
        if cmd == "importar":
            importar(argv[1:])
        else:
            {"cadastrar": cadastrar, "download": download, "stage": stage, "clean": clean,
             "sem_dados": sem_dados, "inpe": inpe}[cmd]()
    except BaseException:
        log.exception("command_failed", command=cmd, duration_ms=ms_desde(inicio))
        raise
    log.info("command_finished", command=cmd, duration_ms=ms_desde(inicio))


if __name__ == "__main__":
    main(sys.argv[1:])
