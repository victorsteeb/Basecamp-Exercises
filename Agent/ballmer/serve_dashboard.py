"""Local live web dashboard for Ballmer — standard library only, no pip installs.

Runs the deterministic always-on session once, then plays it back tick-by-tick
on a wall-clock cadence so the browser shows BAC climbing into the band, the
in-range indicator flipping, and the burndown countdown — live.

Run:
    python serve_dashboard.py                 # http://127.0.0.1:8765 , opens browser
    python serve_dashboard.py --port 9000 --speed 1.5
    python serve_dashboard.py --empty-stomach --no-open --no-loop

Everything is served from localhost; nothing leaves your machine.
"""

import argparse
import json
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ballmer import config
from ballmer.agent import run_session
from ballmer.web_data import build_frames, session_meta

ROOT = Path(__file__).parent
HTML = (ROOT / "web" / "dashboard.html").read_text(encoding="utf-8")


class Playback:
    """Maps wall-clock elapsed time to a frame cursor, looping with an end pause."""
    def __init__(self, frames, speed=2.0, loop=True, end_pause=4.0):
        self.frames = frames
        self.n = len(frames)
        self.speed = speed          # real seconds per simulated tick
        self.loop = loop
        self.end_pause = end_pause
        self.t0 = time.monotonic()

    def current(self):
        elapsed = time.monotonic() - self.t0
        if not self.loop:
            return self.frames[min(self.n - 1, int(elapsed / self.speed))]
        cycle = self.n * self.speed + self.end_pause
        phase = elapsed % cycle
        return self.frames[min(self.n - 1, int(phase / self.speed))]


class AppState:
    """Thread-safe container for the live playback state and config."""

    def __init__(self, frames, meta, cfg):
        self._lock = threading.RLock()
        self._playback = Playback(frames, speed=cfg["speed"], loop=cfg["loop"])
        self._meta = meta
        self._cfg = cfg

    def frame(self):
        with self._lock:
            return self._playback.current()

    def get_meta(self):
        with self._lock:
            return dict(self._meta)

    def get_config(self):
        with self._lock:
            return dict(self._cfg)

    def apply(self, patch, root):
        """Merge patch into config. Re-runs simulation for physiology changes."""
        SIM_KEYS = ("food_state", "auto_consume", "start_time", "profile_overrides")
        needs_sim = any(k in patch for k in SIM_KEYS)
        with self._lock:
            if "profile_overrides" in patch:
                existing = self._cfg.get("profile_overrides") or {}
                self._cfg["profile_overrides"] = {**existing, **patch.pop("profile_overrides")}
            self._cfg.update(patch)
            cfg = self._cfg
            if needs_sim:
                session = run_session(
                    str(root),
                    auto_consume=cfg["auto_consume"],
                    food_state=cfg["food_state"],
                    write_log=False,
                    start_time_str=cfg.get("start_time"),
                    profile_overrides=cfg.get("profile_overrides") or None,
                )
                frames = build_frames(session)
                self._meta = session_meta(session)
                self._playback = Playback(frames, speed=cfg["speed"], loop=cfg["loop"])
            else:
                self._playback.speed = cfg["speed"]
                self._playback.loop = cfg["loop"]


def make_handler(app_state: AppState, root: Path):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, body, ctype="application/json", status=200):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path.startswith("/api/meta"):
                self._send(json.dumps(app_state.get_meta()))
            elif self.path.startswith("/api/state"):
                self._send(json.dumps(app_state.frame()))
            elif self.path.startswith("/api/config"):
                self._send(json.dumps(app_state.get_config()))
            elif self.path in ("/", "/index.html"):
                self._send(HTML, "text/html; charset=utf-8")
            else:
                self.send_error(404)

        def do_POST(self):
            if self.path.startswith("/api/config"):
                length = int(self.headers.get("Content-Length", 0))
                patch = json.loads(self.rfile.read(length))
                app_state.apply(patch, root)
                self._send(json.dumps({"ok": True}))
            else:
                self.send_error(404)

        def log_message(self, *a):
            pass

    return Handler


def main(argv=None):
    p = argparse.ArgumentParser(description="Ballmer live web dashboard (localhost)")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--speed", type=float, default=2.0, help="real seconds per simulated tick")
    p.add_argument("--no-loop", action="store_true")
    p.add_argument("--no-open", action="store_true", help="don't auto-open the browser")
    p.add_argument("--empty-stomach", action="store_true")
    p.add_argument("--full-stomach", action="store_true")
    p.add_argument("--no-auto-consume", action="store_true")
    args = p.parse_args(argv)

    food = ("empty" if args.empty_stomach else
            "full" if args.full_stomach else config.DEFAULT_FOOD_STATE)

    cfg = {
        "food_state": food,
        "auto_consume": not args.no_auto_consume,
        "speed": args.speed,
        "loop": not args.no_loop,
        "start_time": None,
        "profile_overrides": {},
    }

    session = run_session(str(ROOT), auto_consume=cfg["auto_consume"],
                          food_state=cfg["food_state"], write_log=False)
    frames = build_frames(session)
    meta = session_meta(session)
    cfg["start_time"] = meta["start_time"]

    app_state = AppState(frames, meta, cfg)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(app_state, ROOT))
    url = f"http://127.0.0.1:{args.port}"
    print(f"Ballmer dashboard live at {url}")
    print(f"  {len(frames)} ticks · {args.speed}s/tick · "
          f"{'looping' if not args.no_loop else 'play once'} · food={food}")
    print("  Ctrl-C to stop.")
    if not args.no_open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
