"""C2: generate small synthetic aggregates; --apply only accepts an empty test/demo DB."""
import argparse
from datetime import datetime, UTC
import os
from pathlib import Path

import h3
import psycopg


def demo_sql(now):
    cell = h3.str_to_int(h3.latlng_to_cell(-4, -61, 6))
    today = now.date().isoformat()
    timestamp = now.isoformat().replace('+00:00', 'Z')
    return f"""
-- Synthetic data only. Never use these counts as scientific observations.
INSERT INTO regioes(nome,geom,fonte_poligono)
VALUES ('Synthetic demo',ST_Multi(ST_MakeEnvelope(-61.5,-4.5,-60.5,-3.5,4326)),'Synthetic test fixture');
INSERT INTO celula_regiao SELECT {cell},id FROM regioes WHERE nome='Synthetic demo';
INSERT INTO cobertura(regiao_id,satelite,data_inicio,data_fim)
SELECT id,satellite,first_day::date,last_day::date FROM regioes CROSS JOIN
(VALUES ('Aqua','2003-01-01','2012-01-31'),('SNPP','2012-02-01','2026-10-31'),('N20','2026-11-01','{today}'))
AS periods(satellite,first_day,last_day) WHERE nome='Synthetic demo';
INSERT INTO fatores_harmonizacao(regiao_id,satelite_origem,satelite_destino,mes,periodo,ano_calibracao,fator)
SELECT id,'Aqua','SNPP',1,'D',year,factor FROM regioes CROSS JOIN (VALUES (2013,2),(2014,4)) AS f(year,factor)
WHERE nome='Synthetic demo';
INSERT INTO agregados SELECT {cell},2003,1,id,'Aqua','D',5,10 FROM regioes WHERE nome='Synthetic demo';
INSERT INTO agregados_diarios
SELECT {cell},day::date,id,'SNPP','D',amount FROM regioes CROSS JOIN
(VALUES (2024,1),(2025,2)) AS baseline(year,amount)
CROSS JOIN LATERAL generate_series(make_date(year,11,14)-40,make_date(year,11,14)+20,'1 day') AS day
WHERE nome='Synthetic demo';
INSERT INTO focos(sensor,satelite,lat,lon,datahora_utc,confianca,frp,periodo,tipo,qualidade,arquivo_origem,h3)
SELECT 'VIIRS',CASE WHEN day::date<'2026-11-01' THEN 'SNPP' ELSE 'N20' END,
-4,-61,day,'nominal',CASE WHEN day::date='{today}' THEN 30 ELSE 2 END,'D',NULL,'NRT','synthetic.csv',{cell}
FROM generate_series('{timestamp}'::timestamptz-interval '6 days','{timestamp}'::timestamptz,'1 day') AS day;
INSERT INTO agregados_diarios
SELECT {cell},datahora_utc::date,r.id,satelite,periodo,count(*) FROM focos JOIN regioes r ON r.nome='Synthetic demo'
WHERE h3={cell} GROUP BY datahora_utc::date,r.id,satelite,periodo;
INSERT INTO agregados
SELECT h3,extract(year from data)::int,extract(month from data)::int,regiao_id,satelite,periodo,sum(focos_brutos),0
FROM agregados_diarios WHERE h3={cell} GROUP BY h3,extract(year from data),extract(month from data),regiao_id,satelite,periodo;
INSERT INTO config VALUES ('data_version','{timestamp}'),('atualizado_em','{timestamp}')
ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor;
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Apply to empty DEMO_DATABASE_URL ending in _test or _demo.')
    args = parser.parse_args()
    sql = demo_sql(datetime.now(UTC))
    if not args.apply:
        print(sql)
        return
    with psycopg.connect(os.environ['DEMO_DATABASE_URL']) as conn:
        if not conn.info.dbname.endswith(('_test', '_demo')):
            raise SystemExit('Use a disposable database whose name ends in _test or _demo.')
        for path in sorted((Path(__file__).resolve().parents[2] / 'data-pipeline' / 'migrations').glob('*.sql')):
            conn.execute(path.read_text(encoding='utf-8'))
        if conn.execute('SELECT count(*) FROM regioes').fetchone()[0]:
            raise SystemExit('Demo database must be empty. No existing data was changed.')
        conn.execute(sql)
    print('Synthetic demo loaded. These are test values, not NASA observations.')


if __name__ == '__main__':
    main()
