import sqlite3, os, json, sys, re
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__))
c = sqlite3.connect(os.path.join(ROOT, 'data', 'guji.db'))
c.row_factory = sqlite3.Row

stat = defaultdict(lambda: {'n':0,'h2':0,'h3':0,'p':0,'plen':0,'no_body':0})
for r in c.execute('select work_id, blocks from chapters'):
    b = json.loads(r['blocks'] or '[]')
    s = stat[r['work_id']]
    s['n'] += 1
    h2 = sum(1 for x in b if x['t']=='h' and x.get('l')==2)
    h3 = sum(1 for x in b if x['t']=='h' and x.get('l',9)>=3)
    ps = [x for x in b if x['t']=='p']
    s['h2'] += h2; s['h3'] += h3; s['p'] += len(ps)
    s['plen'] += sum(len(x['x']) for x in ps)
    if len(ps) == 0: s['no_body'] += 1

names = dict(c.execute('select id, seed_title from works'))
print(f"{'work':<10}{'ch':>5}{'h2':>5}{'h3':>5}{'p':>6}{'p均长':>7}{'无正文章':>8}")
for wid, s in sorted(stat.items()):
    avg = s['plen']/max(1,s['p'])
    print(f"{names[wid]:<10}{s['n']:>5}{s['h2']:>5}{s['h3']:>5}{s['p']:>6}{avg:>7.0f}{s['no_body']:>8}")

print('\n=== 诗经中 p 总长 < 120 的篇数 ===')
rows = c.execute("""select id,title,blocks from chapters where work_id=5""").fetchall()
short = []
for r in rows:
    b = json.loads(r['blocks'] or '[]')
    L = sum(len(x['x']) for x in b if x['t']=='p')
    if L < 120: short.append((L, r['title']))
print('count=', len(short), 'of', len(rows))
for x in sorted(short)[:10]: print('   ', x)
print('   ...')
for x in sorted(short)[-5:]: print('   ', x)
