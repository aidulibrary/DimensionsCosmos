import sqlite3, os, json, sys, re
from collections import defaultdict, OrderedDict
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__))
c = sqlite3.connect(os.path.join(ROOT, 'data', 'guji.db'))
c.row_factory = sqlite3.Row

def h2_of(blocks):
    for b in blocks:
        if b['t'] == 'h' and b.get('l') == 2:
            return b['x']
    return ''

groups = OrderedDict()
for r in c.execute('select id,title,blocks from chapters where work_id=5 order by id'):
    b = json.loads(r['blocks'] or '[]')
    h2 = h2_of(b)
    parts = h2.split('‧')
    key = '‧'.join(parts[:-1]) if len(parts) >= 2 else (h2 or '未分组')
    name = parts[-1] if len(parts) >= 2 else r['title'].split('/')[-1]
    groups.setdefault(key, []).append((name, r['id'], r['title']))

for k, v in groups.items():
    print(f"## {k}  (n={len(v)})")
    print('   ' + ' | '.join(x[0] for x in v))
