from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import subprocess
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple

import requests

logger = logging.getLogger("sickshift_dashboard.soundtrack")

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache" / "soundtracks"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

PLEX_THEMES_URL_TPL = "https://tvthemes.plexapp.com/{tvdb_id}.mp3"
THEMERR_TV_URL_TPL = "https://app.lizardbyte.dev/ThemerrDB/tv_shows/themoviedb/{tmdb_id}.json"


def get_default_db_path() -> Path:
    from sickshift_dashboard.config import load_config
    cfg = load_config()
    if cfg.db_path and Path(cfg.db_path).is_file():
        return Path(cfg.db_path)
    parent_db = Path(__file__).resolve().parent.parent / "sickbeard.db"
    if parent_db.is_file():
        return parent_db
    return Path("sickbeard.db")


def resolve_tvdb_id(indexer: int, show_id: int, cursor: sqlite3.Cursor) -> Optional[int]:
    """Resolves the canonical TheTVDB ID for a show, mapping from TVmaze/TMDB if necessary."""
    if indexer == 1:
        return show_id

    # Check indexer_mapping table (mindexer 1 = TheTVDB)
    try:
        cursor.execute(
            "SELECT mindexer_id FROM indexer_mapping WHERE indexer_id=? AND indexer=? AND mindexer=1",
            (show_id, indexer),
        )
        row = cursor.fetchone()
        if row and row[0]:
            return int(row[0])
    except Exception as exc:
        logger.warning(f"Failed to query indexer_mapping for TVDB ID: {exc}")

    return None


def resolve_tmdb_id(indexer: int, show_id: int, cursor: sqlite3.Cursor) -> Optional[int]:
    """Resolves the TMDb ID for a show, mapping from TVDB/TVmaze if necessary."""
    if indexer == 4:
        return show_id

    # Check indexer_mapping table (mindexer 4 = TMDb)
    try:
        cursor.execute(
            "SELECT mindexer_id FROM indexer_mapping WHERE indexer_id=? AND indexer=? AND mindexer=4",
            (show_id, indexer),
        )
        row = cursor.fetchone()
        if row and row[0]:
            return int(row[0])
    except Exception as exc:
        logger.warning(f"Failed to query indexer_mapping for TMDB ID: {exc}")

    return None


def find_local_theme_file(location: Optional[str]) -> Optional[Path]:
    """Checks show directory on disk for local theme files."""
    if not location or not os.path.isdir(location):
        return None

    candidates = ["theme.mp3", "soundtrack.mp3", "theme.m4a", "theme.ogg", "theme.wav"]
    for cand in candidates:
        target = Path(location) / cand
        if target.is_file() and target.stat().st_size > 1024:
            return target

    return None


def find_cached_theme_file(indexer: int, show_id: int) -> Optional[Path]:
    """Checks dashboard cache directory for pre-downloaded theme files."""
    cand = CACHE_DIR / f"{indexer}_{show_id}.mp3"
    if cand.is_file() and cand.stat().st_size > 1024:
        return cand
    return None


def check_plex_cdn(tvdb_id: int) -> bool:
    """Checks if Plex TV Themes CDN hosts an MP3 for this TVDB ID."""
    url = PLEX_THEMES_URL_TPL.format(tvdb_id=tvdb_id)
    try:
        resp = requests.head(url, timeout=2.5)
        return resp.status_code == 200
    except Exception:
        return False


def get_themerr_youtube_url(tmdb_id: int) -> Optional[str]:
    """Queries ThemerrDB flat JSON repository for community verified theme song YouTube URLs."""
    url = THEMERR_TV_URL_TPL.format(tmdb_id=tmdb_id)
    try:
        resp = requests.get(url, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            yt_url = data.get("youtube_theme_url")
            if yt_url and isinstance(yt_url, str) and "youtube" in yt_url.lower():
                return yt_url
    except Exception as exc:
        logger.debug(f"ThemerrDB lookup failed for TMDB {tmdb_id}: {exc}")
    return None


def download_youtube_theme(url_or_search: str, output_path: Path, max_duration_s: int = 60) -> bool:
    """Downloads audio track via yt-dlp, trims to max_duration_s, and converts to MP3."""
    yt_dlp_bin = shutil.which("yt-dlp") or os.path.expanduser("~/.local/bin/yt-dlp")
    if not os.path.isfile(yt_dlp_bin) and not shutil.which("yt-dlp"):
        logger.warning("yt-dlp executable not found on system path.")
        return False

    temp_dest = output_path.with_suffix(".temp.%(ext)s")
    cmd = [
        yt_dlp_bin,
        "--postprocessor-args",
        f"ffmpeg:-t {max_duration_s}",
        "-x",
        "--audio-format",
        "mp3",
        "--no-playlist",
        "-o",
        str(temp_dest),
        url_or_search,
    ]

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25, check=False)
        real_temp_mp3 = output_path.with_suffix(".temp.mp3")
        if real_temp_mp3.is_file() and real_temp_mp3.stat().st_size > 1024:
            real_temp_mp3.replace(output_path)
            return True
        elif output_path.is_file() and output_path.stat().st_size > 1024:
            return True
    except Exception as exc:
        logger.error(f"yt-dlp soundtrack extraction failed for {url_or_search}: {exc}")

    return False


def get_soundtrack(
    indexer: int,
    show_id: int,
    db_path: Optional[str] = None,
    allow_download: bool = True,
) -> Tuple[Optional[Path], Optional[str]]:
    """Resolves the best available soundtrack audio for a given show.

    Returns:
        (local_file_path, None) if stored locally or in cache.
        (None, remote_plex_url) if available on Plex CDN.
        (None, None) if not available.
    """
    db_file = Path(db_path) if db_path else get_default_db_path()
    if not db_file.is_file():
        logger.error(f"Database not found at {db_file}")
        return None, None

    show_name = ""
    location = None
    tvdb_id = None
    tmdb_id = None

    try:
        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT show_name, location FROM tv_shows WHERE indexer_id=? AND indexer=?",
            (show_id, indexer),
        )
        row = cursor.fetchone()
        if not row:
            cursor.execute("SELECT show_name, location FROM tv_shows WHERE indexer_id=?", (show_id,))
            row = cursor.fetchone()

        if row:
            show_name = row["show_name"] or ""
            location = row["location"]

        tvdb_id = resolve_tvdb_id(indexer, show_id, cursor)
        tmdb_id = resolve_tmdb_id(indexer, show_id, cursor)
        conn.close()
    except Exception as exc:
        logger.error(f"Error querying show details for soundtrack: {exc}")

    # 1. Check local show directory
    local_file = find_local_theme_file(location)
    if local_file:
        return local_file, None

    # 2. Check dashboard cache directory
    cached_file = find_cached_theme_file(indexer, show_id)
    if cached_file:
        return cached_file, None

    # 3. Check Plex CDN using canonical TheTVDB ID
    if tvdb_id and check_plex_cdn(tvdb_id):
        plex_url = PLEX_THEMES_URL_TPL.format(tvdb_id=tvdb_id)
        return None, plex_url

    if not allow_download:
        return None, None

    # 4. Try ThemerrDB YouTube mapping
    target_cache_file = CACHE_DIR / f"{indexer}_{show_id}.mp3"
    target_local_theme = Path(location) / "theme.mp3" if location and os.path.isdir(location) else None

    yt_theme_url = get_themerr_youtube_url(tmdb_id) if tmdb_id else None
    if yt_theme_url:
        ok = download_youtube_theme(yt_theme_url, target_cache_file)
        if ok and target_cache_file.is_file():
            if target_local_theme and not target_local_theme.is_file():
                try:
                    shutil.copy2(target_cache_file, target_local_theme)
                except Exception:
                    pass
            return target_cache_file, None

    # 5. Search YouTube directly
    if show_name:
        queries = [
            f"ytsearch1:{show_name} official theme song audio",
            f"ytsearch1:{show_name} générique début thème",
            f"ytsearch1:{show_name} opening theme soundtrack",
        ]
        for q in queries:
            ok = download_youtube_theme(q, target_cache_file)
            if ok and target_cache_file.is_file():
                if target_local_theme and not target_local_theme.is_file():
                    try:
                        shutil.copy2(target_cache_file, target_local_theme)
                    except Exception:
                        pass
                return target_cache_file, None

    return None, None
