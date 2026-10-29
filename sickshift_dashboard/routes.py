from __future__ import annotations

import hashlib
import json
import urllib.parse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response

from sickshift_dashboard.services import PILLOW_AVAILABLE
from sickshift_dashboard.state import AppState, state


def http_date(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


def parse_http_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def not_modified(request: Request, etag: str, last_modified: datetime) -> bool:
    inm = request.headers.get("if-none-match")
    if inm and etag in {x.strip() for x in inm.split(",")}:
        return True
    ims = parse_http_date(request.headers.get("if-modified-since"))
    return bool(ims and last_modified.replace(microsecond=0) <= ims.replace(microsecond=0))


def cache_headers(etag: str, last_modified: datetime, content_type: str) -> dict[str, str]:
    return {
        "ETag": etag,
        "Last-Modified": http_date(last_modified),
        "Cache-Control": "private, max-age=0, must-revalidate",
        "Content-Type": content_type,
    }


PWA_ICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><rect width="256" height="256" rx="48" fill="#000"/><circle cx="128" cy="128" r="86" fill="#13131a" stroke="#3dd9eb" stroke-width="12"/><path d="M80 95h96v18H80zm0 34h96v18H80zm0 34h64v18H80z" fill="#e8e8f0"/></svg>"""


def build_pwa_manifest(prefix: str = "") -> dict[str, Any]:
    start = f"{prefix}/" if prefix else "/"
    icon_src = f"{prefix}/app-icon.svg" if prefix else "/app-icon.svg"
    return {
        "name": "SickShift Dashboard",
        "short_name": "SickShift",
        "start_url": start,
        "display": "standalone",
        "background_color": "#000000",
        "theme_color": "#0a0a0f",
        "icons": [
            {
                "src": icon_src,
                "sizes": "any",
                "type": "image/svg+xml",
                "purpose": "any maskable",
            }
        ],
    }


def build_service_worker(prefix: str = "") -> str:
    manifest_url = f"{prefix}/manifest.webmanifest"
    icon_url = f"{prefix}/app-icon.svg"
    home_url = f"{prefix}/" if prefix else "/"
    mini_url = f"{prefix}/mini"
    api_prefix = f"{prefix}/api/"
    return (
        f'const CACHE_NAME="sickshift-dashboard-v4";'
        f'const ATS=["{manifest_url}","{icon_url}"];'
        f'self.addEventListener("install",e=>{{e.waitUntil(caches.open(CACHE_NAME).then(c=>c.addAll(ATS)));self.skipWaiting()}});'
        f'self.addEventListener("activate",e=>{{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE_NAME).map(k=>caches.delete(k)))));self.clients.claim()}});'
        f'self.addEventListener("fetch",e=>{{const u=new URL(e.request.url);if(u.origin!==self.location.origin||e.request.method!=="GET")return;'
        f'if(u.pathname==="{manifest_url}"||u.pathname==="{icon_url}"){{e.respondWith(caches.match(e.request).then(c=>c||fetch(e.request)));return}}'
        f'if(u.pathname==="{home_url}"||u.pathname==="{mini_url}"||u.pathname.startsWith("{api_prefix}"))e.respondWith(fetch(e.request))}});'
    )


def create_router(app_state: AppState = state) -> APIRouter:
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    async def home(request: Request) -> Response:
        if not app_state.snapshot_manager or not app_state.template_engine or not app_state.background_cache:
            raise HTTPException(status_code=503, detail="Application not initialized")
        html, etag, last_modified = await app_state.snapshot_manager.get_rendered_page(mini=False)
        headers = cache_headers(etag, last_modified, "text/html; charset=utf-8")
        if not_modified(request, etag, last_modified):
            return Response(status_code=304, headers=headers)
        return HTMLResponse(html, headers=headers)

    @router.get("/mini", response_class=HTMLResponse)
    async def mini(request: Request) -> Response:
        if not app_state.snapshot_manager or not app_state.template_engine or not app_state.background_cache:
            raise HTTPException(status_code=503, detail="Application not initialized")
        html, etag, last_modified = await app_state.snapshot_manager.get_rendered_page(mini=True)
        headers = cache_headers(etag, last_modified, "text/html; charset=utf-8")
        if not_modified(request, etag, last_modified):
            return Response(status_code=304, headers=headers)
        return HTMLResponse(html, headers=headers)

    @router.get("/api/dashboard")
    async def api_dashboard(request: Request) -> Response:
        if not app_state.snapshot_manager:
            raise HTTPException(status_code=503, detail="Application not initialized")
        snapshot = await app_state.snapshot_manager.get()
        payload = snapshot.model_dump(mode="json")
        headers = cache_headers(snapshot.etag, snapshot.generated_at, "application/json; charset=utf-8")
        if not_modified(request, snapshot.etag, snapshot.generated_at):
            return Response(status_code=304, headers=headers)
        return JSONResponse(payload, headers=headers)

    async def collection_response(request: Request, data: Any, last_modified: datetime) -> Response:
        raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        etag = f'"{hashlib.sha256(raw).hexdigest()[:32]}"'
        headers = cache_headers(etag, last_modified, "application/json; charset=utf-8")
        if not_modified(request, etag, last_modified):
            return Response(status_code=304, headers=headers)
        return JSONResponse(data, headers=headers)

    @router.get("/api/shows")
    async def api_shows(request: Request) -> Response:
        if not app_state.snapshot_manager:
            raise HTTPException(status_code=503, detail="Application not initialized")
        s = await app_state.snapshot_manager.get()
        return await collection_response(request, s.shows, s.generated_at)

    @router.get("/api/missing")
    async def api_missing(request: Request) -> Response:
        if not app_state.snapshot_manager:
            raise HTTPException(status_code=503, detail="Application not initialized")
        s = await app_state.snapshot_manager.get()
        return await collection_response(request, s.missing, s.generated_at)

    @router.get("/api/upcoming")
    async def api_upcoming(request: Request) -> Response:
        if not app_state.snapshot_manager:
            raise HTTPException(status_code=503, detail="Application not initialized")
        s = await app_state.snapshot_manager.get()
        return await collection_response(request, s.upcoming, s.generated_at)

    @router.get("/api/ended")
    async def api_ended(request: Request) -> Response:
        if not app_state.snapshot_manager:
            raise HTTPException(status_code=503, detail="Application not initialized")
        s = await app_state.snapshot_manager.get()
        return await collection_response(request, s.ended, s.generated_at)

    @router.get("/health")
    async def health() -> dict[str, Any]:
        db = Path(app_state.config.db_path)
        return {
            "status": "ok" if db.exists() and app_state.initialized else "degraded",
            "initialized": app_state.initialized,
            "db_exists": db.exists(),
            "db_path": str(db),
            "redis": app_state.redis is not None,
            "pillow": PILLOW_AVAILABLE,
            "webp": bool(app_state.config.webp_enabled and PILLOW_AVAILABLE),
            "snapshot": bool(app_state.snapshot_manager and app_state.snapshot_manager.snapshot),
            "mount_prefix": app_state.config.mount_prefix,
        }

    @router.get("/media/thumb/{indexer}/{show_id}")
    async def media_thumb(indexer: int, show_id: int, request: Request) -> Response:
        if not app_state.thumbnail_service:
            raise HTTPException(status_code=503, detail="Application not initialized")
        path = await app_state.thumbnail_service.get(indexer, show_id)
        if path is None or not path.exists():
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        stat = path.stat()
        etag = f'"img-{stat.st_mtime_ns:x}-{stat.st_size:x}"'
        modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        headers = {
            "ETag": etag,
            "Last-Modified": http_date(modified),
            "Cache-Control": "public, max-age=86400, immutable",
            "X-Content-Type-Options": "nosniff",
        }
        if not_modified(request, etag, modified):
            return Response(status_code=304, headers=headers)
        media_type = (
            "image/webp"
            if path.suffix.lower() == ".webp"
            else ("image/png" if path.suffix.lower() == ".png" else "image/jpeg")
        )
        return FileResponse(path, media_type=media_type, headers=headers)

    @router.api_route("/media/soundtrack/{indexer}/{show_id}", methods=["GET", "HEAD"])
    async def media_soundtrack(indexer: int, show_id: int, request: Request) -> Response:
        import asyncio
        from sickshift_dashboard.soundtrack import get_soundtrack

        file_path, remote_url = await asyncio.to_thread(
            get_soundtrack,
            indexer,
            show_id,
            app_state.config.db_path,
        )

        if file_path is not None and file_path.is_file():
            stat = file_path.stat()
            etag = f'"st-{stat.st_mtime_ns:x}-{stat.st_size:x}"'
            modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            headers = {
                "ETag": etag,
                "Last-Modified": http_date(modified),
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=86400",
                "X-Content-Type-Options": "nosniff",
            }
            if not_modified(request, etag, modified):
                return Response(status_code=304, headers=headers)
            media_type = "audio/mpeg" if file_path.suffix.lower() == ".mp3" else "audio/mp4"
            return FileResponse(file_path, media_type=media_type, headers=headers)

        if remote_url:
            return RedirectResponse(url=remote_url, status_code=302)

        raise HTTPException(status_code=404, detail="Soundtrack not found")

    @router.get("/api/preview-clip-info/{indexer}/{show_id}/{season}/{episode}")
    async def preview_clip_info(
        indexer: int,
        show_id: int,
        season: int,
        episode: int,
        sys_lang: str = "fr",
        fresh: bool = False,
    ) -> JSONResponse:
        import asyncio
        from sickshift_dashboard.preview_clip import resolve_episode_file, get_or_create_preview_clip

        filepath = await asyncio.to_thread(
            resolve_episode_file, indexer, show_id, season, episode, app_state.config.db_path
        )
        if not filepath or not filepath.is_file():
            return JSONResponse({"has_file": False, "error": "file_not_found"}, status_code=404)

        clip_data = await asyncio.to_thread(
            get_or_create_preview_clip,
            filepath,
            indexer,
            show_id,
            season,
            episode,
            sys_lang=sys_lang,
            force_new=fresh,
        )
        if not clip_data:
            return JSONResponse({"has_file": False, "error": "extraction_failed"}, status_code=500)

        mount = app_state.config.mount_prefix or "/dashboard"
        video_url = f"{mount}/media/preview-clip/{indexer}/{show_id}/{season}/{episode}?lang={sys_lang}&v={clip_data['clip_path'].stem}"
        return JSONResponse({
            "has_file": True,
            "filename": clip_data["filename"],
            "duration": clip_data["duration"],
            "start_sec": clip_data["start_sec"],
            "start_formatted": clip_data["start_formatted"],
            "clip_len": clip_data["clip_len"],
            "audio_lang": clip_data["audio_lang"],
            "audio_reason": clip_data["audio_reason"],
            "video_url": video_url,
        })

    @router.api_route("/media/preview-clip/{indexer}/{show_id}/{season}/{episode}", methods=["GET", "HEAD"])
    async def media_preview_clip(
        indexer: int,
        show_id: int,
        season: int,
        episode: int,
        request: Request,
        lang: str = "fr",
        fresh: bool = False,
    ) -> Response:
        import asyncio
        from sickshift_dashboard.preview_clip import resolve_episode_file, get_or_create_preview_clip

        filepath = await asyncio.to_thread(
            resolve_episode_file, indexer, show_id, season, episode, app_state.config.db_path
        )
        if not filepath or not filepath.is_file():
            raise HTTPException(status_code=404, detail="Episode media file not found")

        clip_data = await asyncio.to_thread(
            get_or_create_preview_clip,
            filepath,
            indexer,
            show_id,
            season,
            episode,
            sys_lang=lang,
            force_new=fresh,
        )
        if not clip_data or not clip_data.get("clip_path"):
            raise HTTPException(status_code=500, detail="Failed to generate preview clip")

        file_path = clip_data["clip_path"]
        stat = file_path.stat()
        etag = f'"pv-{stat.st_mtime_ns:x}-{stat.st_size:x}"'
        modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        headers = {
            "ETag": etag,
            "Last-Modified": http_date(modified),
            "Accept-Ranges": "bytes",
            "Cache-Control": "private, max-age=3600",
            "X-Clip-Language": clip_data.get("audio_lang", ""),
            "X-Clip-Start": str(clip_data.get("start_sec", 0)),
        }
        if not_modified(request, etag, modified):
            return Response(status_code=304, headers=headers)

        return FileResponse(file_path, media_type="video/mp4", headers=headers)

    @router.get("/manifest.webmanifest")
    async def manifest() -> JSONResponse:
        return JSONResponse(
            build_pwa_manifest(app_state.config.mount_prefix),
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @router.get("/service-worker.js")
    async def service_worker() -> Response:
        return Response(
            build_service_worker(app_state.config.mount_prefix),
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache"},
        )

    @router.get("/app-icon.svg")
    async def app_icon() -> Response:
        return Response(
            PWA_ICON,
            media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @router.get("/media/network/{network_name:path}")
    async def media_network(network_name: str, request: Request) -> Response:
        if not app_state.network_service:
            raise HTTPException(status_code=503, detail="Application not initialized")
        clean_name = urllib.parse.unquote(network_name)
        path, svg_content = await app_state.network_service.get_logo(clean_name)
        if path is not None and path.exists():
            stat = path.stat()
            etag = f'"net-{stat.st_mtime_ns:x}-{stat.st_size:x}"'
            modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            headers = {
                "ETag": etag,
                "Last-Modified": http_date(modified),
                "Cache-Control": "public, max-age=604800, immutable",
                "X-Content-Type-Options": "nosniff",
            }
            if not_modified(request, etag, modified):
                return Response(status_code=304, headers=headers)
            media_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
            return FileResponse(path, media_type=media_type, headers=headers)
        elif svg_content:
            return Response(
                svg_content,
                media_type="image/svg+xml",
                headers={"Cache-Control": "public, max-age=86400"},
            )
        else:
            raise HTTPException(status_code=404, detail="Logo not found")

    @router.post("/reload-config", response_class=JSONResponse)
    async def reload_config() -> Any:
        try:
            await app_state.reload()
            return {"status": "success", "message": "Configuration reloaded."}
        except Exception as exc:
            return JSONResponse(status_code=500, content={"status": "error", "message": str(exc)})

    @router.get("/config", response_class=JSONResponse)
    async def get_config() -> Any:
        cfg = app_state.config
        return {
            "base_url": cfg.base_url,
            "host": cfg.host,
            "port": cfg.port,
            "mount_prefix": cfg.mount_prefix,
            "data_cache_ttl_s": cfg.data_cache_ttl_s,
            "redis_cache_ttl_s": cfg.redis_cache_ttl_s,
            "snapshot_poll_s": cfg.snapshot_poll_s,
            "bg_update_min": cfg.bg_update_min,
            "redis_connected": app_state.redis is not None,
            "gzip_enabled": cfg.enable_gzip,
            "webp_enabled": bool(cfg.webp_enabled and PILLOW_AVAILABLE),
        }

    return router
