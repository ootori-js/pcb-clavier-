"""Compare the netlist KiCad extracts from the schematic with gen/design.py."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from sexp import parse, find, first
import design
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
t = parse(open(os.path.join(ROOT, 'out', 'netlist.net'), encoding='utf-8').read())[0]
got = {}
for net in find(first(t, 'nets'), 'net'):
    name = str(first(net, 'name')[1]).lstrip('/')
    got[name] = sorted((str(first(n, 'ref')[1]), str(first(n, 'pin')[1])) for n in find(net, 'node'))
want = {k: sorted(v) for k, v in design.nets().items()}
bad = 0
for k in sorted(set(want) | set(got)):
    if k.startswith('unconnected-'):
        continue
    if want.get(k) != got.get(k):
        bad += 1
        print('MISMATCH', k, '\n  want', want.get(k), '\n  got ', got.get(k))
comps = {str(first(c, 'ref')[1]) for c in find(first(t, 'components'), 'comp')}
print('components:', len(comps), 'expected', len(design.PARTS), '| nets checked:', len(want), '| mismatches:', bad)
sys.exit(1 if bad or comps != set(design.PARTS) else 0)
