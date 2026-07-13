#!/usr/bin/env python3
"""Sklearn decision-tree baseline on the AMS receiver CSV.

The point is not to beat PSIMiner on accuracy; it is to make
explicit what a finite-window propositional learner produces
on the same input. We bucketise using the same thresholds as
the PSIMiner conf and train a small decision tree against
HAS_FRAG_EH. We compare:
  - sklearn DT: per-row, no notion of inter-event interval
  - sklearn DT with K-row context window (lagged features):
    closest analogue to NetNomos's finite-window Gamma
"""
import csv
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, classification_report,
                              precision_recall_fscore_support)
from sklearn.tree import DecisionTreeClassifier, export_text


def bucketise(df):
    df = df.copy()
    # PSIMiner-equivalent predicates (see example_frag.conf).
    df["HAS_HBH_EH"]    = (df["nxt"] == 0).astype(int)
    df["HAS_RT_EH"]     = (df["nxt"] == 43).astype(int)
    df["HAS_FRAG_EH"]   = (df["nxt"] == 44).astype(int)
    df["HAS_ESP_EH"]    = (df["nxt"] == 50).astype(int)
    df["HAS_AH_EH"]     = (df["nxt"] == 51).astype(int)
    df["HAS_DST_EH"]    = (df["nxt"] == 60).astype(int)
    df["PLEN_SMALL"]    = (df["plen"] <= 64).astype(int)
    df["PLEN_MED"]      = ((df["plen"] >= 128) & (df["plen"] < 512)).astype(int)
    df["PLEN_BIG"]      = ((df["plen"] >= 512) & (df["plen"] < 1280)).astype(int)
    df["PLEN_HUGE"]     = (df["plen"] >= 1280).astype(int)
    if "hlim" in df.columns:
        df["HLIM_LOW"]  = (df["hlim"] <= 16).astype(int)
        df["HLIM_HIGH"] = (df["hlim"] >= 200).astype(int)
    if "flow" in df.columns:
        df["FLOW_ZERO"] = (df["flow"] == 0).astype(int)
    return df


PREDS = ["HAS_HBH_EH", "HAS_RT_EH", "HAS_ESP_EH",
         "HAS_AH_EH", "HAS_DST_EH",
         "PLEN_SMALL", "PLEN_MED", "PLEN_BIG", "PLEN_HUGE",
         "HLIM_LOW", "HLIM_HIGH", "FLOW_ZERO"]


def fit_dt(X, y, max_depth, label):
    clf = DecisionTreeClassifier(max_depth=max_depth, random_state=0)
    clf.fit(X, y)
    yp = clf.predict(X)
    acc = accuracy_score(y, yp)
    p, r, f1, _ = precision_recall_fscore_support(y, yp, average="binary",
                                                   zero_division=0)
    n_leaves = clf.get_n_leaves()
    print(f"[{label}] depth<={max_depth}  acc={acc:.4f}  "
          f"P={p:.4f}  R={r:.4f}  F1={f1:.4f}  leaves={n_leaves}")
    return clf


def lagged_features(df, preds, K):
    """Build a feature matrix that includes lag-1..lag-K of each predicate.

    This is the closest analogue to NetNomos's finite-window propositional
    fragment: the learner can express 'predicate held K positions ago' but
    intervals are integer position counts, not data-refined real-time
    bounds.
    """
    parts = [df[preds].values]
    names = list(preds)
    for k in range(1, K + 1):
        lagged = df[preds].shift(k).fillna(0).astype(int).values
        parts.append(lagged)
        names.extend([f"{p}_lag{k}" for p in preds])
    X = np.concatenate(parts, axis=1)
    return X, names


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "james_ams_recv.csv"
    df = pd.read_csv(src)
    df = bucketise(df)

    X0 = df[PREDS].values
    y  = df["HAS_FRAG_EH"].values
    print(f"trace={src}  n_packets={len(df)}  "
          f"target prevalence P(HAS_FRAG_EH)={y.mean():.4f}")
    print()

    print("=== per-row DT (no temporal context) ===")
    clf = fit_dt(X0, y, max_depth=3, label="DT-d3")
    print(export_text(clf, feature_names=PREDS, max_depth=3))

    fit_dt(X0, y, max_depth=5, label="DT-d5")
    fit_dt(X0, y, max_depth=10, label="DT-d10")
    print()

    for K in (1, 2, 4, 8):
        XL, names = lagged_features(df, PREDS, K)
        fit_dt(XL, y, max_depth=5, label=f"DT-d5,K={K}")
    print()
    print("note: lagged DT depth and K simulate NetNomos's finite-window "
          "Gamma; intervals are integer positions, not the data-refined "
          "real-time [a:b] of PSIMiner.")


if __name__ == "__main__":
    main()
