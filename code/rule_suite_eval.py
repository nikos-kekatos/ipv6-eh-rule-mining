#!/usr/bin/env python3
"""Rule-family test suite.

Separates SAME-PACKET, CROSS-PACKET TEMPORAL, and SENDER-CONDITIONED
rules, reporting confidence AND coverage AND lift so that reversed
implications cannot look stronger than they are.

Metric conventions (all fractions unless noted):
  SAME-PACKET  A -> B  (A,B on same row):
      support     = P(A)
      confidence  = P(B|A)
      rev_conf    = P(A|B)                (reverse implication)
      lift        = P(A&B) / (P(A)P(B))
      prevalence  = P(B)
  TEMPORAL     A |=> [lo:hi] B:
      coverage    = frac of B-events with an A in preceding window
                    (== PSIMiner / eval_rule 'correlation')
      confidence  = frac of A-events followed by a B in the window
  Time windows are in seconds; packet-lag windows count rows.
"""
import csv
import os
from bisect import bisect_left, bisect_right

from rule_validator import PREDICATE_DEFS, parse_bool

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
MAIN_CSV = os.path.join(DATA, "james_ams_recv2.csv")
LABELED_CSV = os.path.join(DATA, "james_ams_labeled.csv")


# ---------------------------------------------------------------------------
# loading / masks
# ---------------------------------------------------------------------------
def load(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def mask(rows, expr):
    """Boolean mask for a predicate expression over PREDICATE_DEFS."""
    return [parse_bool(expr, r) for r in rows]


def col_mask(rows, colname):
    """Boolean mask from a 0/1 column (for SENT_* flags)."""
    return [int(r[colname]) == 1 for r in rows]


# ---------------------------------------------------------------------------
# SAME-PACKET metrics
# ---------------------------------------------------------------------------
def same_packet(a_mask, b_mask):
    n = len(a_mask)
    na = sum(a_mask)
    nb = sum(b_mask)
    nab = sum(1 for i in range(n) if a_mask[i] and b_mask[i])
    pa = na / n
    pb = nb / n
    pab = nab / n
    support = pa
    prevalence = pb
    confidence = (nab / na) if na else float("nan")
    rev_conf = (nab / nb) if nb else float("nan")
    lift = (pab / (pa * pb)) if (pa and pb) else float("nan")
    return dict(n=n, na=na, nb=nb, nab=nab, support=support,
                prevalence=prevalence, confidence=confidence,
                rev_conf=rev_conf, lift=lift)


# ---------------------------------------------------------------------------
# TEMPORAL metrics -- TIME BASED (seconds)
# ---------------------------------------------------------------------------
def temporal_time(rows, a_mask, b_mask, lo, hi):
    """Time-based coverage + forward confidence for A |=> ##[lo:hi] B.

    coverage:  for each B event at tc, exists A in [tc-hi, tc-lo]  (incl.)
    confidence: for each A event at ta, exists B in [ta+lo, ta+hi]  (incl.)
    """
    n = len(rows)
    ts = [float(r["t"]) for r in rows]
    a_times = sorted(ts[i] for i in range(n) if a_mask[i])
    b_times = sorted(ts[i] for i in range(n) if b_mask[i])
    na = len(a_times)
    nb = len(b_times)

    # coverage: B-events explained by a preceding A
    cov_hits = 0
    for tc in b_times:
        l = bisect_left(a_times, tc - hi)
        r = bisect_right(a_times, tc - lo)
        if r > l:
            cov_hits += 1
    coverage = (cov_hits / nb) if nb else float("nan")

    # forward confidence: A-events followed by a B
    conf_hits = 0
    for ta in a_times:
        l = bisect_left(b_times, ta + lo)
        r = bisect_right(b_times, ta + hi)
        if r > l:
            conf_hits += 1
    confidence = (conf_hits / na) if na else float("nan")

    return dict(na=na, nb=nb, cov_hits=cov_hits, conf_hits=conf_hits,
                coverage=coverage, confidence=confidence)


# ---------------------------------------------------------------------------
# TEMPORAL metrics -- PACKET LAG [1pkt:Kpkt]
# ---------------------------------------------------------------------------
def temporal_lag(a_mask, b_mask, klo, khi):
    """Packet-lag coverage + forward confidence.

    A at row i, B at some row j in [i+klo, i+khi].
    confidence: frac of A rows i with a B in [i+klo, i+khi]
    coverage:   frac of B rows j with an A in [j-khi, j-klo]
    """
    n = len(a_mask)
    a_idx = [i for i in range(n) if a_mask[i]]
    b_idx = [i for i in range(n) if b_mask[i]]
    na = len(a_idx)
    nb = len(b_idx)

    conf_hits = 0
    for i in a_idx:
        found = any(0 <= j < n and b_mask[j]
                    for j in range(i + klo, i + khi + 1))
        if found:
            conf_hits += 1
    confidence = (conf_hits / na) if na else float("nan")

    cov_hits = 0
    for j in b_idx:
        found = any(0 <= i < n and a_mask[i]
                    for i in range(j - khi, j - klo + 1))
        if found:
            cov_hits += 1
    coverage = (cov_hits / nb) if nb else float("nan")

    return dict(na=na, nb=nb, conf_hits=conf_hits, cov_hits=cov_hits,
                confidence=confidence, coverage=coverage)


# ---------------------------------------------------------------------------
# reporting helpers
# ---------------------------------------------------------------------------
def hdr(title):
    print("\n" + "=" * 74)
    print(title)
    print("=" * 74)


def f3(x):
    return "  nan" if x != x else f"{x:.3f}"


def report_same(name, res):
    print(f"\n  {name}")
    print(f"     support P(A)        = {f3(res['support'])}  "
          f"({res['na']}/{res['n']})")
    print(f"     prevalence P(B)     = {f3(res['prevalence'])}  "
          f"({res['nb']}/{res['n']})")
    print(f"     confidence P(B|A)   = {f3(res['confidence'])}  "
          f"({res['nab']}/{res['na']})")
    print(f"     rev_conf   P(A|B)   = {f3(res['rev_conf'])}  "
          f"({res['nab']}/{res['nb']})")
    print(f"     lift                = {f3(res['lift'])}")


def report_temporal(name, res, kind):
    print(f"\n  {name}   [{kind}]")
    print(f"     A-events={res['na']}  B-events={res['nb']}")
    print(f"     coverage  (B expl. by prior A) = {f3(res['coverage'])}  "
          f"({res['cov_hits']}/{res['nb']})")
    print(f"     confidence(A -> later B)       = {f3(res['confidence'])}  "
          f"({res['conf_hits']}/{res['na']})")


# ---------------------------------------------------------------------------
# main suite
# ---------------------------------------------------------------------------
def main():
    rows = load(MAIN_CSV)
    N = len(rows)
    print(f"main CSV: {MAIN_CSV}")
    print(f"rows: {N}")

    # cache commonly used masks
    M = {name: mask(rows, name) for name in
         ["HAS_FRAG_EH", "HAS_DST_EH", "HAS_RT_EH", "HAS_HBH_EH",
          "HAS_AH_EH", "HAS_ESP_EH", "PLEN_MED", "PLEN_SMALL",
          "HLIM_HIGH", "HLIM_LOW", "FLOW_ZERO"]}
    NFRAG = [not b for b in M["HAS_FRAG_EH"]]
    NDST = [not b for b in M["HAS_DST_EH"]]

    # ------------------------------------------------------------------
    hdr("FAMILY 1  --  SAME-PACKET  (A,B on same row; fractions over N)")
    report_same("HAS_FRAG_EH -> PLEN_MED",
                same_packet(M["HAS_FRAG_EH"], M["PLEN_MED"]))
    report_same("PLEN_MED -> HAS_FRAG_EH",
                same_packet(M["PLEN_MED"], M["HAS_FRAG_EH"]))
    report_same("HAS_DST_EH -> !HAS_FRAG_EH",
                same_packet(M["HAS_DST_EH"], NFRAG))
    report_same("HLIM_HIGH -> HAS_FRAG_EH",
                same_packet(M["HLIM_HIGH"], M["HAS_FRAG_EH"]))
    report_same("FLOW_ZERO -> HAS_FRAG_EH",
                same_packet(M["FLOW_ZERO"], M["HAS_FRAG_EH"]))

    # ------------------------------------------------------------------
    hdr("FAMILY 2  --  ZERO-DELAY COMPARISON  PLEN_MED => HAS_FRAG_EH")
    print("  Does the association survive excluding zero-delay / same packet?")
    report_temporal("PLEN_MED |=> ##[0:4s] HAS_FRAG_EH",
                    temporal_time(rows, M["PLEN_MED"], M["HAS_FRAG_EH"],
                                  0.0, 4.0), "time  0..4s (incl 0)")
    report_temporal("PLEN_MED |=> ##[0.001s:4s] HAS_FRAG_EH",
                    temporal_time(rows, M["PLEN_MED"], M["HAS_FRAG_EH"],
                                  0.001, 4.0), "time  .001..4s")
    report_temporal("PLEN_MED |=> [1pkt:4pkt] HAS_FRAG_EH",
                    temporal_lag(M["PLEN_MED"], M["HAS_FRAG_EH"], 1, 4),
                    "packet-lag 1..4")

    # ------------------------------------------------------------------
    hdr("FAMILY 3  --  CROSS-PACKET TEMPORAL (packet-lag, strictly positive)")
    report_temporal("HAS_FRAG_EH |=> [1pkt:4pkt] HAS_FRAG_EH",
                    temporal_lag(M["HAS_FRAG_EH"], M["HAS_FRAG_EH"], 1, 4),
                    "packet-lag 1..4")
    report_temporal("HAS_DST_EH |=> [1pkt:8pkt] HAS_FRAG_EH",
                    temporal_lag(M["HAS_DST_EH"], M["HAS_FRAG_EH"], 1, 8),
                    "packet-lag 1..8")
    report_temporal("!HAS_FRAG_EH |=> [1pkt:4pkt] !HAS_FRAG_EH",
                    temporal_lag(NFRAG, NFRAG, 1, 4), "packet-lag 1..4")

    # ------------------------------------------------------------------
    hdr("FAMILY 4  --  TRANSITION / EXCLUSION (time-based ##[0:4s])")
    report_temporal("HAS_DST_EH |=> ##[0:4s] !HAS_FRAG_EH",
                    temporal_time(rows, M["HAS_DST_EH"], NFRAG, 0.0, 4.0),
                    "time 0..4s")
    report_temporal("HAS_RT_EH |=> ##[0:4s] !HAS_DST_EH",
                    temporal_time(rows, M["HAS_RT_EH"], NDST, 0.0, 4.0),
                    "time 0..4s")

    # ------------------------------------------------------------------
    hdr("FAMILY 5  --  SENDER-CONDITIONED (on IN_WINDOW rows of labeled CSV)")
    lrows_all = load(LABELED_CSV)
    lrows = [r for r in lrows_all if int(r["IN_WINDOW"]) == 1]
    print(f"  labeled CSV: {LABELED_CSV}")
    print(f"  IN_WINDOW rows used: {len(lrows)} / {len(lrows_all)}")
    print("  RECEIVED_X = nxt-based EH flag on the SAME row.")
    print("  (same-packet metrics restricted to IN_WINDOW; coverage = P(A|B))")

    def sender_rule(name, sent_col, recv_expr):
        a = col_mask(lrows, sent_col)
        b = mask(lrows, recv_expr)
        res = same_packet(a, b)
        print(f"\n  {name}")
        print(f"     support   P(SENT)        = {f3(res['support'])}  "
              f"({res['na']}/{res['n']})")
        print(f"     confidence P(RECV|SENT)  = {f3(res['confidence'])}  "
              f"({res['nab']}/{res['na']})")
        print(f"     coverage  P(SENT|RECV)   = {f3(res['rev_conf'])}  "
              f"({res['nab']}/{res['nb']})")
        print(f"     prevalence P(RECV)       = {f3(res['prevalence'])}  "
              f"({res['nb']}/{res['n']})")
        print(f"     lift                     = {f3(res['lift'])}")

    sender_rule("SENT_FRAG -> RECEIVED_FRAG", "SENT_FRAG", "HAS_FRAG_EH")
    sender_rule("SENT_DST  -> RECEIVED_DST",  "SENT_DST",  "HAS_DST_EH")
    sender_rule("SENT_RT   -> RECEIVED_RT",   "SENT_RT",   "HAS_RT_EH")
    sender_rule("SENT_HBH  -> RECEIVED_HBH",  "SENT_HBH",  "HAS_HBH_EH")
    sender_rule("SENT_HBH  -> !RECEIVED_HBH (loss)", "SENT_HBH", "!HAS_HBH_EH")
    sender_rule("SENT_DST  -> RECEIVED_FRAG (transform)", "SENT_DST",
                "HAS_FRAG_EH")

    # ------------------------------------------------------------------
    hdr("FAMILY 6  --  NEGATIVE CONTROLS (packet-lag; expect ~prevalence)")
    for name, a, b, kb in [
        ("PLEN_SMALL |=> [1pkt:4pkt] HAS_HBH_EH", "PLEN_SMALL",
         "HAS_HBH_EH", "HAS_HBH_EH"),
        ("FLOW_ZERO  |=> [1pkt:4pkt] HAS_AH_EH", "FLOW_ZERO",
         "HAS_AH_EH", "HAS_AH_EH"),
        ("HLIM_LOW   |=> [1pkt:4pkt] HAS_ESP_EH", "HLIM_LOW",
         "HAS_ESP_EH", "HAS_ESP_EH"),
    ]:
        res = temporal_lag(M[a], M[b], 1, 4)
        prev = sum(M[kb]) / N
        report_temporal(name, res, "packet-lag 1..4")
        print(f"     prevalence P(B)                = {f3(prev)}  "
              f"(baseline: a B in any 4-pkt window ~ 1-(1-p)^4 "
              f"= {1-(1-prev)**4:.3f})")


if __name__ == "__main__":
    main()
