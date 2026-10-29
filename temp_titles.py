import sqlite3, os, json
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'guji.db')
c = sqlite3.connect(DB)
rows = c.execute('''select c.work_id, w.seed_title, c.id, c.title, c.chars from chapters c join works w on w.id=c.work_id order by c.work_id, c.id''').fetchall()
from collections import defaultdict
g = defaultdict(list)
for r in rows:
    g[r[0]].append(r)
for wid, lst in g.items():
    print(f'### work {wid} {lst[0][1]}  n={len(lst)}')
    for r in lst[:8]:
        print('   ', r[2], '|', r[3], '|', r[4])
    if len(lst) > 8:
        print('    ...')
        for r in lst[-3:]:
            print('   ', r[2], '|', r[3], '|', r[4])
