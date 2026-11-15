import json
import os
from pathlib import Path


def load_rules():
    path = Path(os.environ.get('ALERT_RULES_PATH', Path(__file__).resolve().parents[5] / 'config' / 'alert_rules.json'))
    return json.loads(path.read_text(encoding='utf-8'))
