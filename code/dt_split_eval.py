#!/usr/bin/env python3
"""Rigorous train/test evaluation of the decision-tree baseline.

The prior baseline (exp/baseline_decision_tree.py) reported only training
accuracy (train == test == full data). A reviewer flagged the absence of a
train/test protocol. This script fixes that by reporting:

  0. Plain training accuracy (train == test == full)  -- reference,
     reproduces the paper's current 96.93% number.
  1. CHRONOLOGICAL holdout: first 70% of rows by time order (no shuffle)
     train, last 30% test.
  2. Stratified 5-fold cross-validation (shuffle=True, random_state=0):
     mean +/- SD test accuracy.

It also re-evaluates the CHRONOLOGICAL protocol with K-lag temporal features
(K = 1, 2, 4) to check whether lagged predicates change chronological test
accuracy.

All models: sklearn DecisionTreeClassifier(max_depth=5, random_state=0).
Positive class for P/R/F1 = HAS_FRAG_EH.

Reproducible: fixed random_state everywhere, no shuffling for the
chronological split. Run:  python3 dt_split_eval.py [csv]
"""
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score,
                             precision_recall_fscore_support)
from sklearn.model_selection import StratifiedKFold
from sklearn.tree import DecisionTreeClassifier

MAX_DEPTH = 5
RANDOM_STATE = 0

# IPv6-only predicate features, exactly as the paper uses them
# (see exp/james_ams_tFRAG.conf / exp/baseline_decision_tree.py).
EH_FLAGS = [
    ("HAS_HBH_EH", 0),
    ("HAS_RT_EH", 43),
    # HAS_FRAG_EH (nxt == 44) is the TARGET, excluded from features.
    ("HAS_ESP_EH", 50),
    ("HAS_AH_EH", 51),
    ("HAS_DST_EH", 60),
]

PREDS = [f for f, _ in EH_FLAGS] + [
    "PLEN_SMALL", "PLEN_MED", "PLEN_BIG", "PLEN_HUGE",
    "HLIM_LOW", "HLIM_HIGH", "FLOW_ZERO",
]


def bucketise(df):
    df = df.copy()
    for name, val in EH_FLAGS:
        df[name] = (df["nxt"] == val).astype(int)
    df["HAS_FRAG_EH"] = (df["nxt"] == 44).astype(int)   # target
    df["PLEN_SMALL"] = (df["plen"] <= 64).astype(int)
    df["PLEN_MED"] = (df["plen"] >= 128).astype(int)
    df["PLEN_BIG"] = (df["plen"] >= 512).astype(int)
    df["PLEN_HUGE"] = (df["plen"] >= 1280).astype(int)
    df["HLIM_LOW"] = (df["hlim"] <= 16).astype(int)
    df["HLIM_HIGH"] = (df["hlim"] >= 200).astype(int)
    df["FLOW_ZERO"] = (df["flow"] == 0).astype(int)
    return df


def new_clf():
    return DecisionTreeClassifier(max_depth=MAX_DEPTH,
                                  random_state=RANDOM_STATE)


def metrics(y_true, y_pred):
    acc = accuracy_score(y_true, y_pred)
    p, r, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", pos_label=1, zero_division=0)
    return acc, p, r, f1


def lagged_features(df, preds, K):
    """Feature matrix including lag-1..lag-K of each predicate.

    Closest analogue to a finite-window propositional fragment: the learner
    can express 'predicate held K positions ago', intervals are integer
    position counts. Lags are computed on the full time-ordered trace BEFORE
    any split, so the chronological split still sees only past context.
    """
    parts = [df[preds].values]
    for k in range(1, K + 1):
        parts.append(df[preds].shift(k).fillna(0).astype(int).values)
    return np.concatenate(parts, axis=1)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "james_ams_recv2.csv"
    df = pd.read_csv(src)
    df = bucketise(df)

    X = df[PREDS].values
    y = df["HAS_FRAG_EH"].values
    n = len(df)

    print("=" * 70)
    print("Decision-tree baseline: rigorous train/test evaluation")
    print("=" * 70)
    print(f"trace                : {src}")
    print(f"n_packets            : {n}")
    print(f"P(HAS_FRAG_EH)       : {y.mean():.4f}")
    print(f"model                : DecisionTreeClassifier("
          f"max_depth={MAX_DEPTH}, random_state={RANDOM_STATE})")
    print(f"features ({len(PREDS)})        : {PREDS}")
    print(f"positive class       : HAS_FRAG_EH (nxt == 44)")
    print()

    rows = []  # (protocol, train_acc, test_acc, P, R, F1)

    # ---- 0. Plain training accuracy (train == test == full) -------------
    clf = new_clf().fit(X, y)
    acc, p, r, f1 = metrics(y, clf.predict(X))
    rows.append(("train=test=full (ref)", acc, acc, p, r, f1))
    print("--- 0. Plain training accuracy (train == test == full) ---")
    print(f"    train_acc = test_acc = {acc:.4f}  "
          f"P={p:.4f}  R={r:.4f}  F1={f1:.4f}")
    print("    (reference; reproduces the paper's current 96.93% number)")
    print()

    # ---- 1. Chronological holdout: first 70% train, last 30% test -------
    cut = int(np.floor(0.70 * n))
    Xtr, Xte = X[:cut], X[cut:]
    ytr, yte = y[:cut], y[cut:]
    clf = new_clf().fit(Xtr, ytr)
    tr_acc = accuracy_score(ytr, clf.predict(Xtr))
    te_acc, p, r, f1 = metrics(yte, clf.predict(Xte))
    rows.append(("chronological 70/30", tr_acc, te_acc, p, r, f1))
    print("--- 1. Chronological holdout (first 70% train, last 30% test, "
          "no shuffle) ---")
    print(f"    train rows = {cut} (0..{cut - 1}),  "
          f"test rows = {n - cut} ({cut}..{n - 1})")
    print(f"    train P(pos)={ytr.mean():.4f}  test P(pos)={yte.mean():.4f}")
    print(f"    train_acc={tr_acc:.4f}  test_acc={te_acc:.4f}  "
          f"P={p:.4f}  R={r:.4f}  F1={f1:.4f}")
    print()

    # ---- 2. Stratified 5-fold CV (shuffle=True, random_state=0) ---------
    skf = StratifiedKFold(n_splits=5, shuffle=True,
                          random_state=RANDOM_STATE)
    fold_acc, fold_tr = [], []
    fold_p, fold_r, fold_f1 = [], [], []
    for tr_idx, te_idx in skf.split(X, y):
        clf = new_clf().fit(X[tr_idx], y[tr_idx])
        fold_tr.append(accuracy_score(y[tr_idx], clf.predict(X[tr_idx])))
        a, pp, rr, ff = metrics(y[te_idx], clf.predict(X[te_idx]))
        fold_acc.append(a)
        fold_p.append(pp)
        fold_r.append(rr)
        fold_f1.append(ff)
    fold_acc = np.array(fold_acc)
    print("--- 2. Stratified 5-fold CV (shuffle=True, random_state=0) ---")
    print("    per-fold test acc: " +
          "  ".join(f"{a:.4f}" for a in fold_acc))
    print(f"    mean test_acc = {fold_acc.mean():.4f} "
          f"+/- {fold_acc.std(ddof=0):.4f} (population SD)")
    print(f"    mean test_acc = {fold_acc.mean():.4f} "
          f"+/- {fold_acc.std(ddof=1):.4f} (sample SD, ddof=1)")
    rows.append(("stratified 5-fold CV",
                 np.mean(fold_tr), fold_acc.mean(),
                 np.mean(fold_p), np.mean(fold_r), np.mean(fold_f1)))
    print()

    # ---- Summary table --------------------------------------------------
    print("=" * 70)
    print("SUMMARY TABLE")
    print("=" * 70)
    hdr = f"{'protocol':<24}{'train_acc':>10}{'test_acc':>10}" \
          f"{'precision':>11}{'recall':>9}{'F1':>9}"
    print(hdr)
    print("-" * len(hdr))
    for name, tra, tea, p, r, f1 in rows:
        print(f"{name:<24}{tra:>10.4f}{tea:>10.4f}"
              f"{p:>11.4f}{r:>9.4f}{f1:>9.4f}")
    print()

    # ---- Lagged temporal features, chronological protocol ---------------
    print("=" * 70)
    print("K-LAG temporal features -- CHRONOLOGICAL 70/30 test accuracy")
    print("=" * 70)
    print(f"{'features':<20}{'train_acc':>10}{'test_acc':>10}"
          f"{'precision':>11}{'recall':>9}{'F1':>9}")
    print("-" * 69)
    base_te = None
    for K in (0, 1, 2, 4):
        XL = X if K == 0 else lagged_features(df, PREDS, K)
        Xtr, Xte = XL[:cut], XL[cut:]
        clf = new_clf().fit(Xtr, ytr)
        tra = accuracy_score(ytr, clf.predict(Xtr))
        tea, p, r, f1 = metrics(yte, clf.predict(Xte))
        if K == 0:
            base_te = tea
        label = "no lag (K=0)" if K == 0 else f"K={K} lag"
        print(f"{label:<20}{tra:>10.4f}{tea:>10.4f}"
              f"{p:>11.4f}{r:>9.4f}{f1:>9.4f}")
    print()
    print(f"note: baseline (K=0) chronological test_acc = {base_te:.4f}; "
          "compare rows above for the effect of K-lag features.")


if __name__ == "__main__":
    main()
