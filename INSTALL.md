# Installation & Setup

Tested on macOS (Apple Silicon) and Linux.

## 1. Python analysis tools
Python 3.9+ with scikit-learn (for the decision-tree baseline):
```bash
python3 -m pip install scikit-learn
```
`rule_validator.py`, `rule_suite_eval.py`, the shuffle controls, and the bootstrap
use only the standard library + the above.

## 2. tshark (pcap → CSV)
Needed only if you regenerate CSVs from raw JAMES pcaps.
```bash
# macOS
brew install wireshark          # provides tshark
# Debian/Ubuntu
sudo apt-get install tshark
```
Then:
```bash
python3 code/pcap_to_csv.py <received_traffic.pcap> data/james_<vantage>_recv2.csv 1
```

## 3. PSIMiner (the mining engine, GPL-3.0 — bundled under `third_party/psiminer/`)
An unmodified copy of PSIMiner's source is vendored in this repo (pinned to
upstream commit `b0d0316`; see `third_party/psiminer/UPSTREAM.md`). Build it:
```bash
cd third_party/psiminer && bash build.sh   # requires a C compiler, flex, bison
# produces build/psiMiner; copy it next to the configs, invoked as ./psiMiner <config>.conf
```
macOS deps: `xcode-select --install` (compiler), `brew install flex bison`.

## 4. (optional) LLM rule-miner baseline
`llm_rule_miner.py` calls the Anthropic API; set `ANTHROPIC_API_KEY`.
`llm_heldout_eval.py` re-scores fixed proposals with `rule_validator` and needs no key.

## 5. (optional) MAWI external-validity check
The natural-traffic scan (§ Discussion) downloads a WIDE MAWI trace; parallel
download is much faster:
```bash
brew install aria2
aria2c -x16 -s16 https://mawi.wide.ad.jp/mawi/samplepoint-F/2025/<YYYYMMDD>1400.pcap.gz
gunzip -c <file>.pcap.gz | tshark -r - -Y ipv6 -T fields -e ipv6.nxt | sort | uniq -c
```

## Quick check
```bash
python3 code/rule_validator.py data/james_ams_recv2.csv "!PLEN_MED" 0 4 "!HAS_FRAG_EH"
# expect correlation ~97% (coverage), support ~75%
```
