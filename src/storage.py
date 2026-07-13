from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .utils import ROOT_DIR


HISTORY_PATH = ROOT_DIR / "data" / "history.json"


def load_history() -> list[dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def add_history(record: dict[str, Any]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    history = load_history()
    history.insert(0, {"created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), **record})
    HISTORY_PATH.write_text(json.dumps(history[:100], ensure_ascii=False, indent=2), encoding="utf-8")
