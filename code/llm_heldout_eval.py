#!/usr/bin/env python3
"""Held-out validation of the LLM rule-miner baseline.

A reviewer noted that the LLM baseline validated its proposed rules
on the FULL AMS trace, even though 200 rows of that trace (per seed,
seeds 2026/2027/2028) were shown to the LLM to generate the proposals.
This script re-validates each proposed rule on the HELD-OUT COMPLEMENT
= full trace MINUS the union of the three 200-row samples, and reports
it alongside the full-trace numbers so we can show held-out validity.

The three samples are reconstructed EXACTLY as llm_rule_miner.py draws
them: for seed in (2026, 2027, 2028), random.Random(seed).sample(rows, 200).
random.sample's selection depends only on the population size, so the
positional indices it selects are identical whether we sample the row
dicts or an index range of the same length; we sample indices to build
the complement unambiguously (robust to any duplicate rows).
"""
import csv
import os
import random

from rule_validator import eval_rule

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "james_ams_recv2.csv")
SEEDS = (2026, 2027, 2028)
N_SAMPLE = 200

# (antecedent, window_lo, window_hi, consequent)
RULES = [
    ("PLEN_MED",              0.0, 4.0, "HAS_FRAG_EH"),
    ("HLIM_HIGH",             0.0, 2.0, "HAS_FRAG_EH"),
    ("PLEN_BIG",              0.0, 4.0, "HAS_FRAG_EH"),
    ("PLEN_MED && HLIM_HIGH", 0.0, 2.0, "HAS_FRAG_EH"),
    ("HAS_DST_EH",            0.0, 4.0, "HAS_FRAG_EH"),
    ("!PLEN_MED",             0.0, 4.0, "!HAS_FRAG_EH"),  # PSIMiner ref
]


def main():
    with open(CSV_PATH) as f:
        rows = list(csv.DictReader(f))
    n = len(rows)

    # Reconstruct the union of the three 200-row training samples by index.
    sampled_idx = set()
    for seed in SEEDS:
        sampled_idx.update(
            random.Random(seed).sample(range(n), min(N_SAMPLE, n)))

    heldout = [rows[i] for i in range(n) if i not in sampled_idx]

    print(f"full trace rows          : {n}")
    print(f"union of 3x200 samples   : {len(sampled_idx)} unique rows")
    print(f"held-out complement rows : {len(heldout)}")
    print()

    hdr = (f"{'rule':<26} {'corr_full':>10} {'corr_heldout':>13} "
           f"{'supp_full':>10} {'supp_heldout':>13}")
    print(hdr)
    print("-" * len(hdr))

    for ante, lo, hi, cons in RULES:
        cf, sf, _, _ = eval_rule(rows, ante, lo, hi, cons)
        ch, sh, _, _ = eval_rule(heldout, ante, lo, hi, cons)
        label = f"{ante} |=> {cons}"
        if len(label) > 25:
            label = label[:25]
        print(f"{label:<26} {cf:>9.2f}% {ch:>12.2f}% "
              f"{sf:>9.2f}% {sh:>12.2f}%")


if __name__ == "__main__":
    main()
