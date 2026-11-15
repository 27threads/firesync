"""Logs estruturados (RNF07): uma linha JSON por evento, em UTC, com o contexto da rodada. Não precisa de banco."""
import json
from datetime import date, datetime
from io import BytesIO, TextIOWrapper

import numpy as np

import logs


def test_evento_vira_uma_linha_json_com_hora_utc(capturar_logs):
    logs.logger("job_nrt").info("nrt_run_started", sources=["VIIRS_NOAA20_NRT"], days=2)

    [linha] = capturar_logs()
    assert linha["event"] == "nrt_run_started"
    assert linha["level"] == "info"
    assert linha["logger"] == "firesync.job_nrt"
    assert linha["sources"] == ["VIIRS_NOAA20_NRT"] and linha["days"] == 2
    assert linha["ts"].endswith("Z")
    datetime.strptime(linha["ts"], "%Y-%m-%dT%H:%M:%S.%fZ")


def test_contexto_entra_em_todos_os_eventos_e_sai_no_fim(capturar_logs):
    log = logs.logger("job_nrt")
    with logs.context(run_id="abc"):
        log.info("dentro")
        with logs.context(step="download"):
            log.info("aninhado")
        log.info("depois_do_aninhado")
    log.info("fora")

    dentro, aninhado, depois, fora = capturar_logs()
    assert dentro["run_id"] == "abc" and "step" not in dentro
    assert aninhado["run_id"] == "abc" and aninhado["step"] == "download"
    assert "step" not in depois
    assert "run_id" not in fora


def test_excecao_registra_tipo_mensagem_e_traceback(capturar_logs):
    log = logs.logger("job_nrt")
    try:
        raise RuntimeError("curl falhou (22)")
    except RuntimeError:
        log.exception("nrt_run_failed", step="download")

    [linha] = capturar_logs()
    assert linha["level"] == "error"
    assert linha["step"] == "download"
    assert linha["error_type"] == "RuntimeError"
    assert linha["error_message"] == "curl falhou (22)"
    assert "Traceback" in linha["traceback"]


def test_valores_do_numpy_e_datas_viram_json(capturar_logs):
    logs.logger("importar").info("import_file_done", inserted=np.int64(5), start=date(2026, 11, 1))

    [linha] = capturar_logs()
    assert linha["inserted"] == 5
    assert linha["start"] == "2026-11-01"


def test_saida_sempre_em_utf8_mesmo_com_terminal_cp1252(capturar_logs):
    """Bug achado na simulação: no Windows o stderr é cp1252 e "Amazônia" virava "Amaz\\xf4nia" no arquivo."""
    bruto = BytesIO()
    saida = TextIOWrapper(bruto, encoding="cp1252")
    logs.configure(saida)
    logs.logger("pipeline").info("region_registered", region="Amazônia")
    saida.flush()

    linha = json.loads(bruto.getvalue().decode("utf-8"))
    assert linha["region"] == "Amazônia"


def test_debug_fica_de_fora_por_padrao(capturar_logs):
    log = logs.logger("download")
    log.debug("download_skipped", reason="already_downloaded")
    log.warning("nrt_run_skipped", reason="lock_held")

    [linha] = capturar_logs()
    assert linha["event"] == "nrt_run_skipped" and linha["level"] == "warning"


def test_log_level_do_ambiente_liga_o_debug(capturar_logs, monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    logs.configure(capturar_logs.stream)
    logs.logger("download").debug("download_skipped", reason="already_downloaded")

    [linha] = capturar_logs()
    assert json.dumps(linha)  # é JSON válido
    assert linha["level"] == "debug"
