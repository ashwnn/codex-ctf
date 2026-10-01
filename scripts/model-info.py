#!/usr/bin/env python3
"""Read-only OpenRouter metadata. No model invocation or agent orchestration."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def key():
    value = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if value:
        return value
    file = ROOT / ".runtime/secrets/openrouter.key"
    if not file.exists() or file.stat().st_mode & 0o077:
        raise ValueError("Set OPENROUTER_API_KEY or create a local key file with mode 0600.")
    value = file.read_text().strip()
    if not value:
        raise ValueError("The key file is empty.")
    return value


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(path, token):
    # Never forward the bearer token through a system proxy or a redirect.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    req = urllib.request.Request("https://openrouter.ai/api/v1" + path,
                                 headers={"Authorization": "Bearer " + token})
    with opener.open(req, timeout=30) as response:
        return json.load(response)


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "stealth/space-bunny-alpha"
    try:
        token = key()
        data = request("/models", token)["data"]
        match = next((m for m in data if m["id"] == model), None)
        if not match:
            raise ValueError("Exact model is absent from the catalog; no substitute selected.")
        print(json.dumps({k: match.get(k) for k in ("id", "context_length", "pricing", "reasoning",
                                                   "supported_parameters", "expiration_date")}, indent=2))
        budget = request("/key", token).get("data", {})
        print(json.dumps({k: budget.get(k) for k in ("limit", "limit_remaining", "usage", "is_free_tier")}, indent=2))
        if match.get("expiration_date"):
            print("Temporary model; recheck availability before the event. No automatic fallback.")
        return 0
    except urllib.error.HTTPError as e:
        print("OpenRouter HTTP %s (response body withheld)." % e.code, file=sys.stderr)
    except (ValueError, OSError, urllib.error.URLError) as e:
        print(str(e), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
