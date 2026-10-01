#!/usr/bin/env python3
"""Local metadata extraction only. Codex handles interpretation and decisions."""
import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ("frame.number", "frame.time_epoch", "ip.src", "ipv6.src", "ip.dst", "ipv6.dst",
          "tcp.srcport", "tcp.dstport", "udp.srcport", "udp.dstport", "tcp.stream",
          "frame.len", "frame.cap_len")


def index(capture, port, output, max_packets, tshark=None):
    if not 1 <= port <= 65535 or max_packets <= 0:
        raise ValueError("Port must be 1..65535 and max-packets must be positive.")
    if not capture.is_file():
        raise ValueError("Capture does not exist.")
    if output.exists():
        raise ValueError("Output already exists; raw and derived evidence were preserved.")
    executable = tshark or shutil.which("tshark")
    if not executable:
        raise ValueError("Install Wireshark/tshark for this optional local evidence tool.")
    digest = hashlib.sha256()
    with capture.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    command = [executable, "-n", "-r", str(capture), "-c", str(max_packets),
               "-Y", "tcp.port == %d or udp.port == %d" % (port, port),
               "-T", "fields", "-E", "separator=/t", "-E", "occurrence=f"]
    for field in FIELDS:
        command.extend(["-e", field])
    output.mkdir(parents=True, mode=0o700)
    # Derived addresses and timing are private evidence even without payloads.
    output.chmod(0o700)
    table = output / "frames.tsv"
    # Only numeric protocol metadata/IP addresses, no payload-bearing fields.
    with table.open("w", newline="") as out:
        os.chmod(table, 0o600)
        csv.writer(out, delimiter="\t").writerow(FIELDS)
        process = subprocess.run(command, stdout=out, stderr=subprocess.PIPE, text=True)
    if process.returncode:
        # Do not expose malformed-packet diagnostic bytes in model output.
        table.unlink()
        output.rmdir()
        raise ValueError("tshark failed (exit %d); inspect the capture locally." % process.returncode)
    with table.open() as f:
        rows = sum(1 for _ in f) - 1
    metadata = {
        "capture_name": capture.name,
        "sha256": digest.hexdigest(),
        "indexed_at_utc": datetime.now(timezone.utc).isoformat(),
        "display_filter": "tcp.port == %d or udp.port == %d" % (port, port),
        "capture_scan_packet_limit": max_packets,
        "matching_frames": rows,
        "fields": FIELDS,
        "limits": "Index only; bounded scan of first N capture packets, not complete reassembly. "
                  "No paths, headers, bodies or flags. Review addresses/file names before sharing. "
                  "TLS, snaplen, packet loss and proxy/NAT require separate local inspection.",
    }
    provenance = output / "provenance.json"
    provenance.write_text(json.dumps(metadata, indent=2) + "\n")
    os.chmod(provenance, 0o600)
    return metadata


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("capture", type=Path)
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--max-packets", type=int, default=20000)
    args = p.parse_args()
    try:
        result = index(args.capture, args.port, args.output, args.max_packets)
        print("Indexed %d matching frames; metadata saved to %s" % (result["matching_frames"], args.output))
        return 0
    except (ValueError, OSError) as e:
        print("pcap-index: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
