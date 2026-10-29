import sqlite3, os, json, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__))
c = sqlite3.connect(os.path.join(ROOT, 'data', 'guji.db'))
c.row_factory = sqlite3.Row
for cid in [1146, 1346, 1, 363, 42, 43, 41]:
    r = c.execute('select id,title,quality,quality_note,blocks,text from chapters where id=?', (cid,)).fetchone()
    b = json.loads(r['blocks'] or '[]')
    print(f"--- id={r['id']} {r['title']} q={r['quality']} {r['quality_note']} blocks={len(b)}")
    for x in b[:8]:
        print('    ', x['t'], x.get('l',''), x['x'][:70])
print('\n=== 诗经 42 全部 blocks ===')
r = c.execute('select blocks from chapters where id=42').fetchone()
for x in json.loads(r['blocks'])[:20]:
    print('   ', x['t'], x.get('l',''), x['x'][:90])
print('\n=== 唐诗三百首 ===')
r = c.execute('select blocks from chapters where id=1').fetchone()
for x in json.loads(r['blocks'])[:14]:
    print('   ', x['t'], x.get('l',''), x['x'][:90])
