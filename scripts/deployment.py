#!/usr/bin/env python3
"""Local own-service checkpoints, explicit rollback and remote observations (no agent loop)."""
import argparse
from contextlib import contextmanager
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from urllib.parse import urlsplit

UTC = dt.timezone.utc
NAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.@-]{0,79}\Z")
OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
TAG = re.compile(r"stable-deploy-[0-9]{3,}\Z")
MAX_METADATA_BYTES = 1024 * 1024


class Error(Exception):
    def __init__(self, message, exit_code=None):
        super().__init__(message)
        self.exit_code = exit_code


def now():
    return dt.datetime.now(UTC).isoformat()


def timestamp(value):
    try:
        if isinstance(value, str) and value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = dt.datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
            raise ValueError()
        return parsed.timestamp()
    except (ValueError, TypeError):
        raise Error("timestamp must be an ISO-8601 UTC value with timezone") from None


def token(value):
    if not isinstance(value, str) or not NAME.fullmatch(value) or value.lower() in ("unknown", "unspecified"):
        raise Error("use a non-secret, explicit identifier (letters, digits, . _ @ -)")
    return value


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(encoded(value))
            stream.flush()
            os.fsync(stream.fileno())
            os.replace(temporary, path)
            directory = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        raise Error("required local metadata is missing or invalid") from None


def failure_summary(failure):
    result = {"at": now(), "kind": type(failure).__name__,
              "reason": str(failure) if isinstance(failure, Error) else "timeout, interruption or unavailable local resource"}
    if getattr(failure, "check_name", None):
        result["check"] = failure.check_name
    return result


def command(argv, cwd, timeout, environment=None, capture=False, input_data=None, lock_fd=None):
    """Never evaluate shell text or emit adapter output; stop descendants on timeout/interruption."""
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(argv, cwd=str(cwd), env=environment,
                                   stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
                                   stdout=output if capture else subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=True,
                                   pass_fds=() if lock_fd is None else (lock_fd,))
        try:
            process.communicate(input=input_data, timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            raise
        if process.returncode:
            raise Error("configured command failed (exit %d); output withheld" % process.returncode, process.returncode)
        if not capture:
            return ""
        if output.tell() > MAX_METADATA_BYTES:
            raise Error("command output exceeds metadata bound")
        output.seek(0)
        return output.read().decode("utf-8")


def git(repo, *args, input_data=None):
    # Ref updates must not run repository hooks. No checkouts, filters, credential
    # helpers or remote configuration are used by these local plumbing commands.
    try:
        environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        environment.update(GIT_NO_REPLACE_OBJECTS="1", GIT_OPTIONAL_LOCKS="0")
        return command(["git", "--no-replace-objects", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "-c", "gc.auto=0",
                        "-C", str(repo), *args], repo, 30, environment, capture=True, input_data=input_data).strip()
    except (subprocess.TimeoutExpired, UnicodeError, OSError):
        raise Error("local Git command unavailable, invalid or timed out") from None


class Deployment:
    def __init__(self, config_path):
        self.config_path = Path(config_path).resolve()
        self.config = read_json(self.config_path)
        cfg = self.config
        self.repo = Path(cfg["repository"]).resolve()
        if Path(git(self.repo, "rev-parse", "--show-toplevel")).resolve() != self.repo:
            raise Error("configured repository must be the exact Git working-tree root")
        try:
            self.config_path.relative_to(self.repo)
        except ValueError:
            pass
        else:
            raise Error("trusted deployment config must be outside the service working tree")
        self.service, self.environment = token(cfg["service"]), token(cfg["environment"])
        self.policy = cfg["stability"]
        for key, low, high in (("samples", 3, 100), ("interval_seconds", .001, 60),
                               ("min_window_seconds", .001, 3600), ("max_age_seconds", 1, 3600),
                               ("timeout_seconds", .01, 60)):
            value = self.policy[key]
            if type(value) not in (int, float) or not low <= value <= high:
                raise Error("invalid bounded stability policy: " + key)
        if type(self.policy["samples"]) is not int:
            raise Error("stability samples must be an integer")
        hold = self.policy.get("human_hold_seconds", 0)
        if type(hold) not in (int, float) or not 0 <= hold <= 3600:
            raise Error("invalid human observation hold period")
        if (self.policy["samples"] - 1) * self.policy["interval_seconds"] < self.policy["min_window_seconds"]:
            raise Error("configured samples cannot cover the stability window")
        if self.policy["samples"] * (2 + len(cfg["checks"])) * self.policy["timeout_seconds"] + \
                (self.policy["samples"] - 1) * self.policy["interval_seconds"] > 3600:
            raise Error("check session exceeds one-hour bound")
        if not 1 <= len(cfg["checks"]) <= 64 or not any(c.get("kind") == "functional" for c in cfg["checks"]):
            raise Error("at least one configured functional check is required; startup/HTTP 200 is insufficient")
        names = set()
        for check in cfg["checks"]:
            name = token(check["name"])
            if name in names or check["kind"] not in ("functional", "health"):
                raise Error("check names must be unique and kinds functional or health")
            names.add(name)
            self.validate_argv(check["argv"])
        self.validate_argv(cfg["identity_argv"])
        if "rollback_argv" in cfg:
            self.validate_argv(cfg["rollback_argv"])
        self._program_cache = {}
        self.policy_digest = self.fingerprint(cfg)
        common = Path(git(self.repo, "rev-parse", "--git-common-dir"))
        if not common.is_absolute():
            common = self.repo / common
        self.state = common.resolve()
        for directory in ("ctf-deploy", self.service, self.environment):
            self.state = self.state / directory
            self.private_directory(self.state)
        for directory in ("evidence", "plans", "artifacts", "notices"):
            self.private_directory(self.state / directory)

    @staticmethod
    def private_directory(path):
        if path.is_symlink():
            raise Error("deployment metadata directory is a symlink; refusing writes")
        path.mkdir(exist_ok=True, mode=0o700)
        os.chmod(path, 0o700)

    def fingerprint(self, cfg):
        """Bind configuration and local adapter programs without storing their contents."""
        argv_lists = [cfg["identity_argv"], *[check["argv"] for check in cfg["checks"]]]
        if "rollback_argv" in cfg:
            argv_lists.append(cfg["rollback_argv"])
        paths = set()
        for argv in argv_lists:
            self.validate_argv(argv)
            paths.add(Path(argv[0]).resolve())
            if len(argv) > 1 and re.fullmatch(r"(?:python[0-9.]*|bash|sh|dash|perl|ruby|node)", Path(argv[0]).name) and not argv[1].startswith("-"):
                script = Path(argv[1])
                paths.add((script if script.is_absolute() else self.config_path.parent / script).resolve())
        dependencies = cfg.get("adapter_files", [])
        if not isinstance(dependencies, list) or len(dependencies) > 64:
            raise Error("adapter_files must be a bounded list of absolute dependency paths")
        for dependency in dependencies:
            if not isinstance(dependency, str) or not Path(dependency).is_absolute():
                raise Error("adapter_files require absolute dependency paths")
            paths.add(Path(dependency).resolve())
        programs = {}
        for path in sorted(paths):
            stat = path.stat()
            version = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
            cached = self._program_cache.get(path)
            if cached is None or cached[0] != version:
                cached = (version, digest(path))
                self._program_cache[path] = cached
            programs[str(path)] = cached[1]
        return hashlib.sha256(encoded({"config": cfg, "programs": programs})).hexdigest()

    def configuration_current(self):
        if self.fingerprint(read_json(self.config_path)) != self.policy_digest:
            raise Error("deployment configuration or adapter program changed; run fresh checks with the reviewed configuration")

    @staticmethod
    def validate_argv(argv):
        if not isinstance(argv, list) or not 1 <= len(argv) <= 64 or \
                any(not isinstance(x, str) or "\0" in x or len(x) > 4096 for x in argv) or \
                not Path(argv[0]).is_absolute():
            raise Error("configured commands require bounded argv with an absolute executable")

    @contextmanager
    def lock(self):
        descriptor = os.open(str(self.state / "writer.lock"), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Error("deployment writer lock held; pause and retry") from None
            self._writer_fd = lock.fileno()
            try:
                yield
            finally:
                self._writer_fd = None
                fcntl.flock(lock, fcntl.LOCK_UN)

    def ledger(self):
        path = self.state / "ledger.json"
        if not path.exists():
            write_json(path, {"repository_id": uuid.uuid4().hex, "checkpoints": {}, "active_plan": None, "generation": 0})
        return read_json(path)

    def save_ledger(self, value):
        write_json(self.state / "ledger.json", value)

    def object(self, oid):
        if not isinstance(oid, str) or not OID.fullmatch(oid) or \
                git(self.repo, "rev-parse", "--verify", oid + "^{commit}") != oid:
            raise Error("an available exact full commit ID is required")
        return oid

    def head(self):
        return git(self.repo, "rev-parse", "--verify", "HEAD")

    def clean(self, expected=None):
        self.configuration_current()
        if git(self.repo, "status", "--porcelain", "--untracked-files=normal", "--ignore-submodules=none"):
            raise Error("dirty working tree; pause without changing user files")
        head = self.head()
        if expected is not None and head != expected:
            raise Error("local commit drift; expected HEAD changed")
        return head

    def adapter(self, argv, identity=None, source=None, capture=False):
        self.configuration_current()
        env = dict(os.environ)
        env.update(CTF_DEPLOY_SERVICE=self.service, CTF_DEPLOY_ENVIRONMENT=self.environment)
        if identity is not None:
            env.update(CTF_DEPLOY_COMMIT=identity["commit"],
                       CTF_DEPLOY_ARTIFACT=str(self.artifact(identity["artifact_sha256"])),
                       CTF_DEPLOY_SOURCE_ARCHIVE=str(source or ""))
        return command(argv, self.config_path.parent, self.policy["timeout_seconds"], env, capture,
                       lock_fd=getattr(self, "_writer_fd", None))

    def identity(self):
        try:
            value = json.loads(self.adapter(self.config["identity_argv"], capture=True))
        except (ValueError, UnicodeError):
            raise Error("runtime identity unknown: adapter must return exact JSON") from None
        required = {"service", "environment", "commit", "artifact_sha256", "compatibility"}
        if not isinstance(value, dict) or set(value) != required or \
                value["service"] != self.service or value["environment"] != self.environment or \
                not isinstance(value["commit"], str) or not OID.fullmatch(value["commit"]) or \
                not isinstance(value["artifact_sha256"], str) or not SHA.fullmatch(value["artifact_sha256"]):
            raise Error("runtime identity unknown or service/environment mismatch")
        compatibility = value["compatibility"]
        if not isinstance(compatibility, dict) or set(compatibility) != {"schema", "config", "volumes"}:
            raise Error("schema/config/volume compatibility unspecified; rollback blocked")
        for value_id in compatibility.values():
            token(value_id)
        return value

    def match(self, expected):
        if self.identity() != expected:
            raise Error("runtime identity drift or artifact/compatibility mismatch")

    def artifact(self, sha):
        if not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise Error("invalid artifact digest")
        path = self.state / "artifacts" / sha
        if not path.is_file() or path.is_symlink() or digest(path) != sha:
            raise Error("required artifact unavailable or digest mismatch; restore verified bytes")
        return path

    def store_artifact(self, path):
        path = Path(path)
        if not path.is_file() or path.is_symlink():
            raise Error("artifact must be a regular local file")
        sha = digest(path)
        destination = self.state / "artifacts" / sha
        if destination.exists():
            self.artifact(sha)
            return sha
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
            temporary = Path(stream.name)
            try:
                with path.open("rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        stream.write(chunk)
                stream.flush()
                os.fsync(stream.fileno())
                if digest(temporary) != sha:
                    raise Error("artifact changed while being saved")
                # Link is an atomic create-only install; a concurrent writer cannot replace it.
                os.link(temporary, destination)
                descriptor = os.open(str(destination.parent), os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            finally:
                temporary.unlink(missing_ok=True)
        return sha

    def collect(self, expected, head):
        started, start_clock = now(), time.monotonic()
        observations = []
        for index in range(self.policy["samples"]):
            self.clean(head)
            self.match(expected)
            for check in self.config["checks"]:
                try:
                    self.adapter(check["argv"])
                except BaseException as failure:
                    failure.check_name = check["name"]
                    raise
            self.match(expected)
            observations.append({"at": now(), "passed_checks": [c["name"] for c in self.config["checks"]]})
            if index + 1 < self.policy["samples"]:
                time.sleep(self.policy["interval_seconds"])
        elapsed = time.monotonic() - start_clock
        if elapsed < self.policy["min_window_seconds"]:
            raise Error("bounded stability window insufficient")
        self.clean(head)
        return {"started_at": started, "finished_at": now(), "window_seconds": elapsed,
                "observations": observations, "policy_digest": self.policy_digest, "passed": True}

    def fresh(self, evidence):
        if evidence.get("policy_digest") != self.policy_digest or evidence.get("passed") is not True:
            raise Error("failed checks or changed policy; run fresh checks")
        age = time.time() - timestamp(evidence["finished_at"])
        if age < -2 or age > self.policy["max_age_seconds"]:
            raise Error("stale checks; run fresh checks")
        if len(evidence["observations"]) < self.policy["samples"] or \
                evidence["window_seconds"] < self.policy["min_window_seconds"]:
            raise Error("insufficient check evidence")

    def no_active(self):
        if self.ledger()["active_plan"]:
            raise Error("unresolved rollback; verify or recover it before promotion/new actions")

    def check(self, commit, artifact, operator, notice_id=None):
        self.no_active()
        commit = self.object(commit)
        head = self.clean(commit)
        record = {"id": uuid.uuid4().hex, "operator": token(operator), "requested_commit": commit,
                  "head": head, "generation": self.ledger()["generation"], "status": "checking", "created_at": now()}
        notice = self.load_record("notices", notice_id) if notice_id else None
        if notice and (notice["target_commit"] != commit or notice["generation"] != record["generation"] or
                       notice["policy_digest"] != self.policy_digest):
            raise Error("deployment notice revision mismatch")
        self.save_record("evidence", record)
        try:
            expected = self.identity()
            sha = self.store_artifact(artifact)
            if expected["commit"] != commit or expected["artifact_sha256"] != sha:
                raise Error("runtime does not match the explicit commit and artifact")
            record["identity"] = expected
            record["checks"] = self.collect(expected, head)
            record["status"] = "awaiting-operator"
        except BaseException as failure:
            record["status"] = "interrupted" if isinstance(failure, KeyboardInterrupt) else \
                ("local-checks-timeout" if isinstance(failure, subprocess.TimeoutExpired) else "local-checks-failed")
            record["finished_at"] = now()
            record["failure"] = failure_summary(failure)
            self.save_record("evidence", record)
            if notice:
                notice.update(status=record["status"], evidence=record["id"])
                write_json(self.state / "notices" / (notice_id + ".json"), notice)
            raise
        self.save_record("evidence", record)
        if notice:
            notice.update(status=record["status"], evidence=record["id"])
            write_json(self.state / "notices" / (notice_id + ".json"), notice)
        return record

    def load_record(self, directory, identifier):
        if not isinstance(identifier, str) or not re.fullmatch(r"[0-9a-f]{32}", identifier):
            raise Error("use the explicit local record ID")
        return read_json(self.state / directory / (identifier + ".json"))

    def save_record(self, directory, record):
        record.setdefault("transitions", []).append({"at": now(), "status": record["status"],
                                                      "phase": record.get("phase")})
        write_json(self.state / directory / (record["id"] + ".json"), record)

    def invalidate(self, directory, record):
        record.update(status="evidence-invalidated", invalidated_at=now(), external_status="unknown")
        record.pop("confirmation", None)
        if directory == "plans":
            record.pop("checks", None)
        self.save_record(directory, record)

    def ready(self, directory, record):
        try:
            if record.get("invalidated_at"):
                raise Error("previous evidence invalidated; run fresh checks")
            if record["generation"] != self.ledger()["generation"]:
                raise Error("another deployment action invalidated this evidence; run fresh checks")
            self.configuration_current()
            self.fresh(record.get("checks", {}))
            if directory == "plans":
                self.validate_plan(record)
            else:
                self.clean(record["head"])
            expected = record[record["phase"]] if directory == "plans" else record["identity"]
            self.artifact(expected["artifact_sha256"])
            self.match(expected)
        except BaseException as failure:
            record["failure"] = failure_summary(failure)
            self.invalidate(directory, record)
            raise

    def confirm(self, identifier, is_plan, status, observed_at, operator, tick_id=None, human_attestation=False):
        if human_attestation is not True:
            raise Error("explicit human-observation attestation required; this command cannot verify leaderboard access")
        directory = "plans" if is_plan else "evidence"
        record = self.load_record(directory, identifier)
        if record["generation"] != self.ledger()["generation"]:
            raise Error("another deployment action invalidated this evidence; run fresh checks")
        checks = record.get("checks", {})
        if status == "up":
            self.ready(directory, record)
        expected = record[record["phase"]] if is_plan else record["identity"]
        if status != "up":
            self.clean(record["head"])
            self.match(expected)
        at = timestamp(observed_at)
        minimum = timestamp(checks["finished_at"]) if status == "up" else timestamp(record["created_at"])
        if status == "up":
            minimum = max(minimum, timestamp(checks["started_at"]) + self.policy.get("human_hold_seconds", 0))
        if at < minimum or not -2 <= time.time() - at <= self.policy["max_age_seconds"]:
            raise Error("human observation must be fresh and follow checks for this exact deployment")
        confirmation = {"status": status, "observed_at": observed_at, "recorded_at": now(),
                        "source": "human-reported", "human_attestation": True,
                        "operator": token(operator), "commit": expected["commit"],
                        "artifact_sha256": expected["artifact_sha256"]}
        if tick_id is not None:
            confirmation["tick_id"] = token(tick_id)
        record.setdefault("confirmations", []).append(confirmation)
        record["confirmation"] = confirmation
        record["external_status"] = status
        if checks.get("passed") is True:
            record["status"] = "operator-confirmed-" + status
        if is_plan:
            ledger = self.ledger()
            if ledger["active_plan"] != identifier:
                raise Error("confirmation requires the active rollback plan")
            if status == "up":
                record["status"] = "rolled-back" if record["phase"] == "target" else "recovered"
                ledger["active_plan"] = None
        self.save_record(directory, record)
        if is_plan and status == "up":
            self.save_ledger(ledger)
        return record

    def close(self, identifier, operator):
        """An operator can proceed during a hidden scoreboard without declaring stability."""
        plan = self.load_record("plans", identifier)
        ledger = self.ledger()
        if ledger["active_plan"] != identifier or plan.get("checks", {}).get("passed") is not True:
            raise Error("close requires successful local verification of the active rollback")
        self.ready("plans", plan)
        plan.update(status="closed-external-unconfirmed", closed_by=token(operator), closed_at=now())
        self.save_record("plans", plan)
        ledger["active_plan"] = None
        self.save_ledger(ledger)
        return plan

    def promote(self, identifier, operator, requested_tag=None):
        self.no_active()
        record = self.load_record("evidence", identifier)
        self.ready("evidence", record)
        confirmation = record.get("confirmation", {})
        if confirmation.get("status") != "up" or confirmation.get("commit") != record["identity"]["commit"] or \
                confirmation.get("artifact_sha256") != record["identity"]["artifact_sha256"] or \
                confirmation.get("human_attestation") is not True or confirmation.get("source") != "human-reported" or \
                not -2 <= time.time() - timestamp(confirmation["observed_at"]) <= self.policy["max_age_seconds"]:
            raise Error("fresh explicit human leaderboard up confirmation required for this exact deployment")
        self.artifact(record["identity"]["artifact_sha256"])
        ledger = self.ledger()
        if any(c["evidence_id"] == identifier for c in ledger["checkpoints"].values()):
            raise Error("evidence already promoted; run new checks for a new checkpoint")
        tags = git(self.repo, "tag", "--list", "stable-deploy-*").splitlines()
        number = max([int(t.rsplit("-", 1)[1]) for t in tags if TAG.fullmatch(t)] or [0]) + 1
        if requested_tag and not TAG.fullmatch(requested_tag):
            raise Error("checkpoint names must be stable-deploy-NNN")
        metadata = {"format": "ctf-deploy-v1", "state_at_creation": "known-good", "repository_id": ledger["repository_id"],
                    "checkpoint_id": uuid.uuid4().hex, "created_at": now(), "operator": token(operator),
                    "identity": record["identity"], "evidence_id": identifier, "checks": record["checks"],
                    "human_confirmation": confirmation}
        for attempt in range(100):
            tag = requested_tag or "stable-deploy-%03d" % (number + attempt)
            annotation = ("object %s\ntype commit\ntag %s\ntagger ctf-deploy <local@invalid> %d +0000\n\n" %
                          (record["identity"]["commit"], tag, int(time.time()))).encode() + encoded(metadata)
            if len(annotation) > MAX_METADATA_BYTES:
                raise Error("checkpoint evidence exceeds the bounded metadata limit; reduce the check policy")
            oid = git(self.repo, "mktag", input_data=annotation)
            try:
                git(self.repo, "update-ref", "refs/tags/" + tag, oid, "0" * len(oid))
            except Error:
                if requested_tag or not git(self.repo, "tag", "--list", tag):
                    raise Error("immutable checkpoint collision/ref failure; no reference was force-moved") from None
                continue
            ledger["checkpoints"][tag] = {"tag_oid": oid, "status": "known-good", "evidence_id": identifier,
                                         "commit": record["identity"]["commit"], "created_at": metadata["created_at"]}
            self.save_ledger(ledger)
            return {"checkpoint": tag, "tag_oid": oid, "status": "known-good", "commit": record["identity"]["commit"]}
        raise Error("checkpoint collision retry bound exceeded")

    def checkpoint(self, tag):
        if not isinstance(tag, str) or not TAG.fullmatch(tag):
            raise Error("select an explicit stable-deploy-NNN checkpoint")
        ledger = self.ledger()
        registered = ledger["checkpoints"].get(tag)
        if not registered or registered["status"] != "known-good":
            raise Error("checkpoint not locally known-good (unknown or revoked)")
        oid = git(self.repo, "rev-parse", "--verify", "refs/tags/" + tag)
        if oid != registered["tag_oid"] or git(self.repo, "cat-file", "-t", oid) != "tag":
            raise Error("checkpoint provenance changed; refusing rollback")
        raw = git(self.repo, "cat-file", "tag", oid)
        metadata = json.loads(raw.split("\n\n", 1)[1])
        if metadata["format"] != "ctf-deploy-v1" or metadata["repository_id"] != ledger["repository_id"] or \
                metadata["identity"]["service"] != self.service or metadata["identity"]["environment"] != self.environment or \
                git(self.repo, "rev-parse", "refs/tags/" + tag + "^{commit}") != metadata["identity"]["commit"]:
            raise Error("checkpoint provenance mismatch")
        self.object(metadata["identity"]["commit"])
        self.artifact(metadata["identity"]["artifact_sha256"])
        return metadata

    def revoke(self, tag, operator):
        ledger = self.ledger()
        if not isinstance(tag, str) or not TAG.fullmatch(tag) or tag not in ledger["checkpoints"]:
            raise Error("revocation requires an explicitly registered checkpoint")
        # Quarantine must remain possible when the artifact or ref itself is damaged.
        ledger["checkpoints"][tag].update(status="revoked", revoked_at=now(), revoked_by=token(operator))
        self.save_ledger(ledger)
        return {"checkpoint": tag, "status": "revoked"}

    def notice(self, commit, checkpoint, summary, maintenance_seconds, operator):
        self.no_active()
        self.clean(commit)
        self.object(commit)
        saved = self.checkpoint(checkpoint)["identity"]
        current = self.identity()
        self.object(current["commit"])
        self.artifact(current["artifact_sha256"])
        if current["compatibility"] != saved["compatibility"]:
            raise Error("known-good rollback checkpoint is incompatible with current schema/config/volumes")
        notice = {"id": uuid.uuid4().hex, "status": "announced-awaiting-deployment", "created_at": now(),
                  "generation": self.ledger()["generation"] + 1, "policy_digest": self.policy_digest,
                  "operator": token(operator), "service": self.service, "environment": self.environment,
                  "old_commit": current["commit"], "target_commit": commit, "summary": summary,
                  "maintenance_seconds": maintenance_seconds, "rollback_checkpoint": checkpoint,
                  "check_plan": [c["name"] for c in self.config["checks"]],
                  "instruction": "Watch the external leaderboard; local checks cannot determine external availability."}
        write_json(self.state / "notices" / (notice["id"] + ".json"), notice)
        ledger = self.ledger()
        ledger["generation"] += 1
        self.save_ledger(ledger)
        return notice

    def plan(self, checkpoint, summary, maintenance_seconds, operator):
        self.no_active()
        head = self.clean()
        metadata = self.checkpoint(checkpoint)
        current = self.identity()
        self.object(current["commit"])
        self.artifact(current["artifact_sha256"])
        target = metadata["identity"]
        if current["compatibility"] != target["compatibility"]:
            raise Error("schema/config/volume compatibility differs; use an explicit compatible recovery procedure")
        if "rollback_argv" not in self.config:
            raise Error("rollback adapter unspecified; configure a service-specific data-preserving procedure")
        plan = {"id": uuid.uuid4().hex, "status": "planned", "phase": "target", "created_at": now(),
                "generation": self.ledger()["generation"],
                "head": head, "operator": token(operator), "checkpoint": checkpoint,
                "tag_oid": self.ledger()["checkpoints"][checkpoint]["tag_oid"],
                "target": target, "previous": current, "policy_digest": self.policy_digest,
                "summary": summary, "maintenance_seconds": maintenance_seconds}
        self.save_record("plans", plan)
        return {**plan, "dry_run": True, "artifact": str(self.artifact(target["artifact_sha256"])),
                "source": "Git archive at explicit target commit; no checkout/reset or data restore",
                "check_plan": [c["name"] for c in self.config["checks"]]}

    def validate_plan(self, plan, recovery=False):
        self.clean(plan["head"])
        if plan["generation"] != self.ledger()["generation"]:
            raise Error("another deployment action invalidated this plan")
        if plan["policy_digest"] != self.policy_digest:
            raise Error("deployment configuration changed; plan invalid")
        restoring_previous = recovery or plan["phase"] == "previous"
        if not restoring_previous:
            self.checkpoint(plan["checkpoint"])
            if self.ledger()["checkpoints"][plan["checkpoint"]]["tag_oid"] != plan["tag_oid"]:
                raise Error("planned checkpoint reference changed")
        for key in (("previous",) if restoring_previous else ("target", "previous")):
            self.object(plan[key]["commit"])
            self.artifact(plan[key]["artifact_sha256"])

    def archive(self, plan, expected):
        path = self.state / "plans" / (plan["id"] + "-" + plan["phase"] + ".tar")
        # Archive only: untrusted source and attributes are never extracted or executed.
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
        try:
            git(self.repo, "archive", "--format=tar", "--output=" + str(temporary), expected["commit"])
            with temporary.open("rb") as stream:
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return path

    def transition_notice(self, plan, action):
        expected = plan[plan["phase"]]
        event = {"id": uuid.uuid4().hex, "action": action, "at": now(), "plan": plan["id"],
                 "service": self.service, "environment": self.environment,
                 "old_commit": self.identity()["commit"], "target_commit": expected["commit"],
                 "summary": plan["summary"], "maintenance_seconds": plan["maintenance_seconds"],
                 "rollback_checkpoint": plan["checkpoint"],
                 "check_plan": [c["name"] for c in self.config["checks"]],
                 "instruction": "Watch the external leaderboard. Maintenance window is a plan, not proof of expected downtime."}
        write_json(self.state / "notices" / (event["id"] + ".json"), event)
        print(json.dumps({"predeployment_notice": event}), flush=True)

    def apply(self, identifier, operator, recover=False):
        plan = self.load_record("plans", identifier)
        self.validate_plan(plan, recovery=recover)
        ledger = self.ledger()
        if recover:
            if ledger["active_plan"] != identifier:
                raise Error("recovery requires the unresolved active rollback plan")
            plan["phase"] = "previous"
            current = self.identity()
            if current["compatibility"] != plan["previous"]["compatibility"]:
                raise Error("live compatibility changed; recovery blocked")
        else:
            self.no_active()
            if plan["status"] != "planned" or not -2 <= time.time() - timestamp(plan["created_at"]) <= self.policy["max_age_seconds"]:
                raise Error("plan already used or stale; create a fresh dry-run plan")
            self.match(plan["previous"])
        expected = plan[plan["phase"]]
        source = self.archive(plan, expected)
        self.transition_notice(plan, "recovery" if recover else "rollback")
        plan.update(status="applying", action_operator=token(operator), action_started_at=now())
        ledger["generation"] += 1
        plan["generation"] = ledger["generation"]
        plan.pop("checks", None)
        plan.pop("confirmation", None)
        plan.pop("invalidated_at", None)
        plan.pop("failure", None)
        plan["external_status"] = "unknown"
        self.save_record("plans", plan)
        ledger["active_plan"] = identifier
        self.save_ledger(ledger)
        try:
            self.adapter(self.config["rollback_argv"], expected, source)
            plan["status"] = "awaiting-local-verification"
        except BaseException as failure:
            plan["status"] = "interrupted" if isinstance(failure, KeyboardInterrupt) else \
                ("adapter-timeout" if isinstance(failure, subprocess.TimeoutExpired) else "adapter-failed")
            plan["action_finished_at"] = now()
            plan["failure"] = failure_summary(failure)
            self.save_record("plans", plan)
            raise
        plan["action_finished_at"] = now()
        self.save_record("plans", plan)
        return plan

    def verify(self, identifier):
        plan = self.load_record("plans", identifier)
        if self.ledger()["active_plan"] != identifier:
            raise Error("verification requires the unresolved active rollback plan")
        plan.pop("checks", None)
        plan.pop("confirmation", None)
        plan.pop("invalidated_at", None)
        plan.pop("failure", None)
        plan["external_status"] = "unknown"
        plan["status"] = "verifying"
        self.save_record("plans", plan)
        try:
            self.validate_plan(plan)
            plan["checks"] = self.collect(plan[plan["phase"]], plan["head"])
            plan["status"] = "awaiting-operator"
        except BaseException as failure:
            plan.pop("checks", None)
            plan.pop("confirmation", None)
            plan["status"] = "interrupted" if isinstance(failure, KeyboardInterrupt) else \
                ("local-checks-timeout" if isinstance(failure, subprocess.TimeoutExpired) else "local-checks-failed")
            plan["failure"] = failure_summary(failure)
            self.save_record("plans", plan)
            raise
        self.save_record("plans", plan)
        return plan

    def status(self, history=False):
        ledger = self.ledger()
        result = {"service": self.service, "environment": self.environment, "head": self.head(),
                  "dirty": bool(git(self.repo, "status", "--porcelain", "--untracked-files=normal", "--ignore-submodules=none")),
                  "checkpoints": ledger["checkpoints"], "active_plan": ledger["active_plan"],
                  "generation": ledger["generation"],
                  "external_availability": "requires fresh human observation; never inferred"}
        if ledger["active_plan"]:
            result["rollback"] = self.load_record("plans", ledger["active_plan"])
        if history:
            for directory in ("evidence", "plans", "notices"):
                result[directory] = [read_json(p) for p in sorted((self.state / directory).glob("*.json"))]
            if (self.state / "watch.json").exists():
                result["remote_observations"] = read_json(self.state / "watch.json")
        return result

    def poll(self, expected_head):
        self.clean(expected_head)
        self.no_active()
        watch = self.config.get("watch", {})
        remote, branch = watch.get("remote", ""), watch.get("branch", "")
        # Never resolve a named remote or run repository-defined transport helpers.
        if not isinstance(remote, str) or not isinstance(branch, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,199}", branch):
            raise Error("watch requires an explicit remote URL/absolute local path and branch")
        git(self.repo, "check-ref-format", "refs/heads/" + branch)
        url = urlsplit(remote)
        if url.scheme == "https":
            if not url.hostname or url.username or url.password or url.query or url.fragment:
                raise Error("watch URL must not contain credentials, query or fragment")
        elif not remote.startswith("/") or url.scheme or "\n" in remote:
            raise Error("watch accepts only credential-free HTTPS or an absolute local repository path")
        cache = self.state / "watch.git"
        if not cache.exists():
            git(self.state, "init", "--bare", str(cache))
        path = self.state / "watch.json"
        observations = read_json(path) if path.exists() else {"remote_digest": hashlib.sha256(remote.encode()).hexdigest(),
                                                            "branch": branch, "tip": None, "pending": {}}
        if observations["remote_digest"] != hashlib.sha256(remote.encode()).hexdigest() or observations["branch"] != branch:
            raise Error("watch remote/branch changed; preserve journal and configure a separate service/environment")
        # A private bare cache ignores user/system Git config and all hooks/helpers.
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(self.state),
               "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_TERMINAL_PROMPT": "0"}
        args = ["git", "-c", "core.hooksPath=/dev/null", "-c", "gc.auto=0", "-c", "credential.helper=",
                "-c", "uploadpack.packObjectsHook=",
                "-c", "protocol.allow=never", "-c", "protocol.https.allow=always", "-c", "protocol.file.allow=always",
                "-C", str(cache), "fetch", "--no-tags", "--no-recurse-submodules", "--no-auto-gc", remote,
                "refs/heads/" + branch]
        command(args, self.state, self.policy["timeout_seconds"], env, lock_fd=getattr(self, "_writer_fd", None))
        self.clean(expected_head)
        tip = git(cache, "rev-parse", "--verify", "FETCH_HEAD^{commit}")
        old = observations["tip"]
        relation, commits = "initial", [tip]
        if old == tip:
            relation, commits = "unchanged", []
        elif old:
            def ancestor(left, right):
                try:
                    git(cache, "merge-base", "--is-ancestor", left, right)
                    return True
                except Error as failure:
                    if failure.exit_code == 1:
                        return False
                    raise
            if ancestor(old, tip):
                relation = "fast-forward"
                commits = git(cache, "rev-list", "--max-count=201", tip, "^" + old).splitlines()
                if len(commits) > 200:
                    raise Error("remote change exceeds 200-commit bound; review history manually")
            else:
                relation = "rewritten" if ancestor(tip, old) else "diverged"
        for commit in commits:
            observations["pending"].setdefault(commit, {"state": "pending", "observed_at": now(), "relation": relation})
        observations.update(tip=tip, relation=relation, last_poll_at=now())
        write_json(path, observations)
        return {"watch": "observed", "tip": tip, "relation": relation, "pending_count": len(observations["pending"]),
                "deployment": "unchanged; pending commits require explicit verification and human confirmation"}


def watch_loop(deployment, expected_head, polls, interval, sleeper=time.sleep):
    failures = 0
    for index in range(polls):
        try:
            with deployment.lock():
                result = deployment.poll(expected_head)
            failures = 0
        except (Error, subprocess.TimeoutExpired) as failure:
            failures += 1
            result = {"watch": "paused-or-fetch-failed", "attempt": index + 1,
                      "reason": "fetch timeout" if isinstance(failure, subprocess.TimeoutExpired) else str(failure),
                      "deployment": "unchanged", "retry_seconds": min(interval * (2 ** min(failures - 1, 10)), 3600)}
        print(json.dumps(result), flush=True)
        if index + 1 < polls:
            sleeper(result["retry_seconds"] if failures else interval)
    return failures == 0


def main():
    os.umask(0o077)
    def interrupted(signum, frame):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, interrupted)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Trusted private JSON outside service repository")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "history"):
        commands.add_parser(name)
    check = commands.add_parser("check", help="Collect bounded local checks for the exact deployed identity")
    check.add_argument("--commit", required=True)
    check.add_argument("--artifact", required=True)
    check.add_argument("--operator", required=True)
    check.add_argument("--notice")
    confirm = commands.add_parser("confirm", help="Record the HUMAN's external leaderboard observation")
    group = confirm.add_mutually_exclusive_group(required=True)
    group.add_argument("--evidence")
    group.add_argument("--plan")
    confirm.add_argument("--status", choices=("up", "down", "unknown"), required=True)
    confirm.add_argument("--observed-at", required=True)
    confirm.add_argument("--operator", required=True)
    confirm.add_argument("--tick-id", help="Optional human-observed checker tick identifier")
    confirm.add_argument("--human-observation", action="store_true", required=True,
                         help="Explicitly attest that the supplied status/time came from a human observer")
    promote = commands.add_parser("promote")
    promote.add_argument("--evidence", required=True)
    promote.add_argument("--operator", required=True)
    promote.add_argument("--tag")
    revoke = commands.add_parser("revoke")
    revoke.add_argument("--checkpoint", required=True)
    revoke.add_argument("--operator", required=True)
    for name in ("notice", "rollback-plan"):
        action = commands.add_parser(name)
        if name == "notice":
            action.add_argument("--commit", required=True)
        action.add_argument("--checkpoint", required=True)
        action.add_argument("--summary", required=True, help="Non-secret, short change description")
        action.add_argument("--maintenance-seconds", type=int, required=True)
        action.add_argument("--operator", required=True)
    for name in ("rollback-apply", "rollback-verify", "rollback-recover", "close"):
        action = commands.add_parser(name)
        action.add_argument("--plan", required=True)
        if name != "rollback-verify":
            action.add_argument("--operator", required=True)
    watch = commands.add_parser("watch", help="Bounded observations only; default one poll")
    watch.add_argument("--expected-head", required=True)
    watch.add_argument("--polls", type=int, default=1)
    watch.add_argument("--interval", type=float, default=30)
    args = parser.parse_args()
    try:
        deployment = Deployment(args.config)
        if args.command == "watch":
            if not 1 <= args.polls <= 10000 or not 1 <= args.interval <= 3600:
                raise Error("watch requires 1..10000 polls and 1..3600 second interval")
            return 0 if watch_loop(deployment, args.expected_head, args.polls, args.interval) else 2
        if hasattr(args, "summary") and (not 1 <= len(args.summary) <= 240 or any(ord(c) < 32 for c in args.summary) or
                                         not 0 <= args.maintenance_seconds <= 600):
            raise Error("use a short non-secret summary and 0..600 second planned maintenance window")
        with deployment.lock():
            name = args.command
            if name in ("status", "history"):
                result = deployment.status(history=name == "history")
            elif name == "check":
                result = deployment.check(args.commit, args.artifact, args.operator, args.notice)
            elif name == "confirm":
                result = deployment.confirm(args.plan or args.evidence, bool(args.plan), args.status, args.observed_at, args.operator, args.tick_id,
                                            human_attestation=args.human_observation)
            elif name == "promote":
                result = deployment.promote(args.evidence, args.operator, args.tag)
            elif name == "revoke":
                result = deployment.revoke(args.checkpoint, args.operator)
            elif name == "notice":
                result = deployment.notice(args.commit, args.checkpoint, args.summary, args.maintenance_seconds, args.operator)
            elif name == "rollback-plan":
                result = deployment.plan(args.checkpoint, args.summary, args.maintenance_seconds, args.operator)
            elif name in ("rollback-apply", "rollback-recover"):
                result = deployment.apply(args.plan, args.operator, recover=name == "rollback-recover")
            elif name == "close":
                result = deployment.close(args.plan, args.operator)
            else:
                result = deployment.verify(args.plan)
        print(json.dumps(result, sort_keys=True), flush=True)
        return 0
    except KeyboardInterrupt:
        print(json.dumps({"state": "interrupted", "external_availability": "unknown; ask the operator",
                          "instruction": "Inspect status/history; verify or recover any unresolved rollback."}), file=sys.stderr)
        return 130
    except (Error, subprocess.TimeoutExpired, OSError, KeyError, TypeError, ValueError, AttributeError) as failure:
        reason = "configured command timed out; inspect status/history" if isinstance(failure, subprocess.TimeoutExpired) else \
            (str(failure) if isinstance(failure, Error) else "invalid configuration/metadata or unavailable local resource")
        print(json.dumps({"state": "failed", "reason": reason, "external_availability": "unknown; ask the operator"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
