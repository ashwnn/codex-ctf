#!/usr/bin/env python3
"""Run a loopback-only checker/persistence/restart/source-rollback drill."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "benchmarks/operations-drill/service.py"
UTC = dt.timezone.utc


def now():
    return dt.datetime.now(UTC).isoformat()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Fixture:
    def __init__(self, source, database, directory):
        self.port_file = directory / "service.port"
        self.port_file.unlink(missing_ok=True)
        self.process = subprocess.Popen(
            [sys.executable, str(source), "--db", str(database), "--port-file", str(self.port_file)],
            cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, env={**os.environ, "http_proxy": "", "https_proxy": "",
                                             "HTTP_PROXY": "", "HTTPS_PROXY": "", "ALL_PROXY": ""})
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError("synthetic service exited during startup")
            if self.port_file.exists():
                ready = json.loads(self.port_file.read_text())
                self.port = int(ready["port"])
                self.revision = ready["revision"]
                self.base = "http://127.0.0.1:%d" % self.port
                return
            time.sleep(0.02)
        self.stop()
        raise RuntimeError("synthetic service readiness timeout")

    def request(self, method, path, payload=None, principal=None):
        headers = {}
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode()
        if principal is not None:
            headers["X-Principal"] = principal
        request = urllib.request.Request(self.base + path, data=body, headers=headers, method=method)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(request, timeout=2) as response:
                return response.status, json.loads(response.read(16385))
        except urllib.error.HTTPError as response:
            return response.code, json.loads(response.read(16385))

    def stop(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="New private result directory (default: .runtime/operations-drill/run-UTC)")
    args = parser.parse_args()
    default_name = dt.datetime.now(UTC).strftime("run-%Y%m%dT%H%M%SZ")
    output = Path(args.output) if args.output else ROOT / ".runtime/operations-drill" / default_name
    if not output.is_absolute():
        output = ROOT / output
    output.mkdir(parents=True, mode=0o700)
    os.chmod(output, 0o700)

    baseline = output / "baseline.py"
    candidate = output / "candidate.py"
    source_text = SERVICE.read_text()
    if source_text.count('REVISION = "baseline"') != 1:
        raise SystemExit("operations-drill: fixture revision marker is not unique")
    baseline.write_text(source_text)
    candidate.write_text(source_text.replace('REVISION = "baseline"', 'REVISION = "candidate"'))
    baseline.chmod(0o600)
    candidate.chmod(0o600)
    db_path = output / "records.sqlite3"
    backup_path = output / "recovery-backup.sqlite3"
    result = {
        "fixture": "synthetic-loopback-only",
        "started_at": now(),
        "sources": {"baseline_sha256": digest(baseline), "candidate_sha256": digest(candidate)},
        "checks": [], "health_observations": {}, "stop_start_intervals_seconds": {},
        "record_count_after_rollback": None,
    }
    checks = result["checks"]
    phases = {}
    fixture = None

    def check(name, observed, expected):
        checks.append({"name": name, "passed": observed == expected,
                       "expected_status": expected[0], "observed_status": observed[0],
                       "response_matches": observed[1] == expected[1]})
        return observed == expected

    def health_samples(phase, app):
        samples = []
        for _ in range(3):
            before = time.monotonic()
            status, body = app.request("GET", "/health")
            samples.append({"at": now(), "status": status,
                            "expected_response": body == {"service": "synthetic", "status": "ok"},
                            "latency_ms": round((time.monotonic() - before) * 1000, 3)})
            time.sleep(0.02)
        result["health_observations"][phase] = samples
        checks.append({"name": phase + "_health_3_samples",
                       "passed": all(item["status"] == 200 and item["expected_response"] for item in samples),
                       "sample_count": len(samples)})

    def start(phase, source):
        phases[phase] = {"started_at": now(), "source_sha256": digest(source)}
        app = Fixture(source, db_path, output)
        phases[phase]["revision"] = app.revision
        return app

    def stop(phase, app):
        app.stop()
        phases[phase]["stopped_at"] = now()

    def interval(name, previous_phase, next_phase):
        stopped = dt.datetime.fromisoformat(phases[previous_phase]["stopped_at"])
        started = dt.datetime.fromisoformat(phases[next_phase]["started_at"])
        result["stop_start_intervals_seconds"][name] = round((started - stopped).total_seconds(), 3)

    try:
        fixture = start("baseline", baseline)
        health_samples("baseline", fixture)
        check("place_A", fixture.request("POST", "/records", {"id": "A", "owner": "alice", "body": "SYNTHETIC_A"}),
              (201, {"id": "A", "placed": True}))
        check("owner_reads_A", fixture.request("GET", "/records/A", principal="alice"),
              (200, {"id": "A", "body": "SYNTHETIC_A"}))
        check("other_owner_cannot_read_A", fixture.request("GET", "/records/A", principal="bob"),
              (404, {"error": "not found"}))
        stop("baseline", fixture)
        fixture = None

        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(backup_path)
        src.backup(dst)
        dst.close()
        src.close()
        backup_path.chmod(0o600)
        result["recovery_backup"] = {"created": True, "sha256": digest(backup_path)}

        fixture = start("candidate", candidate)
        interval("baseline_to_candidate", "baseline", "candidate")
        health_samples("candidate", fixture)
        check("candidate_reads_A", fixture.request("GET", "/records/A", principal="alice"),
              (200, {"id": "A", "body": "SYNTHETIC_A"}))
        check("place_B_after_change", fixture.request("POST", "/records", {"id": "B", "owner": "bob", "body": "SYNTHETIC_B"}),
              (201, {"id": "B", "placed": True}))
        check("owner_reads_B", fixture.request("GET", "/records/B", principal="bob"),
              (200, {"id": "B", "body": "SYNTHETIC_B"}))
        stop("candidate", fixture)
        fixture = None

        fixture = start("candidate_restart", candidate)
        interval("candidate_restart", "candidate", "candidate_restart")
        health_samples("candidate_restart", fixture)
        check("A_survives_candidate_restart", fixture.request("GET", "/records/A", principal="alice"),
              (200, {"id": "A", "body": "SYNTHETIC_A"}))
        check("B_survives_candidate_restart", fixture.request("GET", "/records/B", principal="bob"),
              (200, {"id": "B", "body": "SYNTHETIC_B"}))
        stop("candidate_restart", fixture)
        fixture = None

        # Roll back executable source only; keep the current live database.
        fixture = start("rollback", baseline)
        interval("rollback_source_only", "candidate_restart", "rollback")
        health_samples("rollback", fixture)
        check("A_survives_source_rollback", fixture.request("GET", "/records/A", principal="alice"),
              (200, {"id": "A", "body": "SYNTHETIC_A"}))
        check("B_survives_source_rollback", fixture.request("GET", "/records/B", principal="bob"),
              (200, {"id": "B", "body": "SYNTHETIC_B"}))
        with sqlite3.connect(db_path) as db:
            result["record_count_after_rollback"] = db.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        stop("rollback", fixture)
        fixture = None
        result["phases"] = phases
        result["completed_at"] = now()
        result["passed"] = all(item["passed"] for item in checks)
    except Exception:
        result["phases"] = phases
        result["completed_at"] = now()
        result["passed"] = False
        result["error"] = "drill interrupted; inspect local diagnostic setup"
    finally:
        if fixture is not None:
            fixture.stop()
        result_path = output / "result.json"
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        result_path.chmod(0o600)
    print("operations-drill: %s (%d checks)" % ("passed" if result["passed"] else "failed", len(checks)))
    print("result: %s" % result_path)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
