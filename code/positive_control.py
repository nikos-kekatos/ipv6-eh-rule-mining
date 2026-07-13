#!/usr/bin/env python3
"""Positive control for the negative-control protocol.
We synthesise a trace with a GENUINE cross-packet temporal rule: a MARK event
deterministically causes a HIT exactly 2 packets later (network-temporal), with
no within-packet co-occurrence. The joint-row permutation must DESTROY it
(score -> base rate), unlike the JAMES within-packet rule which is invariant.
This demonstrates the protocol flags genuine network-temporal structure."""
import random, statistics
random.seed(2026)
N=38692
p_mark=0.20
# build trace: mark[i] iid; hit[i] = 1 iff mark[i-2]==1 (pure 2-lag causation)
mark=[1 if random.random()<p_mark else 0 for _ in range(N)]
hit=[0]*N
for i in range(2,N):
    if mark[i-2]==1: hit[i]=1
base=sum(hit)/N
def fwd_conf(mk, ht, lo, hi):
    A=B=0
    for i in range(N):
        if mk[i]==1:
            A+=1
            if any(ht[j]==1 for j in range(i+lo,min(i+hi+1,N))): B+=1
    return B/A if A else float('nan')
ordv=fwd_conf(mark,hit,1,4)
perm=[]
for _ in range(20):
    idx=list(range(N)); random.shuffle(idx)
    perm.append(fwd_conf([mark[k] for k in idx],[hit[k] for k in idx],1,4))
m=statistics.mean(perm)
print(f"synthetic genuine 2-lag rule MARK=>[1:4]HIT")
print(f"  base rate window 1-(1-p)^4 = {1-(1-base)**4:.4f}")
print(f"  ordered  = {ordv:.4f}")
print(f"  permuted = {m:.4f} +/- {statistics.pstdev(perm):.4f}")
print(f"  Delta    = {ordv-m:+.4f}  (large negative-going collapse => protocol flags it TEMPORAL)")
