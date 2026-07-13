#!/usr/bin/env python3
"""Row-permute predicate columns while keeping timestamps in place.

Inputs:  CSV with header t,nxt,plen,icmpv6_type,l4,iat,label
Output:  CSV in the same schema with the predicate block
         (nxt, plen, icmpv6_type, l4, iat) permuted across rows.
The label column is left as-is.
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

pred_cols = [1, 2, 3, 4, 5]
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
