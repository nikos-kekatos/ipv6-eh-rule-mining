#!/bin/bash
# Multi-bucket rule search across all six IPv6 EH targets, IPv6-only vocab.
# For each target we run PSIMiner (seqLength=4 -> up to 4 buckets), retrying
# past the known non-deterministic SIGSEGV, and keep the full ranked rule list.
set +e
BASE=james_ams_v3_tFRAG.conf
declare -A NAME=( [1]=HBH [2]=RT [3]=FRAG [4]=ESP [5]=AH [6]=DST )
echo "target,attempts,seconds,rc" > multibucket/runlog.csv
for t in 1 2 3 4 5 6; do
  conf="multibucket/t${NAME[$t]}.conf"
  cp "$BASE" "$conf"
  # set the target block: replace the "(3)" between 'targets\nbegin' and 'end'
  perl -0pi -e "s/targets\s*\nbegin\s*\n\(\d+\)\s*\nend/targets\nbegin\n($t)\nend/s" "$conf"
  ok=0
  for attempt in 1 2 3 4 5 6 7 8; do
    start=$SECONDS
    ./psiMiner "$conf" > "multibucket/t${NAME[$t]}.log" 2>&1
    rc=$?
    dur=$((SECONDS-start))
    asrt="multibucket/t${NAME[$t]}-assertions.txt"
    if [ $rc -eq 0 ] && [ -s "$asrt" ] && grep -q CORRELATION "$asrt"; then
      echo "${NAME[$t]},${attempt},${dur},0" >> multibucket/runlog.csv
      echo "[ok] ${NAME[$t]} in ${attempt} attempt(s), ${dur}s"
      ok=1; break
    fi
  done
  [ $ok -eq 0 ] && { echo "${NAME[$t]},8,NA,FAIL" >> multibucket/runlog.csv; echo "[FAIL] ${NAME[$t]}"; }
done
echo "=== DONE multibucket search ==="
