#!/usr/bin/env python3
"""RS2 permutation control: is the positive-delay MED=>FRAG score within-packet
or measurement-temporal? Joint-row permutation (shuffle row order, keep each
row's tuple) destroys ordering; if the packet-lag score falls to the window
base rate it is probe-burst temporal, not within-packet.
Usage: python3 rs2_permutation_delta.py [data/james_ams_recv2.csv]"""
import csv, random, statistics, sys
random.seed(2026)
path = sys.argv[1] if len(sys.argv)>1 else 'data/james_ams_recv2.csv'
rows=[]
with open(path) as f:
    for x in csv.DictReader(f):
        rows.append((int(x['nxt']), float(x['plen'])))
N=len(rows); med=lambda p:p>=128; frag=lambda n:n==44
def fwd_conf(seq, lo, hi):
    A=B=0
    for i,(n,p) in enumerate(seq):
        if med(p):
            A+=1
            if any(frag(seq[j][0]) for j in range(i+lo,min(i+hi+1,len(seq)))): B+=1
    return B/A if A else float('nan')
base=sum(1 for n,_ in rows if frag(n))/N
ordv=fwd_conf(rows,1,4)
perm=[( [ (lambda s:(random.shuffle(s),fwd_conf(s,1,4))[1])(rows[:]) ] )[0] for _ in range(20)]
m=statistics.mean(perm)
print(f"N={N}  P(FRAG)={base:.4f}  window base rate 1-(1-p)^4={1-(1-base)**4:.4f}")
print(f"MED=>[1pk:4pk]FRAG ordered={ordv:.4f} permuted={m:.4f}+/-{statistics.pstdev(perm):.4f} delta={ordv-m:+.4f}")
