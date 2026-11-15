"""Logs estruturados (RNF07): uma linha JSON por evento, para depurar e seguir o fluxo de cada rodada.

    log = logs.logger("job_nrt")
    with logs.context(run_id="..."):              # entra em todos os eventos dentro do bloco
        log.info("nrt_run_started", days=2)

Cada linha tem `ts` (UTC), `level`, `logger`, `event` e os campos do evento. Nomes de evento e de campo em
inglês (quem lê o repositório público lê inglês). Saída em stderr, que o `docker compose logs` já junta.
Nível pelo ambiente: LOG_LEVEL=DEBUG mostra também as decisões de rotina (arquivo já baixado, etc.).
Nunca registre a URL do FIRMS sem `pipeline.mask_key`: a MAP_KEY vai nela.
"""
import json
import logging
import os
import sys
import traceback
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone

RAIZ = "firesync"
_contexto = ContextVar("contexto_dos_logs", default={})


def _para_json(valor):
    if hasattr(valor, "item"):  # escalares do numpy e do pandas
        return valor.item()
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return str(valor)


class FormatoJson(logging.Formatter):
    def format(self, record):
        linha = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": record.getMessage(),
            **_contexto.get(),
            **getattr(record, "campos", {}),
        }
        if record.exc_info:
            tipo, erro, tb = record.exc_info
            linha["error_type"] = tipo.__name__
            linha["error_message"] = str(erro)
            linha["traceback"] = "".join(traceback.format_exception(tipo, erro, tb))
        return json.dumps(linha, ensure_ascii=False, default=_para_json)


def configure(stream=None):
    """Troca a saída dos logs (padrão: stderr) e relê o LOG_LEVEL. Pode ser chamada de novo."""
    raiz = logging.getLogger(RAIZ)
    for h in list(raiz.handlers):
        raiz.removeHandler(h)
    stream = stream or sys.stderr
    if hasattr(stream, "reconfigure"):  # o stderr do Windows é cp1252: "Amazônia" chegaria quebrada no arquivo
        stream.reconfigure(encoding="utf-8")
    handler = logging.StreamHandler(stream)
    handler.setFormatter(FormatoJson())
    raiz.addHandler(handler)
    raiz.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
    raiz.propagate = False


class Logger:
    """Um evento por chamada: `log.info("nome_do_evento", campo=valor, ...)`."""

    def __init__(self, nome):
        self._log = logging.getLogger(f"{RAIZ}.{nome}")

    def debug(self, evento, **campos):
        self._log.debug(evento, extra={"campos": campos})

    def info(self, evento, **campos):
        self._log.info(evento, extra={"campos": campos})

    def warning(self, evento, **campos):
        self._log.warning(evento, extra={"campos": campos})

    def exception(self, evento, **campos):
        """Dentro de um `except`: grava como erro, com o tipo, a mensagem e o traceback."""
        self._log.error(evento, exc_info=True, extra={"campos": campos})


def logger(nome):
    if not logging.getLogger(RAIZ).handlers:
        configure()
    return Logger(nome)


@contextmanager
def context(**campos):
    """Campos que entram em todos os eventos dentro do bloco (ex.: run_id da rodada, etapa atual)."""
    token = _contexto.set({**_contexto.get(), **campos})
    try:
        yield
    finally:
        _contexto.reset(token)
