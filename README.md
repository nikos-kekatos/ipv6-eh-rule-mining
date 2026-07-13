# Explainable Rule Mining of IPv6 Extension-Header Presence Patterns

Reproducibility artifact for the IEEE CSR 2026 paper *"Explainable Rule Mining of
IPv6 Extension-Header Presence Patterns from Paired-Vantage Captures."*

The paper studies an explainable pipeline that mines short, human-readable timed
temporal-logic rules from IPv6 packet captures (via **PSIMiner**), and contributes
(i) a **negative-control protocol** (joint-row permutation, independent-column
shuffle, lag-augmented decision-tree cross-check) that diagnoses whether a mined
"temporal" rule is genuine cross-packet dynamics or within-packet co-occurrence,
and (ii) a sender-conditioned per-family **EH-retention measurement**. The headline
result is a **controlled negative finding**: on the JAMES paired-vantage dataset the
portable Fragment-EH rule is a within-packet, near-definitional co-occurrence, so
the temporal-logic machinery is inert on this corpus.

## What's here

```
code/     analysis scripts (parsing, mining configs, controls, baselines)
data/     21 per-vantage receiver CSVs derived from the JAMES dataset
results/  reproducible outputs (ablation grid, 21-vantage rule table)
```

### `code/`
| file | purpose |
|---|---|
| `pcap_to_csv.py` | project a `.pcap`/`.pcapng` to the per-packet IPv6-header CSV schema |
| `rule_validator.py` | deterministic validator for `<antecedent> \|=> ##[a:b] <consequent>` rules (coverage/confidence) |
| `example_frag.conf` | example PSIMiner config (IPv6-only vocabulary, target `HAS_FRAG_EH`) |
| `run_ablation_1d_ipv6only.sh` | one-dimensional hyperparameter ablation |
| `shuffle_predicates.py` / `shuffle_independent.py` | joint-row permutation / independent-column shuffle controls |
| `baseline_decision_tree.py`, `dt_split_eval.py` | decision-tree baseline + chronological train/test protocol |
| `llm_rule_miner.py`, `llm_heldout_eval.py` | LLM rule-miner baseline + held-out validation |
| `rule_suite_eval.py` | the RS1–RS5 rule-taxonomy suite (coverage/confidence/lift, ordered vs permuted) |
| `cross_vantage_bootstrap.py` | bootstrap CI over per-vantage correlations |

## Data provenance

- **`data/*.csv`** are per-packet projections of the receiver `received_traffic.pcap`
  captures from the **JAMES** dataset (Léas, Iurman, Vyncke, Donnet, *IMC 2022*;
  Apache-2.0), <https://gitlab.uliege.be/Benoit.Donnet/james>. Columns:
  `t,nxt,plen,icmpv6_type,l4,iat,hlim,flow,label`. Raw pcaps are **not** redistributed
  here; regenerate with `pcap_to_csv.py` from the JAMES release if desired.
- The mining engine **PSIMiner** (Bruto da Costa & Dasgupta, JAIR 2021; GPL-3.0) is
  **vendored unmodified** under [`third_party/psiminer/`](third_party/psiminer/)
  (pinned to upstream commit `b0d0316`); build it from there (see `INSTALL.md`).
  It remains a separate GPL-3.0 work; the MIT scripts invoke its binary as a
  separate program. Upstream: <https://github.com/antoniobruto/PSIMiner>.

## Reproduce

See [`INSTALL.md`](INSTALL.md) for dependencies. Then, e.g.:

```bash
# validate the headline rule on the Amsterdam receiver
python3 code/rule_validator.py data/james_ams_recv2.csv "!PLEN_MED" 0 4 "!HAS_FRAG_EH"

# the RS1-RS5 rule taxonomy (coverage/confidence/lift, ordered vs permuted)
python3 code/rule_suite_eval.py            # prints the RS1-RS6 suite to stdout

# hole-free 1-D ablation (needs the PSIMiner binary on PATH as ./psiMiner)
bash code/run_ablation_1d_ipv6only.sh
```

## Citing

If you use this artifact, please cite the paper and the JAMES dataset.

## Additional controls (this revision)

```bash
# RS2 permutation delta: is the positive-delay MED=>FRAG score within-packet or probe-burst?
python3 code/rs2_permutation_delta.py            # ordered 79.2% -> permuted 59.3% (base rate)

# positive control: protocol correctly FLAGS a genuine cross-packet rule
python3 code/positive_control.py                 # synthetic 2-lag rule 99.99% -> 59.0% under permutation

# multi-bucket search across the six EH targets (needs ./psiMiner + base_frag.conf)
bash  code/multibucket/run_multibucket.sh
python3 code/multibucket/parse_multibucket.py    # best per bucket-count: 1->93.0%, 2->24.8%, 3->2.3%
```
`results/` holds the regenerated snapshots (per-target assertions, run timings,
and the MAWI 2025-12-31 IPv6 next-header distribution).
