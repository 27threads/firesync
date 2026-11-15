import json
import sys
from io import StringIO
from pathlib import Path

import pytest

# os módulos do pipeline (pipeline.py, agregar.py, job_nrt.py) ficam na pasta acima
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class LogsCapturados:
    """Chamar devolve os eventos gravados até agora, um dict por linha JSON."""

    def __init__(self):
        self.stream = StringIO()

    def __call__(self):
        return [json.loads(linha) for linha in self.stream.getvalue().splitlines()]

    def eventos(self, nome):
        return [linha for linha in self() if linha["event"] == nome]


@pytest.fixture()
def capturar_logs(monkeypatch):
    import logs

    monkeypatch.delenv("LOG_LEVEL", raising=False)
    capturados = LogsCapturados()
    logs.configure(capturados.stream)
    yield capturados
    logs.configure(sys.stderr)
