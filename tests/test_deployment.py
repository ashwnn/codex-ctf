"""Deployment recovery tests use only temporary Git repositories and dummy adapters."""
from contextlib import redirect_stdout
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("deployment", ROOT / "scripts/deployment.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, timeout=10)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "service"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.name", "Fixture")
        git(self.repo, "config", "user.email", "fixture@invalid")
        self.commit = self.new_commit("baseline")
        self.runtime = self.root / "runtime.json"
        self.artifact = self.root / "artifact.bin"
        self.artifact.write_bytes(b"dummy-baseline-artifact")
        self.data = self.root / "persistent-records"
        self.data.write_text("before-change\nafter-change\n")
        self.flag = self.root / "adapter-mode"
        self.flag.write_text("ok")
        self.adapter = self.root / "adapter.py"
        self.adapter.write_text('''import hashlib, json, os, pathlib, sys, time
root = pathlib.Path(__file__).parent
mode = (root / 'adapter-mode').read_text()
runtime = root / 'runtime.json'
if sys.argv[1] == 'identity':
    print(runtime.read_text())
elif sys.argv[1] == 'functional':
    print('OUTPUT_MUST_STAY_PRIVATE')
    sys.exit(1 if mode == 'fail-check' else 0)
else:
    notices = list((root / 'service/.git/ctf-deploy/service/test/notices').glob('*.json'))
    assert notices, 'no predeployment notice'
    (root / 'adapter-started').write_text(str(len(notices)))
    if mode == 'timeout': time.sleep(10)
    if mode == 'hold': time.sleep(.8)
    value = json.loads(runtime.read_text())
    value['commit'] = os.environ['CTF_DEPLOY_COMMIT']
    value['artifact_sha256'] = hashlib.sha256(pathlib.Path(os.environ['CTF_DEPLOY_ARTIFACT']).read_bytes()).hexdigest()
    assert pathlib.Path(os.environ['CTF_DEPLOY_SOURCE_ARCHIVE']).is_file()
    runtime.write_text(json.dumps(value))
    sys.exit(1 if mode == 'partial-fail' else 0)
''')
        self.config = {"repository": str(self.repo), "service": "service", "environment": "test",
                       "identity_argv": [sys.executable, str(self.adapter), "identity"],
                       "checks": [{"name": "ordinary-read-write", "kind": "functional",
                                   "argv": [sys.executable, str(self.adapter), "functional"]}],
                       "rollback_argv": [sys.executable, str(self.adapter), "rollback"],
                       "stability": {"samples": 3, "interval_seconds": .002, "min_window_seconds": .004,
                                     "max_age_seconds": 120, "timeout_seconds": 2}}
        self.config_path = self.root / "deployment.json"
        m.write_json(self.config_path, self.config)
        self.identity = {"service": "service", "environment": "test", "commit": self.commit,
                         "artifact_sha256": m.digest(self.artifact),
                         "compatibility": {"schema": "records-v1", "config": "config-v1", "volumes": "preserve-v1"}}
        m.write_json(self.runtime, self.identity)
        self.d = m.Deployment(self.config_path)

    def new_commit(self, content):
        (self.repo / "service.txt").write_text(content)
        git(self.repo, "add", "service.txt")
        git(self.repo, "commit", "-m", content)
        return git(self.repo, "rev-parse", "HEAD")

    def checked(self):
        with self.d.lock():
            return self.d.check(self.identity["commit"], self.artifact, "human")

    def confirmed(self, record):
        with self.d.lock():
            return self.d.confirm(record["id"], False, "up", m.now(), "human", "tick-5", human_attestation=True)

    def stable(self, tag=None):
        record = self.confirmed(self.checked())
        with self.d.lock():
            return self.d.promote(record["id"], "human", tag)

    def candidate(self):
        self.identity["commit"] = self.new_commit("candidate")
        self.artifact.write_bytes(b"dummy-candidate-artifact")
        self.identity["artifact_sha256"] = m.digest(self.artifact)
        m.write_json(self.runtime, self.identity)
        return self.checked()

    def rollback_plan(self):
        checkpoint = self.stable("stable-deploy-005")
        self.candidate()
        with self.d.lock():
            plan = self.d.plan(checkpoint["checkpoint"], "restore verified source", 15, "human")
        return plan

    def run_cli(self, *args):
        return subprocess.run([str(ROOT / "bin/ctf-codex"), "deploy", "--config", str(self.config_path), *args],
                              capture_output=True, text=True, timeout=15)

    def test_exact_annotated_checkpoint_and_private_evidence(self):
        checkpoint = self.stable("stable-deploy-005")
        self.assertEqual(checkpoint["commit"], self.commit)
        self.assertEqual(git(self.repo, "cat-file", "-t", checkpoint["tag_oid"]), "tag")
        self.assertEqual(git(self.repo, "rev-parse", "stable-deploy-005^{commit}"), self.commit)
        raw = git(self.repo, "cat-file", "tag", checkpoint["tag_oid"])
        annotation = json.loads(raw.split("\n\n", 1)[1])
        self.assertEqual(annotation["identity"], self.identity)
        self.assertEqual(annotation["human_confirmation"]["tick_id"], "tick-5")
        self.assertEqual(len(annotation["checks"]["observations"]), 3)
        self.assertNotIn("OUTPUT_MUST_STAY_PRIVATE", raw)
        self.assertNotIn(str(self.root), raw)
        for path in self.d.state.rglob("*.json"):
            self.assertEqual(path.stat().st_mode & 0o077, 0)
        self.assertEqual(self.run_cli("history").returncode, 0)

    def test_startup_only_policy_and_untrusted_config_rejected(self):
        cfg = copy.deepcopy(self.config)
        cfg["checks"][0]["kind"] = "health"
        m.write_json(self.config_path, cfg)
        with self.assertRaisesRegex(m.Error, "functional"):
            m.Deployment(self.config_path)
        m.write_json(self.repo / "deployment.json", self.config)
        with self.assertRaisesRegex(m.Error, "outside"):
            m.Deployment(self.repo / "deployment.json")

    def test_human_up_required_unknown_down_retained_and_not_reused(self):
        record = self.checked()
        with self.d.lock():
            with self.assertRaisesRegex(m.Error, "human"):
                self.d.promote(record["id"], "agent")
            for status in ("unknown", "down"):
                self.d.confirm(record["id"], False, status, m.now(), "human", human_attestation=True)
                with self.assertRaisesRegex(m.Error, "human"):
                    self.d.promote(record["id"], "agent")
            updated = self.d.confirm(record["id"], False, "up", m.now(), "human", human_attestation=True)
            self.assertEqual([c["status"] for c in updated["confirmations"]], ["unknown", "down", "up"])
            self.d.promote(record["id"], "agent")
        new = self.checked()
        with self.d.lock(), self.assertRaisesRegex(m.Error, "human"):
            self.d.promote(new["id"], "agent")

    def test_confirmation_requires_exact_identity_time_and_configured_hold(self):
        self.config["stability"]["human_hold_seconds"] = 10
        m.write_json(self.config_path, self.config)
        self.d = m.Deployment(self.config_path)
        record = self.checked()
        with self.d.lock(), self.assertRaisesRegex(m.Error, "follow checks"):
            self.d.confirm(record["id"], False, "up", m.now(), "human", human_attestation=True)
        self.identity["commit"] = "a" * 40
        m.write_json(self.runtime, self.identity)
        with self.d.lock(), self.assertRaisesRegex(m.Error, "drift"):
            self.d.confirm(record["id"], False, "up", m.now(), "human", human_attestation=True)

    def test_stale_failed_checks_and_dirty_tree_fail_closed(self):
        record = self.confirmed(self.checked())
        record["checks"]["finished_at"] = "2020-01-01T00:00:00+00:00"
        m.write_json(self.d.state / "evidence" / (record["id"] + ".json"), record)
        with self.d.lock(), self.assertRaisesRegex(m.Error, "stale"):
            self.d.promote(record["id"], "human")
        self.flag.write_text("fail-check")
        with self.assertRaises(m.Error):
            self.checked()
        records = self.d.status(True)["evidence"]
        self.assertTrue(any(r["status"] == "local-checks-failed" for r in records))
        self.assertFalse(git(self.repo, "tag", "--list"))
        self.flag.write_text("ok")
        (self.repo / "untracked").write_text("keep")
        with self.assertRaisesRegex(m.Error, "dirty"):
            self.checked()
        self.assertEqual((self.repo / "untracked").read_text(), "keep")

    def test_commit_drift_cannot_tag_new_head_or_finish_checks(self):
        record = self.confirmed(self.checked())
        changed = self.new_commit("human-race")
        with self.d.lock(), self.assertRaisesRegex(m.Error, "commit drift"):
            self.d.promote(record["id"], "human")
        self.assertFalse(git(self.repo, "tag", "--list"))
        self.assertNotEqual(self.commit, changed)
        self.identity["commit"] = changed
        m.write_json(self.runtime, self.identity)
        original = self.d.adapter
        mutated = []
        def racing(argv, *args, **kwargs):
            value = original(argv, *args, **kwargs)
            if argv[-1] == "functional" and not mutated:
                mutated.append(self.new_commit("another-human-race"))
            return value
        with mock.patch.object(self.d, "adapter", side_effect=racing), self.assertRaisesRegex(m.Error, "drift"):
            self.checked()

    def test_policy_runtime_and_artifact_drift_block_promotion(self):
        record = self.confirmed(self.checked())
        artifact = self.d.artifact(self.identity["artifact_sha256"])
        artifact.write_bytes(b"corrupted")
        with self.d.lock(), self.assertRaisesRegex(m.Error, "artifact unavailable"):
            self.d.promote(record["id"], "human")
        artifact.write_bytes(self.artifact.read_bytes())
        record = self.confirmed(self.checked())
        self.identity["compatibility"]["schema"] = "new-schema"
        m.write_json(self.runtime, self.identity)
        with self.d.lock(), self.assertRaisesRegex(m.Error, "drift"):
            self.d.promote(record["id"], "human")
        self.identity["compatibility"]["schema"] = "records-v1"
        m.write_json(self.runtime, self.identity)
        record = self.confirmed(self.checked())
        self.config["stability"]["max_age_seconds"] = 100
        m.write_json(self.config_path, self.config)
        changed = m.Deployment(self.config_path)
        with changed.lock(), self.assertRaisesRegex(m.Error, "changed policy"):
            changed.promote(record["id"], "human")

    def test_lock_and_concurrent_explicit_tag_collision_never_move_tag(self):
        one = self.confirmed(self.checked())
        two = self.confirmed(self.checked())
        with self.d.lock():
            other = m.Deployment(self.config_path)
            with self.assertRaisesRegex(m.Error, "lock held"):
                with other.lock():
                    pass
            self.assertNotEqual(self.run_cli("promote", "--evidence", one["id"], "--operator", "agent").returncode, 0)
        processes = [subprocess.Popen([str(ROOT / "bin/ctf-codex"), "deploy", "--config", str(self.config_path),
                                      "promote", "--evidence", r["id"], "--operator", "human", "--tag", "stable-deploy-005"],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for r in (one, two)]
        results = [(p.communicate(timeout=15), p.returncode) for p in processes]
        self.assertEqual(sorted(r[1] for r in results), [0, 2], results)
        tag_oid = git(self.repo, "rev-parse", "refs/tags/stable-deploy-005")
        loser = one if self.d.ledger()["checkpoints"]["stable-deploy-005"]["evidence_id"] != one["id"] else two
        with self.d.lock(), self.assertRaisesRegex(m.Error, "collision"):
            self.d.promote(loser["id"], "human", "stable-deploy-005")
        self.assertEqual(git(self.repo, "rev-parse", "refs/tags/stable-deploy-005"), tag_oid)

    def test_external_writer_auto_number_collision_retries_create_only(self):
        record = self.confirmed(self.checked())
        original = m.git
        collision = []
        def race(repo, *args, **kwargs):
            if args[:1] == ("update-ref",) and not collision:
                collision.append(True)
                git(self.repo, "tag", "stable-deploy-001", self.commit)
            return original(repo, *args, **kwargs)
        with self.d.lock(), mock.patch.object(m, "git", side_effect=race):
            promoted = self.d.promote(record["id"], "human")
        self.assertEqual(promoted["checkpoint"], "stable-deploy-002")
        self.assertEqual(git(self.repo, "cat-file", "-t", "stable-deploy-001"), "commit")

    def test_dry_run_notice_apply_verify_and_human_confirm_preserve_data_and_head(self):
        plan = self.rollback_plan()
        head = git(self.repo, "rev-parse", "HEAD")
        source = (self.repo / "service.txt").read_text()
        data = self.data.read_text()
        self.assertTrue(plan["dry_run"])
        self.assertFalse((self.root / "adapter-started").exists())
        applied = self.run_cli("rollback-apply", "--plan", plan["id"], "--operator", "human")
        self.assertEqual(applied.returncode, 0, applied.stderr)
        lines = [json.loads(line) for line in applied.stdout.splitlines()]
        self.assertIn("predeployment_notice", lines[0])
        self.assertEqual(lines[1]["status"], "awaiting-local-verification")
        self.assertTrue((self.root / "adapter-started").exists())
        verified = self.run_cli("rollback-verify", "--plan", plan["id"])
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(json.loads(verified.stdout)["status"], "awaiting-operator")
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), head)
        self.assertEqual((self.repo / "service.txt").read_text(), source)
        self.assertEqual(self.data.read_text(), data)
        with self.d.lock():
            final = self.d.confirm(plan["id"], True, "up", m.now(), "human", human_attestation=True)
        self.assertEqual(final["status"], "rolled-back")
        self.assertIsNone(self.d.ledger()["active_plan"])

    def test_partial_failure_and_explicit_recovery_are_truthful_and_audited(self):
        plan = self.rollback_plan()
        self.flag.write_text("partial-fail")
        with self.d.lock(), redirect_stdout(io.StringIO()), self.assertRaises(m.Error):
            self.d.apply(plan["id"], "human")
        self.assertEqual(self.d.status()["rollback"]["status"], "adapter-failed")
        self.assertEqual(m.read_json(self.runtime)["commit"], self.commit)
        with self.assertRaisesRegex(m.Error, "unresolved"):
            self.checked()
        self.flag.write_text("ok")
        with self.d.lock(), redirect_stdout(io.StringIO()):
            recovered = self.d.apply(plan["id"], "human", recover=True)
            self.assertEqual(recovered["phase"], "previous")
            self.d.verify(plan["id"])
            final = self.d.confirm(plan["id"], True, "up", m.now(), "human", human_attestation=True)
        self.assertEqual(final["status"], "recovered")
        self.assertEqual(m.read_json(self.runtime), self.identity)
        self.assertIn("adapter-failed", [t["status"] for t in final["transitions"]])
        self.assertEqual(self.data.read_text(), "before-change\nafter-change\n")

    def test_interrupt_timeout_failed_verification_and_unknown_close(self):
        plan = self.rollback_plan()
        original = self.d.adapter
        def interrupt(argv, *args, **kwargs):
            if argv[-1] == "rollback":
                raise KeyboardInterrupt()
            return original(argv, *args, **kwargs)
        with self.d.lock(), redirect_stdout(io.StringIO()), mock.patch.object(self.d, "adapter", side_effect=interrupt), self.assertRaises(KeyboardInterrupt):
            self.d.apply(plan["id"], "human")
        self.assertEqual(self.d.status()["rollback"]["status"], "interrupted")
        self.flag.write_text("timeout")
        self.d.policy["timeout_seconds"] = .2
        with self.d.lock(), redirect_stdout(io.StringIO()), self.assertRaises(subprocess.TimeoutExpired):
            self.d.apply(plan["id"], "human", recover=True)
        self.assertEqual(self.d.status()["rollback"]["status"], "adapter-timeout")
        self.flag.write_text("ok")
        with self.d.lock(), redirect_stdout(io.StringIO()):
            self.d.apply(plan["id"], "human", recover=True)
        self.flag.write_text("fail-check")
        with self.d.lock(), self.assertRaises(m.Error):
            self.d.verify(plan["id"])
        self.assertEqual(self.d.status()["rollback"]["status"], "local-checks-failed")
        self.flag.write_text("ok")
        with self.d.lock():
            self.d.verify(plan["id"])
            self.d.confirm(plan["id"], True, "unknown", m.now(), "human", human_attestation=True)
            closed = self.d.close(plan["id"], "human")
        self.assertEqual(closed["status"], "closed-external-unconfirmed")
        self.assertIsNone(self.d.ledger()["active_plan"])
        record = self.checked()
        with self.d.lock(), self.assertRaisesRegex(m.Error, "human"):
            self.d.promote(record["id"], "human")

    def test_incompatible_missing_artifact_revocation_and_provenance_block_rollback(self):
        stable = self.stable()
        self.candidate()
        self.identity["compatibility"]["schema"] = "schema-v2"
        m.write_json(self.runtime, self.identity)
        with self.d.lock(), self.assertRaisesRegex(m.Error, "compatibility differs"):
            self.d.plan(stable["checkpoint"], "rollback", 5, "human")
        self.identity["compatibility"]["schema"] = "records-v1"
        m.write_json(self.runtime, self.identity)
        old_artifact = self.d.checkpoint(stable["checkpoint"])["identity"]["artifact_sha256"]
        self.d.artifact(old_artifact).unlink()
        with self.d.lock(), self.assertRaisesRegex(m.Error, "artifact unavailable"):
            self.d.plan(stable["checkpoint"], "rollback", 5, "human")
        (self.d.state / "artifacts" / old_artifact).write_bytes(b"dummy-baseline-artifact")
        with self.d.lock():
            self.d.revoke(stable["checkpoint"], "human")
            with self.assertRaisesRegex(m.Error, "revoked"):
                self.d.plan(stable["checkpoint"], "rollback", 5, "human")
        ledger = self.d.ledger()
        ledger["checkpoints"][stable["checkpoint"]]["status"] = "known-good"
        self.d.save_ledger(ledger)
        git(self.repo, "update-ref", "refs/tags/" + stable["checkpoint"], self.identity["commit"])
        with self.d.lock(), self.assertRaisesRegex(m.Error, "provenance"):
            self.d.plan(stable["checkpoint"], "rollback", 5, "human")
        with self.d.lock():
            revoked = self.d.revoke(stable["checkpoint"], "human")
        self.assertEqual(revoked["status"], "revoked")

    def test_forward_notice_is_only_intent_and_requests_human_observation(self):
        stable = self.stable()
        candidate = self.new_commit("forward-candidate")
        before = self.runtime.read_bytes()
        result = self.run_cli("notice", "--commit", candidate, "--checkpoint", stable["checkpoint"],
                              "--summary", "literal $(not-executed)", "--maintenance-seconds", "10", "--operator", "human")
        self.assertEqual(result.returncode, 0, result.stderr)
        notice = json.loads(result.stdout)
        self.assertEqual(notice["old_commit"], self.commit)
        self.assertEqual(notice["target_commit"], candidate)
        self.assertIn("leaderboard", notice["instruction"])
        self.assertEqual(self.runtime.read_bytes(), before)
        self.assertFalse((self.root / "adapter-started").exists())

    def configure_watch(self):
        remote = self.root / "remote.git"
        subprocess.run(["git", "clone", "--bare", str(self.repo), str(remote)], check=True, capture_output=True)
        self.config["watch"] = {"remote": str(remote), "branch": "main"}
        m.write_json(self.config_path, self.config)
        self.d = m.Deployment(self.config_path)
        return remote

    def poll(self, expected=None):
        with self.d.lock():
            return self.d.poll(expected or git(self.repo, "rev-parse", "HEAD"))

    def test_watch_initial_duplicate_fast_forward_diverged_and_rewritten(self):
        remote = self.configure_watch()
        self.assertEqual(self.poll()["relation"], "initial")
        self.assertEqual(self.poll()["pending_count"], 1)
        self.assertEqual(self.poll()["relation"], "unchanged")
        candidate = self.new_commit("remote-patch")
        git(self.repo, "push", str(remote), "main")
        self.assertEqual(self.poll()["relation"], "fast-forward")
        self.assertEqual(self.poll()["pending_count"], 2)
        tree = git(self.repo, "rev-parse", "HEAD^{tree}")
        divergent = git(self.repo, "commit-tree", tree, "-p", self.commit, "-m", "literal $(touch malicious)")
        git(self.repo, "push", str(remote), divergent + ":refs/heads/other")
        git(remote, "update-ref", "refs/heads/main", divergent)
        self.assertEqual(self.poll()["relation"], "diverged")
        git(remote, "update-ref", "refs/heads/main", self.commit)
        self.assertEqual(self.poll()["relation"], "rewritten")
        self.assertEqual(self.poll()["pending_count"], 3)
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), candidate)
        self.assertFalse(git(self.repo, "tag", "--list"))

    def test_watch_dirty_lock_local_drift_untrusted_hooks_and_interrupted_fetch(self):
        remote = self.configure_watch()
        marker = self.root / "hook-executed"
        for hooks in (self.repo / ".git/hooks", remote / "hooks"):
            hooks.mkdir(exist_ok=True)
            for name in ("reference-transaction", "post-fetch", "pre-auto-gc"):
                hook = hooks / name
                hook.write_text("#!/bin/sh\ntouch '" + str(marker) + "'\n")
                hook.chmod(0o755)
        fsmonitor = self.root / "fsmonitor"
        fsmonitor.write_text("#!/bin/sh\ntouch '" + str(marker) + "'\n")
        fsmonitor.chmod(0o755)
        git(self.repo, "config", "core.fsmonitor", str(fsmonitor))
        self.poll()
        self.assertFalse(marker.exists())
        before = (self.d.state / "watch.json").read_bytes()
        command = m.command
        def interrupted(argv, *args, **kwargs):
            if "fetch" in argv:
                raise KeyboardInterrupt()
            return command(argv, *args, **kwargs)
        with mock.patch.object(m, "command", side_effect=interrupted), self.assertRaises(KeyboardInterrupt):
            self.poll()
        self.assertEqual((self.d.state / "watch.json").read_bytes(), before)
        (self.repo / "dirty").write_text("keep")
        with self.assertRaisesRegex(m.Error, "dirty"):
            self.poll()
        (self.repo / "dirty").unlink()
        original_head = self.commit
        git(self.repo, "config", "--unset", "core.fsmonitor")
        candidate = self.new_commit("local-drift")
        with self.assertRaisesRegex(m.Error, "commit drift"):
            self.poll(original_head)
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), candidate)
        with self.d.lock(), redirect_stdout(io.StringIO()) as output:
            self.assertFalse(m.watch_loop(self.d, candidate, 1, 30))
        self.assertIn("lock held", output.getvalue())

    def test_watch_offline_bounded_backoff_remote_helper_rejection_and_retry(self):
        remote = self.configure_watch()
        expected = self.commit
        remote.rename(self.root / "temporarily-missing")
        delays = []
        with redirect_stdout(io.StringIO()) as output:
            ok = m.watch_loop(self.d, expected, 3, 30, sleeper=delays.append)
        self.assertFalse(ok)
        self.assertEqual(delays, [30, 60])
        self.assertNotIn("external_availability", output.getvalue())
        (self.root / "temporarily-missing").rename(remote)
        with redirect_stdout(io.StringIO()):
            self.assertTrue(m.watch_loop(self.d, expected, 1, 30))
        for remote_url in ("ext::anything", "origin", "https://user:secret@example.invalid/repo", "ssh://example.invalid/repo"):
            self.d.config["watch"]["remote"] = remote_url
            with self.assertRaisesRegex(m.Error, "watch"):
                self.poll()

    def test_help_exposes_documented_commands_without_codex_inference(self):
        result = subprocess.run([str(ROOT / "bin/ctf-codex"), "deploy", "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ("status", "history", "check", "confirm", "promote", "revoke", "notice", "rollback-plan",
                        "rollback-apply", "rollback-verify", "rollback-recover", "close", "watch"):
            self.assertIn(command, result.stdout)
        self.assertEqual(self.run_cli("status").returncode, 0)
        runbook = (ROOT / "docs/deployment-checkpoints.md").read_text()
        examples = set(re.findall(r'bin/ctf-codex deploy --config "\$CFG" ([a-z-]+)', runbook))
        self.assertGreaterEqual(len(examples), 10)
        for command in examples:
            help_result = self.run_cli(command, "--help")
            self.assertEqual(help_result.returncode, 0, command + help_result.stderr)

    def test_notice_and_rollback_invalidate_older_same_revision_confirmation(self):
        stable = self.stable()
        old = self.confirmed(self.checked())
        with self.d.lock():
            self.d.notice(self.commit, stable["checkpoint"], "repeat rollout", 0, "human")
            with self.assertRaisesRegex(m.Error, "invalidated"):
                self.d.promote(old["id"], "human")
            with self.assertRaisesRegex(m.Error, "invalidated"):
                self.d.confirm(old["id"], False, "up", m.now(), "human", human_attestation=True)
        self.candidate()
        candidate = self.confirmed(self.checked())
        with self.d.lock(), redirect_stdout(io.StringIO()):
            plan = self.d.plan(stable["checkpoint"], "restore baseline", 0, "human")
            self.d.apply(plan["id"], "human")
            self.d.apply(plan["id"], "human", recover=True)
            self.d.verify(plan["id"])
            self.d.close(plan["id"], "human")
            with self.assertRaisesRegex(m.Error, "invalidated"):
                self.d.promote(candidate["id"], "human")

    def test_failed_local_evidence_can_record_human_down_but_never_up(self):
        self.flag.write_text("fail-check")
        with self.assertRaises(m.Error):
            self.checked()
        record = self.d.status(True)["evidence"][0]
        with self.d.lock():
            down = self.d.confirm(record["id"], False, "down", m.now(), "human", human_attestation=True)
            self.assertEqual(down["external_status"], "down")
            self.assertEqual(down["status"], "local-checks-failed")
            with self.assertRaisesRegex(m.Error, "failed checks"):
                self.d.confirm(record["id"], False, "up", m.now(), "human", human_attestation=True)

    def test_plan_stale_drift_unknown_identity_and_apply_refused_without_notice(self):
        plan = self.rollback_plan()
        path = self.d.state / "plans" / (plan["id"] + ".json")
        saved = m.read_json(path)
        saved["created_at"] = "2020-01-01T00:00:00Z"
        m.write_json(path, saved)
        with self.d.lock(), self.assertRaisesRegex(m.Error, "stale"):
            self.d.apply(plan["id"], "human")
        self.assertFalse((self.root / "adapter-started").exists())
        saved["created_at"] = m.now()
        m.write_json(path, saved)
        self.runtime.write_text("unknown")
        with self.d.lock(), self.assertRaisesRegex(m.Error, "identity unknown"):
            self.d.apply(plan["id"], "human")
        self.assertFalse((self.root / "adapter-started").exists())
        m.write_json(self.runtime, self.identity)
        self.new_commit("plan-drift")
        with self.d.lock(), self.assertRaisesRegex(m.Error, "commit drift"):
            self.d.apply(plan["id"], "human")
        self.assertFalse((self.root / "adapter-started").exists())

    def test_check_timeout_and_interruption_retain_local_outcome(self):
        original = self.d.adapter
        for exception, state in ((subprocess.TimeoutExpired(["dummy"], .1), "local-checks-timeout"),
                                 (KeyboardInterrupt(), "interrupted")):
            def failing(argv, *args, **kwargs):
                if argv[-1] == "functional":
                    raise exception
                return original(argv, *args, **kwargs)
            with mock.patch.object(self.d, "adapter", side_effect=failing), self.assertRaises(type(exception)):
                self.checked()
            self.assertTrue(any(r["status"] == state for r in self.d.status(True)["evidence"]))

    def test_poll_drift_after_fetch_keeps_previous_journal_and_retries(self):
        remote = self.configure_watch()
        self.poll()
        journal = self.d.state / "watch.json"
        before = journal.read_bytes()
        candidate = self.new_commit("next-remote")
        git(self.repo, "push", str(remote), "main")
        original = self.d.clean
        count = []
        def drift(expected):
            count.append(True)
            if len(count) == 2:
                self.new_commit("local-change-during-fetch")
            return original(expected)
        with mock.patch.object(self.d, "clean", side_effect=drift), self.assertRaisesRegex(m.Error, "commit drift"):
            self.poll(candidate)
        self.assertEqual(journal.read_bytes(), before)
        self.assertEqual(self.poll()["tip"], candidate)

    def test_killed_cli_retains_writer_lock_until_dummy_adapter_exits(self):
        plan = self.rollback_plan()
        self.flag.write_text("hold")
        process = subprocess.Popen([str(ROOT / "bin/ctf-codex"), "deploy", "--config", str(self.config_path),
                                    "rollback-apply", "--plan", plan["id"], "--operator", "human"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: process.kill() if process.poll() is None else None)
        deadline = time.monotonic() + 5
        while not (self.root / "adapter-started").exists() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue((self.root / "adapter-started").exists())
        process.kill()
        process.communicate(timeout=3)
        blocked = self.run_cli("status")
        self.assertEqual(blocked.returncode, 2)
        self.assertIn("lock held", blocked.stderr)
        time.sleep(1)
        self.assertEqual(self.d.status()["rollback"]["status"], "applying")
        self.flag.write_text("ok")
        with self.d.lock():
            self.d.verify(plan["id"])
            self.d.confirm(plan["id"], True, "up", m.now(), "human", human_attestation=True)
        self.assertIsNone(self.d.ledger()["active_plan"])

    def test_shared_git_worktrees_use_the_same_single_writer_lock(self):
        worktree = self.root / "second-worktree"
        git(self.repo, "worktree", "add", "-b", "other-writer", str(worktree), self.commit)
        other_config = copy.deepcopy(self.config)
        other_config["repository"] = str(worktree)
        config_path = self.root / "other-config.json"
        m.write_json(config_path, other_config)
        other = m.Deployment(config_path)
        self.assertEqual(other.state, self.d.state)
        with self.d.lock(), self.assertRaisesRegex(m.Error, "lock held"):
            with other.lock():
                pass

    def test_unknown_candidate_does_not_block_next_notice_with_compatible_rollback(self):
        stable = self.stable()
        candidate = self.candidate()
        with self.d.lock():
            self.d.confirm(candidate["id"], False, "unknown", m.now(), "human", human_attestation=True)
        old = self.identity["commit"]
        new = self.new_commit("next-operator-chosen-candidate")
        with self.d.lock():
            notice = self.d.notice(new, stable["checkpoint"], "next reviewed candidate", 10, "human")
        self.assertEqual(notice["old_commit"], old)
        self.assertEqual(notice["target_commit"], new)
        self.assertEqual(notice["rollback_checkpoint"], stable["checkpoint"])
        self.assertEqual(len(self.d.ledger()["checkpoints"]), 1)

    def test_recover_previous_when_failed_target_is_revoked_or_missing(self):
        plan = self.rollback_plan()
        self.flag.write_text("partial-fail")
        with self.d.lock(), redirect_stdout(io.StringIO()), self.assertRaises(m.Error):
            self.d.apply(plan["id"], "human")
        self.d.artifact(plan["target"]["artifact_sha256"]).unlink()
        with self.d.lock():
            self.d.revoke(plan["checkpoint"], "human")
        self.flag.write_text("ok")
        with self.d.lock(), redirect_stdout(io.StringIO()):
            self.d.apply(plan["id"], "human", recover=True)
            self.d.verify(plan["id"])
            final = self.d.confirm(plan["id"], True, "up", m.now(), "human", human_attestation=True)
        self.assertEqual(final["status"], "recovered")
        self.assertEqual(m.read_json(self.runtime), self.identity)
        self.assertEqual(self.d.ledger()["checkpoints"][plan["checkpoint"]]["status"], "revoked")

    def test_failed_preflight_verification_removes_old_pass_and_confirmation(self):
        plan = self.rollback_plan()
        with self.d.lock(), redirect_stdout(io.StringIO()):
            self.d.apply(plan["id"], "human")
            self.d.verify(plan["id"])
            self.d.confirm(plan["id"], True, "unknown", m.now(), "human", human_attestation=True)
        (self.repo / "dirty").write_text("keep")
        with self.d.lock(), self.assertRaisesRegex(m.Error, "dirty"):
            self.d.verify(plan["id"])
        recorded = self.d.status()["rollback"]
        self.assertNotIn("checks", recorded)
        self.assertNotIn("confirmation", recorded)
        self.assertEqual(recorded["status"], "local-checks-failed")
        self.assertEqual(recorded["external_status"], "unknown")
        (self.repo / "dirty").unlink()
        with self.d.lock():
            with self.assertRaisesRegex(m.Error, "failed checks"):
                self.d.confirm(plan["id"], True, "up", m.now(), "human", human_attestation=True)
            with self.assertRaisesRegex(m.Error, "successful local"):
                self.d.close(plan["id"], "human")
            self.d.verify(plan["id"])
            self.d.close(plan["id"], "human")

    def test_close_requires_fresh_health_and_confirmation_rechecks_artifact(self):
        plan = self.rollback_plan()
        with self.d.lock(), redirect_stdout(io.StringIO()):
            self.d.apply(plan["id"], "human")
            self.d.verify(plan["id"])
        path = self.d.state / "plans" / (plan["id"] + ".json")
        recorded = m.read_json(path)
        recorded["checks"]["finished_at"] = "2020-01-01T00:00:00Z"
        m.write_json(path, recorded)
        with self.d.lock(), self.assertRaisesRegex(m.Error, "stale"):
            self.d.close(plan["id"], "human")
        with self.d.lock():
            self.d.verify(plan["id"])
        artifact = self.d.artifact(plan["target"]["artifact_sha256"])
        before = artifact.read_bytes()
        artifact.unlink()
        with self.d.lock(), self.assertRaisesRegex(m.Error, "artifact unavailable"):
            self.d.confirm(plan["id"], True, "up", m.now(), "human", human_attestation=True)
        self.assertEqual(self.d.status()["rollback"]["status"], "evidence-invalidated")
        artifact.write_bytes(before)
        with self.d.lock():
            self.d.verify(plan["id"])
            self.d.close(plan["id"], "human")

    def test_confirm_requires_explicit_human_attestation_and_records_its_source(self):
        record = self.checked()
        rejected = self.run_cli("confirm", "--evidence", record["id"], "--status", "up",
                                "--observed-at", m.now(), "--operator", "agent")
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("human-observation", rejected.stderr)
        with self.d.lock(), self.assertRaisesRegex(m.Error, "attestation"):
            self.d.confirm(record["id"], False, "up", m.now(), "agent")
        accepted = self.run_cli("confirm", "--evidence", record["id"], "--status", "up",
                                "--observed-at", m.now(), "--operator", "human", "--human-observation")
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        confirmation = json.loads(accepted.stdout)["confirmation"]
        self.assertEqual(confirmation["source"], "human-reported")
        self.assertIs(confirmation["human_attestation"], True)

    def test_observed_runtime_drift_permanently_invalidates_prior_confirmation(self):
        record = self.confirmed(self.checked())
        original = copy.deepcopy(self.identity)
        self.identity["compatibility"]["config"] = "config-changed"
        m.write_json(self.runtime, self.identity)
        with self.d.lock(), self.assertRaisesRegex(m.Error, "drift"):
            self.d.promote(record["id"], "human")
        self.identity = original
        m.write_json(self.runtime, self.identity)
        with self.d.lock(), self.assertRaisesRegex(m.Error, "previous evidence invalidated"):
            self.d.promote(record["id"], "human")
        invalidated = self.d.load_record("evidence", record["id"])
        self.assertNotIn("confirmation", invalidated)
        self.assertEqual(invalidated["external_status"], "unknown")
        self.assertEqual(len(invalidated["confirmations"]), 1)
        self.stable()

    def test_config_and_adapter_changes_during_check_fail_closed(self):
        original = self.d.adapter
        changed = []
        def changing(argv, *args, **kwargs):
            result = original(argv, *args, **kwargs)
            if argv[-1] == "functional" and not changed:
                changed.append(True)
                cfg = copy.deepcopy(self.config)
                cfg["stability"]["max_age_seconds"] = 99
                m.write_json(self.config_path, cfg)
            return result
        with mock.patch.object(self.d, "adapter", side_effect=changing), self.assertRaisesRegex(m.Error, "configuration"):
            self.checked()
        m.write_json(self.config_path, self.config)
        record = self.confirmed(self.checked())
        program = self.adapter.read_text()
        self.adapter.write_text(program + "\n# adapter code changed\n")
        with self.d.lock(), self.assertRaisesRegex(m.Error, "adapter program changed"):
            self.d.promote(record["id"], "human")
        self.adapter.write_text(program)
        with self.d.lock(), self.assertRaisesRegex(m.Error, "invalidated"):
            self.d.promote(record["id"], "human")

    def test_archive_ignores_replace_refs_and_never_follows_output_symlink(self):
        import tarfile
        plan = self.rollback_plan()
        git(self.repo, "replace", self.commit, self.identity["commit"])
        victim = self.root / "must-not-be-clobbered"
        victim.write_text("keep operator files")
        output = self.d.state / "plans" / (plan["id"] + "-target.tar")
        output.symlink_to(victim)
        with self.d.lock():
            archive = self.d.archive(plan, plan["target"])
        self.assertEqual(victim.read_text(), "keep operator files")
        self.assertFalse(archive.is_symlink())
        with tarfile.open(archive) as source:
            self.assertEqual(source.extractfile("service.txt").read(), b"baseline")

    def test_git_environment_cannot_redirect_repository_and_watch_leaves_index_unchanged(self):
        remote = self.configure_watch()
        before = (self.repo / ".git/index").read_bytes()
        (self.repo / "service.txt").touch()
        with mock.patch.dict(os.environ, {"GIT_DIR": str(remote), "GIT_WORK_TREE": str(self.root)}):
            self.assertEqual(self.d.head(), self.commit)
            self.poll()
        self.assertEqual((self.repo / ".git/index").read_bytes(), before)
        self.assertEqual((self.repo / "service.txt").read_text(), "baseline")

    def test_metadata_and_lock_symlinks_are_rejected(self):
        victim = self.root / "victim"
        victim.write_text("keep")
        lock = self.d.state / "writer.lock"
        lock.symlink_to(victim)
        with self.assertRaises(OSError):
            with self.d.lock():
                pass
        self.assertEqual(victim.read_text(), "keep")
        lock.unlink()
        import shutil
        shutil.rmtree(self.d.state / "notices")
        (self.d.state / "notices").symlink_to(self.root)
        with self.assertRaisesRegex(m.Error, "symlink"):
            m.Deployment(self.config_path)

    def test_unknown_identity_is_audited_after_forward_notice(self):
        stable = self.stable()
        with self.d.lock():
            notice = self.d.notice(self.commit, stable["checkpoint"], "repeat known revision", 0, "human")
        self.runtime.write_text("identity unavailable")
        with self.d.lock(), self.assertRaisesRegex(m.Error, "identity unknown"):
            self.d.check(self.commit, self.artifact, "human", notice["id"])
        recorded = self.d.load_record("notices", notice["id"])
        self.assertEqual(recorded["status"], "local-checks-failed")
        self.assertIn("evidence", recorded)
        evidence = self.d.load_record("evidence", recorded["evidence"])
        self.assertEqual(evidence["requested_commit"], self.commit)
        self.assertNotIn("checks", evidence)

    def test_promotion_never_creates_a_checkpoint_it_cannot_read_back(self):
        record = self.confirmed(self.checked())
        with self.d.lock(), mock.patch.object(m, "MAX_METADATA_BYTES", 1000), self.assertRaisesRegex(m.Error, "metadata limit"):
            self.d.promote(record["id"], "human")
        self.assertFalse(git(self.repo, "tag", "--list"))


if __name__ == "__main__":
    unittest.main()
