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


def make_handler(playback, meta):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, body, ctype="application/json"):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path.startswith("/api/meta"):
                self._send(json.dumps(meta))
            elif self.path.startswith("/api/state"):
                self._send(json.dumps(playback.current()))
            elif self.path in ("/", "/index.html"):
                self._send(HTML, "text/html; charset=utf-8")
            else:
                self.send_error(404)

        def log_message(self, *a):  # silence per-request console spam
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

    session = run_session(str(ROOT), auto_consume=not args.no_auto_consume,
                          food_state=food, write_log=False)
    frames = build_frames(session)
    meta = session_meta(session)
    playback = Playback(frames, speed=args.speed, loop=not args.no_loop)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(playback, meta))
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
