#!/usr/bin/env python3
"""Loopback-only synthetic service used by the operations continuity drill."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
from urllib.parse import unquote, urlsplit

REVISION = "baseline"


class Handler(BaseHTTPRequestHandler):
    db_path = None

    def respond(self, status, payload):
        body = json.dumps(payload, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/health":
            self.respond(200, {"service": "synthetic", "status": "ok"})
            return
        if path.startswith("/records/"):
            ident = unquote(path[len("/records/"):])
            with sqlite3.connect(self.db_path) as db:
                row = db.execute("SELECT owner, body FROM records WHERE id=?", (ident,)).fetchone()
            principal = self.headers.get("X-Principal", "")
            if row is None or row[0] != principal:
                self.respond(404, {"error": "not found"})
            else:
                self.respond(200, {"id": ident, "body": row[1]})
            return
        self.respond(404, {"error": "not found"})

    def do_POST(self):
        if urlsplit(self.path).path != "/records":
            self.respond(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 16384:
                raise ValueError
            data = json.loads(self.rfile.read(length))
            if any(not isinstance(data.get(key), str) or not data[key]
                   for key in ("id", "owner", "body")):
                raise ValueError
            with sqlite3.connect(self.db_path) as db:
                db.execute("INSERT INTO records(id,owner,body) VALUES(?,?,?)",
                           (data["id"], data["owner"], data["body"]))
            self.respond(201, {"id": data["id"], "placed": True})
        except (ValueError, TypeError, json.JSONDecodeError, sqlite3.IntegrityError):
            self.respond(400, {"error": "invalid record"})

    def log_message(self, fmt, *args):
        # Keep synthetic record bodies and local requests out of diagnostic logs.
        return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--port-file", required=True)
    args = parser.parse_args()
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.db) as db:
        db.execute("CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY, owner TEXT NOT NULL, body TEXT NOT NULL)")
    Handler.db_path = args.db
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    Path(args.port_file).write_text(json.dumps({"port": server.server_address[1],
                                                "revision": REVISION}))
    print("revision=" + REVISION, flush=True)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
