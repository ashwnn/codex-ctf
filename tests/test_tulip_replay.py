"""Tulip replay must stay one-target, allowlisted, bounded, and flag-private."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/tulip-replay.py"
FLAG = "FAUST_" + "A" * 32


class Handler(BaseHTTPRequestHandler):
    requests = []

    def do_GET(self):
        type(self).requests.append(self.path)
        body = FLAG.encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


class TulipReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        Handler.requests = []
        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.thread.join, 2)
        self.addCleanup(self.server.shutdown)
        self.target = "http://127.0.0.1:%d" % self.server.server_port
        self.targets = self.root / "published-targets.txt"
        self.targets.write_text(self.target + "\n")
        self.targets.chmod(0o600)
        self.request_file = self.root / "request.raw"
        self.request_file.write_bytes(
            b"GET /note/{FLAGID} HTTP/1.1\r\nHost: {HOST}\r\n"
            b"X-Principal: alice\r\nConnection: close\r\n\r\n")
        self.request_file.chmod(0o600)

    def command(self, target=None):
        return subprocess.run([
            sys.executable, str(SCRIPT), "--request", str(self.request_file),
            "--published-targets", str(self.targets), "--target", target or self.target,
            "--flag-id", "public-id-7", "--service", "svc", "--team", "7",
            "--flag-regex", r"FAUST_[A-Za-z0-9+/=]{32}", "--source", "finding-1",
        ], cwd=self.workspace, capture_output=True, text=True, timeout=10)

    def test_single_allowlisted_request_hands_flag_to_private_inbox(self):
        result = self.command()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(FLAG, result.stdout + result.stderr)
        self.assertEqual(Handler.requests, ["/note/public-id-7"])
        self.assertIn("captured 1 value(s)", result.stdout)
        inbox = self.workspace / ".runtime/flags/inbox"
        files = list(inbox.glob("tulip-*.jsonl"))
        self.assertEqual(len(files), 1)
        self.assertEqual(inbox.stat().st_mode & 0o777, 0o700)
        self.assertEqual(files[0].stat().st_mode & 0o777, 0o600)
        record = json.loads(files[0].read_text())
        self.assertEqual(record["flag"], FLAG)
        self.assertEqual(record["flag_id"], "public-id-7")
        self.assertEqual(record["service"], "svc")

    def test_target_outside_exact_published_list_is_refused_before_request(self):
        unlisted = "http://127.0.0.1:%d" % (self.server.server_port + 1)
        result = self.command(unlisted)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(Handler.requests, [])
        self.assertFalse((self.workspace / ".runtime/flags").exists())

    def test_public_plain_http_is_refused(self):
        self.targets.write_text("http://8.8.8.8\n")
        result = self.command("http://8.8.8.8")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(Handler.requests, [])


if __name__ == "__main__":
    unittest.main()
