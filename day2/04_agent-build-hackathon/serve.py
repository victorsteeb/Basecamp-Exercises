#!/usr/bin/env python3
"""Local launcher for helios_agent.html.

Serves the HTML on http://127.0.0.1:8765 and exposes one endpoint:

    GET /api/env-key  ->  {"ANTHROPIC_API_KEY": "<value or empty string>"}

The browser fetches this at load time and pre-fills the API-key field.
Opening helios_agent.html directly (file://) skips this and falls back to
localStorage / manual paste.
"""
from __future__ import annotations

import json
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
PORT = int(os.environ.get("HELIOS_PORT", "8765"))
HOST = "127.0.0.1"


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, code: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/env-key":
            self._send_json({"ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "")})
            return
        if self.path in ("/", "/helios_agent.html"):
            self._send_file(ROOT / "helios_agent.html", "text/html; charset=utf-8")
            return
        # Refuse anything else — single-page app, no other assets.
        self.send_response(404)
        self.end_headers()

    def log_message(self, fmt: str, *args) -> None:  # quiet
        sys.stderr.write(f"[helios] {fmt % args}\n")


def main() -> int:
    if not (ROOT / "helios_agent.html").exists():
        sys.stderr.write("helios_agent.html not found next to serve.py\n")
        return 1
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}/helios_agent.html"
    print(f"Helios RFP Agent → {url}")
    print(f"  ANTHROPIC_API_KEY in env: {'yes' if has_key else 'no (paste in UI)'}")
    print("  Ctrl-C to stop.")
    if "--no-open" not in sys.argv:
        try: webbrowser.open(url)
        except Exception: pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
