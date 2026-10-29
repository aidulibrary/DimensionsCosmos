import json, sqlite3, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__))
c = sqlite3.connect(os.path.join(ROOT, 'data', 'guji.db'))
c.row_factory = sqlite3.Row

rep = json.load(open(os.path.join(ROOT, 'output', 'p0_normalize_report.json'), encoding='utf-8'))
print('== works detail ==')
for w in rep['works_detail']:
    print(f"{w['work_id']:>3} {w['title']:<8} ch={w['chapters']:>4} chars={w['total_chars']:>8} avg={w['total_chars']//max(1,w['chapters']):>5} {w['quality']:<12} {w['note']}")

# 需要 clean_text 才写库；dry-run 未写，这里临时重算抽样
sys.path.insert(0, ROOT)
from pipeline.normalize_text import clean_text, to_blocks
print('\n== noise ratio top ==')
rows = c.execute('select id,work_id,title,text,chars from chapters').fetchall()
stats = []
for r in rows:
    raw = r['text'] or ''
    cl = clean_text(raw)
    n = len(re.sub(r'\s','',cl)); o = len(re.sub(r'\s','',raw))
    stats.append((1 - n/max(1,o), r['id'], r['title'], o, n))
stats.sort(reverse=True)
for s in stats[:8]:
    print(f"loss={s[0]*100:5.1f}% id={s[1]} {s[2]} raw={s[3]} clean={s[4]}")

print('\n== samples ==')
for cid in [2, 3, 363, 1146, 1550]:
    r = c.execute('select title,text from chapters where id=?', (cid,)).fetchone()
    blocks = to_blocks(clean_text(r['text'] or ''))
    print(f"--- id={cid} {r['title']} blocks={len(blocks)}")
    for b in blocks[:4]:
        print('   |', b[:80])
