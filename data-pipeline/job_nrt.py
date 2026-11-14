"""Job NRT (issue #5): mantém `focos` e `agregados` atualizados com os dados quase em tempo real do FIRMS.

Uso:
    python job_nrt.py          # uma rodada (o container chama a cada 3 h)

Cada rodada:
    1. baixa as últimas 48 h de VIIRS_NOAA20_NRT e VIIRS_NOAA21_NRT no bbox da cobertura;
    2. importa (upsert em `focos`, cobertura e SP substituindo NRT, ver pipeline.importar);
    3. refaz `agregados` só dos meses da janela;
    4. atualiza `dias_sem_dados`;
    5. grava `config.atualizado_em` (UTC, ISO 8601) para a API mostrar quão fresco é o dado.
Uma rodada que falha no meio não grava `atualizado_em`, então a API continua mostrando a última que deu certo.
"""
import sys
from datetime import datetime, timedelta, timezone

import agregar
import pipeline as p

FONTES = ["VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"]
DIAS = 2  # a API devolve de hoje até hoje-(DIAS-1): 48 h
LOCK = 5_4815  # id da trava no Postgres: só uma rodada por vez


def meses_da_janela(hoje, dias=DIAS):
    """[primeiro dia do mês do dia mais antigo da janela, primeiro dia do mês seguinte a hoje)."""
    ini = (hoje - timedelta(days=dias - 1)).replace(day=1)
    return ini, agregar.proximo_mes(hoje.replace(day=1))


def rodada():
    conn = p.db()
    if not conn.execute("SELECT pg_try_advisory_lock(%s)", (LOCK,)).fetchone()[0]:
        print("job_nrt: outra rodada ainda está rodando; esta sai sem fazer nada", flush=True)
        return
    key = p.env("FIRMS_MAP_KEY")
    regions = p.load_regions(conn)
    if regions.empty:
        sys.exit("tabela regioes vazia: rode `python pipeline.py cadastrar` antes")
    bbox = ",".join(f"{v:.2f}" for v in p.bbox_of(regions))
    agora = datetime.now(timezone.utc)
    pasta = p.RAW / "nrt_job"
    pasta.mkdir(parents=True, exist_ok=True)
    arquivos = []
    for fonte in FONTES:
        dest = pasta / f"{fonte}_{agora:%Y%m%dT%H%M}.csv"
        p.curl(f"{p.API}/area/csv/{key}/{fonte}/{bbox}/{DIAS}", dest)
        arquivos.append(dest)
    p.importar(arquivos)
    agregar.agregar(*meses_da_janela(agora.date()))
    p.sem_dados()
    conn.execute("""INSERT INTO config (chave, valor) VALUES ('atualizado_em', %s)
                    ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor""", (agora.isoformat(timespec="seconds"),))
    for a in arquivos:  # já está no banco; dá para baixar de novo se precisar
        a.unlink()
    print(f"job_nrt: ok, atualizado_em = {agora:%Y-%m-%dT%H:%M:%S}Z", flush=True)


if __name__ == "__main__":
    rodada()
