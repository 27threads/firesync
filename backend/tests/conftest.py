import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# O pacote backend é instalado pelo pyproject.toml; não altere sys.path nos testes.


@pytest.fixture(scope="session")
def api_example():
    return json.loads((ROOT / "docs" / "api-exemplo.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def alert_rules():
    return json.loads((ROOT / "config" / "alert_rules.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def risk_rules():
    return json.loads((ROOT / "config" / "risk_rules.json").read_text(encoding="utf-8"))
