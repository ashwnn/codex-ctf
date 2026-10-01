#!/usr/bin/env python3
"""Replay one reviewed Tulip HTTP request to one exact allowlisted service URL.

The operator supplies the published target list and current flag metadata. This
tool performs one request, never submits, and stores captured values privately.
"""
import argparse
import datetime as dt
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

DROP_HEADERS = {"host", "content-length", "connection", "proxy-connection",
                "transfer-encoding"}
ID_RE = re.compile(r"^[A-Za-z0-9._~:-]{1,256}$")
UTC = dt.timezone.utc


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def normalize_target(value):
    parsed = urllib.parse.urlsplit(value.strip())
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname or
            parsed.username or parsed.password or parsed.query or parsed.fragment or
            parsed.path not in {"", "/"}):
        raise ValueError("target must be a base HTTP(S) URL without credentials or a path")
    if parsed.scheme == "http":
        if parsed.hostname == "localhost":
            pass
        else:
            try:
                address = ipaddress.ip_address(parsed.hostname)
            except ValueError:
                raise ValueError("plain HTTP is allowed only for loopback/private IP targets")
            if not (address.is_loopback or address.is_private or address.is_link_local):
                raise ValueError("plain HTTP is allowed only for loopback/private IP targets")
    host = parsed.hostname.lower()
    port = parsed.port
    netloc = "[%s]" % host if ":" in host else host
    if port is not None:
        netloc += ":%d" % port
    return urllib.parse.urlunsplit((parsed.scheme.lower(), netloc, "", "", ""))


def load_targets(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("published-targets file must be a regular local file")
    targets = set()
    for line in path.read_text().splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        targets.add(normalize_target(value))
    if not targets:
        raise ValueError("published-targets file contains no targets")
    return targets


def parse_request(raw, target, flag_id):
    if b"\r\n\r\n" in raw:
        head, body = raw.split(b"\r\n\r\n", 1)
        delimiter = b"\r\n"
    elif b"\n\n" in raw:
        head, body = raw.split(b"\n\n", 1)
        delimiter = b"\n"
    else:
        raise ValueError("request must contain a header/body separator")
    lines = head.split(delimiter)
    try:
        parts = lines[0].decode("ascii").split()
    except UnicodeDecodeError:
        raise ValueError("request line must be ASCII")
    if len(parts) != 3 or parts[2] not in {"HTTP/1.0", "HTTP/1.1"}:
        raise ValueError("expected one HTTP/1.x request line")
    method, path, _ = parts
    if method.upper() not in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}:
        raise ValueError("unsupported HTTP method")
    if not path.startswith("/") or path.startswith("//") or "#" in path:
        raise ValueError("request target must be an origin-form path")
    target_parts = urllib.parse.urlsplit(target)
    host = target_parts.hostname
    path = path.replace("{HOST}", host)
    if b"{FLAGID}" not in raw:
        raise ValueError("request template must contain {FLAGID}")
    encoded_id = flag_id.encode("ascii")
    path = path.replace("{FLAGID}", urllib.parse.quote(flag_id, safe="._~:-"))
    body = body.replace(b"{HOST}", host.encode("ascii"))
    body = body.replace(b"{FLAGID}", encoded_id)

    headers = {}
    for line in lines[1:]:
        if not line:
            continue
        name, sep, value = line.partition(b":")
        if not sep or name[:1] in b" \t":
            raise ValueError("malformed or folded HTTP header")
        try:
            key = name.decode("ascii").strip()
            text = value.decode("latin-1").strip()
        except UnicodeDecodeError:
            raise ValueError("malformed HTTP header")
        if not key or any(c in key for c in "\r\n") or any(c in text for c in "\r\n"):
            raise ValueError("malformed HTTP header")
        if key.lower() in DROP_HEADERS:
            continue
        text = text.replace("{HOST}", host).replace("{FLAGID}", flag_id)
        headers[key] = text
    return method.upper(), path, headers, body


def replay(raw, target, flag_id, flag_pattern, timeout=5, max_response=1048576):
    if not ID_RE.fullmatch(flag_id):
        raise ValueError("flag ID contains unsupported characters")
    method, path, headers, body = parse_request(raw, target, flag_id)
    url = target + path
    data = body if body else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        response = opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        payload = response.read(max_response + 1)
        status = response.code
    if len(payload) > max_response:
        raise ValueError("response exceeded the configured size limit")
    text = payload.decode("utf-8", errors="replace")
    return status, list(dict.fromkeys(match.group(0) for match in flag_pattern.finditer(text)))


def save_flags(inbox, flags, service, team, flag_id, source, expires_at):
    inbox = Path(inbox)
    if inbox.exists() and inbox.is_symlink():
        raise ValueError("flag inbox may not be a symlink")
    flags_dir = inbox.parent
    if flags_dir.exists() and flags_dir.is_symlink():
        raise ValueError("flags directory may not be a symlink")
    inbox.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(inbox, 0o700)
    name = "tulip-%s.jsonl" % uuid.uuid4().hex
    path = inbox / name
    entries = [{"flag": flag, "service": service, "team": team,
                "flag_id": flag_id, "source": source,
                **({"expires_at": expires_at} if expires_at else {})} for flag in flags]
    data = "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in entries)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(data)
    return path


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, help="private, reviewed raw HTTP request file")
    parser.add_argument("--published-targets", required=True, help="one published base URL per line")
    parser.add_argument("--target", required=True, help="exact base URL from --published-targets")
    parser.add_argument("--flag-id", required=True, help="one current public flag ID")
    parser.add_argument("--service", required=True)
    parser.add_argument("--team", required=True)
    parser.add_argument("--flag-regex", required=True, help="event-specific flag format")
    parser.add_argument("--source", required=True, help="finding/evidence reference, no request body")
    parser.add_argument("--expires-at", help="published timezone-aware expiry, if available")
    parser.add_argument("--timeout", type=float, default=5)
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", args.service):
            raise ValueError("invalid service name")
        if not args.team or len(args.team) > 128 or any(c.isspace() for c in args.team):
            raise ValueError("invalid team ID")
        if not args.source or len(args.source) > 256 or "\n" in args.source:
            raise ValueError("invalid source reference")
        if args.timeout <= 0 or args.timeout > 15:
            raise ValueError("timeout must be between 0 and 15 seconds")
        if args.expires_at:
            expiry = dt.datetime.fromisoformat(args.expires_at.replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                raise ValueError("expiry must include a timezone")
        target = normalize_target(args.target)
        if target not in load_targets(args.published_targets):
            raise ValueError("target is not an exact entry in the published-targets file")
        request_path = Path(args.request)
        if request_path.is_symlink() or not request_path.is_file():
            raise ValueError("request template must be a regular local file")
        if request_path.stat().st_mode & 0o077:
            raise ValueError("request template must have private file permissions")
        if request_path.stat().st_size > 65536:
            raise ValueError("request template exceeds 64 KiB")
        targets_path = Path(args.published_targets)
        if targets_path.stat().st_mode & 0o077:
            raise ValueError("published-targets file must have private file permissions")
        if len(args.flag_regex) > 512:
            raise ValueError("flag regex is too long")
        pattern = re.compile(args.flag_regex)
        if pattern.match(""):
            raise ValueError("flag regex must not match an empty value")
        status, flags = replay(request_path.read_bytes(), target, args.flag_id, pattern, args.timeout)
        if not flags:
            print("tulip-replay: one request completed with status %s; no flag captured" % status)
            return 1
        path = save_flags("flags/inbox", flags, args.service, args.team, args.flag_id,
                          args.source, args.expires_at)
        print("tulip-replay: status %s; captured %d value(s) to %s" % (status, len(flags), path))
        return 0
    except (OSError, ValueError, urllib.error.URLError, urllib.error.HTTPError):
        print("tulip-replay: request refused or failed; inspect local configuration and evidence", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
