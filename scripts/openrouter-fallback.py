#!/usr/bin/env python3
"""Local, in-memory OpenRouter Responses relay with ZDR and ordered failover.

The relay binds only to loopback and lives only as long as the Codex process.
It never writes request bodies, responses, or credentials to disk.
"""
import http.server
import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation

UPSTREAM = "https://openrouter.ai/api/v1/responses"
PREFERRED_FREE_MODELS = (
    "qwen/qwen3.8-27b:free",
    "inclusionai/ling-3.1-flash",
    "apodex/apodex-1.1-mini:free",
    "inclusionai/ling-3.0-flash-sante:free",
)
PAID_MODELS = ("deepseek/deepseek-v4.1-flash", "xiaomi/mimo-v2.6-flash")
DEFAULT_MODEL = PREFERRED_FREE_MODELS[0]
RETRY_STATUSES = {429, 502, 503, 504}
_catalog_lock = threading.Lock()
_catalog_models = None
_failed_free_models = set()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def catalog_json(path):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open("https://openrouter.ai/api/v1" + path, timeout=15) as response:
        return json.load(response)["data"]


def free_zdr_models():
    """Discover current zero-priced ZDR endpoints with tool support."""
    models = {model.get("id") for model in catalog_json("/models?zdr=true")}
    endpoints_by_model = {}
    for endpoint in catalog_json("/endpoints/zdr"):
        model = endpoint.get("model_id")
        if model not in models or endpoint.get("status") != 0:
            continue
        price = endpoint.get("pricing") or {}
        try:
            free = all(Decimal(str(price.get(field))) == 0
                       for field in ("prompt", "completion"))
        except (InvalidOperation, TypeError):
            free = False
        usable = free and "tools" in (endpoint.get("supported_parameters") or [])
        endpoints_by_model.setdefault(model, []).append(usable)
    eligible = {model for model, statuses in endpoints_by_model.items() if all(statuses)}
    preferred = [model for model in PREFERRED_FREE_MODELS if model in eligible]
    return tuple(preferred + sorted(eligible - set(preferred)))


def current_free_models():
    global _catalog_models
    with _catalog_lock:
        if _catalog_models is None:
            _catalog_models = free_zdr_models()
        return _catalog_models


def attempt_order(requested):
    if requested == DEFAULT_MODEL:
        # Paid fallbacks remain behind every currently eligible free model.
        with _catalog_lock:
            free = tuple(model for model in current_free_models_unlocked()
                         if model not in _failed_free_models)
        return free + PAID_MODELS
    # An explicit --model or profile override is respected.
    return (requested,)


def current_free_models_unlocked():
    global _catalog_models
    if _catalog_models is None:
        _catalog_models = free_zdr_models()
    return _catalog_models


def prepare_body(raw, model):
    body = json.loads(raw)
    if not isinstance(body, dict) or not isinstance(body.get("model"), str):
        raise ValueError("Responses request needs a model")
    body["model"] = model
    provider = body.get("provider") or {}
    if not isinstance(provider, dict):
        raise ValueError("Invalid provider routing")
    provider["zdr"] = True
    provider["data_collection"] = "deny"
    body["provider"] = provider
    return json.dumps(body, separators=(",", ":")).encode()


def upstream_request(raw, model, authorization):
    data = prepare_body(raw, model)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(
        UPSTREAM, data=data, method="POST",
        headers={"Authorization": authorization,
                 "Content-Type": "application/json", "Accept": "text/event-stream"},
    )
    return opener.open(request, timeout=180)


class Relay(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *_args):
        pass

    def do_POST(self):
        if self.path != "/responses":
            self.send_error(404)
            return
        authorization = self.headers.get("Authorization", "")
        if authorization != "Bearer " + os.environ.get("OPENROUTER_API_KEY", ""):
            self.send_error(401)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 32 * 1024 * 1024:
                raise ValueError("Invalid request length")
            raw = self.rfile.read(length)
            requested = json.loads(raw)["model"]
            if not isinstance(requested, str):
                raise ValueError("Invalid model")
        except (ValueError, KeyError, json.JSONDecodeError):
            self.send_error(400)
            return
        try:
            order = attempt_order(requested)
        except (ValueError, KeyError, urllib.error.URLError, OSError):
            self.send_error(503, "OpenRouter ZDR catalog unavailable")
            return
        last_error = None
        for model in order:
            try:
                response = upstream_request(raw, model, authorization)
            except urllib.error.HTTPError as error:
                last_error = error
                if error.code == 429 and model in current_free_models():
                    with _catalog_lock:
                        _failed_free_models.add(model)
                if error.code in RETRY_STATUSES and model != order[-1]:
                    print("ctf-codex: OpenRouter model unavailable; trying next ZDR model.", file=sys.stderr)
                    error.close()
                    continue
                break
            except (urllib.error.URLError, TimeoutError, OSError):
                self.send_error(502, "OpenRouter connection failed")
                return
            with response:
                self.send_response(response.status)
                self.send_header("Content-Type", response.headers.get("Content-Type", "text/event-stream"))
                self.send_header("Connection", "close")
                self.end_headers()
                try:
                    while True:
                        chunk = response.read1(65536)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError, TimeoutError):
                    pass
            return
        if last_error is not None:
            with last_error:
                payload = last_error.read()
                self.send_response(last_error.code)
                self.send_header("Content-Type", last_error.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)


def main():
    if len(sys.argv) < 2 or not os.environ.get("OPENROUTER_API_KEY"):
        raise SystemExit("ctf-codex: fallback relay requires Codex command and OPENROUTER_API_KEY")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Relay)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    remote_config = 'model_providers.openrouter.base_url="https://openrouter.ai/api/v1"'
    local_config = 'model_providers.openrouter.base_url="http://127.0.0.1:%d"' % server.server_port
    arguments = [arg.replace(remote_config, local_config) for arg in sys.argv[2:]]
    if arguments == sys.argv[2:]:
        raise SystemExit("ctf-codex: missing OpenRouter base URL override")
    try:
        return subprocess.call([sys.argv[1], *arguments])
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    sys.exit(main())
