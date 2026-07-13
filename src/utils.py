from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT_DIR / "config"
UPLOADS_DIR = ROOT_DIR / "uploads"
OUTPUTS_DIR = ROOT_DIR / "outputs"
RAW_MATERIALS_DIR = ROOT_DIR / "20260707南铝板带销售合同及模板"


def ensure_directories() -> None:
    for directory in (UPLOADS_DIR, OUTPUTS_DIR, ROOT_DIR / "data"):
        directory.mkdir(parents=True, exist_ok=True)


def load_environment() -> None:
    load_dotenv(ROOT_DIR / ".env")


def load_contract_config() -> dict[str, Any]:
    path = CONFIG_DIR / "contract_types.yaml"
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def env_value(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def safe_filename(value: str) -> str:
    banned = '<>:"/\\|?*'
    cleaned = "".join("_" if c in banned else c for c in value)
    cleaned = cleaned.strip().strip(".")
    return cleaned or "未命名合同"


def find_materials_base() -> Path | None:
    if not RAW_MATERIALS_DIR.exists():
        return None
    nested = RAW_MATERIALS_DIR / "20260707南铝板带销售合同及模板"
    return nested if nested.exists() else RAW_MATERIALS_DIR
