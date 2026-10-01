#!/usr/bin/env python3
"""Read-only OpenRouter metadata. No model invocation or agent orchestration."""
import json
import os
import re
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


def print_zdr(models, token):
    if not models:
        raise ValueError("Pass one or more exact OpenRouter model slugs after --zdr.")
    for model in models:
        if not re.fullmatch(r"[a-zA-Z0-9_.~-]+/[a-zA-Z0-9_.:~-]+", model):
            raise ValueError("Use a complete OpenRouter slug for --zdr.")
    endpoints = request("/endpoints/zdr", token).get("data", [])
    result = []
    for model in models:
        matching = [endpoint for endpoint in endpoints if endpoint.get("model_id") == model]
        rows = []
        for endpoint in matching:
            pricing = endpoint.get("pricing") or {}
            latency = endpoint.get("latency_last_30m") or {}
            throughput = endpoint.get("throughput_last_30m") or {}
            def per_million(value):
                try:
                    return round(float(value) * 1_000_000, 6)
                except (TypeError, ValueError):
                    return None
            rows.append({
                "provider": endpoint.get("provider_name"),
                "input_usd_per_million": per_million(pricing.get("prompt")),
                "output_usd_per_million": per_million(pricing.get("completion")),
                "latency_p50_ms": latency.get("p50"),
                "throughput_p50_tokens_per_second": throughput.get("p50"),
                "uptime_1d_percent": endpoint.get("uptime_last_1d"),
            })
        rows.sort(key=lambda row: (row["input_usd_per_million"] or 0) +
                  (row["output_usd_per_million"] or 0))
        result.append({"model": model, "eligible_endpoints": rows})
    print(json.dumps({
        "zdr_catalog_endpoints": result,
        "notice": "Lists ZDR-eligible endpoints only; it does not verify account or API-key ZDR enforcement.",
    }, indent=2))


def main():
    try:
        token = key()
        if len(sys.argv) > 1 and sys.argv[1] == "--zdr":
            print_zdr(sys.argv[2:], token)
            return 0
        if len(sys.argv) > 2:
            raise ValueError("Pass one model slug, or use --zdr with one or more model slugs.")
        model = sys.argv[1] if len(sys.argv) > 1 else "deepseek/deepseek-v4.1-flash"
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
