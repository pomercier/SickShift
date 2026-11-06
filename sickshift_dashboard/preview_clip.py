from __future__ import annotations

import json
import logging
import os
import random
import re
import shutil
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Optional, Tuple

logger = logging.getLogger("sickshift_dashboard.preview_clip")

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache" / "preview_clips"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_PROBE_CACHE: dict[str, Tuple[float, dict]] = {}


_TOOLS_STATUS = None


def preview_tools_available() -> bool:
    """Require runnable FFmpeg and ffprobe; missing native tools are optional."""
    global _TOOLS_STATUS
    paths = tuple(shutil.which(name) for name in ("ffmpeg", "ffprobe"))
    if not all(paths):
        return False
    try:
        signature = tuple((path, Path(path).stat().st_mtime_ns) for path in paths)
    except OSError:
        return False
    now = time.monotonic()
    if _TOOLS_STATUS and _TOOLS_STATUS[0] == signature and now - _TOOLS_STATUS[1] < 30:
        return _TOOLS_STATUS[2]
    available = True
    for path in paths:
        try:
            result = subprocess.run([path, "-version"], stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, timeout=3)
            if result.returncode != 0:
                available = False
                break
        except (OSError, subprocess.TimeoutExpired):
            available = False
            break
    _TOOLS_STATUS = (signature, now, available)
    return available


def get_default_db_path() -> Path:
    from sickshift_dashboard.config import load_config
    cfg = load_config()
    if cfg.db_path and Path(cfg.db_path).is_file():
        return Path(cfg.db_path)
    parent_db = Path(__file__).resolve().parent.parent / "sickbeard.db"
    if parent_db.is_file():
        return parent_db
    return Path("sickbeard.db")


def resolve_episode_file(
    indexer: int,
    show_id: int,
    season: int,
    episode: int,
    db_path: Optional[Any] = None,
) -> Optional[Path]:
    """Finds the local file path on disk for a given episode."""
    db_file = Path(db_path) if db_path else get_default_db_path()
    if not db_file.is_file():
        return None

    try:
        with sqlite3.connect(str(db_file), timeout=5.0) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT location FROM tv_episodes WHERE indexer=? AND showid=? AND season=? AND episode=?",
                (indexer, show_id, season, episode),
            )
            row = cursor.fetchone()
            if row and row[0]:
                p = Path(row[0])
                if p.is_file():
                    return p

            # Fallback: try by showid alone across indexers if indexer was remapped
            cursor.execute(
                "SELECT location FROM tv_episodes WHERE showid=? AND season=? AND episode=? AND location != ''",
                (show_id, season, episode),
            )
            row = cursor.fetchone()
            if row and row[0]:
                p = Path(row[0])
                if p.is_file():
                    return p
    except Exception as exc:
        logger.error(f"Error querying episode file for {show_id} S{season:02d}E{episode:02d}: {exc}")

    return None


def probe_file(filepath: Path) -> Optional[dict[str, Any]]:
    """Probes media file metadata and stream details via ffprobe."""
    mtime = filepath.stat().st_mtime
    cache_key = f"{filepath}:{mtime}"
    cached = _PROBE_CACHE.get(cache_key)
    if cached:
        return cached[1]

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "stream=index,codec_type,codec_name,color_transfer,color_primaries,color_space:stream_side_data=dv_profile:stream_tags=language,title:format=duration",
        "-of", "json",
        str(filepath),
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode != 0:
            logger.warning(f"ffprobe failed for {filepath}: {res.stderr}")
            return None

        data = json.loads(res.stdout)
        duration = float(data.get("format", {}).get("duration", 0.0))
        streams = data.get("streams", [])
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

        probe_info = {
            "duration": duration,
            "video_streams": video_streams,
            "audio_streams": audio_streams,
        }
        _PROBE_CACHE[cache_key] = (time.time(), probe_info)
        return probe_info
    except Exception as exc:
        logger.error(f"Exception during ffprobe of {filepath}: {exc}")
        return None


def select_audio_stream(
    audio_streams: list[dict[str, Any]],
    sys_lang: str = "fr",
) -> Tuple[Optional[dict[str, Any]], str, str, Optional[str]]:
    """Selects audio track based on priority:
    1. Français Québécois / Canadien (VQ, VFQ, QC, QBC, CA).
    2. Français standard / France (VF, VFF).
    3. English fallback (VO, VOSTFR).
    4. First encoded audio stream.

    Also detects dual-mono tracks (e.g. 'Anglais / Français Québécois') and returns an audio filter.
    Returns (selected_stream, reason, display_name, audio_filter_or_none).
    """
    if not audio_streams:
        return None, "no_audio", "Muet", None

    # Regex patterns for matching
    RE_VQ = re.compile(
        r"\b(vfq|vq|quebec|qu[eé]bec|qu[eé]b[eé]cois|quebecois|canadien|canadienne|fr-ca|fra-ca|qc|qbc)\b",
        re.I,
    )
    RE_FR = re.compile(
        r"\b(vf|vff|vfi|vfb|french|francais|fran[cç]ais)\b",
        re.I,
    )
    RE_EN = re.compile(
        r"\b(english|anglais|vo|vostfr|vost)\b",
        re.I,
    )

    RE_DUAL_EN_FR = re.compile(
        r"anglais\s*/\s*fran[cç]ais|anglais\s*/\s*qu[eé]b[eé]cois|english\s*/\s*french",
        re.I,
    )
    RE_DUAL_FR_EN = re.compile(
        r"fran[cç]ais\s*/\s*anglais|qu[eé]b[eé]cois\s*/\s*anglais|french\s*/\s*english",
        re.I,
    )

    def check_dual_mono(title_str: str) -> Optional[str]:
        if RE_DUAL_EN_FR.search(title_str):
            # Left channel is English, Right channel is French -> map Right channel to both
            return "pan=stereo|c0=c1|c1=c1"
        if RE_DUAL_FR_EN.search(title_str):
            # Left channel is French, Right channel is English -> map Left channel to both
            return "pan=stereo|c0=c0|c1=c0"
        return None

    # 1. Tier 1: Français Québécois / Canadien
    for stream in audio_streams:
        tags = stream.get("tags") or {}
        lang_code = (tags.get("language") or "").lower().strip()
        title = (tags.get("title") or "").strip()

        if lang_code in {"qbc", "fr-ca", "fra-ca"} or RE_VQ.search(title) or RE_VQ.search(lang_code):
            af = check_dual_mono(title)
            return stream, "fr_qc", "Français (Québec)", af

    # 2. Tier 2: Français standard / de France
    for stream in audio_streams:
        tags = stream.get("tags") or {}
        lang_code = (tags.get("language") or "").lower().strip()
        title = (tags.get("title") or "").strip()

        if lang_code in {"fr", "fre", "fra"} or RE_FR.search(title):
            af = check_dual_mono(title)
            return stream, "fr_std", "Français", af

    # 3. Tier 3: English fallback
    for stream in audio_streams:
        tags = stream.get("tags") or {}
        lang_code = (tags.get("language") or "").lower().strip()
        title = (tags.get("title") or "").strip()

        if lang_code in {"en", "eng"} or RE_EN.search(title):
            return stream, "fallback_english", "English", None

    # 4. Tier 4: First encoded audio stream
    first_stream = audio_streams[0]
    tags = first_stream.get("tags") or {}
    lang_tag = tags.get("language") or tags.get("title") or "Piste 1"
    return first_stream, "first_encoded", str(lang_tag).capitalize(), None


def choose_random_timestamp(duration: float, clip_len: int = 20) -> int:
    """Picks a random start timestamp within the file, avoiding intros and credits."""
    if duration <= clip_len + 30:
        return 0

    min_start = int(max(45, duration * 0.12))
    max_start = int(min(duration - clip_len - 30, duration * 0.88))

    if max_start <= min_start:
        return min_start

    return random.randint(min_start, max_start)


def format_timestamp(seconds: int) -> str:
    """Formats seconds into MM:SS or HH:MM:SS."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def preview_video_filters(video_stream: dict[str, Any]) -> str:
    """Keep previews small and convert HDR to SDR before encoding browser-safe 8-bit video."""
    if any(data.get("dv_profile") == 5 for data in video_stream.get("side_data_list", [])):
        # Profile 5 uses IPTPQc2 rather than ordinary YCbCr. Preserve the
        # original samples and Dolby metadata until libplacebo reshapes them.
        return (
            "fps=24,libplacebo=w=854:h=480:force_original_aspect_ratio=decrease:"
            "force_divisible_by=2:format=yuv420p:colorspace=bt709:"
            "color_primaries=bt709:color_trc=bt709:range=tv:"
            "apply_dolbyvision=true,format=yuv420p,setsar=1"
        )
    filters = [
        "fps=24",
        r"scale=w=min(854\,iw):h=min(480\,ih):force_original_aspect_ratio=decrease:force_divisible_by=2:out_range=tv",
    ]
    transfer = video_stream.get("color_transfer")
    if transfer in {"smpte2084", "arib-std-b67"}:
        # Work at preview resolution, not 4K, for the expensive float conversion.
        primaries = video_stream.get("color_primaries") or "bt2020"
        matrix = video_stream.get("color_space") or "bt2020nc"
        if primaries == "unknown":
            primaries = "bt2020"
        if matrix == "unknown":
            matrix = "bt2020nc"
        filters.extend([
            f"zscale=tin={transfer}:pin={primaries}:min={matrix}:t=linear:npl=100",
            "format=gbrpf32le",
            "zscale=p=bt709",
            "tonemap=tonemap=hable:desat=0",
            "zscale=t=bt709:m=bt709:r=tv",
        ])
    filters.extend(["format=yuv420p", "setsar=1"])
    return ",".join(filters)


def get_or_create_preview_clip(
    filepath: Path,
    indexer: int,
    show_id: int,
    season: int,
    episode: int,
    sys_lang: str = "fr",
    force_new: bool = False,
    clip_len: int = 20,
) -> Optional[dict[str, Any]]:
    """Generates or retrieves a cached video preview clip for the given episode."""
    if not preview_tools_available():
        return None
    probe = probe_file(filepath)
    if not probe:
        return None

    duration = probe["duration"]
    video_streams = probe["video_streams"]
    audio_streams = probe["audio_streams"]

    if not video_streams:
        logger.warning(f"No video streams found in {filepath}")
        return None

    video_stream = video_streams[0]
    chosen_audio, reason, lang_display, audio_filter = select_audio_stream(audio_streams, sys_lang=sys_lang)

    audio_idx = chosen_audio["index"] if chosen_audio else 0
    audio_map = f"0:{audio_idx}" if chosen_audio else "0:a:0"

    source_stat = filepath.stat()
    mtime_int = source_stat.st_mtime_ns
    # Version the encoding so old High 10/HDR clips cannot be reused.
    base_prefix = (
        f"clip_v3_{indexer}_{show_id}_s{season:02d}e{episode:02d}_a{audio_idx}"
        f"_m{mtime_int}_b{source_stat.st_size}_d{clip_len}"
    )

    # Check for existing cached clips for this episode/audio
    existing_clips = sorted(CACHE_DIR.glob(f"{base_prefix}_*.mp4"))

    if existing_clips and not force_new:
        target_clip = existing_clips[0]
        parts = target_clip.stem.split("_")
        try:
            start_sec = int(parts[-2])
        except (ValueError, IndexError):
            start_sec = 0

        return {
            "clip_path": target_clip,
            "filename": filepath.name,
            "duration": duration,
            "start_sec": start_sec,
            "start_formatted": format_timestamp(start_sec),
            "clip_len": clip_len,
            "audio_reason": reason,
            "audio_lang": lang_display,
        }

    # Generate new random clip
    start_sec = choose_random_timestamp(duration, clip_len=clip_len)
    output_filename = f"{base_prefix}_{start_sec}_{mtime_int}.mp4"
    output_path = CACHE_DIR / output_filename
    # Keep in-progress files outside the cache lookup pattern.
    temp_path = CACHE_DIR / f"tmp_{uuid.uuid4().hex}.mp4"

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", str(start_sec),
        "-i", str(filepath),
        "-t", str(clip_len),
        "-map", f"0:{video_stream['index']}",
    ]

    if chosen_audio:
        cmd.extend(["-map", audio_map])

    # Video filters & encoding
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        "-crf", "24",
        "-vf", preview_video_filters(video_stream),
        "-pix_fmt", "yuv420p",
        "-profile:v", "main",
        "-c:a", "aac",
        "-b:a", "128k",
    ])

    # Audio channel filter or stereo downmix
    if audio_filter:
        cmd.extend(["-af", audio_filter])
    else:
        cmd.extend(["-ac", "2"])

    cmd.extend([
        "-movflags", "+faststart",
        str(temp_path),
    ])

    try:
        t0 = time.time()
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60)
        if res.returncode != 0:
            logger.error(f"FFmpeg clip extraction failed for {filepath}: {res.stderr.decode('utf-8', 'ignore')}")
            if temp_path.exists():
                temp_path.unlink()
            return None

        temp_path.replace(output_path)
        logger.info(f"Generated preview clip in {time.time() - t0:.2f}s: {output_path.name}")

        # Keep cache trimmed: remove older clips for this specific episode/audio
        for old in existing_clips:
            try:
                if old.is_file() and old != output_path:
                    old.unlink()
            except Exception:
                pass

        return {
            "clip_path": output_path,
            "filename": filepath.name,
            "duration": duration,
            "start_sec": start_sec,
            "start_formatted": format_timestamp(start_sec),
            "clip_len": clip_len,
            "audio_reason": reason,
            "audio_lang": lang_display,
        }
    except Exception as exc:
        logger.error(f"Exception during clip generation for {filepath}: {exc}")
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        return None
