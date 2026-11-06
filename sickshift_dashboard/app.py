from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from sickshift_dashboard.config import Settings
from sickshift_dashboard.routes import create_router
from sickshift_dashboard.state import AppState, state


def create_app(
    app_state: AppState = state,
    config_override: Optional[Settings] = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            print("[APP] Initializing...")
            await app_state.initialize(config_override=config_override)
            print(f"[APP] http://{app_state.config.host}:{app_state.config.port}{app_state.config.mount_prefix}")
            yield
        finally:
            print("[APP] Shutting down...")
            await app_state.shutdown()

    fastapi_app = FastAPI(
        title="SickShift - FastAPI Dashboard",
        version="4.0.0",
        lifespan=lifespan,
    )

    cfg = config_override or app_state.config
    if cfg.enable_gzip:
        fastapi_app.add_middleware(
            GZipMiddleware,
            minimum_size=cfg.gzip_min_size,
            compresslevel=cfg.gzip_compress_level,
        )

    router = create_router(app_state=app_state)
    fastapi_app.include_router(router)
    return fastapi_app


app = create_app()
