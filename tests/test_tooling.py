"""Tooling contracts: native launch, private evidence, credential handling."""
import importlib.util
import json
import os
import shutil
import socket
import sqlite3
import struct
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pcap_index", ROOT / "scripts/pcap-index.py")
pcap_index = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcap_index)


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ctf-tooling-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for directory in ("bin", "config", "skills", "prompts"):
            shutil.copytree(ROOT / directory, self.root / directory)
        shutil.copy2(ROOT / "codex-ctf", self.root / "codex-ctf")
        self.fakebin = self.root / "fakebin"
        self.fakebin.mkdir()
        self.capture = self.root / "captured-args.txt"
        fake = self.fakebin / "codex"
        fake.write_text('''#!/bin/sh
if [ "$1" = "--version" ]; then
  printf 'codex-cli 0.159.2\n'
  exit 0
fi
printf '%s\n' "$@" > "$CTF_CAPTURE"
printf 'HOME=%s\nOPENAI=%s\nCODEX_KEY=%s\n' "$CODEX_HOME" "${OPENAI_API_KEY:-unset}" "${CODEX_API_KEY:-unset}" >> "$CTF_CAPTURE"
''')
        fake.chmod(0o755)
        self.env = dict(os.environ)
        self.env.update(PATH=str(self.fakebin) + os.pathsep + os.environ["PATH"],
                        HOME=str(self.root / "personal"), CTF_CAPTURE=str(self.capture),
                        OPENROUTER_API_KEY="synthetic-test-key",
                        OPENAI_API_KEY="other-provider", CODEX_API_KEY="other-key")

    def run_cli(self, *args):
        return subprocess.run([str(self.root / "bin/ctf-codex"), *args],
                              env=self.env, capture_output=True, text=True)

    def test_three_step_entrypoint_opens_tui_at_root_without_initial_prompt(self):
        result = subprocess.run([str(self.root / "codex-ctf")], env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.capture.read_text().splitlines()
        self.assertEqual(args[args.index("--cd") + 1], str(self.root))
        self.assertEqual(args[args.index("--profile") + 1], "team")
        self.assertNotIn("exec", args)
        self.assertNotIn("$ad-ctf-team", self.capture.read_text())
        self.assertEqual(args[-1], "CODEX_KEY=unset")
        self.assertFalse((self.root / "workspaces").exists())
        self.assertTrue((self.root / ".runtime/flags/inbox").is_dir())
        config = (self.root / ".runtime/codex/config.toml").read_text()
        self.assertIn('model = "deepseek/deepseek-v4.1-flash"', config)
        self.assertIn('trust_level = "trusted"', config)

    def test_modes_are_native_prompts_and_brrrr_uses_team_profile(self):
        result = self.run_cli("brrrr")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.capture.read_text()
        self.assertIn("--profile\nteam", args)
        self.assertIn("features.multi_agent=true", args)
        self.assertIn("points-producing", args)
        self.assertIn("\n--\n---\ndescription: Points-first", args)
        home = self.root / ".runtime/codex"
        for name in ("brrrr", "chillax", "team", "audit", "traffic", "patch"):
            self.assertTrue((home / f"prompts/{name}.md").exists())
        source_agents = {agent.name for agent in (self.root / "config/agents").glob("*.toml")}
        installed_agents = {agent.name for agent in (home / "agents").glob("*.toml")}
        self.assertEqual(installed_agents, source_agents)
        for agent in (home / "agents").glob("*.toml"):
            self.assertNotIn("\nmodel =", agent.read_text())

    def test_single_agent_commands_select_their_profiles(self):
        for command, profile in (("run", "cheap"), ("audit", "audit"),
                                 ("traffic", "traffic"), ("patch", "patch")):
            with self.subTest(command=command):
                result = self.run_cli(command, "synthetic task")
                self.assertEqual(result.returncode, 0, result.stderr)
                args = self.capture.read_text().splitlines()
                self.assertEqual(args[args.index("--profile") + 1], profile)
                self.assertNotIn("features.multi_agent=true", args)

        result = self.run_cli("run", "--profile", "mimo", "synthetic task")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.capture.read_text().splitlines()
        self.assertEqual(args[args.index("--profile") + 1], "mimo")
        self.assertIn('model = "xiaomi/mimo-v2.6-flash"',
                      (self.root / ".runtime/codex/mimo.config.toml").read_text())

    def test_resume_and_provider_binding(self):
        result = self.run_cli("resume", "--last", "Continue")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.capture.read_text().splitlines()
        self.assertIn("resume", args)
        self.assertIn("--last", args)
        self.assertIn("Continue", args)
        self.assertIn('model_provider="openrouter"', args)
        self.assertIn("HOME=" + str(self.root / ".runtime/codex"), args)
        self.assertIn("OPENAI=unset", args)
        self.assertIn("CODEX_KEY=unset", args)
        self.assertNotIn("synthetic-test-key", self.capture.read_text())

    def test_resume_exec_supports_native_team_session_recovery(self):
        output = str(self.root / "answer.md")
        result = self.run_cli("resume", "--exec", "--json", "--output", output,
                              "synthetic-session-id", "--", "Continue the interrupted team task")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.capture.read_text().splitlines()
        self.assertLess(args.index("exec"), args.index("resume"))
        self.assertEqual(args[args.index("--sandbox") + 1], "workspace-write")
        self.assertIn("--json", args)
        self.assertEqual(args[args.index("--output-last-message") + 1], output)
        self.assertIn("synthetic-session-id", args)
        self.assertIn("Continue the interrupted team task", args)
        self.assertIn('model_provider="openrouter"', args)
        self.assertNotIn("synthetic-test-key", self.capture.read_text())

    def test_exec_keeps_workspace_write_sandbox(self):
        result = self.run_cli("run", "--exec", "Check")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.capture.read_text().splitlines()
        self.assertEqual(args[args.index("--sandbox") + 1], "workspace-write")
        self.assertNotIn("--ephemeral", args)

    def test_falls_back_to_bundled_cli_when_path_version_is_old(self):
        fake = self.fakebin / "codex"
        fake.write_text("#!/bin/sh\nprintf 'codex-cli 0.158.0\\n'\n")
        bundled = self.root / "personal/AppData/Local/OpenAI/Codex/bin/current/codex.exe"
        bundled.parent.mkdir(parents=True)
        bundled.write_text("#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then printf 'codex-cli 0.159.2\\n'; exit; fi\nprintf '%s\\n' \"$@\" > \"$CTF_CAPTURE\"\n")
        bundled.chmod(0o755)
        result = self.run_cli("team")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.capture.exists())

    def test_missing_key_and_project_override_fail_closed(self):
        self.env.pop("OPENROUTER_API_KEY")
        result = self.run_cli("team")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Export OPENROUTER_API_KEY", result.stderr)
        self.assertFalse(self.capture.exists())
        self.env["OPENROUTER_API_KEY"] = "synthetic-test-key"
        config = self.root / ".codex/config.toml"
        config.parent.mkdir()
        config.write_text('model = "untrusted"\n')
        result = self.run_cli("team")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(config.read_text(), 'model = "untrusted"\n')
        self.assertFalse(self.capture.exists())

    def test_rejects_unsupported_options(self):
        for args in (("team", "--workspace", "elsewhere"),
                     ("team", "--model", "missing-prefix"),
                     ("resume", "--remote"),
                     ("resume", "--exec")):
            result = self.run_cli(*args)
            self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.capture.exists())

    def test_setup_is_idempotent(self):
        self.assertEqual(self.run_cli("setup").returncode, 0)
        self.assertEqual(self.run_cli("setup").returncode, 0)
        home = self.root / ".runtime/codex"
        self.assertEqual((home / "config.toml").read_text().count('[projects."'), 1)
        self.assertTrue((home / "skills/ad-ctf-team/SKILL.md").exists())

    def test_submitter_starts_when_config_appears_after_launch(self):
        shutil.copytree(ROOT / "scripts", self.root / "scripts")
        fake = self.fakebin / "codex"
        fake.write_text(fake.read_text() + "sleep 3\n")
        adapter = self.root / "synthetic-adapter.py"
        adapter.write_text('''import json, sys
if sys.argv[1:] == ["--check"]:
    print('{"ready":true}')
else:
    data = json.load(sys.stdin)
    print(json.dumps({"results": [{"id": item["id"], "status": "accepted"}
                                  for item in data["flags"]]}))
''')
        self.env["CTF_SUBMISSION_ADAPTER"] = str(adapter)
        proc = subprocess.Popen([str(self.root / "bin/ctf-codex"), "team"],
                                env=self.env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 5
            while not self.capture.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(self.capture.exists())
            flags_dir = self.root / ".runtime/flags"
            capture = flags_dir / "capture.tmp"
            capture.write_text(json.dumps({"flag": "SYNTHETIC_FLAG_ASAP", "service": "synthetic",
                                           "team": "2", "flag_id": "test-object",
                                           "source": "local mock", "expires_at": None}) + "\n")
            capture.replace(flags_dir / "inbox/capture.jsonl")
            config = flags_dir / "submission.json"
            config.write_text("{}\n")
            config.chmod(0o600)
            db_path = flags_dir / "ledger.sqlite3"
            accepted = False
            while time.monotonic() < deadline:
                if db_path.exists():
                    with sqlite3.connect(db_path) as db:
                        accepted = db.execute("SELECT COUNT(*) FROM flags WHERE state='accepted'").fetchone()[0] == 1
                    if accepted:
                        break
                time.sleep(0.05)
            self.assertTrue(accepted, "configured submitter did not process the waiting flag")
        finally:
            proc.terminate()
            proc.communicate(timeout=5)


def udp_packet(port, payload):
    ethernet = bytes.fromhex("00112233445566778899aabb0800")
    udp = struct.pack("!HHHH", 12345, port, 8 + len(payload), 0) + payload
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(udp), 1, 0, 64, 17, 0,
                     socket.inet_aton("192.0.2.1"), socket.inet_aton("192.0.2.2"))
    return ethernet + ip + udp


class EvidenceTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("tshark"), "optional tshark unavailable")
    def test_real_tshark_index_filters_port_omits_payload_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            capture = root / "synthetic.pcap"
            raw = struct.pack("<IHHIIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)
            for i, port in enumerate((8080, 9090)):
                packet = udp_packet(port, b"SYNTHETIC_PRIVATE_PAYLOAD_MUST_NOT_APPEAR")
                raw += struct.pack("<IIII", 1700000000 + i, 0, len(packet), len(packet)) + packet
            capture.write_bytes(raw)
            out = root / "derived"
            result = pcap_index.index(capture, 8080, out, 20000)
            self.assertEqual(result["matching_frames"], 1)
            table = (out / "frames.tsv").read_text()
            self.assertIn("8080", table)
            self.assertNotIn("9090", table)
            self.assertNotIn("PRIVATE_PAYLOAD", table)
            self.assertEqual(capture.read_bytes(), raw)
            self.assertIn("sha256", json.loads((out / "provenance.json").read_text()))
            self.assertEqual(out.stat().st_mode & 0o777, 0o700)
            self.assertEqual((out / "frames.tsv").stat().st_mode & 0o777, 0o600)
            self.assertEqual((out / "provenance.json").stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                pcap_index.index(capture, 8080, out, 20000)

    def test_invalid_port_is_rejected_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "derived"
            with self.assertRaises(ValueError):
                pcap_index.index(Path("missing.pcap"), 0, out, 20000)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
