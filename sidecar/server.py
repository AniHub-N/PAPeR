"""
server.py — the sidecar's local web server (stdlib http.server, zero deps).

This is what makes the frontend "no download": it serves a single self-contained
HTML page and a /state JSON endpoint the page polls. Users open a browser at
http://localhost:8787 — nothing to install.

Run:
    python3 sidecar/server.py --demo     # seed sample data, then serve
    python3 sidecar/server.py            # serve whatever's in the DB
    SIDECAR_UI_PORT=9000 python3 sidecar/server.py

Routes:
    GET /            -> ui/index.html
    GET /state       -> JSON snapshot for the UI (from db/store.get_state)
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# make sibling packages importable when run directly
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# load .env so the server sees the same provider/key config as the hooks
try:
    from primary_router.side_model import _load_dotenv
    _load_dotenv()
except Exception:
    pass

from db import store  # noqa: E402

UI_DIR = Path(__file__).resolve().parent / "ui"
PORT = int(os.environ.get("SIDECAR_UI_PORT", "8787"))


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, content_type):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            index = UI_DIR / "index.html"
            if index.is_file():
                self._send(200, index.read_text(encoding="utf-8"),
                           "text/html; charset=utf-8")
            else:
                self._send(404, "index.html not found", "text/plain")
            return
        if path == "/state":
            conn = store.connect()
            try:
                payload = json.dumps(store.get_state(conn))
            finally:
                conn.close()
            self._send(200, payload, "application/json")
            return
        self._send(404, "not found", "text/plain")

    def log_message(self, *args):
        pass  # quiet; flip to super().log_message for debugging


def main():
    if "--demo" in sys.argv:
        conn = store.connect()
        store.seed_demo(conn)
        conn.close()
        print("[server] seeded demo data")

    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[server] PAPeR sidecar UI → http://localhost:{PORT}  (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] stopped")
        httpd.server_close()


if __name__ == "__main__":
    main()
