import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
c = sqlite3.connect('data/guji.db'); c.row_factory = sqlite3.Row
q = "select title, chars, text from chapters where work_id=26"
rows = c.execute(q).fetchall()
num_rows = [r for r in rows if r['title'].split('/')[-1].isdigit()]
named = [r for r in rows if not r['title'].split('/')[-1].isdigit()]
print('数字章', len(num_rows), '篇名章', len(named))
for r in num_rows[:3]:
    print(r['title'], r['chars'], repr((r['text'] or '')[:150]))
print('---')
for r in named[:3]:
    print(r['title'], r['chars'], repr((r['text'] or '')[:150]))
print('--- 数字章总字数', sum(r['chars'] or 0 for r in num_rows), '篇名章总字数', sum(r['chars'] or 0 for r in named))
