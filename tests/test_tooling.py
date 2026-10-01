"""Tooling contracts: native launch, private evidence, credential handling."""
import importlib.util
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pcap_index", ROOT / "scripts/pcap-index.py")
pcap_index = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcap_index)


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ctf "tooling ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for directory in ("bin", "config", "skills", "templates", "prompts"):
            shutil.copytree(ROOT / directory, self.root / directory)
        shutil.copy2(ROOT / "codex-ctf", self.root / "codex-ctf")
        self.fakebin = self.root / "fakebin"
        self.fakebin.mkdir()
        self.capture = self.root / "captured-args.txt"
        fake = self.fakebin / "codex"
        fake.write_text('''#!/bin/sh
if [ "$1" = "--version" ]; then
  printf 'codex-cli %s\\n' "${CTF_FAKE_CODEX_VERSION:-0.159.2}"
  exit 0
fi
printf '%s\\n' "$@" > "$CTF_CAPTURE"
printf 'HOME=%s\\nOPENAI=%s\\nCODEX_KEY=%s\\n' "$CODEX_HOME" "${OPENAI_API_KEY:-unset}" "${CODEX_API_KEY:-unset}" >> "$CTF_CAPTURE"
''')
        fake.chmod(0o755)
        self.env = dict(os.environ)
        self.env.update(PATH=str(self.fakebin) + os.pathsep + os.environ["PATH"],
                        HOME=str(self.root / "personal"), CTF_CAPTURE=str(self.capture),
                        OPENROUTER_API_KEY="synthetic-test-key",
                        OPENAI_API_KEY="synthetic-other-provider", CODEX_API_KEY="synthetic-other-key")

    def run_cli(self, *args):
        return subprocess.run([str(self.root / "bin/ctf-codex"), *args], env=self.env,
                              capture_output=True, text=True)

    def test_root_entrypoint_opens_ui_and_prepares_workspace_without_setup(self):
        launcher = self.root / "codex-ctf"
        for _ in range(2):
            result = subprocess.run([str(launcher)], env=self.env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            args = self.capture.read_text().splitlines()
            self.assertNotIn("exec", args)
            self.assertEqual(args[args.index("--cd") + 1], str(self.root / "workspaces/default"))
            self.assertEqual(args[args.index("--profile") + 1], "team")
            self.assertIn("$ad-ctf-team", self.capture.read_text())
        workspace = self.root / "workspaces/default"
        self.assertTrue((workspace / "service.toml").exists())
        self.assertTrue((workspace / "team.toml").exists())
        self.assertTrue((workspace / "flags/inbox").is_dir())
        self.assertTrue((workspace / "coordination/inbox").is_dir())
        self.assertTrue((workspace / "AGENTS.md").exists())
        self.assertTrue((workspace / "evidence/raw").is_dir())
        config = (self.root / ".runtime/codex/config.toml").read_text()
        self.assertIn('model = "stealth/space-bunny-alpha"', config)
        self.assertIn('trust_level = "trusted"', config)

    def test_team_native_configuration_and_single_agent_profiles(self):
        self.assertEqual(self.run_cli("team", "--network", "Test").returncode, 0)
        args = self.capture.read_text()
        self.assertIn(str(self.root / "workspaces/default"), args)
        self.assertFalse((self.root / "flags").exists())
        self.assertFalse((self.root / "coordination").exists())
        self.assertIn('sandbox_workspace_write.network_access=true', args)
        self.assertIn("Team launch: start five workers initially", args)
        self.assertIn("features.multi_agent=true", args)
        self.assertIn("agents.enabled=true", args)
        self.assertIn("agents.max_concurrent_threads_per_session=20", args)
        home = self.root / ".runtime/codex"
        installed_agents = {path.stem for path in (home / "agents").glob("ctf-*.toml")}
        self.assertTrue({"ctf-flagkeeper", "ctf-traffic", "ctf-docker-logs",
                         "ctf-code-review", "ctf-poc-dev"}.issubset(installed_agents))
        self.assertIn("enabled = true", (home / "team.config.toml").read_text())
        self.assertIn("max_concurrent_threads_per_session = 20", (home / "team.config.toml").read_text())
        self.assertIn("multi_agent = false", (home / "config.toml").read_text())
        for file in (home / "agents").glob("*.toml"):
            self.assertNotIn("model_provider =", file.read_text())
            self.assertNotIn("model =", file.read_text())
        self.assertTrue((home / "skills/ad-ctf-flagkeeper/SKILL.md").exists())
        self.assertTrue((home / "skills/ad-ctf-team/references/communication.md").exists())
        self.assertTrue((home / "prompts/brrr.md").exists())

    def test_brrr_native_surge_command(self):
        result = self.run_cli("brrr", "--workspace", str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.capture.read_text()
        self.assertIn("--profile\nteam", args)
        self.assertIn("features.multi_agent=true", args)
        self.assertIn("agents.max_concurrent_threads_per_session=20", args)
        self.assertIn("scale toward twenty concurrent agents", " ".join(args.split()))
        self.assertIn("shared role inbox files", args)
        self.assertIn("primary relays urgent messages", args)
        self.assertIn("flagkeeper", args)
        self.assertIn("Do not run broad scans", args)
        self.assertIn("Surge launch: up to twenty spawned agents", args)
        self.assertNotIn("Five workers are authorized", args)

    def test_launch_is_native_and_provider_is_openrouter(self):
        result = self.run_cli("run", "--exec", "--json", "--model", "stealth/space-bunny-alpha", "Test")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = self.capture.read_text().splitlines()
        self.assertIn("exec", args)
        self.assertIn("--no-daemon", args)
        self.assertIn("--strict-config", args)
        self.assertIn('model_provider="openrouter"', args)
        self.assertIn("--json", args)
        self.assertIn("OPENAI=unset", args)
        self.assertIn("CODEX_KEY=unset", args)
        self.assertIn("HOME=" + str(self.root / ".runtime/codex"), args)
        self.assertNotIn("synthetic-test-key", self.capture.read_text())

    def test_skill_prompt_is_data_and_shell_substitution_is_not_executed(self):
        marker = self.root / "unwanted"
        prompt = "Review literal $(touch %s) and `echo injection`" % marker
        result = self.run_cli("audit", prompt)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("$ad-ctf-service-audit", self.capture.read_text())
        self.assertIn(prompt, self.capture.read_text())
        self.assertFalse(marker.exists())

    def test_init_preserves_existing_workspace_and_rejects_traversal(self):
        self.assertNotEqual(self.run_cli("init", "../outside").returncode, 0)
        self.assertEqual(self.run_cli("init", "sample-service").returncode, 0)
        file = self.root / "workspaces/sample-service/source/keep.txt"
        file.write_text("evidence")
        self.assertNotEqual(self.run_cli("init", "sample-service").returncode, 0)
        self.assertEqual(file.read_text(), "evidence")

    def test_rejects_unknown_profile_and_provider_override(self):
        self.assertNotEqual(self.run_cli("run", "--profile", "invalid").returncode, 0)
        self.assertNotEqual(self.run_cli("run", "--model", "missing-prefix").returncode, 0)
        self.assertNotEqual(self.run_cli("run", "-c", 'model_provider="openai"').returncode, 0)
        self.assertFalse(self.capture.exists())

    def test_setup_rejects_codex_older_than_minimum(self):
        self.env["CTF_FAKE_CODEX_VERSION"] = "0.159.1"
        result = self.run_cli("setup")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(">= 0.159.2 is required", result.stderr)
        self.assertFalse((self.root / ".runtime/codex").exists())

    def test_setup_refresh_removes_stale_managed_assets_and_escapes_toml(self):
        home = self.root / ".runtime/codex"
        stale_skill = home / "skills/ad-ctf-removed/SKILL.md"
        stale_skill.parent.mkdir(parents=True)
        stale_skill.write_text("stale")
        stale_agent = home / "agents/ctf-removed.toml"
        stale_agent.parent.mkdir(parents=True, exist_ok=True)
        stale_agent.write_text("stale")
        result = self.run_cli("setup")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(stale_skill.parent.exists())
        self.assertFalse(stale_agent.exists())
        config = (home / "config.toml").read_text()
        self.assertIn('projects."' + str(self.root).replace('"', '\\"') + '"', config)

    def test_missing_credentials_fail_before_codex_launch(self):
        self.env.pop("OPENROUTER_API_KEY")
        self.assertNotEqual(self.run_cli("run", "Test").returncode, 0)
        self.assertFalse(self.capture.exists())

    def test_private_key_mode_and_env_precedence(self):
        key = self.root / ".runtime/secrets/openrouter.key"
        key.parent.mkdir(parents=True)
        key.write_text("synthetic-file-key")
        key.chmod(0o644)
        helper = self.root / "bin/openrouter-token"
        result = subprocess.run([str(helper)], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.stdout, "synthetic-test-key")
        self.env.pop("OPENROUTER_API_KEY")
        result = subprocess.run([str(helper)], env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        key.chmod(0o600)
        result = subprocess.run([str(helper)], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.stdout, "synthetic-file-key")

    def test_private_key_file_newline_is_stripped(self):
        self.env.pop("OPENROUTER_API_KEY")
        key = self.root / ".runtime/secrets/openrouter.key"
        key.parent.mkdir(parents=True)
        key.write_text("synthetic-newline-key\n")
        key.chmod(0o600)
        result = subprocess.run([str(self.root / "bin/openrouter-token")], env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.stdout, "synthetic-newline-key")

    def test_root_entrypoint_passes_through_help_and_subcommands(self):
        launcher = self.root / "codex-ctf"
        help_result = subprocess.run([str(launcher), "--help"], env=self.env,
                                     capture_output=True, text=True)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("Usage:", help_result.stdout)
        self.assertFalse(self.capture.exists())
        init_result = subprocess.run([str(launcher), "init", "demo"], env=self.env,
                                     capture_output=True, text=True)
        self.assertEqual(init_result.returncode, 0, init_result.stderr)
        self.assertTrue((self.root / "workspaces/demo/service.toml").exists())
        self.assertFalse(self.capture.exists())

    def test_models_defaults_to_configured_model_and_forwards_arguments(self):
        stub = self.root / "scripts/model-info.py"
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text("import sys\nprint('MODEL=' + ','.join(sys.argv[1:]))\n")
        default = self.run_cli("models")
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertEqual(default.stdout.strip(), "MODEL=stealth/space-bunny-alpha")
        explicit = self.run_cli("models", "deepseek/deepseek-v4.1-flash")
        self.assertEqual(explicit.stdout.strip(), "MODEL=deepseek/deepseek-v4.1-flash")

    def test_brrr_warns_when_an_explicit_profile_is_ignored(self):
        result = self.run_cli("brrr", "--profile", "deepseek-audit", "Surge")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ignoring --profile", result.stderr)
        self.assertIn("--profile\nteam", self.capture.read_text())

    def test_launch_removes_planted_workspace_project_config(self):
        self.run_cli("init", "svc")
        planted = self.root / "workspaces/svc/.codex/config.toml"
        planted.parent.mkdir(parents=True)
        planted.write_text('model = "injected-model"\n')
        result = self.run_cli("run", "--workspace", str(self.root / "workspaces/svc"), "go")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(planted.parent.exists())

    def test_setup_is_idempotent_with_single_trust_and_managed_counts(self):
        self.run_cli("setup")
        config = self.root / ".runtime/codex/config.toml"
        self.run_cli("setup")
        text = config.read_text()
        self.assertEqual(text.count('[projects."'), 1)
        self.assertEqual(text.count("[[skills.config]]"), 4)
        self.assertEqual(len(list((self.root / ".runtime/codex").glob("*.config.toml"))), 7)
        self.assertTrue(text.endswith("\n"))

    def test_setup_disables_host_agent_skills_and_installs_all_prompts(self):
        host_skill = self.root / "personal/.agents/skills/host-tool/SKILL.md"
        host_skill.parent.mkdir(parents=True)
        host_skill.write_text("---\nname: host-tool\ndescription: x\n---\n")
        self.assertEqual(self.run_cli("setup").returncode, 0)
        text = (self.root / ".runtime/codex/config.toml").read_text()
        self.assertIn("host-tool/SKILL.md", text)
        self.assertEqual(text.count("[[skills.config]]"), 5)
        for prompt in ("brrr", "team", "audit", "traffic", "patch"):
            self.assertTrue((self.root / f".runtime/codex/prompts/{prompt}.md").exists())


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
