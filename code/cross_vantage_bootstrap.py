#!/usr/bin/env python3
"""Cross-vantage bootstrap CI on the multi-vantage correlation band.

Treats the 10 observed per-vantage correlations as a sample
from the population of plausible vantages, and reports the
B=10000 percentile CI for the mean.
"""
import random
import statistics
import sys

# Correlations from Table 1 (paper), in same order.
data = [
    ("fra", 98.89),
    ("nyc", 98.36),
    ("sgp", 97.21),
    ("blr", 94.91),
    ("lon", 94.74),
    ("mad", 94.38),
    ("eze", 94.37),
    ("tyo", 94.31),
    ("ams", 93.04),
    ("syd", 89.45),
]

corrs = [c for _, c in data]
n = len(corrs)
print(f"observed: n={n}, mean={statistics.mean(corrs):.2f}, "
      f"min={min(corrs):.2f}, max={max(corrs):.2f}, "
      f"sd={statistics.stdev(corrs):.2f}")

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
