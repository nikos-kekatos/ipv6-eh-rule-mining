#!/usr/bin/env python3
"""Validate a PSIMiner-style rule against a CSV.

A rule has the form: <antecedent> |=> ##[a:b] <consequent>
where antecedent / consequent are boolean expressions over the
predicate vocabulary defined here. The correlation metric is
PSIMiner's: it counts, over all rows where the antecedent
matches, the fraction whose ##[a:b] window contains a row
matching the consequent.

Predicate vocabulary (IPv6-header-only):
    HAS_HBH_EH, HAS_RT_EH, HAS_FRAG_EH, HAS_ESP_EH,
    HAS_AH_EH,  HAS_DST_EH,
    PLEN_SMALL, PLEN_MED, PLEN_BIG, PLEN_HUGE,
    HLIM_LOW,   HLIM_HIGH,
    FLOW_ZERO
"""
import argparse
import csv
import re
import sys
from bisect import bisect_left, bisect_right


PREDICATE_DEFS = {
    "HAS_HBH_EH":  lambda r: int(r["nxt"]) == 0,
    "HAS_RT_EH":   lambda r: int(r["nxt"]) == 43,
    "HAS_FRAG_EH": lambda r: int(r["nxt"]) == 44,
    "HAS_ESP_EH":  lambda r: int(r["nxt"]) == 50,
    "HAS_AH_EH":   lambda r: int(r["nxt"]) == 51,
    "HAS_DST_EH":  lambda r: int(r["nxt"]) == 60,
    # NB: PSIMiner predicates here are MONOTONIC (overlapping),
    # exactly as written in the .conf:  plen<=64 / plen>=128 /
    # plen>=512 / plen>=1280. A 1500-byte packet is PLEN_MED AND
    # PLEN_BIG AND PLEN_HUGE simultaneously.
    "PLEN_SMALL":  lambda r: int(r["plen"]) >= 0 and int(r["plen"]) <= 64,
    "PLEN_MED":    lambda r: int(r["plen"]) >= 128,
    "PLEN_BIG":    lambda r: int(r["plen"]) >= 512,
    "PLEN_HUGE":   lambda r: int(r["plen"]) >= 1280,
    "HLIM_LOW":    lambda r: int(r.get("hlim", -1)) >= 0 and
                              int(r.get("hlim", -1)) <= 16,
    "HLIM_HIGH":   lambda r: int(r.get("hlim", -1)) >= 200,
    "FLOW_ZERO":   lambda r: int(r.get("flow", -1)) == 0,
}


def parse_bool(expr, row):
    """Evaluate a boolean expression over PREDICATE_DEFS for a row."""
    e = expr.strip()
    if not e:
        return True
    # Replace predicate names with their truth values in this row.
    # Use word-boundary substitution to avoid touching && / ||.
    py = e
    py = py.replace("&&", " and ").replace("||", " or ").replace("!", " not ")
    for name, fn in PREDICATE_DEFS.items():
        py = re.sub(rf"\b{name}\b", "True" if fn(row) else "False", py)
    return bool(eval(py, {"__builtins__": {}}, {}))


def eval_rule(rows, antecedent_str, window_lo, window_hi, consequent_str):
    """Return (correlation_pct, support_pct, n_consequent, n_match).

    correlation = #(antecedent matches whose window contains a
                    consequent match) / #(consequent matches in trace)
                  * 100
    support     = #(antecedent matches) / N * 100
    """
    n = len(rows)
    ts = [float(r["t"]) for r in rows]

    ante_mask = [parse_bool(antecedent_str, r) for r in rows]
    cons_mask = [parse_bool(consequent_str, r) for r in rows]
    cons_times = [ts[i] for i in range(n) if cons_mask[i]]
    cons_times_sorted = sorted(cons_times)
    n_match_ante = sum(ante_mask)
    n_match_cons = sum(cons_mask)

    # For each consequent event, was there an antecedent match in
    # the preceding window [t - window_hi, t - window_lo]?
    n_explained = 0
    # We need fast lookup of antecedent times.
    ante_times = sorted([ts[i] for i in range(n) if ante_mask[i]])
    for tc in cons_times:
        lo = tc - window_hi
        hi = tc - window_lo
        l = bisect_left(ante_times, lo)
        r = bisect_right(ante_times, hi)
        if r > l:
            n_explained += 1

    corr = (n_explained / n_match_cons * 100.0) if n_match_cons else 0.0
    supp = (n_match_ante / n * 100.0) if n else 0.0
    return corr, supp, n_match_cons, n_match_ante


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("antecedent")
    ap.add_argument("window_lo", type=float)
    ap.add_argument("window_hi", type=float)
    ap.add_argument("consequent")
    args = ap.parse_args()

    with open(args.csv) as f:
        rows = list(csv.DictReader(f))

    corr, supp, n_c, n_a = eval_rule(
        rows, args.antecedent, args.window_lo,
        args.window_hi, args.consequent)
    print(f"rule:  {args.antecedent} |=> ##[{args.window_lo}:{args.window_hi}] {args.consequent}")
    print(f"  correlation = {corr:.4f}%   (n_explained / n_consequent_matches)")
    print(f"  support     = {supp:.4f}%   (n_antecedent_matches / N)")
    print(f"  n_consequent_matches = {n_c}")
    print(f"  n_antecedent_matches = {n_a}")


if __name__ == "__main__":
    main()
