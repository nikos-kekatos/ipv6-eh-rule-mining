#!/usr/bin/env python3
"""Cross-vantage bootstrap CI on the multi-vantage correlation band.

Treats the 21 observed per-vantage correlations (results/james21_multivantage.csv)
as a sample from the population of plausible vantages, and reports the
B=10000 percentile CI for the mean. A fixed RNG seed makes it reproducible.
"""
import csv
import os
import random
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(os.path.dirname(HERE), "results",
                        "james21_multivantage.csv")


def load_corrs(path):
    """Read the per-vantage correlations (percent) from the multi-vantage CSV."""
    corrs = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            c = (row.get("corr") or "").strip()
            if not c:            # skip sentinel rows (e.g. JAMES21_DONE)
                continue
            try:
                corrs.append(float(c))
            except ValueError:
                continue
    return corrs


corrs = load_corrs(CSV_PATH)
n = len(corrs)
print(f"observed: n={n}, mean={statistics.mean(corrs):.2f}, "
      f"min={min(corrs):.2f}, max={max(corrs):.2f}, "
      f"sd={statistics.pstdev(corrs):.2f}")

rng = random.Random(2026)
B = 10000
boot_means = []
for _ in range(B):
    sample = [rng.choice(corrs) for _ in range(n)]
    boot_means.append(sum(sample) / n)
boot_means.sort()
lo = boot_means[int(0.025 * B)]
hi = boot_means[int(0.975 * B)]
print(f"bootstrap 95% CI on mean: [{lo:.2f}, {hi:.2f}]")
print(f"bootstrap SE: {statistics.stdev(boot_means):.2f}")
