#!/usr/bin/env python3
"""Independently permute each predicate column.

Destroys the within-row joint distribution: nxt is decoupled
from plen, from hlim, from flow. Tests whether the rule depends on
the FRAG-EH <-> PLEN_MED association at all.
"""
import csv
import random
import sys

src, dst, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
rng = random.Random(seed)

with open(src, newline="") as f:
    rd = csv.reader(f)
    header = next(rd)
    rows = list(rd)

# columns: t=0, nxt=1, plen=2, icmpv6_type=3, l4=4, iat=5,
#          hlim=6, flow=7, label=8
# Independently shuffle the predicate tuple (nxt, plen, hlim, flow).
for col in (1, 2, 6, 7):
    vals = [r[col] for r in rows]
    rng.shuffle(vals)
    for r, v in zip(rows, vals):
        r[col] = v

with open(dst, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(header)
    w.writerows(rows)

print(f"wrote {dst} ({len(rows)} rows, seed={seed}, independent shuffle)")
