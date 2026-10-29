import sqlite3, sys, json
sys.stdout.reconfigure(encoding='utf-8')
c = sqlite3.connect('data/guji.db'); c.row_factory = sqlite3.Row
print('== 韩非子 79 章 ==')
print(' | '.join(r['title'].split('/')[-1] for r in c.execute("select title from chapters where work_id=26 order by id")))
print()
print('== 周易未定位 ==')
for r in c.execute("select id,title,text from chapters where work_id=8 and ord is null"):
    print(' ', r['id'], r['title'], '|', repr((r['text'] or '')[:50]))
print()
print('== 詩經/無衣 ==')
for r in c.execute("select id,title,blocks from chapters where work_id=5 and title like '%無衣%'"):
    b = json.loads(r['blocks'] or '[]')
    print(' ', r['id'], r['title'], '|', [x['x'][:28] for x in b[:3]])
print()
print('== 荀子未定位 ==')
for r in c.execute("select title from chapters where work_id=25 and ord is null"):
    print(' ', r['title'])
print()
print('== 文心雕龙 諧 ==')
for r in c.execute("select id,title,ord from chapters where work_id=46 and title like '%諧%'"):
    print(' ', r['id'], r['title'], r['ord'])
