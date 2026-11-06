from __future__ import annotations

import asyncio
import os
import urllib.parse
from pathlib import Path
from typing import Any, Optional

from sickshift_dashboard.config import Settings, load_config
from sickshift_dashboard.state import AppState, state


def create_sub_app(
    mount_prefix: str = "/dashboard",
    app_state: AppState = state,
    config_override: Optional[Settings] = None,
) -> Any:
    """Creates a FastAPI application configured with a prefix (e.g. '/dashboard')
    for mounting under ASGI or behind a reverse proxy."""
    from sickshift_dashboard.app import create_app

    cfg = config_override or load_config()
    cfg.mount_prefix = mount_prefix
    return create_app(app_state=app_state, config_override=cfg)


def register_tornado_bridge(
    tornado_app: Any,
    host_pattern: str = r".*",
    web_root: str = "",
    prefix: str = "/dashboard",
    app_state: AppState = state,
) -> None:
    """Native integration bridge inside SickShift's Tornado web server (`webserveInit.py`).

    Registers:
    1. ASGI handler for FastAPI dashboard under `prefix` (e.g. `/dashboard`).
    2. Transparent white network logo handler under `/images/network/(.*)` with legibility checks.
    """
    import tornado.routing
    import tornado.web
    from tornado.ioloop import IOLoop

    clean_root = (web_root or "").rstrip("/")
    clean_prefix = "/" + prefix.strip("/")
    full_prefix = f"{clean_root}{clean_prefix}"

    cfg = load_config()
    cfg.web_root = clean_root
    cfg.mount_prefix = full_prefix
    cfg.base_url = clean_root

    # Dynamically detect db_path from SickShift runtime if available
    try:
        import sickshift
        if hasattr(sickshift, "db") and hasattr(sickshift.db, "dbFilename"):
            db_fn = sickshift.db.dbFilename()
            if db_fn:
                cfg.db_path = str(Path(db_fn).resolve())
    except Exception:
        pass

    fastapi_app = create_sub_app(mount_prefix=full_prefix, app_state=app_state, config_override=cfg)

    # Asynchronous initialization on Tornado event loop if not yet completed
    async def _ensure_init() -> None:
        if not app_state.initialized:
            await app_state.initialize(config_override=cfg)

    try:
        IOLoop.current().add_callback(_ensure_init)
    except Exception:
        pass

    class _ASGIAdapterHandler(tornado.web.RequestHandler):
        def check_xsrf_cookie(self) -> None:
            # Dashboard API routes handle their own security
            return

        async def _dispatch_asgi(self) -> None:
            if not app_state.initialized:
                await app_state.initialize(config_override=cfg)

            path = self.request.path
            if path.startswith(full_prefix):
                sub_path = path[len(full_prefix) :] or "/"
            else:
                sub_path = path or "/"

            decoded_path = urllib.parse.unquote(sub_path)

            raw_headers = [
                (k.lower().encode("latin-1"), v.encode("latin-1"))
                for k, v in self.request.headers.get_all()
            ]

            # Dynamic host and port extraction from request
            server_host = "127.0.0.1"
            server_port = 8081
            if self.request.host:
                parts = self.request.host.split(":")
                server_host = parts[0]
                if len(parts) > 1 and parts[1].isdigit():
                    server_port = int(parts[1])
                elif getattr(self.request, "protocol", "http") == "https":
                    server_port = 443
                else:
                    server_port = 80
            elif app_state.config.port:
                server_port = app_state.config.port
                server_host = app_state.config.host or "127.0.0.1"

            scope = {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": self.request.method or "GET",
                "scheme": self.request.protocol or "http",
                "path": decoded_path,
                "raw_path": sub_path.encode("utf-8"),
                "root_path": full_prefix,
                "query_string": (self.request.query or "").encode("latin-1"),
                "headers": raw_headers,
                "client": (self.request.remote_ip or "127.0.0.1", 0),
                "server": (server_host, server_port),
            }

            body_bytes = self.request.body or b""
            request_sent = False

            async def receive() -> dict[str, Any]:
                nonlocal request_sent
                if not request_sent:
                    request_sent = True
                    return {"type": "http.request", "body": body_bytes, "more_body": False}
                await asyncio.Future()
                return {"type": "http.disconnect"}

            async def send(message: dict[str, Any]) -> None:
                msg_type = message.get("type")
                if msg_type == "http.response.start":
                    self.set_status(message.get("status", 200))
                    for hk, hv in message.get("headers", []):
                        h_name = hk.decode("latin-1")
                        h_val = hv.decode("latin-1")
                        if h_name.lower() == "content-length":
                            continue
                        self.set_header(h_name, h_val)
                elif msg_type == "http.response.body":
                    chunk = message.get("body", b"")
                    if chunk:
                        self.write(chunk)
                    if not message.get("more_body", False):
                        self.finish()

            await fastapi_app(scope, receive, send)

        async def get(self, *_args: Any, **_kwargs: Any) -> None:
            await self._dispatch_asgi()

        async def post(self, *_args: Any, **_kwargs: Any) -> None:
            await self._dispatch_asgi()

        async def head(self, *_args: Any, **_kwargs: Any) -> None:
            await self._dispatch_asgi()

    class _NetworkLogoHandler(tornado.web.RequestHandler):
        """Handler for serving white silhouette network logos on transparent backgrounds with legibility fallback."""
        def compute_etag(self) -> Optional[str]:
            return None

        def head(self, path_arg: str) -> None:
            self._serve(path_arg, is_head=True)

        def get(self, path_arg: str) -> None:
            self._serve(path_arg, is_head=False)

        def _serve(self, path_arg: str, is_head: bool = False) -> None:
            clean_filename = urllib.parse.unquote(path_arg or "").strip("/")
            if not clean_filename:
                self.set_status(404)
                return

            # Search in gui/slick/images/network
            logo_path = None
            search_dirs: list[Path] = [
                Path(__file__).resolve().parent.parent / "gui" / "slick" / "images" / "network",
            ]
            try:
                import sickshift
                if hasattr(sickshift, "PROG_DIR") and sickshift.PROG_DIR:
                    search_dirs.append(Path(sickshift.PROG_DIR) / "gui" / "slick" / "images" / "network")
            except Exception:
                pass

            for sdir in search_dirs:
                if not sdir.is_dir():
                    continue
                cand = sdir / clean_filename
                if cand.is_file():
                    logo_path = cand
                    break
                # Try lower-cased filename
                cand_lower = sdir / clean_filename.lower()
                if cand_lower.is_file():
                    logo_path = cand_lower
                    break
                # Case-insensitive directory scan
                clean_stem_lower = Path(clean_filename).stem.lower()
                for entry in sdir.glob("*.png"):
                    if entry.stem.lower() == clean_stem_lower:
                        logo_path = entry
                        break
                if logo_path:
                    break

            if not logo_path:
                self.set_status(404)
                return

            from sickshift_dashboard.white_logo import get_white_or_original_logo
            target = get_white_or_original_logo(logo_path)

            self.set_header("Content-Type", "image/png")
            self.set_header("Cache-Control", "no-cache, must-revalidate")
            if not is_head:
                try:
                    self.write(target.read_bytes())
                except Exception:
                    self.set_status(500)

    # Register FastAPI dashboard ASGI handler
    tornado_app.add_handlers(
        host_pattern,
        [
            (rf"{full_prefix}(/?.*)", _ASGIAdapterHandler),
        ],
    )

    # Intercept /images/network/(.*) with high priority rule to serve white logos
    try:
        network_rule = tornado.web.URLSpec(
            rf"{clean_root}/images/network/(.*)",
            _NetworkLogoHandler,
        )
        if hasattr(tornado_app, "default_router") and hasattr(tornado_app.default_router, "rules"):
            for r in tornado_app.default_router.rules:
                if hasattr(r, "target") and hasattr(r.target, "rules"):
                    r.target.rules.insert(0, network_rule)
    except Exception as exc:
        print(f"[BRIDGE] Tornado network logo rule not prepended: {exc}")
