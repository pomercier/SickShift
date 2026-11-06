from __future__ import annotations

import asyncio
from contextlib import suppress
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sickshift_dashboard.config import Settings, load_config
from sickshift_dashboard.services import (
    BackgroundCache,
    DataService,
    NetworkService,
    SnapshotManager,
    ThumbnailService,
)
from sickshift_dashboard.templates import TemplateEngine

try:
    import redis.asyncio as redis
except ImportError:
    redis = None


class AppState:
    def __init__(self, config: Optional[Settings] = None) -> None:
        self.config: Settings = config or load_config()
        self.engine: Optional[AsyncEngine] = None
        self.version_connection: Optional[AsyncConnection] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self.redis: Any = None
        self.data_service: Optional[DataService] = None
        self.background_cache: Optional[BackgroundCache] = None
        self.snapshot_manager: Optional[SnapshotManager] = None
        self.background_task: Optional[asyncio.Task[Any]] = None
        self.template_engine: Optional[TemplateEngine] = None
        self.thumbnail_service: Optional[ThumbnailService] = None
        self.network_service: Optional[NetworkService] = None
        self.initialized = False
        self._init_lock = asyncio.Lock()

    async def _close_version_connection(self) -> None:
        if self.version_connection is not None:
            with suppress(Exception):
                await self.version_connection.close()
        self.version_connection = None

    async def _create_engine(self) -> None:
        await self._close_version_connection()
        if self.engine is not None:
            with suppress(Exception):
                await self.engine.dispose()

        # Read-only SQLite connection (URI mode=ro):
        # Cross-platform compatible with Linux, macOS, and Windows (normalized POSIX file URI)
        db_path = self.config.db_path
        if not db_path or not Path(db_path).is_file():
            from sickshift_dashboard.config import find_default_db_path
            db_path = find_default_db_path()
            self.config.db_path = db_path

        clean_path = Path(db_path).resolve().as_posix()
        if not clean_path.startswith("/"):
            clean_path = "/" + clean_path
        db_url = f"sqlite+aiosqlite:///file:{clean_path}?mode=ro&uri=true"
        self.engine = create_async_engine(
            db_url,
            connect_args={"timeout": 10, "uri": True},
            pool_pre_ping=True,
        )

        @event.listens_for(self.engine.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            with suppress(Exception):
                cursor.execute("PRAGMA query_only=ON")
                cursor.execute("PRAGMA busy_timeout=5000")
                cursor.execute("PRAGMA temp_store=MEMORY")
                cursor.execute("PRAGMA cache_size=-32000")
            cursor.close()

        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

        try:
            self.version_connection = await self.engine.connect()
        except Exception as exc:
            print(f"[SQLITE] data_version indisponible : {exc}")

    async def _connect_redis(self) -> None:
        if self.redis is not None:
            with suppress(Exception):
                await self.redis.aclose()
            self.redis = None
        if redis is None or not self.config.redis_enabled:
            print("[REDIS] désactivé")
            return
        try:
            client = redis.from_url(
                self.config.redis_url,
                socket_connect_timeout=2,
                socket_timeout=2,
                decode_responses=True,
            )
            await client.ping()
            self.redis = client
            print(f"[REDIS] connecté : {self.config.redis_url}")
        except Exception as exc:
            print(f"[REDIS] indisponible : {exc}")
            self.redis = None

    async def initialize(self, config_override: Optional[Settings] = None) -> None:
        async with self._init_lock:
            if self.initialized:
                return
            if config_override is not None:
                self.config = config_override
            else:
                self.config = load_config(self.config.config_file)
            await self._create_engine()
            await self._connect_redis()
            self.data_service = DataService(self)
            self.template_engine = TemplateEngine(self.config)
            self.background_cache = BackgroundCache(self)
            self.snapshot_manager = SnapshotManager(self)
            self.thumbnail_service = ThumbnailService(self)
            self.network_service = NetworkService(self)
            self.background_task = asyncio.create_task(self._run_workers())
            self.initialized = True

    async def _run_workers(self) -> None:
        assert self.snapshot_manager is not None
        assert self.background_cache is not None
        tasks = [
            asyncio.create_task(self.snapshot_manager.run()),
            asyncio.create_task(self.background_cache.run()),
        ]
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            for task in tasks:
                task.cancel()
            for task in tasks:
                with suppress(asyncio.CancelledError):
                    await task
            raise

    async def reload(self) -> None:
        old_db_path = self.config.db_path
        old_redis_url = self.config.redis_url
        old_redis_enabled = self.config.redis_enabled
        old_mount_prefix = self.config.mount_prefix
        self.config = load_config(self.config.config_file)
        if old_mount_prefix and not self.config.mount_prefix:
            self.config.mount_prefix = old_mount_prefix

        if self.config.db_path != old_db_path:
            await self._create_engine()
        else:
            await self._close_version_connection()
            if self.engine is not None:
                try:
                    self.version_connection = await self.engine.connect()
                except Exception:
                    self.version_connection = None

        if self.config.redis_url != old_redis_url or self.config.redis_enabled != old_redis_enabled:
            await self._connect_redis()

        self.template_engine = TemplateEngine(self.config)
        self.thumbnail_service = ThumbnailService(self)
        if self.background_cache:
            self.background_cache.invalidate()
        if self.snapshot_manager:
            self.snapshot_manager.tracker.reset()
            await self.snapshot_manager.invalidate()

    async def shutdown(self) -> None:
        if self.snapshot_manager:
            self.snapshot_manager.stop()
        if self.background_cache:
            self.background_cache.stop()
        if self.background_task:
            self.background_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.background_task
            self.background_task = None
        await self._close_version_connection()
        if self.redis:
            with suppress(Exception):
                await self.redis.aclose()
            self.redis = None
        if self.engine:
            with suppress(Exception):
                await self.engine.dispose()
            self.engine = None
        self.initialized = False


state = AppState()
