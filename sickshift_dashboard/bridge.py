from __future__ import annotations

import asyncio
import os
import urllib.parse
from pathlib import Path
from typing import Any, Optional, Sequence

from sickshift_dashboard.config import Settings, load_config
from sickshift_dashboard.state import AppState, state



def resolve_network_logo(path_arg: str, search_dirs: Sequence[Path]) -> Optional[Path]:
    """Serve only a PNG inside an approved logo directory.

    Reject path traversal, URL-encoded separators, absolute paths, control
    characters and symlinks resolving outside the configured logo directory.
    Keep the historical case-insensitive filename fallback.
    """
    try:
        filename = urllib.parse.unquote(path_arg or "", errors="strict")
    except UnicodeDecodeError:
        return None
    if (
        not filename
        or "/" in filename
        or "\\" in filename
        or filename in (".", "..")
        or any(ord(char) < 32 or ord(char) == 127 for char in filename)
        or len(filename.encode("utf-8")) > 255
        or not filename.lower().endswith(".png")
    ):
        return None

    for directory in search_dirs:
        if not directory.is_dir():
            continue
        try:
            approved_root = directory.resolve(strict=True)
        except OSError:
            continue
        exact = directory / filename
        lowercase = directory / filename.lower()
        # Restrict the fallback scan to PNG files in the selected directory.
        candidates = [exact, lowercase]
        if not any(candidate.is_file() for candidate in candidates):
            stem = Path(filename).stem.casefold()
            candidates.extend(
                candidate for candidate in directory.glob("*.png")
                if candidate.stem.casefold() == stem
            )
        for candidate in candidates:
            try:
                if (
                    candidate.is_file()
                    and candidate.resolve(strict=True).is_relative_to(approved_root)
                ):
                    return candidate
            except (OSError, RuntimeError):
                continue
    return None


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
            # Never access a caller-supplied path outside an approved PNG folder.
            search_dirs: list[Path] = [
                Path(__file__).resolve().parent.parent / "gui" / "slick" / "images" / "network",
            ]
            try:
                import sickshift
                if hasattr(sickshift, "PROG_DIR") and sickshift.PROG_DIR:
                    search_dirs.append(Path(sickshift.PROG_DIR) / "gui" / "slick" / "images" / "network")
            except Exception:
                pass
            logo_path = resolve_network_logo(path_arg, search_dirs)

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
