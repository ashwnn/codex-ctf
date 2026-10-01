"""The local continuity/rollback drill must remain synthetic and loopback-only."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class OperationsDrillTests(unittest.TestCase):
    def test_persistent_records_survive_restart_and_source_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "drill"
            run = subprocess.run([sys.executable, str(ROOT / "scripts/operations-drill.py"),
                                  "--output", str(output)], capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            result = json.loads((output / "result.json").read_text())
            self.assertTrue(result["passed"])
            self.assertNotEqual(result["sources"]["baseline_sha256"], result["sources"]["candidate_sha256"])
            self.assertEqual(result["phases"]["baseline"]["revision"], "baseline")
            self.assertEqual(result["phases"]["candidate"]["revision"], "candidate")
            self.assertEqual(result["phases"]["rollback"]["revision"], "baseline")
            self.assertEqual(result["record_count_after_rollback"], 2)
            self.assertTrue(result["recovery_backup"]["created"])
            self.assertEqual(set(result["health_observations"]),
                             {"baseline", "candidate", "candidate_restart", "rollback"})
            self.assertTrue(all(len(samples) == 3 for samples in result["health_observations"].values()))
            self.assertTrue(any(check["name"] == "B_survives_source_rollback" and check["passed"]
                                for check in result["checks"]))
            serialized = json.dumps(result)
            self.assertNotIn("SYNTHETIC_A", serialized)
            self.assertNotIn("SYNTHETIC_B", serialized)


if __name__ == "__main__":
    unittest.main()
