"""Local checks for ZDR routing and the free-first fallback order."""
import importlib.util
import io
import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/openrouter-fallback.py"
SPEC = importlib.util.spec_from_file_location("openrouter_fallback", SCRIPT)
RELAY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RELAY)


class Response:
    status = 200
    headers = {"Content-Type": "text/event-stream"}

    def __init__(self):
        self.data = io.BytesIO(b"data: ok\n\n")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass

    def read1(self, size):
        return self.data.read(size)


class FallbackTests(unittest.TestCase):
    def setUp(self):
        RELAY._catalog_models = None
        RELAY._failed_free_models.clear()

    def test_catalog_includes_ling_and_excludes_paid_endpoint(self):
        data = [
            [{"id": "qwen/qwen3.8-27b:free"}, {"id": "inclusionai/ling-3.1-flash"}],
            [
                {"model_id": "qwen/qwen3.8-27b:free", "status": 0,
                 "pricing": {"prompt": "0", "completion": "0"},
                 "supported_parameters": ["tools"]},
                {"model_id": "inclusionai/ling-3.1-flash", "status": 0,
                 "pricing": {"prompt": "0", "completion": "0"},
                 "supported_parameters": ["tools"]},
                {"model_id": "inclusionai/ling-3.1-flash", "status": 0,
                 "pricing": {"prompt": "0.01", "completion": "0"},
                 "supported_parameters": ["tools"]},
            ],
        ]
        with patch.object(RELAY, "catalog_json", side_effect=data):
            self.assertEqual(RELAY.free_zdr_models(), ("qwen/qwen3.8-27b:free",))
        data[1].pop()
        with patch.object(RELAY, "catalog_json", side_effect=data):
            self.assertEqual(RELAY.free_zdr_models(),
                             ("qwen/qwen3.8-27b:free", "inclusionai/ling-3.1-flash"))

    def test_relay_retries_free_then_paid_with_zdr_and_skips_failed_free_model(self):
        RELAY._catalog_models = ("qwen/qwen3.8-27b:free", "inclusionai/ling-3.1-flash")
        calls = []

        def upstream(raw, model, authorization):
            body = json.loads(RELAY.prepare_body(raw, model))
            calls.append((model, body["provider"], authorization))
            if model in RELAY._catalog_models:
                raise urllib.error.HTTPError("mock", 429, "rate limit", {}, io.BytesIO(b"{}"))
            return Response()

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "synthetic-key"}), \
             patch.object(RELAY, "upstream_request", side_effect=upstream):
            server = RELAY.http.server.ThreadingHTTPServer(("127.0.0.1", 0), RELAY.Relay)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = "http://127.0.0.1:%d/responses" % server.server_port
                request = urllib.request.Request(
                    url, data=json.dumps({"model": RELAY.DEFAULT_MODEL,
                                          "input": "synthetic"}).encode(),
                    headers={"Authorization": "Bearer synthetic-key",
                             "Content-Type": "application/json"})
                with urllib.request.urlopen(request) as response:
                    self.assertEqual(response.read(), b"data: ok\n\n")
                self.assertEqual([call[0] for call in calls],
                                 ["qwen/qwen3.8-27b:free", "inclusionai/ling-3.1-flash",
                                  "deepseek/deepseek-v4.1-flash"])
                self.assertTrue(all(call[1]["zdr"] for call in calls))
                self.assertTrue(all(call[2] == "Bearer synthetic-key" for call in calls))
                calls.clear()
                with urllib.request.urlopen(request) as response:
                    self.assertEqual(response.status, 200)
                self.assertEqual([call[0] for call in calls],
                                 ["deepseek/deepseek-v4.1-flash"])
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
