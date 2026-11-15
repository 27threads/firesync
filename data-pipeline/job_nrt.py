"""Job NRT (issue #5): mantém `focos` e `agregados` atualizados com os dados quase em tempo real do FIRMS.

Uso:
    python job_nrt.py          # uma rodada (o container chama a cada 3 h)

Cada rodada:
    1. baixa VIIRS_NOAA20_NRT e VIIRS_NOAA21_NRT no bbox da cobertura, do último dia NRT gravado até hoje
       (no mínimo 48 h, no máximo os 5 dias que a API de área aceita): um job parado não deixa buraco;
    2. importa (upsert em `focos`, cobertura e SP substituindo NRT, ver pipeline.importar);
    3. atualiza `dias_sem_dados` (se a página do FIRMS falhar, segue com a tabela antiga e registra um aviso);
    4. refaz `agregados` e `agregados_diarios` dos meses da janela e grava `config.atualizado_em` (UTC, ISO 8601
       com Z, o `updated_at` do api.md) na mesma transação (issue #15).
Uma rodada que falha no meio não grava `atualizado_em`, então a API continua mostrando a última que deu certo.
Logs (RNF07): todos os eventos da rodada levam o mesmo `run_id`; o fim registra quantos focos entraram e quanto
tempo levou, e a falha registra em que etapa parou (ver logs.py).
"""
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import agregar
import logs
import pipeline as p

FONTES = ["VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"]
DIAS = 2  # mínimo: a API devolve de hoje até hoje-(DIAS-1), 48 h
MAX_DIAS = 5  # teto do DAY_RANGE da API de área do FIRMS (1..5)
LOCK = 5_4815  # id da trava no Postgres: só uma rodada por vez

log = logs.logger("job_nrt")


def dias_da_janela(hoje, ultimo_nrt):
    """Dias a baixar: do último dia com NRT gravado até hoje, entre DIAS e MAX_DIAS. Sem NRT no banco, o máximo."""
    if ultimo_nrt is None:
        return MAX_DIAS
    return min(MAX_DIAS, max(DIAS, (hoje - ultimo_nrt).days + 1))


def meses_da_janela(hoje, dias=DIAS):
    """[primeiro dia do mês do dia mais antigo da janela, primeiro dia do mês seguinte a hoje)."""
    ini = (hoje - timedelta(days=dias - 1)).replace(day=1)
    return ini, agregar.proximo_mes(hoje.replace(day=1))


def rodada():
    with logs.context(run_id=uuid.uuid4().hex[:12]):
        conn = p.db()
        if not conn.execute("SELECT pg_try_advisory_lock(%s)", (LOCK,)).fetchone()[0]:
            log.warning("nrt_run_skipped", reason="lock_held")
            return
        inicio = time.monotonic()
        etapa = Etapa()
        try:
            resultado = executar(conn, etapa)
        except BaseException:
            log.exception("nrt_run_failed", step=etapa.atual, duration_ms=p.ms_desde(inicio))
            raise
        log.info("nrt_run_finished", duration_ms=p.ms_desde(inicio), **resultado)


class Etapa:
    """Em que etapa a rodada está, para o evento de falha dizer onde parou."""

    def __init__(self):
        self.atual = "setup"


def executar(conn, etapa):
    key = p.env("FIRMS_MAP_KEY")
    regions = p.load_regions(conn)
    if regions.empty:
        sys.exit("tabela regioes vazia: rode `python pipeline.py cadastrar` antes")
    bbox = ",".join(f"{v:.2f}" for v in p.bbox_of(regions))
    agora = datetime.now(timezone.utc)
    ultimo = conn.execute("SELECT max(datahora_utc)::date FROM focos WHERE qualidade = 'NRT' AND sensor = 'VIIRS'"
                          ).fetchone()[0]
    dias = dias_da_janela(agora.date(), ultimo)
    log.info("nrt_run_started", sources=FONTES, days=dias, last_nrt_day=ultimo, bbox=bbox, regions=len(regions))
    pasta = p.RAW / "nrt_job"
    pasta.mkdir(parents=True, exist_ok=True)
    arquivos = []
    etapa.atual = "download"
    for fonte in FONTES:
        dest = pasta / f"{fonte}_{agora:%Y%m%dT%H%M}.csv"
        p.curl(f"{p.API}/area/csv/{key}/{fonte}/{bbox}/{dias}", dest)
        arquivos.append(dest)
        log.info("nrt_download_done", source=fonte, file=dest.name, bytes=dest.stat().st_size)
    etapa.atual = "import"
    totais = p.importar(arquivos)
    etapa.atual = "missing_days"
    try:
        p.sem_dados()
    except Exception as erro:  # JSON não documentado do FIRMS: se quebrar, segue com a tabela antiga
        log.warning("missing_days_failed", error=repr(erro))
    # por último: o commit da agregação leva a versão nova junto com os dados (issue #15)
    etapa.atual = "aggregate"
    versao = agregar.agregar(*meses_da_janela(agora.date(), dias))
    for a in arquivos:  # já está no banco; dá para baixar de novo se precisar
        a.unlink()
    return {**totais, "updated_at": versao}


if __name__ == "__main__":
    rodada()
