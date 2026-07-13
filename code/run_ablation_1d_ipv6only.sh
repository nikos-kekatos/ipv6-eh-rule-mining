#!/bin/bash
# Clean 1-D ablation under the STRICT IPv6-only vocabulary
# (nxt/plen/hlim/flow), baseline (sl=4, dp=5, dr=1.0).
# Re-runs on the current PSIMiner build to close the two grid
# cells that crashed in the earlier richer-vocabulary sweep.
# Originals are preserved: this writes to a new OUTDIR.
set +e

BASE=example_frag.conf   # IPv6-only vocab, target HAS_FRAG_EH, recv2.csv
OUTDIR=ablation_ams_1d_ipv6only
rm -rf $OUTDIR
mkdir -p $OUTDIR
echo "axis,seqLength,depth,delayRes,top_corr,top_support,top_rule" > $OUTDIR/grid.csv

run_one() {
  local axis=$1 sl=$2 dp=$3 dr=$4 dr_label=$5
  local tag="${axis}_sl${sl}_dp${dp}_dr${dr_label}"
  local conf="$OUTDIR/${tag}.conf"
  cp $BASE $conf
  # Portable in-place edit (BSD/macOS sed and GNU/Linux sed differ on -i).
  sed_i() { sed "$1" "$2" > "$2.tmp" && mv "$2.tmp" "$2"; }
  sed_i "s|^seqLength=.*|seqLength=${sl}|"  $conf
  sed_i "s|^depth=.*|depth=${dp}|"          $conf
  sed_i "s|^delayRes=.*|delayRes=${dr}|"    $conf
  ./psiMiner $conf > $OUTDIR/${tag}.log 2>&1
  rc=$?
  ASRT="$OUTDIR/${tag}-assertions.txt"
  if [ $rc -ne 0 ] || [ ! -s $ASRT ] || ! grep -q CORRELATION $ASRT; then
    echo "${axis},${sl},${dp},${dr},FAIL,FAIL,rc=${rc}" >> $OUTDIR/grid.csv
    echo "[fail] ${tag} rc=${rc}"
    return
  fi
  corr=$(grep -m1 'CORRELATION' $ASRT | sed 's/.*\[\(.*\)\].*/\1/')
  supp=$(grep -m1 'SUPPORT' $ASRT | sed 's/.*\[\(.*\)\].*/\1/')
  rule=$(grep -m1 '|=>' $ASRT | tr ',' ';')
  echo "${axis},${sl},${dp},${dr},${corr},${supp},${rule}" >> $OUTDIR/grid.csv
  echo "[done] ${tag}: corr=${corr} rule=${rule}"
}

for sl in 2 3 4 5; do run_one seqLength $sl 5 1.0 10; done
for dp in 3 4 5 6; do run_one depth 4 $dp 1.0 10; done
for dr_label in 05 10 20; do
  case $dr_label in 05) dr=0.5;; 10) dr=1.0;; 20) dr=2.0;; esac
  run_one delayRes 4 5 $dr $dr_label
done

echo "--- grid summary ---"
column -t -s, $OUTDIR/grid.csv
