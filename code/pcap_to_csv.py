#!/usr/bin/env python3
"""
Convert a pcap to a PSIMiner-ready CSV time series.

Schema (column order):
    t, nxt, plen, icmpv6_type, l4, iat, label

t           relative timestamp in seconds (column 1, as PSIMiner requires)
nxt         IPv6 Next Header value (-1 if not IPv6)
plen        IPv6 payload length in bytes (-1 if not IPv6)
icmpv6_type ICMPv6 type (-1 if not ICMPv6)
l4          layer-4 family encoded as int:
                6  TCP, 17 UDP, 58 ICMPv6, 60 DstOpts (when nxt=60), -1 other
iat         inter-arrival time in seconds since previous packet in this trace
label       provided as CLI arg, constant across the trace (the outcome class)

Usage: python3 pcap_to_csv.py <in.pcap> <out.csv> <label>
"""

import csv
import subprocess
import sys


def run_tshark(pcap):
    fields = ["frame.time_relative", "ipv6.nxt", "ipv6.plen",
              "icmpv6.type", "ipv6.hlim", "ipv6.flow"]
    cmd = ["tshark", "-r", pcap, "-T", "fields", "-E", "separator=,",
           "-E", "occurrence=f"]
    for f in fields:
        cmd.extend(["-e", f])
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return out.stdout.strip().splitlines()


def parse_int(x):
    if x == "" or x is None:
        return -1
    try:
        return int(x, 0) if x.startswith("0x") else int(x)
    except ValueError:
        return -1


def parse_float(x):
    if x == "" or x is None:
        return 0.0
    try:
        return float(x)
    except ValueError:
        return 0.0


def main(pcap, csv_out, label):
    rows = run_tshark(pcap)
    label = int(label)
    prev_t = None
    with open(csv_out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t", "nxt", "plen", "icmpv6_type", "l4", "iat",
                    "hlim", "flow", "label"])
        for line in rows:
            parts = line.split(",")
            while len(parts) < 6:
                parts.append("")
            t = parse_float(parts[0])
            nxt = parse_int(parts[1])
            plen = parse_int(parts[2])
            icmpv6_type = parse_int(parts[3])
            hlim = parse_int(parts[4])
            flow = parse_int(parts[5])
            if nxt == 58 or icmpv6_type >= 0:
                l4 = 58
            elif nxt == 6:
                l4 = 6
            elif nxt == 17:
                l4 = 17
            elif nxt == 60:
                l4 = 60
            else:
                l4 = -1
            iat = 0.0 if prev_t is None else max(0.0, t - prev_t)
            prev_t = t
            w.writerow([f"{t:.6f}", nxt, plen, icmpv6_type, l4,
                        f"{iat:.6f}", hlim, flow, label])


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
