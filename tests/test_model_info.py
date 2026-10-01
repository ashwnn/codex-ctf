import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/model-info.py"
SPEC = importlib.util.spec_from_file_location("model_info", SCRIPT)
MODEL_INFO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODEL_INFO)


class ModelInfoTests(unittest.TestCase):
    def test_zdr_report_filters_exact_models_and_discloses_scope(self):
        endpoints = [
            {
                "model_id": "deepseek/deepseek-v4.1-flash",
                "provider_name": "Example ZDR Provider",
                "pricing": {"prompt": "0.0000001", "completion": "0.0000005"},
                "latency_last_30m": {"p50": 400},
                "throughput_last_30m": {"p50": 100},
                "uptime_last_1d": 99.5,
                "api_key": "must-not-appear",
            },
            {
                "model_id": "other/model",
                "provider_name": "Unrequested Provider",
                "pricing": {"prompt": "1", "completion": "1"},
            },
        ]
        output = io.StringIO()
        with patch.object(MODEL_INFO, "request", return_value={"data": endpoints}), \
             redirect_stdout(output):
            MODEL_INFO.print_zdr(["deepseek/deepseek-v4.1-flash"], "private-token")
        result = output.getvalue()
        self.assertIn('"input_usd_per_million": 0.1', result)
        self.assertIn('"output_usd_per_million": 0.5', result)
        self.assertIn('"throughput_p50_tokens_per_second": 100', result)
        self.assertIn("does not verify account or API-key ZDR enforcement", result)
        self.assertNotIn("must-not-appear", result)
        self.assertNotIn("private-token", result)
        self.assertNotIn("other/model", result)

    def test_zdr_report_handles_no_matching_endpoints(self):
        output = io.StringIO()
        with patch.object(MODEL_INFO, "request", return_value={"data": []}), \
             redirect_stdout(output):
            MODEL_INFO.print_zdr(["xiaomi/mimo-v2.6-pro"], "private-token")
        self.assertIn('"eligible_endpoints": []', output.getvalue())

    def test_zdr_requires_complete_slugs(self):
        with self.assertRaisesRegex(ValueError, "complete OpenRouter slug"):
            MODEL_INFO.print_zdr(["not-a-slug"], "private-token")


if __name__ == "__main__":
    unittest.main()
