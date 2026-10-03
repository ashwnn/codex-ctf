#!/usr/bin/env python3
"""Opt-in JSON HTTP adapter. Configure from real API docs, not Rules.pdf guesses.

Reads .runtime/flags/submission.json (or CTF_SUBMISSION_CONFIG) locally. Contract:
{"url": "https://...", "token_file": "...", "flags_field": "flags",
 "results_field": "results", "flag_field": "flag", "status_field": "status",
 "status_map": {"actual API label": "accepted"}, "timeout": 10}
POSTs a list of flag strings; expects per-flag receipts with mapped statuses.
Use a custom adapter if the real event uses any other request/response contract.
"""
import ipaddress
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

STATES = {"accepted", "duplicate", "rejected", "expired", "retry", "uncertain"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate(config):
    if not isinstance(config, dict) or not isinstance(config.get("url"), str):
        raise ValueError("Missing endpoint")
    url = urllib.parse.urlsplit(config["url"])
    if not url.hostname or url.username or url.password or url.fragment:
        raise ValueError("Invalid endpoint")
    if url.scheme not in {"https", "http"}:
        raise ValueError("Unsupported endpoint scheme")
    if url.scheme == "http" and not (
            config.get("allow_plain_http") is True
            and _private_plain_http(url.hostname)):
        raise ValueError("Plain HTTP requires a loopback/private-network host opt-in")
    fields = ("flags_field", "results_field", "flag_field", "status_field")
    if any(key in config and not isinstance(config[key], str) for key in fields):
        raise ValueError("Invalid field name")
    mapping = config.get("status_map", {})
    if not isinstance(mapping, dict) or not mapping or any(
            not isinstance(key, str) or value not in STATES for key, value in mapping.items()):
        raise ValueError("Invalid status mapping")
    if "timeout" in config and (type(config["timeout"]) not in (int, float) or config["timeout"] <= 0):
        raise ValueError("Invalid timeout")
    if config.get("token_file"):
        path = Path(config["token_file"])
        if path.stat().st_mode & 0o077 or not path.read_text().strip():
            raise ValueError("Token file must be private and nonempty")


def _private_plain_http(hostname):
    # Plain HTTP is only acceptable for a loopback or private-network literal.
    if hostname == "localhost":
        return True
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return address.is_loopback or address.is_private or address.is_link_local


def run(payload, config):
    validate(config)
    entries = payload["flags"]
    flags = {e["flag"]: e["id"] for e in entries}
    if len(flags) != len(entries):
        raise ValueError("Duplicate batch")
    headers = {"Content-Type": "application/json"}
    if config.get("token_file"):
        path = Path(config["token_file"])
        if path.stat().st_mode & 0o077:
            raise ValueError("Token file must be private")
        headers["Authorization"] = "Bearer " + path.read_text().strip()
    body = json.dumps({config.get("flags_field", "flags"): list(flags)}).encode()
    request = urllib.request.Request(config["url"], data=body, headers=headers, method="POST")
    # Do not use system HTTP proxies or follow redirects with flags/credentials.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=config.get("timeout", 10)) as response:
            raw = response.read(1048577)
            if len(raw) > 1048576:
                raise ValueError("Response too large")
    except urllib.error.HTTPError as exc:
        # Documented request rejection: stop, require review and a new release.
        state = "retry" if exc.code in {401, 403, 429} else "uncertain"
        exc.close()
        return {"results": [{"id": e["id"], "status": state} for e in entries]}
    response = json.loads(raw)
    receipts = response[config.get("results_field", "results")]
    results = []
    seen = set()
    for receipt in receipts:
        flag = receipt[config.get("flag_field", "flag")]
        state = config["status_map"].get(receipt[config.get("status_field", "status")], "uncertain")
        if flag not in flags or flag in seen or state not in STATES:
            raise ValueError("Unmatched or invalid receipt")
        seen.add(flag)
        results.append({"id": flags[flag], "status": state})
    return {"results": results}


def main():
    try:
        path = Path(os.environ.get("CTF_SUBMISSION_CONFIG", ".runtime/flags/submission.json"))
        if path.stat().st_mode & 0o077:
            raise ValueError("Configuration must be private")
        config = json.loads(path.read_text())
        validate(config)
        if sys.argv[1:] == ["--check"]:
            print('{"ready":true}')
            return 0
        if sys.argv[1:]:
            raise ValueError("Unknown option")
        result = run(json.load(sys.stdin), config)
        print(json.dumps(result))
        return 0
    except Exception:
        # Never emit secret-bearing HTTP responses, request strings or tracebacks.
        print("submission adapter failed; inspect configuration locally", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
