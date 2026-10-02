"""A real local HTTP server, so tests exercise actual requests, redirects, and statuses."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


@dataclass
class Site:
    base: str
    routes: dict[str, tuple[int, dict[str, str], bytes]] = field(default_factory=dict)
    requests: list[tuple[str, str]] = field(default_factory=list)  # (path, user agent)

    def add(self, path: str, body: str | bytes = b"", status: int = 200, **headers: str) -> None:
        data = body.encode() if isinstance(body, str) else body
        headers = {k.replace("_", "-"): v for k, v in headers.items()}
        headers.setdefault("Content-Type", "text/html; charset=utf-8")
        self.routes[path] = (status, headers, data)

    def html(self, path: str, body: str, **headers: str) -> None:
        self.add(
            path, f"<html><head><title>{path}</title></head><body>{body}</body></html>", **headers
        )

    def fetched(self) -> list[str]:
        return [path for path, _ in self.requests]


@pytest.fixture
def site() -> Iterator[Site]:
    holder: dict[str, Site] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            current = holder["site"]
            current.requests.append((self.path, self.headers.get("User-Agent", "")))
            status, headers, body = current.routes.get(
                self.path, (404, {"Content-Type": "text/plain"}, b"not found")
            )
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    holder["site"] = Site(f"http://127.0.0.1:{server.server_port}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield holder["site"]
    server.shutdown()
    server.server_close()


@pytest.fixture
def no_sleep() -> list[float]:
    """Collects requested sleeps instead of waiting, so pacing is asserted, not endured."""
    return []
