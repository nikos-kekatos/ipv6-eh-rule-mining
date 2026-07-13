#!/usr/bin/env python3
"""Row-permute predicate columns while keeping timestamps in place.

Inputs:  CSV with header t,nxt,plen,icmpv6_type,l4,iat,hlim,flow,label
Output:  CSV in the same schema with the predicate tuple
         (nxt, plen, hlim, flow) jointly permuted across rows.
The joint-row permutation keeps each (nxt,plen,hlim,flow) tuple intact
but reassigns whole tuples to new rows, preserving the within-tuple
joint distribution while destroying its alignment to time/label.
Other columns (icmpv6_type, l4, iat, label) are left as-is.
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
pred_cols = [1, 2, 6, 7]  # (nxt, plen, hlim, flow)
block = [[r[c] for c in pred_cols] for r in rows]
rng.shuffle(block)
for r, b in zip(rows, block):
    for c, v in zip(pred_cols, b):
        r[c] = v

with open(dst, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(header)
    w.writerows(rows)

print(f"wrote {dst} ({len(rows)} rows, seed={seed})")
