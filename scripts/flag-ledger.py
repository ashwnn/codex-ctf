#!/usr/bin/env python3
"""Private flag evidence/transport tool. No inference or agent orchestration."""
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

STATES = {"accepted", "duplicate", "rejected", "expired", "retry", "uncertain"}
UTC = dt.timezone.utc


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Expected a timezone-aware ISO timestamp")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    return parsed.timestamp()


def iso(value):
    return dt.datetime.fromtimestamp(value, UTC).isoformat()


def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    db = sqlite3.connect(str(path), timeout=30)
    db.row_factory = sqlite3.Row
    os.chmod(path, 0o600)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS flags (
            id TEXT PRIMARY KEY, flag TEXT NOT NULL, service TEXT NOT NULL,
            team TEXT NOT NULL, flag_id TEXT NOT NULL, source TEXT NOT NULL,
            captured REAL NOT NULL, expires REAL, state TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY, flag_id TEXT NOT NULL, at REAL NOT NULL,
            state TEXT NOT NULL, evidence TEXT);
    """)
    receipt_columns = {row[1] for row in db.execute("PRAGMA table_info(receipts)")}
    if "evidence" not in receipt_columns:
        db.execute("ALTER TABLE receipts ADD COLUMN evidence TEXT")
    return db


def ingest(db, stream):
    added = duplicates = 0
    # Atomic import: a malformed line rolls back the entire file.
    with db:
        for line in stream:
            if not line.strip():
                continue
            entry = json.loads(line)
            required = ("flag", "service", "team", "flag_id", "source")
            if not isinstance(entry, dict) or any(
                    not isinstance(entry.get(k), str) or not entry[k] for k in required):
                raise ValueError("Flag records need nonempty string provenance fields")
            if len(entry["flag"]) > 4096 or any(c.isspace() for c in entry["flag"]):
                raise ValueError("Invalid flag length or whitespace")
            expiry = timestamp(entry["expires_at"]) if entry.get("expires_at") else None
            captured = timestamp(entry["captured_at"]) if entry.get("captured_at") else time.time()
            ident = hashlib.sha256(entry["flag"].encode()).hexdigest()
            row = db.execute("SELECT expires FROM flags WHERE id=?", (ident,)).fetchone()
            if row:
                # Authoritative metadata may fill a previously unknown expiry;
                # differing known expirations must be reconciled, never extended.
                if expiry is not None and row["expires"] is not None and expiry != row["expires"]:
                    raise ValueError("Conflicting published expiry for an existing flag")
                if expiry is not None and row["expires"] is None:
                    db.execute("UPDATE flags SET expires=?, state='pending' WHERE id=? AND state='pending'",
                               (expiry, ident))
                duplicates += 1
                continue
            db.execute("INSERT INTO flags (id,flag,service,team,flag_id,source,captured,expires,state) "
                       "VALUES (?,?,?,?,?,?,?,?, 'pending')",
                       (ident, *(entry[k] for k in required), captured, expiry))
            added += 1
    return {"added": added, "duplicates": duplicates}


def expire(db, now):
    with db:
        db.execute("UPDATE flags SET state='expired' WHERE state='pending' AND expires<=?", (now,))


def status(db, margin=30, at=None):
    now = time.time()
    expire(db, now)
    counts = dict(db.execute("SELECT state,COUNT(*) FROM flags GROUP BY state").fetchall())
    unknown = db.execute("SELECT COUNT(*) FROM flags WHERE state='pending' AND expires IS NULL").fetchone()[0]
    deadline = at if at is not None else now
    loss = db.execute("SELECT COUNT(*) FROM flags WHERE state='pending' AND expires<=?",
                      (deadline + margin,)).fetchone()[0]
    earliest = db.execute("SELECT MIN(expires) FROM flags WHERE state='pending'").fetchone()[0]
    return {"states": counts, "unknown_expiry": unknown, "at_risk_by": iso(deadline),
            "at_risk_count": loss, "earliest_expiry": iso(earliest) if earliest else None,
            "safety_margin_seconds": margin, "submission_mode": "hold_until_signal"}


def review(db, limit=100):
    """List uncertain/retry metadata only; never return flag values."""
    if limit < 1 or limit > 500:
        raise ValueError("Review limit must be 1..500")
    rows = db.execute("""
        SELECT f.id, f.state, f.captured, f.expires, f.attempts,
               (SELECT COUNT(*) FROM receipts r WHERE r.flag_id=f.id) AS receipt_count,
               (SELECT MAX(at) FROM receipts r WHERE r.flag_id=f.id) AS latest_receipt_at
        FROM flags f WHERE f.state IN ('uncertain','retry')
        ORDER BY f.expires IS NULL, f.expires, f.id LIMIT ?
    """, (limit,)).fetchall()
    return [{"id": row["id"], "state": row["state"],
             "captured_at": iso(row["captured"]),
             "expires_at": iso(row["expires"]) if row["expires"] is not None else None,
             "attempts": row["attempts"], "receipt_count": row["receipt_count"],
             "latest_receipt_at": iso(row["latest_receipt_at"])
             if row["latest_receipt_at"] is not None else None} for row in rows]


def receipt_history(db, ident, limit=100):
    if not isinstance(ident, str) or len(ident) != 64 or any(c not in "0123456789abcdef" for c in ident):
        raise ValueError("Receipt ID must be a lowercase SHA-256 digest")
    if limit < 1 or limit > 500:
        raise ValueError("Receipt limit must be 1..500")
    rows = db.execute("SELECT at,state,evidence FROM receipts WHERE flag_id=? ORDER BY at DESC,id DESC LIMIT ?",
                      (ident, limit)).fetchall()
    return [{"at": iso(row["at"]), "status": row["state"], "evidence": row["evidence"]}
            for row in rows]


def apply_results(db, rows, payload):
    expected = {row["id"] for row in rows}
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ValueError("Adapter response must include a results list")
    results = {}
    for entry in payload["results"]:
        if (not isinstance(entry, dict) or entry.get("id") not in expected or
                entry["id"] in results or entry.get("status") not in STATES):
            raise ValueError("Invalid adapter receipt")
        results[entry["id"]] = entry["status"]
    with db:
        for ident in expected:
            state = results.get(ident, "uncertain")
            db.execute("UPDATE flags SET state=? WHERE id=?", (state, ident))
            db.execute("INSERT INTO receipts (flag_id,at,state) VALUES (?,?,?)",
                       (ident, time.time(), state))
    return results


def submit(db, adapter, signal, batch_size=25, max_batches=100, delay=1,
           timeout=15, margin=30, at=None):
    if signal != "SUBMIT_NOW":
        raise ValueError("An explicit SUBMIT_NOW signal is required")
    if batch_size < 1 or batch_size > 1000 or max_batches < 1 or max_batches > 10000:
        raise ValueError("Invalid bounded batch limits")
    if delay < 0.1 or timeout <= 0 or margin < 0:
        raise ValueError("Invalid timing limits")
    # Snapshot the pending IDs: producers can keep importing; later arrivals hold.
    cutoff = time.time()
    expire(db, cutoff)
    # Absolute cap keeps a large --batch-size/--max-batches product bounded.
    queue_limit = min(batch_size * max_batches, 50000)
    ids = [r[0] for r in db.execute("SELECT id FROM flags WHERE state='pending' AND expires>? "
                                    "ORDER BY expires,id LIMIT ?", (cutoff + margin, queue_limit))]
    batches = sent = 0
    stopped = None
    for offset in range(0, min(len(ids), batch_size * max_batches), batch_size):
        if batches:
            time.sleep(delay)
        if at is not None and time.time() + timeout + margin >= at:
            stopped = "release_deadline"
            break
        batch_ids = ids[offset:offset + batch_size]
        placeholders = ",".join("?" for _ in batch_ids)
        # Transactionally claim before network send: concurrent submissions cannot
        # resend this batch. Crash/timeout leaves uncertain entries for reconciliation.
        with db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT * FROM flags WHERE state='pending' AND expires>? "
                              "AND id IN (" + placeholders + ") ORDER BY expires,id",
                              (time.time() + timeout + margin, *batch_ids)).fetchall()
            for row in rows:
                db.execute("UPDATE flags SET state='uncertain', attempts=attempts+1 WHERE id=?",
                           (row["id"],))
                db.execute("INSERT INTO receipts (flag_id,at,state) VALUES (?,?, 'uncertain')",
                           (row["id"], time.time()))
        if not rows:
            continue
        batches += 1
        sent += len(rows)
        request = {"flags": [{"id": r["id"], "flag": r["flag"]} for r in rows]}
        try:
            proc = subprocess.run([sys.executable, str(Path(adapter).resolve())],
                                  input=json.dumps(request), text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  timeout=timeout, check=True)
            results = apply_results(db, rows, json.loads(proc.stdout))
        except (OSError, subprocess.SubprocessError, ValueError, TypeError):
            stopped = "adapter_error_or_ambiguous_receipt"
            break
        if len(results) != len(rows) or any(v in {"retry", "uncertain"} for v in results.values()):
            stopped = "retry_or_uncertain_receipt"
            break
    return {"batches": batches, "attempted": sent, "stopped": stopped, **status(db, margin)}


def reconcile(db, stream):
    # Receipts supplied after independently checking the scoring API.
    count = 0
    with db:
        for line in stream:
            if not line.strip():
                continue
            r = json.loads(line)
            if (not isinstance(r, dict) or r.get("status") not in STATES | {"pending"} or
                    not isinstance(r.get("evidence"), str) or not r["evidence"].strip()):
                raise ValueError("Reconciliation needs a valid status and receipt evidence path")
            updated = db.execute("UPDATE flags SET state=? WHERE id=? AND state IN ('uncertain','retry')",
                                 (r["status"], r.get("id")))
            if updated.rowcount != 1:
                raise ValueError("Reconciliation ID must identify an uncertain/retry record")
            db.execute("INSERT INTO receipts (flag_id,at,state,evidence) VALUES (?,?,?,?)",
                       (r["id"], time.time(), r["status"], r["evidence"]))
            count += 1
    return {"reconciled": count}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="flags/ledger.sqlite3")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("ingest", help="Import JSONL on stdin, print counts only")
    commands.add_parser("reconcile", help="Apply reviewed receipts from JSONL stdin")
    review_parser = commands.add_parser("review", help="List uncertain/retry metadata without flag values")
    review_parser.add_argument("--limit", type=int, default=100)
    receipts_parser = commands.add_parser("receipts", help="Show receipt history for a hashed flag ID")
    receipts_parser.add_argument("--id", required=True)
    receipts_parser.add_argument("--limit", type=int, default=100)
    for command in ("status", "plan"):
        p = commands.add_parser(command)
        p.add_argument("--at", help="ISO time of planned submission")
        p.add_argument("--margin", type=float, default=30)
    p = commands.add_parser("submit", help="One explicit release, no scheduler")
    p.add_argument("--signal", required=True, choices=["SUBMIT_NOW"])
    p.add_argument("--adapter", required=True, help="Local Python transport adapter")
    p.add_argument("--batch-size", type=int, default=25)
    p.add_argument("--max-batches", type=int, default=100)
    p.add_argument("--delay", type=float, default=1)
    p.add_argument("--timeout", type=float, default=15)
    p.add_argument("--margin", type=float, default=30)
    p.add_argument("--at", help="Stop before this release deadline (ISO)")
    args = parser.parse_args()
    db = connect(args.db)
    try:
        if args.command == "ingest":
            result = ingest(db, sys.stdin)
        elif args.command == "reconcile":
            result = reconcile(db, sys.stdin)
        elif args.command == "review":
            result = {"items": review(db, args.limit)}
        elif args.command == "receipts":
            result = {"id": args.id, "receipts": receipt_history(db, args.id, args.limit)}
        elif args.command == "submit":
            result = submit(db, args.adapter, args.signal, args.batch_size,
                            args.max_batches, args.delay, args.timeout, args.margin,
                            timestamp(args.at) if args.at else None)
        else:
            if args.margin < 0:
                raise ValueError("Margin must be nonnegative")
            result = status(db, args.margin, timestamp(args.at) if args.at else None)
        print(json.dumps(result, sort_keys=True))
    except (ValueError, TypeError, KeyError, sqlite3.Error, OSError):
        # Input/adapter exception strings can contain flags; never echo them.
        print("flag-ledger: operation failed; check private input/adapter contract", file=sys.stderr)
        return 2
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
