"""Serve the viewer locally and keep its data fresh.

    python -m dsnsim.serve                 # http://localhost:8002, rebuild every 60 min
    python -m dsnsim.serve --port 8080 --interval 30
    python -m dsnsim.serve --no-build      # serve only

Builds the data once at start-up, then again every --interval minutes, while
serving the site folder. Stop with Ctrl-C.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import sys
import threading
import time
from pathlib import Path

from . import build


def _rebuild_loop(out: Path, interval_min: float) -> None:
    while True:
        try:
            build.main(["--out", str(out)])
        except (Exception, SystemExit) as exc:  # keep serving the last good data
            print(f"build failed: {exc!r}", file=sys.stderr, flush=True)
        if interval_min <= 0:
            return
        time.sleep(interval_min * 60)


class _Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):  # quiet: the viewer polls every few minutes
        pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", default="site", help="folder to serve (default: site)")
    ap.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 to allow other machines to connect")
    ap.add_argument("--port", type=int, default=8002)
    ap.add_argument("--interval", type=float, default=60, help="minutes between rebuilds; 0 builds once")
    ap.add_argument("--no-build", action="store_true", help="serve only")
    args = ap.parse_args(argv)

    site = Path(args.site)
    if not (site / "index.html").exists():
        ap.error(f"{site}/index.html not found; run from the repository root or pass --site")
    if not args.no_build:
        threading.Thread(target=_rebuild_loop, args=(site / "data", args.interval), daemon=True).start()

    handler = functools.partial(_Handler, directory=str(site))
    with http.server.ThreadingHTTPServer((args.host, args.port), handler) as httpd:
        print(f"Serving {site}/ at http://localhost:{args.port}  (Ctrl-C to stop)", flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
