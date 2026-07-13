#!/usr/bin/env python3
"""Best rule at each antecedent bucket-count across all six EH targets.
Antecedent bucket count = (# of '##[' before '|=>') + 1."""
import glob, re
rules=[]
for fn in glob.glob('t*-assertions.txt'):
    txt=open(fn).read()
    m=re.search(r'TARGET \[(\w+)\]', txt); tgt=m.group(1) if m else fn
    L=txt.splitlines()
    for i,l in enumerate(L):
        if '|=>' in l:
            c=None
            for j in range(i+1,min(i+4,len(L))):
                mm=re.search(r'CORRELATION\s*=\s*\[([\d.]+)\]',L[j])
                if mm: c=float(mm.group(1)); break
            if c is None: continue
            rules.append((c, l.split('|=>')[0].count('##[')+1, tgt, l.strip()))
for nb in (1,2,3,4):
    g=[r for r in rules if r[1]==nb]
    if g:
        b=max(g,key=lambda r:r[0]); print(f"{nb}-bucket best: {b[0]:.2f}% [{b[2]}] {b[3]}")
