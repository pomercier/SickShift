from __future__ import annotations

import json
import locale
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def get_default_config_path() -> str:
    """Returns a temporary configuration file path compatible with Linux, macOS, and Windows."""
    return str(Path(tempfile.gettempdir()) / "sickshift_dashboard_config.json")


def find_default_db_path() -> str:
    """Dynamically locates sickbeard.db on any operating system (Linux, macOS, Windows)."""
    # 1. Explicit environment variable
    env_db = os.environ.get("SICKSHIFT_DB")
    if env_db and Path(env_db).is_file():
        return str(Path(env_db).resolve())

    # 2. Native runtime SickShift context
    try:
        import sickshift
        if hasattr(sickshift, "db") and hasattr(sickshift.db, "db_filename"):
            fn = sickshift.db.db_filename()
            if fn and Path(fn).is_file():
                return str(Path(fn).resolve())
        if hasattr(sickshift, "DATA_DIR") and sickshift.DATA_DIR:
            candidate = Path(sickshift.DATA_DIR) / "sickbeard.db"
            if candidate.is_file():
                return str(candidate.resolve())
        if hasattr(sickshift, "PROG_DIR") and sickshift.PROG_DIR:
            candidate = Path(sickshift.PROG_DIR) / "sickbeard.db"
            if candidate.is_file():
                return str(candidate.resolve())
    except Exception:
        pass

    # 3. Dynamic candidate relative to package location or current directory
    try:
        base_dir = Path(__file__).resolve().parent.parent
        for candidate in [base_dir / "sickbeard.db", Path.cwd() / "sickbeard.db"]:
            if candidate.is_file():
                return str(candidate.resolve())
    except Exception:
        pass

    try:
        return str((Path(__file__).resolve().parent.parent / "sickbeard.db").resolve())
    except Exception:
        return "sickbeard.db"


def find_default_port() -> int:
    """Dynamically detects the configured port in SickShift."""
    try:
        import sickshift
        if hasattr(sickshift, "WEB_PORT") and sickshift.WEB_PORT:
            return int(sickshift.WEB_PORT)
    except Exception:
        pass
    return 8081


class Settings(BaseModel):
    base_url: str = ""
    web_root: str = ""
    db_path: str = Field(default_factory=find_default_db_path)
    host: str = "0.0.0.0"
    port: int = Field(default_factory=find_default_port)

    # URL mount prefix (e.g. "/dashboard" when mounted inside SickShift or ASGI)
    mount_prefix: str = ""

    data_cache_ttl_s: int = 30
    redis_cache_ttl_s: int = 60
    bg_update_min: int = 30
    snapshot_poll_s: int = 15

    background_sample_limit: int = 200
    background_candidates: int = 12
    background_history_size: int = 20

    # Optional conversion of posters to WebP format
    webp_enabled: bool = True
    webp_cache_dir: str = ""
    webp_quality: int = 82
    webp_method: int = 4
    webp_max_concurrency: int = 4

    enable_gzip: bool = True
    gzip_min_size: int = 1000
    gzip_compress_level: int = 5

    redis_url: str = "redis://localhost:6379"
    redis_enabled: bool = True

    config_file: str = Field(default_factory=get_default_config_path)

    model_config = ConfigDict(extra="ignore")

    @field_validator("db_path", mode="before")
    @classmethod
    def resolve_db_path(cls, value: Any) -> str:
        if not value:
            return find_default_db_path()
        return str(Path(value).resolve())

    @field_validator("config_file", mode="before")
    @classmethod
    def resolve_config_file(cls, value: Any) -> str:
        if not value:
            return get_default_config_path()
        return str(Path(value).resolve())

    @field_validator("port", mode="before")
    @classmethod
    def resolve_port(cls, value: Any) -> int:
        if not value:
            return find_default_port()
        return int(value)

    @field_validator("mount_prefix")
    @classmethod
    def normalize_prefix(cls, value: str) -> str:
        val = (value or "").strip().rstrip("/")
        if val and not val.startswith("/"):
            val = "/" + val
        return val


def load_config(config_file: Optional[str] = None) -> Settings:
    default_path = get_default_config_path()
    config_path = Path(config_file or os.environ.get("SICKSHIFT_CONFIG", default_path))

    if not config_path.exists():
        return Settings(config_file=str(config_path))

    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        data["config_file"] = str(config_path)
        return Settings(**data)
    except Exception as exc:
        print(f"[CONFIG] Unable to load {config_path}: {exc}")
        return Settings(config_file=str(config_path))
