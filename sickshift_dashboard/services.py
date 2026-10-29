from __future__ import annotations

import asyncio
import hashlib
import io
import json
import math
import os
import random
import unicodedata
import urllib.parse
import urllib.request
from collections import deque
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import String, case, distinct, func, select

from sickshift_dashboard.cache import REDIS_CACHE_KEYS, cached_load, memory_cache
from sickshift_dashboard.models import (
    DashboardSnapshot,
    MissingEpisode,
    Show,
    TVEpisode,
    TVShow,
    UpcomingShow,
)

if TYPE_CHECKING:
    from sickshift_dashboard.state import AppState

try:
    from PIL import Image, ImageOps

    PILLOW_AVAILABLE = True
except ImportError:
    Image = None
    ImageOps = None
    PILLOW_AVAILABLE = False


# ============================================================
# DATA SERVICE (SQL optimized with SickShift composite indexes)
# ============================================================


class DataService:
    def __init__(self, app_state: "AppState") -> None:
        self.state = app_state

    def _media_url(self, indexer: Any, show_id: Any) -> str:
        prefix = self.state.config.mount_prefix
        return f"{prefix}/media/thumb/{indexer}/{show_id}"

    async def get_shows(self) -> list[dict[str, Any]]:
        async def load() -> list[dict[str, Any]]:
            async with self.state.session_factory() as session:
                repertory = str(Path(self.state.config.db_path).parent) + "/"

                # Direct ROW_NUMBER() window function + join on composite index
                # idx_indexer_id (indexer, indexer_id): ~0.8 ms instead of ~590 ms
                ranked = (
                    select(
                        TVShow.show_name,
                        TVShow.indexer_id,
                        TVShow.indexer,
                        TVEpisode.season,
                        TVEpisode.episode,
                        TVEpisode.name,
                        TVShow.network,
                        (TVShow.location + "/fanart.jpg").label("location"),
                        (
                            f"{repertory}cache/images/shows/"
                            + TVShow.indexer.cast(String)
                            + "-"
                            + TVShow.indexer_id.cast(String)
                            + "/fanart"
                        ).label("showid"),
                        func.row_number()
                        .over(
                            partition_by=(TVShow.indexer, TVShow.indexer_id),
                            order_by=(TVEpisode.season, TVEpisode.episode),
                        )
                        .label("rn"),
                    )
                    .select_from(TVEpisode)
                    .join(
                        TVShow,
                        (TVShow.indexer == TVEpisode.indexer)
                        & (TVShow.indexer_id == TVEpisode.showid),
                    )
                    .where(
                        TVEpisode.status.not_in([1, 5, 7]),
                        TVEpisode.season > 0,
                        func.coalesce(TVShow.paused, 0) == 0,
                    )
                    .subquery()
                )

                stmt = (
                    select(
                        ranked.c.show_name.label("show_name"),
                        ranked.c.season.label("season"),
                        ranked.c.episode.label("episode"),
                        ranked.c.name.label("ep_name"),
                        ranked.c.network.label("network"),
                        ranked.c.location.label("location"),
                        ranked.c.showid.label("showid"),
                        ranked.c.indexer_id.label("show_id"),
                        ranked.c.indexer.label("indexer_id"),
                    )
                    .where(ranked.c.rn == 1)
                    .order_by(func.lower(ranked.c.show_name))
                )

                result = await session.execute(stmt)
                rows = result.mappings().all()

                output: list[dict[str, Any]] = []
                for row in rows:
                    item = Show.model_validate(row)
                    if item.indexer_id is not None and item.show_id is not None:
                        item.thumbnail = self._media_url(item.indexer_id, item.show_id)
                    output.append(item.model_dump())

                return output

        return await cached_load(self.state, "shows", load)

    async def get_missing_episodes(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        async def load() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
            async with self.state.session_factory() as session:
                season_str = case(
                    (TVEpisode.season < 10, "0" + TVEpisode.season.cast(String)),
                    else_=TVEpisode.season.cast(String),
                )
                episode_str = case(
                    (TVEpisode.episode < 10, "0" + TVEpisode.episode.cast(String)),
                    else_=TVEpisode.episode.cast(String),
                )
                missing_expr = TVShow.show_name + " S" + season_str + "E" + episode_str

                stmt = (
                    select(
                        distinct(missing_expr).label("missing"),
                        TVShow.show_name.label("show_name"),
                        TVEpisode.season.label("season"),
                        TVEpisode.episode.label("episode"),
                        TVEpisode.name.label("ep_name"),
                        TVShow.indexer_id.label("show_id"),
                        TVShow.indexer.label("indexer_id"),
                        TVEpisode.airdate,
                    )
                    .select_from(TVEpisode)
                    .join(
                        TVShow,
                        (TVShow.indexer == TVEpisode.indexer)
                        & (TVShow.indexer_id == TVEpisode.showid),
                    )
                    .where(
                        TVEpisode.status.not_in([1, 5, 7]),
                        TVEpisode.status < 100,
                        TVEpisode.season != 0,
                        TVEpisode.file_size == 0,
                        func.coalesce(TVShow.paused, 0) == 0,
                    )
                    .order_by(func.lower(missing_expr))
                )

                result = await session.execute(stmt)
                rows = result.mappings().all()

                output: list[dict[str, Any]] = []
                for row in rows:
                    item = MissingEpisode.model_validate(row)
                    if item.indexer_id is not None and item.show_id is not None:
                        item.thumbnail = self._media_url(item.indexer_id, item.show_id)
                    output.append(item.model_dump())

                def alpha_sort_key(entry: dict[str, Any]) -> str:
                    raw = entry.get("missing") or entry.get("show_name") or ""
                    nfkd = unicodedata.normalize("NFKD", raw)
                    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()

                output.sort(key=alpha_sort_key)

                # Group missing episodes by show
                grouped_dict: dict[str, dict[str, Any]] = {}
                for entry in output:
                    s_name = (entry.get("show_name") or "").strip()
                    if s_name not in grouped_dict:
                        grouped_dict[s_name] = {
                            "show_name": s_name,
                            "show_id": entry.get("show_id"),
                            "indexer_id": entry.get("indexer_id"),
                            "thumbnail": entry.get("thumbnail"),
                            "episodes": [],
                        }
                    grouped_dict[s_name]["episodes"].append(entry)

                def group_sort_key(g: dict[str, Any]) -> str:
                    nfkd = unicodedata.normalize("NFKD", g.get("show_name") or "")
                    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()

                missing_groups = sorted(grouped_dict.values(), key=group_sort_key)
                return output, missing_groups

        return await cached_load(self.state, "missing", load)

    async def get_ended_shows(self) -> dict[str, list[str]]:
        async def load() -> dict[str, list[str]]:
            async with self.state.session_factory() as session:
                stmt = (
                    select(TVShow.indexer_id, TVShow.indexer)
                    .where(
                        TVShow.status == "Ended",
                        func.coalesce(TVShow.paused, 0) == 0,
                    )
                    .order_by(TVShow.show_name)
                )

                result = await session.execute(stmt)
                urls: list[str] = []
                links: list[str] = []

                for row in result:
                    show_id = row.indexer_id
                    indexer = row.indexer
                    if not show_id or not indexer:
                        continue

                    urls.append(self._media_url(indexer, show_id))
                    root_prefix = (self.state.config.web_root or self.state.config.base_url or "").rstrip("/")
                    links.append(
                        f"{root_prefix}/home/view-show?tvid_prodid={indexer}:{show_id}"
                    )

                return {"urls": urls, "links": links}

        return await cached_load(self.state, "ended", load)

    async def get_upcoming_shows(self) -> list[dict[str, Any]]:
        async def load() -> list[dict[str, Any]]:
            async with self.state.session_factory() as session:
                today_ordinal = date.today().toordinal()

                stmt = (
                    select(
                        TVShow.show_name,
                        TVShow.indexer,
                        TVShow.indexer_id,
                        func.min(TVEpisode.airdate).label("next_airdate"),
                    )
                    .select_from(TVEpisode)
                    .join(
                        TVShow,
                        (TVShow.indexer == TVEpisode.indexer)
                        & (TVShow.indexer_id == TVEpisode.showid),
                    )
                    .where(
                        TVEpisode.airdate >= today_ordinal,
                        TVEpisode.season > 0,
                        func.coalesce(TVShow.paused, 0) == 0,
                    )
                    .group_by(TVShow.show_name, TVShow.indexer, TVShow.indexer_id)
                    .order_by("next_airdate")
                    .limit(20)
                )

                result = await session.execute(stmt)
                output: list[dict[str, Any]] = []

                for row in result:
                    try:
                        date_str = datetime.fromordinal(row.next_airdate).strftime("%Y-%m-%d 00:00")
                    except (TypeError, ValueError):
                        date_str = ""

                    output.append(
                        UpcomingShow(
                            show_name=str(row.show_name),
                            airdate=date_str,
                            image=self._media_url(row.indexer, row.indexer_id),
                            indexer_id=str(row.indexer) if row.indexer is not None else "",
                            show_id=str(row.indexer_id) if row.indexer_id is not None else "",
                        ).model_dump()
                    )

                return output

        return await cached_load(self.state, "upcoming", load)


# ============================================================
# DATABASE CHANGE TRACKER & SNAPSHOT MANAGER
# ============================================================


class DatabaseChangeTracker:
    def __init__(self, app_state: "AppState") -> None:
        self.state = app_state
        self.last_fingerprint: Optional[str] = None
        self.last_stat: Optional[tuple[int, int, int, int]] = None
        self.last_check = 0.0
        self.last_day: int = date.today().toordinal()

    def reset(self) -> None:
        self.last_fingerprint = None
        self.last_stat = None
        self.last_check = 0.0

    async def fingerprint(self) -> str:
        db_path = Path(self.state.config.db_path)
        wal_path = Path(f"{self.state.config.db_path}-wal")
        today_ord = date.today().toordinal()

        try:
            st = db_path.stat()
            db_mtime, db_size = st.st_mtime_ns, st.st_size
        except OSError:
            db_mtime, db_size = 0, 0

        try:
            wst = wal_path.stat()
            wal_mtime, wal_size = wst.st_mtime_ns, wst.st_size
        except OSError:
            wal_mtime, wal_size = 0, 0

        stat = (db_mtime, db_size, wal_mtime, wal_size)
        now = asyncio.get_running_loop().time()

        if (
            self.last_fingerprint
            and self.last_stat == stat
            and self.last_day == today_ord
            and now - self.last_check < 0.5
        ):
            return self.last_fingerprint

        data_version = "unknown"
        if self.state.version_connection is not None:
            try:
                result = await self.state.version_connection.exec_driver_sql("PRAGMA data_version")
                row = result.first()
                if row:
                    data_version = str(row[0])
            except Exception:
                pass

        value = f"{stat[0]}:{stat[1]}:{stat[2]}:{stat[3]}:{data_version}:{today_ord}"
        self.last_fingerprint = value
        self.last_stat = stat
        self.last_day = today_ord
        self.last_check = now
        return value


class RenderedPageCache:
    """In-memory cache for pre-rendered HTML to avoid Jinja2 parsing on every request."""

    def __init__(self) -> None:
        self.key: Optional[str] = None
        self.html: str = ""
        self.etag: str = ""
        self.last_modified: Optional[datetime] = None


class SnapshotManager:
    def __init__(self, app_state: "AppState") -> None:
        self.state = app_state
        self.tracker = DatabaseChangeTracker(app_state)
        self.snapshot: Optional[DashboardSnapshot] = None
        self.lock = asyncio.Lock()
        self.condition = asyncio.Condition()
        self.stop_event = asyncio.Event()
        self._home_render_cache = RenderedPageCache()
        self._mini_render_cache = RenderedPageCache()

    def stop(self) -> None:
        self.stop_event.set()

    async def _clear_caches(self) -> None:
        self._home_render_cache = RenderedPageCache()
        self._mini_render_cache = RenderedPageCache()
        await memory_cache.clear()
        if self.state.redis is not None:
            for key in REDIS_CACHE_KEYS:
                try:
                    await self.state.redis.delete(f"sickshift:{key}")
                except Exception:
                    pass

    async def invalidate(self) -> None:
        async with self.lock:
            self.snapshot = None
        await self._clear_caches()

    async def build(self, version: str) -> DashboardSnapshot:
        await memory_cache.clear()
        if self.state.redis is not None:
            for key in REDIS_CACHE_KEYS:
                try:
                    await self.state.redis.delete(f"sickshift:{key}")
                except Exception:
                    pass

        ds = self.state.data_service

        shows, (missing, missing_groups), ended, upcoming = await asyncio.gather(
            ds.get_shows(),
            ds.get_missing_episodes(),
            ds.get_ended_shows(),
            ds.get_upcoming_shows(),
        )

        missing_show_ids = {
            str(x["show_id"]) for x in missing if x.get("show_id") is not None
        }
        upcoming_filtered = [x for x in upcoming if str(x.get("show_id")) not in missing_show_ids]

        # ETag depends strictly on actual rendered content,
        # not SQLite internal version which updates on internal tasks.
        content_payload = {
            "shows": shows,
            "missing": missing,
            "missing_groups": missing_groups,
            "ended": ended,
            "upcoming": upcoming_filtered,
        }
        raw_json = json.dumps(content_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        etag = f'"{hashlib.sha256(raw_json).hexdigest()[:32]}"'
        return DashboardSnapshot(
            version=version,
            generated_at=datetime.now(timezone.utc),
            shows=shows,
            missing=missing,
            missing_groups=missing_groups,
            ended=ended,
            upcoming=upcoming_filtered,
            etag=etag,
        )

    async def get(self) -> DashboardSnapshot:
        version = await self.tracker.fingerprint()
        if self.snapshot is not None and self.snapshot.version == version:
            return self.snapshot

        async with self.lock:
            version = await self.tracker.fingerprint()
            if self.snapshot is not None and self.snapshot.version == version:
                return self.snapshot

            new_snapshot = await self.build(version)
            # If content did not change despite mtime update,
            # retain existing snapshot, timestamp, and pre-rendered HTML cache.
            if self.snapshot is not None and self.snapshot.etag == new_snapshot.etag:
                self.snapshot.version = version
                return self.snapshot

            self.snapshot = new_snapshot
            self._home_render_cache = RenderedPageCache()
            self._mini_render_cache = RenderedPageCache()
            async with self.condition:
                self.condition.notify_all()
            return self.snapshot

    async def get_rendered_page(self, *, mini: bool = False) -> tuple[str, str, datetime]:
        snapshot = await self.get()
        bg_file = await self.state.background_cache.get()
        cache_obj = self._mini_render_cache if mini else self._home_render_cache
        cache_key = f"{snapshot.etag}:{bg_file}:{'mini' if mini else 'home'}"

        last_modified = snapshot.generated_at
        if self.state.background_cache.last_update:
            bg_dt = self.state.background_cache.last_update
            if bg_dt.tzinfo is None:
                bg_dt = bg_dt.replace(tzinfo=timezone.utc)
            last_modified = max(last_modified, bg_dt)

        if cache_obj.key == cache_key and cache_obj.html:
            return cache_obj.html, cache_obj.etag, cache_obj.last_modified or last_modified

        if mini:
            html = self.state.template_engine.render(
                mini=True,
                shows=snapshot.shows,
                missing=snapshot.missing,
                missing_groups=snapshot.missing_groups,
                bg_file=bg_file,
            )
        else:
            html = self.state.template_engine.render(
                shows=snapshot.shows,
                missing=snapshot.missing,
                missing_groups=snapshot.missing_groups,
                image_urls=snapshot.ended["urls"],
                image_links=snapshot.ended["links"],
                upcoming=snapshot.upcoming,
                bg_file=bg_file,
            )

        etag = f'"{hashlib.sha256(cache_key.encode("utf-8")).hexdigest()[:32]}"'
        cache_obj.key = cache_key
        cache_obj.html = html
        cache_obj.etag = etag
        cache_obj.last_modified = last_modified
        return html, etag, last_modified

    async def wait_for_change(self, previous_version: str, timeout: float = 15.0) -> Optional[DashboardSnapshot]:
        async def waiter() -> Optional[DashboardSnapshot]:
            async with self.condition:
                await self.condition.wait_for(
                    lambda: self.snapshot is not None and self.snapshot.version != previous_version
                )
                return self.snapshot

        try:
            return await asyncio.wait_for(waiter(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                await self.get()
                try:
                    await asyncio.wait_for(
                        self.stop_event.wait(),
                        timeout=self.state.config.snapshot_poll_s,
                    )
                except asyncio.TimeoutError:
                    pass
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"[SNAPSHOT] error: {exc}")
                await asyncio.sleep(3)


# ============================================================
# BACKGROUND CACHE
# ============================================================


class BackgroundCache:
    def __init__(self, app_state: "AppState") -> None:
        self.state = app_state
        self.cache: str = ""
        self.last_update: Optional[datetime] = None
        self.lock = asyncio.Lock()
        self.stop_event = asyncio.Event()
        self.history: deque[str] = deque(maxlen=self.state.config.background_history_size)

    def stop(self) -> None:
        """Signals graceful termination of background loop."""
        self.stop_event.set()

    def interval(self) -> timedelta:
        return timedelta(minutes=max(1, self.state.config.bg_update_min))

    def is_valid(self) -> bool:
        return bool(
            self.cache
            and self.last_update
            and datetime.now(timezone.utc) - self.last_update < self.interval()
        )

    def invalidate(self) -> None:
        self.cache = ""
        self.last_update = None
        self.history.clear()
        self.history = deque(maxlen=self.state.config.background_history_size)

    @staticmethod
    def _find_images(directory: Path, limit: int) -> list[tuple[Path, int]]:
        result: list[tuple[Path, int]] = []
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    if not entry.name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                        continue
                    try:
                        size = entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        size = 0
                    result.append((Path(entry.path), size))
                    if len(result) >= limit:
                        break
        except OSError:
            return []
        return result

    async def refresh(self) -> None:
        if self.lock.locked():
            return
        async with self.lock:
            if self.is_valid():
                return
            try:
                snapshot = await self.state.snapshot_manager.get()
                root = Path(self.state.config.db_path).parent.resolve()
                shows = snapshot.shows[:]
                random.shuffle(shows)
                candidates: list[tuple[Path, float]] = []

                for show in shows[: self.state.config.background_candidates]:
                    showid = show.get("showid") or show.get("Showid")
                    if not showid:
                        continue
                    try:
                        directory = Path(showid).expanduser().resolve()
                        directory.relative_to(root)
                    except (OSError, ValueError):
                        continue

                    files = await asyncio.to_thread(
                        self._find_images,
                        directory,
                        self.state.config.background_sample_limit,
                    )
                    for path, size in files:
                        try:
                            rel_str = str(path.resolve().relative_to(root)).replace(os.sep, "/")
                            root_prefix = (self.state.config.web_root or self.state.config.base_url or "").rstrip("/")
                            url = f"{root_prefix}/{rel_str}"
                        except ValueError:
                            continue
                        if url == self.cache or url in self.history:
                            continue
                        score = math.log(max(size, 1024)) + random.random() * 5.0
                        candidates.append((path, score))

                if candidates:
                    candidates.sort(key=lambda item: item[1], reverse=True)
                    selected = random.choice(candidates[: min(8, len(candidates))])[0]
                    rel = selected.resolve().relative_to(root)
                    root_prefix = (self.state.config.web_root or self.state.config.base_url or "").rstrip("/")
                    self.cache = f"{root_prefix}/{str(rel).replace(os.sep, '/')}"
                    self.history.append(self.cache)
                else:
                    self.cache = ""
                self.last_update = datetime.now(timezone.utc)
            except Exception as exc:
                print(f"[BACKGROUND] error: {exc}")

    async def get(self) -> str:
        if not self.is_valid():
            await self.refresh()
        return self.cache

    async def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                await self.refresh()
                try:
                    await asyncio.wait_for(self.stop_event.wait(), timeout=60)
                except asyncio.TimeoutError:
                    pass
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"[BACKGROUND] error: {exc}")
                await asyncio.sleep(5)


# =======================================================================
# THUMBNAIL SERVICE (Per-thumbnail parallelization + Concurrency semaphore)
# =======================================================================


class ThumbnailService:
    def __init__(self, app_state: "AppState") -> None:
        self.state = app_state
        self.semaphore = asyncio.Semaphore(max(1, app_state.config.webp_max_concurrency))
        self._key_locks: dict[tuple[int, int], asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def _lock_for(self, indexer: int, show_id: int) -> asyncio.Lock:
        key = (indexer, show_id)
        async with self._guard:
            if len(self._key_locks) > 512:
                unlocked = [k for k, lk in self._key_locks.items() if not lk.locked()]
                for k in unlocked[:256]:
                    self._key_locks.pop(k, None)
            lock = self._key_locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._key_locks[key] = lock
            return lock

    def sources(self, indexer: int, show_id: int) -> list[Path]:
        base = (
            Path(self.state.config.db_path).parent
            / "cache"
            / "images"
            / "shows"
            / f"{indexer}-{show_id}"
            / "thumbnails"
        )
        return [
            base / "poster.jpg",
            base / "poster.jpeg",
            base / "poster.png",
            base / "poster.webp",
        ]

    def output(self, indexer: int, show_id: int) -> Path:
        root = (
            Path(self.state.config.webp_cache_dir).expanduser()
            if self.state.config.webp_cache_dir
            else Path(self.state.config.db_path).parent / "cache" / "dashboard_webp"
        )
        root.mkdir(parents=True, exist_ok=True)
        return root / f"{indexer}-{show_id}.webp"

    @staticmethod
    def convert(source: Path, output: Path, quality: int, method: int) -> None:
        if Image is None:
            raise RuntimeError("Pillow absent")
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image) if ImageOps else image
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            output.parent.mkdir(parents=True, exist_ok=True)
            image.save(output, "WEBP", quality=quality, method=method)

    async def get(self, indexer: int, show_id: int) -> Optional[Path]:
        sources = [x for x in self.sources(indexer, show_id) if x.exists()]
        if not sources:
            return None
        source = sources[0]
        if not self.state.config.webp_enabled or not PILLOW_AVAILABLE:
            return source

        output = self.output(indexer, show_id)
        try:
            if output.exists() and output.stat().st_mtime_ns >= source.stat().st_mtime_ns:
                return output
        except OSError:
            pass

        item_lock = await self._lock_for(indexer, show_id)
        async with item_lock:
            try:
                if output.exists() and output.stat().st_mtime_ns >= source.stat().st_mtime_ns:
                    return output
            except OSError:
                pass
            async with self.semaphore:
                try:
                    await asyncio.to_thread(
                        self.convert,
                        source,
                        output,
                        self.state.config.webp_quality,
                        self.state.config.webp_method,
                    )
                    return output if output.exists() else source
                except Exception as exc:
                    print(f"[WEBP] {source}: {exc}")
                    return source


# ============================================================
# NETWORK LOGO SERVICE (Local Resolution & Web Download)
# ============================================================


class NetworkService:
    def __init__(self, app_state: "AppState") -> None:
        self.state = app_state
        self._download_locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

        # Name alias mapping for network variations (Quebec, Canada, etc.)
        self.aliases: dict[str, str] = {
            "radiocanada": "radio-canada",
            "iciradiocanada": "radio-canada",
            "iciradiocanadatele": "radio-canada",
            "icitoutv": "ici tou.tv",
            "icitoutvextra": "ici tou.tv",
            "toutv": "ici tou.tv",
            "tva": "tva",
            "tqs": "tqs",
            "telequebec": "tele-quebec",
        }

        # Known high-quality direct URLs for networks without direct TMDB entries
        self.known_urls: dict[str, str] = {
            "tva": "https://commons.wikimedia.org/wiki/Special:FilePath/TVA%20logo%202020.svg?width=300",
            "tqs": "https://image.tmdb.org/t/p/w500/iq7ZGb7RN4JCaWvuCvn3VngFCy7.png",
            "ici tou.tv": "https://image.tmdb.org/t/p/w500/wP7QDZA7TOCa3B5rD00DtBjI31.png",
            "radio-canada": "https://image.tmdb.org/t/p/w500/32OnRA75a9xn30N2fC44IcCzHkC.png",
        }

    def images_dir(self) -> Path:
        """Official SickShift network logos directory so both SickShift and dashboard benefit."""
        return Path(self.state.config.db_path).parent / "gui" / "slick" / "images" / "network"

    @staticmethod
    def normalize_name(name: str) -> str:
        """Removes accents and converts to lowercase without excessive punctuation."""
        nfc = unicodedata.normalize("NFKD", name or "")
        ascii_clean = "".join(c for c in nfc if not unicodedata.combining(c))
        return ascii_clean.lower().strip()

    def find_local(self, network_name: str) -> Optional[Path]:
        net_dir = self.images_dir()
        if not net_dir.exists():
            return None

        clean = self.normalize_name(network_name)
        key = clean.replace(" ", "").replace("-", "").replace(".", "")
        alias_target = self.aliases.get(key, clean)

        candidates = [
            f"{network_name.lower()}.png",
            f"{clean}.png",
            f"{clean.replace(' ', '')}.png",
            f"{clean.replace('-', '')}.png",
            f"{alias_target}.png",
            f"{alias_target.replace(' ', '')}.png",
            f"{alias_target.replace('-', '')}.png",
        ]

        try:
            with os.scandir(net_dir) as entries:
                files_map: dict[str, Path] = {}
                for entry in entries:
                    if entry.is_file() and entry.name.lower().endswith(".png"):
                        entry_norm = self.normalize_name(entry.name[:-4])
                        p = Path(entry.path)
                        files_map[entry.name.lower()] = p
                        files_map[entry_norm] = p
                        files_map[entry_norm.replace(" ", "").replace("-", "").replace(".", "")] = p
        except OSError:
            return None

        for c in candidates:
            if c.lower() in files_map:
                return files_map[c.lower()]
            c_stem = c[:-4] if c.endswith(".png") else c
            c_norm = self.normalize_name(c_stem)
            if c_norm in files_map:
                return files_map[c_norm]
            c_key = c_norm.replace(" ", "").replace("-", "").replace(".", "")
            if c_key in files_map:
                return files_map[c_key]

        return None

    async def _lock_for(self, key: str) -> asyncio.Lock:
        async with self._guard:
            lock = self._download_locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._download_locks[key] = lock
            return lock

    async def get_logo(self, network_name: str) -> tuple[Optional[Path], Optional[str]]:
        local_path = self.find_local(network_name)
        if local_path and local_path.exists():
            from sickshift_dashboard.white_logo import get_white_or_original_logo
            return get_white_or_original_logo(local_path), None

        # If absent locally, attempt automatic download
        downloaded = await self.download_network_logo(network_name)
        if downloaded and downloaded.exists():
            from sickshift_dashboard.white_logo import get_white_or_original_logo
            return get_white_or_original_logo(downloaded), None

        # Clean fallback to styled SVG badge
        return None, self.generate_svg_badge(network_name)

    async def download_network_logo(self, network_name: str) -> Optional[Path]:
        clean = self.normalize_name(network_name)
        key = clean.replace(" ", "").replace("-", "").replace(".", "")
        clean_target = self.aliases.get(key, clean)

        lock = await self._lock_for(key)
        async with lock:
            local_path = self.find_local(network_name)
            if local_path and local_path.exists():
                return local_path

            dest_dir = self.images_dir()
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / f"{clean_target}.png"

            # 1. Check if direct URL is known
            url = self.known_urls.get(clean_target) or self.known_urls.get(clean)

            # 2. Otherwise query TMDB API
            if not url:
                url = await self._search_tmdb_logo(network_name)

            # 3. Otherwise query Wikidata API
            if not url:
                url = await self._search_wikidata_logo(network_name)

            if not url:
                return None

            try:
                data = await asyncio.to_thread(self._fetch_bytes, url)
                if not data:
                    return None

                def _save() -> None:
                    if PILLOW_AVAILABLE and Image is not None:
                        im = Image.open(io.BytesIO(data))
                        im.save(dest_file, "PNG")
                    else:
                        dest_file.write_bytes(data)

                await asyncio.to_thread(_save)
                print(f"[NETWORK] Logo saved for '{network_name}' -> {dest_file.name}")
                return dest_file
            except Exception as exc:
                print(f"[NETWORK] Unable to download logo for '{network_name}': {exc}")
                return None

    @staticmethod
    def _fetch_bytes(url: str) -> bytes:
        headers = {"User-Agent": "Mozilla/5.0 (SickShiftDashboard/4.0 logo fetcher)"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read()

    async def _search_tmdb_logo(self, network_name: str) -> Optional[str]:
        api_key = os.environ.get("SICKSHIFT_TMDB_API_KEY", "")
        if not api_key:
            return None
        q = urllib.parse.quote(network_name)
        url = f"https://api.themoviedb.org/3/search/company?query={q}&api_key={api_key}"
        try:
            raw = await asyncio.to_thread(self._fetch_bytes, url)
            res = json.loads(raw.decode("utf-8")).get("results", [])
            for r in res:
                if r.get("logo_path"):
                    return f"https://image.tmdb.org/t/p/w500{r['logo_path']}"
        except Exception:
            pass
        return None

    async def _search_wikidata_logo(self, network_name: str) -> Optional[str]:
        q = urllib.parse.quote(network_name)
        search_url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={q}&language=fr&format=json&limit=5&type=item"
        try:
            raw = await asyncio.to_thread(self._fetch_bytes, search_url)
            items = json.loads(raw.decode("utf-8")).get("search", [])
            for it in items:
                qid = it.get("id")
                if not qid:
                    continue
                e_url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
                e_raw = await asyncio.to_thread(self._fetch_bytes, e_url)
                claims = json.loads(e_raw.decode("utf-8")).get("entities", {}).get(qid, {}).get("claims", {})
                if "P154" in claims:
                    logo_val = claims["P154"][0].get("mainsnak", {}).get("datavalue", {}).get("value")
                    if logo_val:
                        return f"https://commons.wikimedia.org/wiki/Special:FilePath/{urllib.parse.quote(logo_val)}?width=300"
        except Exception:
            pass
        return None

    @staticmethod
    def generate_svg_badge(network_name: str) -> str:
        escaped = (network_name or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        width = max(60, len(escaped) * 8 + 16)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="28" viewBox="0 0 {width} 28">'
            f'<rect width="{width}" height="28" rx="5" fill="#1e1e2a" stroke="#333346" stroke-width="1"/>'
            f'<text x="50%" y="54%" dominant-baseline="middle" text-anchor="middle" fill="#3dd9eb" '
            f'font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="11" font-weight="600">{escaped}</text>'
            f'</svg>'
        )
