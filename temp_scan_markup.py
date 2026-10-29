import sqlite3, os, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__))
c = sqlite3.connect(os.path.join(ROOT, 'data', 'guji.db'))

pats = {
    'h2(== x ==)': re.compile(r'^==\s*[^=]+?\s*==\s*$', re.M),
    'h3(=== x ===)': re.compile(r'^===\s*[^=]+?\s*===\s*$', re.M),
    'table({|)': re.compile(r'\{\|'),
    'template({{)': re.compile(r'\{\{'),
    'linkpipe([[a|b]])': re.compile(r'\[\[[^\]]*\|'),
    'ref(<ref)': re.compile(r'<ref'),
    'div/span': re.compile(r'<(div|span|p|center|small|big)\b', re.I),
    'poem': re.compile(r'<poem', re.I),
    '第X卦': re.compile(r'第[一二三四五六七八九十百]+卦'),
    'DEFAULTSORT/Category': re.compile(r'DEFAULTSORT|Category:|分類:'),
    '註疏': re.compile(r'註疏'),
}
cnt = Counter()
per_work = {}
for wid, text in c.execute('select work_id, text from chapters'):
    t = text or ''
    hits = [k for k, p in pats.items() if p.search(t)]
    for h in hits:
        cnt[h] += 1
    per_work.setdefault(wid, Counter()).update(hits)

print('== 标记命中章数 ==')
for k, v in cnt.most_common():
    print(f'{k:<22} {v}')

print('\n== 有 h2 标题的书 ==')
for wid, cc in sorted(per_work.items()):
    if cc['h2(== x ==)'] or cc['h3(=== x ===)']:
        title = c.execute('select seed_title from works where id=?', (wid,)).fetchone()[0]
        print(f'  {wid} {title}: h2={cc["h2(== x ==)"]} h3={cc["h3(=== x ===)"]}')

print('\n== 周易 首块样本 ==')
for r in c.execute("select id,title,substr(text,1,180) from chapters where work_id=8 limit 4"):
    print(r[0], r[1]); print('   ', repr(r[2][:180]))

print('\n== 杜工部集 h2 样本 ==')
for r in c.execute("select id,title,text from chapters where work_id=50 limit 1"):
    import re as _re
    hs = _re.findall(r'^==\s*[^=]+?\s*==\s*$', r[2], _re.M)
    print(r[1], 'h2 count=', len(hs), hs[:6])

print('\n== 诗经 首块样本 ==')
for r in c.execute("select id,title,substr(text,1,200) from chapters where work_id=5 limit 3"):
    print(r[0], r[1]); print('   ', repr(r[2][:200]))
