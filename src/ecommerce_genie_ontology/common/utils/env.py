from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from ecommerce_genie_ontology.common.paths import PROJECT_ROOT


def find_env_file() -> Path | None:
    for candidate in (Path.cwd() / ".env", PROJECT_ROOT / ".env"):
        if candidate.is_file():
            return candidate
    return None


def load_env() -> Path | None:
    env_file = find_env_file()
    if env_file is not None:
        load_dotenv(env_file, override=False)
        _fill_blank(env_file)
    else:
        load_dotenv(override=False)
    return env_file


def _fill_blank(env_file: Path) -> None:
    for raw in env_file.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and value and not os.getenv(key, "").strip():
            os.environ[key] = value


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(
            f"Missing required setting {name}. Copy .env.example to .env and fill in credentials."
        )
    return value


def optional_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def optional_int(name: str, default: int) -> int:
    raw = optional_env(name, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


def env_emails(name: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in optional_env(name).split(",") if part.strip())
