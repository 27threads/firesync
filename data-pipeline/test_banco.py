"""Teste de integração com Postgres: importar, SP substituindo NRT, cobertura e agregar.

Precisa de um banco DESCARTÁVEL (PostGIS) em TEST_DATABASE_URL. Recusa rodar se `focos` já tiver dados.
Banco de teste em um comando (bash):
    docker run -d --rm --name firesync-db-teste -e POSTGRES_PASSWORD=teste -e POSTGRES_DB=firesync_teste -p 5434:5432 postgis/postgis:16-3.4
    TEST_DATABASE_URL=postgresql://postgres:teste@localhost:5434/firesync_teste python test_banco.py
"""
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

import h3
import pandas as pd

url = os.environ.get("TEST_DATABASE_URL")
if not url:
    sys.exit("defina TEST_DATABASE_URL (banco descartável); nada foi testado")
os.environ["DATABASE_URL"] = url

import agregar  # noqa: E402
import pipeline as p  # noqa: E402

conn = p.db()
for m in sorted((p.ROOT / "migrations").glob("*.sql")):  # idempotentes
    conn.execute(m.read_text(encoding="utf-8"))
if conn.execute("SELECT count(*) FROM focos").fetchone()[0]:
    sys.exit("focos já tem dados: use um banco descartável")

# uma região retangular de teste e as células dela
conn.execute("DELETE FROM regioes")
rid = conn.execute("""INSERT INTO regioes (nome, geom, fonte_poligono)
                      VALUES ('Teste', ST_Multi(ST_MakeEnvelope(-61, -4, -59, -2, 4326)), 'teste') RETURNING id""").fetchone()[0]
res = int(p.config(conn, "h3_resolucao"))

COLS = ["latitude", "longitude", "bright_ti4", "scan", "track", "acq_date", "acq_time", "satellite",
        "instrument", "confidence", "version", "bright_ti5", "frp", "daynight"]
sp = pd.DataFrame([
    [-3.1, -60.1, 330, 0.4, 0.4, "2020-09-01", "1730", "N", "VIIRS", "n", "2", 290, 5.0, "D", 0],  # conta
    [-3.2, -60.2, 330, 0.4, 0.4, "2020-09-02", "1730", "N", "VIIRS", "h", "2", 290, 9.0, "D", 0],  # conta
    [-3.3, -60.3, 330, 0.4, 0.4, "2020-09-02", "1730", "N", "VIIRS", "l", "2", 290, 2.0, "D", 0],  # baixa: fora
    [-3.4, -60.4, 330, 0.4, 0.4, "2020-09-02", "0430", "N", "VIIRS", "n", "2", 290, 3.0, "N", 2],  # type 2: fora
    [-3.5, -60.5, 330, 0.4, 0.4, "2020-09-02", "0430", "N", "VIIRS", "n", "2", 290, 0.0, "N", 0],  # frp 0: fora
], columns=COLS + ["type"])
nrt = pd.DataFrame([
    [-3.21, -60.21, 330, 0.4, 0.4, "2020-09-02", "1731", "N", "VIIRS", "n", "2.0NRT", 290, 9.0, "D"],  # SP já tem o dia: sai
    [-3.6, -60.6, 330, 0.4, 0.4, "2020-09-03", "1730", "N", "VIIRS", "n", "2.0NRT", 290, 4.0, "D"],    # depois do SP: fica
], columns=COLS)

with tempfile.TemporaryDirectory() as d:
    sp_csv, nrt_csv = Path(d) / "sp.csv", Path(d) / "nrt.csv"
    sp.to_csv(sp_csv, index=False)
    nrt.to_csv(nrt_csv, index=False)
    cells = {h3.str_to_int(h3.latlng_to_cell(a, b, res)) for a, b in zip(pd.concat([sp, nrt]).latitude,
                                                                          pd.concat([sp, nrt]).longitude)}
    with conn.cursor().copy("COPY celula_regiao (h3, regiao_id) FROM STDIN") as cp:
        for c in cells:
            cp.write_row((c, rid))

    p.importar([nrt_csv])  # NRT antes do SP: a ordem não pode importar
    p.importar([sp_csv])
    q = "SELECT qualidade, datahora_utc::date, count(*) FROM focos GROUP BY 1, 2 ORDER BY 1, 2"
    got = conn.execute(q).fetchall()
    assert got == [("NRT", date(2020, 9, 3), 1), ("SP", date(2020, 9, 1), 1), ("SP", date(2020, 9, 2), 4)], got

    p.importar([nrt_csv])  # NRT de novo depois do SP: o dia com SP continua fora
    assert conn.execute(q).fetchall() == got
    p.importar([sp_csv])   # reimportar não duplica
    assert conn.execute("SELECT count(*) FROM focos").fetchone()[0] == 6

    cob = conn.execute("SELECT satelite, data_inicio, data_fim FROM cobertura WHERE regiao_id = %s", (rid,)).fetchall()
    assert cob == [("SNPP", date(2020, 9, 1), date(2020, 9, 3))], cob

    agregar.agregar(date(2020, 9, 1), date(2020, 10, 1))
    agregar.agregar(date(2020, 9, 1), date(2020, 10, 1))  # duas vezes, mesmo resultado
    tot = conn.execute("SELECT sum(focos_brutos), sum(frp_soma), count(DISTINCT satelite) FROM agregados").fetchone()
    assert tot == (3, 18.0, 1), tot  # 2 SP válidos + 1 NRT; frp 5 + 9 + 4

    # as regras do clean (pandas) e do agregar (SQL) mantêm os mesmos focos
    main, _ = p.clean_viirs(p.normalize(sp.astype({"acq_time": str, "version": str, "confidence": str}), "viirs"), {})
    sp_agregado = conn.execute("""SELECT count(*) FROM focos WHERE qualidade = 'SP' AND confianca IN ('nominal','alta')
                                  AND tipo = 0 AND frp > 0""").fetchone()[0]
    assert len(main) == sp_agregado == 2, (len(main), sp_agregado)

print("ok (banco)")
