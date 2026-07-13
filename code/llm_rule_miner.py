#!/usr/bin/env python3
"""LLM rule-miner baseline.

Prompts an LLM with the same predicate vocabulary PSIMiner is
given, plus a 200-row uniform sample from the AMS receiver CSV,
and asks it to propose rules of the form
    <antecedent> |=> ##[a:b] HAS_FRAG_EH
in a strict JSON schema. Each proposed rule is then validated
against the full AMS CSV using rule_validator.eval_rule().

Usage:
    ANTHROPIC_API_KEY=sk-... python3 llm_rule_miner.py \\
        --csv james_ams_recv2.csv --runs 3
"""
import argparse
import csv
import json
import os
import random
import sys
import textwrap

try:
    from anthropic import Anthropic   # pip install anthropic
except ImportError:
    Anthropic = None

from rule_validator import eval_rule


PREDICATE_DOC = textwrap.dedent("""\
    Vocabulary (all are boolean predicates over an IPv6 packet):
        HAS_HBH_EH    Hop-by-Hop Options EH present  (nxt == 0)
        HAS_RT_EH     Routing EH present             (nxt == 43)
        HAS_FRAG_EH   Fragment EH present            (nxt == 44)
        HAS_ESP_EH    ESP EH present                 (nxt == 50)
        HAS_AH_EH     Authentication EH present      (nxt == 51)
        HAS_DST_EH    Destination Options EH         (nxt == 60)
        PLEN_SMALL    IPv6 Payload Length <= 64
        PLEN_MED      IPv6 Payload Length >= 128     (monotonic)
        PLEN_BIG      IPv6 Payload Length >= 512     (monotonic)
        PLEN_HUGE     IPv6 Payload Length >= 1280    (monotonic)
        HLIM_LOW      IPv6 Hop Limit <= 16
        HLIM_HIGH     IPv6 Hop Limit >= 200
        FLOW_ZERO     IPv6 Flow Label == 0

    Boolean operators: && (and), || (or), ! (not).

    Rule template:
        <antecedent boolean expression>
        |=> ##[a:b] <consequent boolean expression>

    where a and b are non-negative real numbers in seconds and
    a <= b. ##[a:b] is the metric-temporal-logic ``eventually''
    operator: the consequent must hold at some time in
    [t + a, t + b] after the antecedent at time t.
    """)


PROMPT = textwrap.dedent("""\
    You are a network-analysis specification miner.

    {predicate_doc}

    The target predicate is HAS_FRAG_EH (IPv6 Fragment Extension
    Header present in the packet).

    Below is a uniform random sample of {n_sample} rows from an
    Internet-scale IPv6 packet capture (single receiver vantage,
    {n_total} rows total in the full trace).

    {sample_csv}

    Propose between 1 and 3 candidate rules of the form
        antecedent |=> ##[a:b] HAS_FRAG_EH
    or
        antecedent |=> ##[a:b] !HAS_FRAG_EH
    that you believe will have high correlation on the full
    trace. Use only the predicate vocabulary above. Keep each
    antecedent short (<=4 conjuncts).

    Reply with strict JSON of the form
        {{ "rules": [
            {{"antecedent": "...", "window_lo": 0.0, "window_hi": 4.0,
              "consequent": "HAS_FRAG_EH" or "!HAS_FRAG_EH"}}, ...
        ] }}
    and nothing else.
    """)


def sample_rows(rows, k, seed):
    rng = random.Random(seed)
    return rng.sample(rows, min(k, len(rows)))


def call_llm(prompt, model="claude-opus-4-8", temperature=0.7):
    if Anthropic is None:
        raise RuntimeError("anthropic SDK not installed; "
                           "pip install anthropic")
    client = Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def parse_response(text):
    # Tolerate code-fence wrappers around the JSON.
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`").lstrip("json").strip()
    return json.loads(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--n_sample", type=int, default=200)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()

    with open(args.csv) as f:
        rows = list(csv.DictReader(f))

    headers = list(rows[0].keys())

    for run in range(args.runs):
        sampled = sample_rows(rows, args.n_sample, args.seed + run)
        sample_csv = ",".join(headers) + "\n" + "\n".join(
            ",".join(r[h] for h in headers) for r in sampled)
        prompt = PROMPT.format(
            predicate_doc=PREDICATE_DOC,
            n_sample=len(sampled),
            n_total=len(rows),
            sample_csv=sample_csv,
        )
        try:
            text = call_llm(prompt)
        except Exception as e:
            print(f"[run {run}] LLM call failed: {e}", file=sys.stderr)
            continue
        try:
            obj = parse_response(text)
        except Exception as e:
            print(f"[run {run}] could not parse LLM response: {e}",
                  file=sys.stderr)
            print(text, file=sys.stderr)
            continue
        for i, r in enumerate(obj.get("rules", [])):
            corr, supp, _, _ = eval_rule(
                rows, r["antecedent"], r["window_lo"],
                r["window_hi"], r["consequent"])
            print(f"[run {run}.{i}]  "
                  f"{r['antecedent']} |=> "
                  f"##[{r['window_lo']}:{r['window_hi']}] "
                  f"{r['consequent']}   "
                  f"corr={corr:.2f}%  supp={supp:.2f}%")


if __name__ == "__main__":
    main()
