from __future__ import annotations

from contextlib import closing
from datetime import datetime
import logging
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Optional

logger = logging.getLogger("sickshift_dashboard.db_backup")

DEFAULT_BACKUP_KEEP_DAYS = 7
SQLITE_HEADER_PREFIX = b"SQLite format 3\x00"


def _backup_keep_days() -> int:
    raw = os.environ.get("SICKSHIFT_BACKUP_KEEP_DAYS", str(DEFAULT_BACKUP_KEEP_DAYS))
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_BACKUP_KEEP_DAYS


def _is_valid_sqlite(path: Path) -> bool:
    try:
        if not path.is_file() or path.stat().st_size < 100:
            return False
        with path.open("rb") as fh:
            return fh.read(16) == SQLITE_HEADER_PREFIX
    except OSError:
        return False


def backup_database(
    db_path: str | Path,
    backup_dir: Optional[str | Path] = None,
    keep_days: Optional[int] = None,
    force: bool = False,
) -> dict[str, Any]:
    """Create a hot online SQLite backup using sqlite3.backup() with rolling retention.

    Safe to run while SickShift is actively reading/writing the database.
    Creates at most one backup per calendar day unless force=True.
    """
    src_path = Path(db_path).resolve()
    if not _is_valid_sqlite(src_path):
        return {"status": "skipped", "reason": "invalid_or_missing_db"}

    env_dir = os.environ.get("SICKSHIFT_BACKUP_DIR", "").strip()
    if backup_dir is not None:
        dest_dir = Path(backup_dir)
    elif env_dir:
        dest_dir = Path(env_dir)
    else:
        dest_dir = src_path.parent / "backups"

    dest_dir.mkdir(parents=True, exist_ok=True)

    # Clean any stray .tmp files from interrupted runs
    for tmp in dest_dir.glob("sickshift-*.db.tmp"):
        try:
            tmp.unlink()
        except OSError:
            continue

    today_tag = datetime.now().strftime("%Y%m%d")
    target_path = dest_dir / f"sickshift-{today_tag}.db"

    created = False
    if force or not target_path.is_file():
        tmp_path = dest_dir / f"sickshift-{today_tag}.db.tmp"
        clean_src = src_path.as_posix()
        if not clean_src.startswith("/"):
            clean_src = "/" + clean_src
        src_uri = f"file:{clean_src}?mode=ro&uri=true"
        try:
            with closing(sqlite3.connect(src_uri, uri=True, timeout=15)) as src_conn:
                with closing(sqlite3.connect(str(tmp_path), timeout=15)) as dst_conn:
                    src_conn.backup(dst_conn, pages=256, sleep=0.05)
            os.replace(tmp_path, target_path)
            created = True
            logger.info("Hot SQLite backup created: %s", target_path.name)
        except Exception as exc:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            logger.warning("Hot SQLite backup failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    # Rolling retention (default 7 days)
    retention_days = _backup_keep_days() if keep_days is None else max(1, int(keep_days))
    cutoff = time.time() - (retention_days * 86400)
    pruned = 0
    for old in dest_dir.glob("sickshift-*.db"):
        if old.resolve() == target_path.resolve():
            continue
        try:
            if old.is_file() and old.stat().st_mtime < cutoff:
                old.unlink()
                pruned += 1
        except OSError:
            continue

    return {
        "status": "ok" if created else "skipped",
        "created": created,
        "backup_file": target_path.name,
        "pruned": pruned,
        "keep_days": retention_days,
    }
