"""Synthetic flag lifecycle and transport tests; never send live flags."""
import contextlib
import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ledger = load("flag_ledger", "flag-ledger.py")
http = load("submit_http", "submit-http.py")


def record(flag="SYNTHETIC_FLAG_A", expires=None):
    return {"flag": flag, "service": "synthetic", "team": "2", "flag_id": "test-object",
            "source": "local mock", "expires_at": expires}


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = ledger.connect(self.root / "flags/ledger.sqlite3")
        self.addCleanup(self.db.close)

    def ingest(self, *records):
        return ledger.ingest(self.db, io.StringIO("\n".join(json.dumps(r) for r in records)))

    def adapter(self, code):
        path = self.root / "adapter.py"
        path.write_text("import json, sys\np=json.load(sys.stdin)\n" + code)
        return path

    def test_deduplication_unknown_expiry_and_private_storage(self):
        self.assertEqual(self.ingest(record(), record()), {"added": 1, "duplicates": 1})
        self.assertEqual(ledger.status(self.db)["unknown_expiry"], 1)
        self.assertEqual((self.root / "flags").stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.root / "flags/ledger.sqlite3").stat().st_mode & 0o777, 0o600)
        expiry = ledger.iso(time.time() + 500)
        self.ingest(record(expires=expiry))
        self.assertEqual(ledger.status(self.db)["unknown_expiry"], 0)
        with self.assertRaises(ValueError):
            self.ingest(record(expires=ledger.iso(time.time() + 1000)))
        self.assertEqual(self.db.execute("SELECT expires FROM flags").fetchone()[0], ledger.timestamp(expiry))

    def test_invalid_import_is_atomic_and_timezone_required(self):
        with self.assertRaises(ValueError):
            self.ingest(record(), record("OTHER", "2026-10-01T12:00:00"))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM flags").fetchone()[0], 0)

    def test_hold_plan_and_signal_requirement(self):
        now = time.time()
        self.ingest(record("OLD", ledger.iso(now - 1)), record("SOON", ledger.iso(now + 100)), record())
        plan = ledger.status(self.db, at=now + 200)
        self.assertEqual(plan["states"]["expired"], 1)
        self.assertEqual(plan["at_risk_count"], 1)
        self.assertEqual(plan["submission_mode"], "hold_until_signal")
        with self.assertRaises(ValueError):
            ledger.submit(self.db, "missing", "timer")
        self.assertEqual(self.db.execute("SELECT SUM(attempts) FROM flags").fetchone()[0], 0)

    def test_submit_earliest_first_partial_receipt_and_no_unknown_expiry(self):
        now = time.time()
        self.ingest(record("LATER", ledger.iso(now + 600)), record("FIRST", ledger.iso(now + 300)), record())
        adapter = self.adapter('assert p["flags"][0]["flag"] == "FIRST"\n'
                               'print(json.dumps({"results":[{"id":p["flags"][0]["id"],"status":"accepted"}]}))\n')
        result = ledger.submit(self.db, adapter, "SUBMIT_NOW")
        self.assertEqual(result["attempted"], 2)
        self.assertEqual(result["states"], {"accepted": 1, "pending": 1, "uncertain": 1})
        self.assertEqual(result["stopped"], "retry_or_uncertain_receipt")

    def test_error_is_uncertain_and_next_release_does_not_resend(self):
        self.ingest(record(expires=ledger.iso(time.time() + 300)))
        adapter = self.adapter('print("SECRET_BAD_RECEIPT")\n')
        result = ledger.submit(self.db, adapter, "SUBMIT_NOW")
        self.assertEqual(result["states"]["uncertain"], 1)
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertEqual(ledger.submit(self.db, adapter, "SUBMIT_NOW")["attempted"], 0)
        ident = self.db.execute("SELECT id FROM flags").fetchone()[0]
        item = ledger.review(self.db)[0]
        self.assertEqual(item["id"], ident)
        self.assertEqual(item["state"], "uncertain")
        self.assertNotIn("flag", item)
        self.assertNotIn("SYNTHETIC_FLAG_A", json.dumps(item))
        ledger.reconcile(self.db, io.StringIO(json.dumps({"id": ident, "status": "pending", "evidence": "receipts/mock.json"})))
        self.assertEqual(ledger.status(self.db)["states"]["pending"], 1)
        receipts = ledger.receipt_history(self.db, ident)
        self.assertEqual(receipts[0]["evidence"], "receipts/mock.json")
        self.assertEqual(receipts[0]["status"], "pending")

    def test_old_receipt_schema_is_migrated_without_data_loss(self):
        path = self.root / "old/ledger.sqlite3"
        path.parent.mkdir()
        old = sqlite3.connect(path)
        old.execute("CREATE TABLE receipts (id INTEGER PRIMARY KEY, flag_id TEXT NOT NULL, at REAL NOT NULL, state TEXT NOT NULL)")
        old.execute("INSERT INTO receipts (flag_id,at,state) VALUES ('%s',1,'uncertain')" % ("a" * 64))
        old.commit()
        old.close()
        migrated = ledger.connect(path)
        self.addCleanup(migrated.close)
        history = ledger.receipt_history(migrated, "a" * 64)
        self.assertEqual(history[0]["status"], "uncertain")
        self.assertIsNone(history[0]["evidence"])

    def test_timeout_and_bad_receipts_do_not_report_acceptance(self):
        self.ingest(record(expires=ledger.iso(time.time() + 300)))
        adapter = self.adapter('import time\ntime.sleep(1)\n')
        self.assertEqual(ledger.submit(self.db, adapter, "SUBMIT_NOW", timeout=0.05)["states"], {"uncertain": 1})
        row = self.db.execute("SELECT * FROM flags").fetchone()
        with self.assertRaises(ValueError):
            ledger.apply_results(self.db, [row], {"results": [{"id": "unknown", "status": "accepted"}]})

    def test_bounded_flush_and_delay_rechecks_expiry(self):
        now = time.time()
        self.ingest(record("A", ledger.iso(now + 300)), record("B", ledger.iso(now + 400)))
        adapter = self.adapter('print(json.dumps({"results":[{"id":e["id"],"status":"duplicate"} for e in p["flags"]]}))\n')
        result = ledger.submit(self.db, adapter, "SUBMIT_NOW", batch_size=1, max_batches=1)
        self.assertEqual(result["states"], {"duplicate": 1, "pending": 1})
        self.assertEqual(ledger.submit(self.db, adapter, "SUBMIT_NOW", at=now + 1)["attempted"], 0)

    def test_crash_claim_and_new_arrivals_stay_held(self):
        self.ingest(record(expires=ledger.iso(time.time() + 300)))
        adapter = self.adapter('''import sqlite3
db=sqlite3.connect(%r)
assert db.execute("SELECT state FROM flags").fetchone()[0] == "uncertain"
db.execute("INSERT INTO flags(id,flag,service,team,flag_id,source,captured,expires,state) VALUES ('new','NEW','s','2','i','mock',0,9999999999,'pending')")
db.commit()
print(json.dumps({"results":[{"id":e["id"],"status":"accepted"} for e in p["flags"]]}))
''' % str(self.root / "flags/ledger.sqlite3"))
        result = ledger.submit(self.db, adapter, "SUBMIT_NOW", batch_size=1)
        self.assertEqual(result["states"], {"accepted": 1, "pending": 1})
        self.assertEqual(result["attempted"], 1)

    def test_cli_output_does_not_leak_flags_or_malformed_input(self):
        env = dict(os.environ)
        command = [sys.executable, str(ROOT / "scripts/flag-ledger.py"), "--db",
                   str(self.root / "cli/ledger.sqlite3"), "ingest"]
        for data in (json.dumps(record()), '{"SYNTHETIC_SECRET_BROKEN":'):
            result = subprocess.run(command, input=data, text=True, capture_output=True, env=env)
            self.assertNotIn("SYNTHETIC", result.stdout + result.stderr)

    def test_review_and_receipts_cli_expose_only_hashed_metadata(self):
        db_path = self.root / "cli-review/ledger.sqlite3"
        command = [sys.executable, str(ROOT / "scripts/flag-ledger.py"), "--db", str(db_path)]
        imported = subprocess.run(command + ["ingest"], input=json.dumps(record()), text=True,
                                  capture_output=True)
        self.assertEqual(imported.returncode, 0, imported.stderr)
        ident = hashlib.sha256(b"SYNTHETIC_FLAG_A").hexdigest()
        db = sqlite3.connect(db_path)
        db.execute("UPDATE flags SET state='uncertain' WHERE id=?", (ident,))
        db.execute("INSERT INTO receipts (flag_id,at,state,evidence) VALUES (?,1,'uncertain','receipts/source.json')",
                   (ident,))
        db.commit()
        db.close()
        review_result = subprocess.run(command + ["review"], text=True, capture_output=True)
        self.assertEqual(review_result.returncode, 0, review_result.stderr)
        self.assertIn(ident, review_result.stdout)
        self.assertNotIn("SYNTHETIC_FLAG_A", review_result.stdout)
        receipts = subprocess.run(command + ["receipts", "--id", ident], text=True, capture_output=True)
        self.assertEqual(receipts.returncode, 0, receipts.stderr)
        self.assertIn("receipts/source.json", receipts.stdout)
        self.assertNotIn("SYNTHETIC_FLAG_A", receipts.stdout)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.received = []
        self.response = (200, {"results": [{"flag": "SYNTHETIC", "status": "OK"}]})
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                parent.received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                status, body = parent.response
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(body).encode())

            def log_message(self, *args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.config = {"url": "http://127.0.0.1:%d/submit" % self.server.server_port,
                       "allow_plain_http": True, "status_map": {"OK": "accepted"}}
        self.payload = {"flags": [{"id": "digest", "flag": "SYNTHETIC"}]}

    def test_receipt_mapping_and_plain_http_opt_in(self):
        result = http.run(self.payload, self.config)
        self.assertEqual(result, {"results": [{"id": "digest", "status": "accepted"}]})
        self.assertEqual(self.received, [{"flags": ["SYNTHETIC"]}])
        self.config.pop("allow_plain_http")
        with self.assertRaises(ValueError):
            http.run(self.payload, self.config)

    def test_rate_limit_and_auth_stop_without_acceptance(self):
        for status in (401, 403, 429):
            self.response = (status, {})
            self.assertEqual(http.run(self.payload, self.config)["results"][0]["status"], "retry")

    def test_unrecognized_status_is_uncertain(self):
        self.response = (200, {"results": [{"flag": "SYNTHETIC", "status": "UNMAPPED"}]})
        self.assertEqual(http.run(self.payload, self.config)["results"][0]["status"], "uncertain")

    def test_plain_http_public_host_is_rejected(self):
        self.config["url"] = "http://example.com/submit"
        with self.assertRaises(ValueError):
            http.run(self.payload, self.config)
        self.assertTrue(http._private_plain_http("127.0.0.1"))
        self.assertTrue(http._private_plain_http("10.0.0.5"))
        self.assertTrue(http._private_plain_http("localhost"))
        self.assertFalse(http._private_plain_http("example.com"))


if __name__ == "__main__":
    unittest.main()
