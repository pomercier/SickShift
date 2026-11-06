from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any, Awaitable, Callable

if TYPE_CHECKING:
    from sickshift_dashboard.state import AppState

REDIS_CACHE_KEYS = ("shows", "missing", "ended", "upcoming")


class MemoryCache:
    def __init__(self, max_locks: int = 256) -> None:
        self._data: dict[str, tuple[float, Any]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._locks_guard = asyncio.Lock()
        self._max_locks = max_locks

    async def get(self, key: str) -> Any:
        item = self._data.get(key)
        if item is None:
            return None

        expires_at, value = item
        if asyncio.get_running_loop().time() >= expires_at:
            self._data.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        self._data[key] = (asyncio.get_running_loop().time() + ttl, value)

    async def invalidate(self, key: str) -> None:
        self._data.pop(key, None)

    async def clear(self) -> None:
        self._data.clear()
        async with self._locks_guard:
            # Prune unacquired locks to prevent unbounded memory growth
            unlocked_keys = [k for k, lk in self._locks.items() if not lk.locked()]
            for k in unlocked_keys:
                self._locks.pop(k, None)

    async def lock_for(self, key: str) -> asyncio.Lock:
        async with self._locks_guard:
            if len(self._locks) >= self._max_locks:
                unlocked_keys = [k for k, lk in self._locks.items() if not lk.locked()]
                for k in unlocked_keys[: len(unlocked_keys) // 2 + 1]:
                    self._locks.pop(k, None)
            lock = self._locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock
            return lock


memory_cache = MemoryCache()


async def cached_load(state: "AppState", key: str, loader: Callable[[], Awaitable[Any]]) -> Any:
    ttl = state.config.data_cache_ttl_s

    value = await memory_cache.get(key)
    if value is not None:
        return value

    key_lock = await memory_cache.lock_for(key)

    async with key_lock:
        value = await memory_cache.get(key)
        if value is not None:
            return value

        redis_key = f"sickshift:{key}"

        if state.redis is not None:
            try:
                raw = await state.redis.get(redis_key)
                if raw:
                    value = json.loads(raw)
                    await memory_cache.set(key, value, ttl)
                    return value
            except Exception as exc:
                print(f"[REDIS] GET {key}: {exc}")

        value = await loader()
        await memory_cache.set(key, value, ttl)

        if state.redis is not None:
            try:
                await state.redis.setex(
                    redis_key,
                    state.config.redis_cache_ttl_s,
                    json.dumps(value, ensure_ascii=False),
                )
            except Exception as exc:
                print(f"[REDIS] SET {key}: {exc}")

        return value
