import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# o código da API vai em backend/src/firesync_api (arquitetura hexagonal, ver docs/arquitetura.md)
sys.path.insert(0, str(ROOT / "backend" / "src"))


@pytest.fixture(scope="session")
def api_example():
    return json.loads((ROOT / "docs" / "api-exemplo.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def alert_rules():
    return json.loads((ROOT / "config" / "alert_rules.json").read_text(encoding="utf-8"))
