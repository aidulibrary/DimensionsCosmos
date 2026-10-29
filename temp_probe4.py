import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
c = sqlite3.connect('data/guji.db'); c.row_factory = sqlite3.Row
print('== 韩非子 ord NULL ==')
for r in c.execute("select title, chars, ord_group from chapters where work_id=26 and ord is null order by title"):
    print(' ', r['title'], r['chars'], r['ord_group'])
print()
print('== 史记两章 ==')
for r in c.execute("select id,title,chars,substr(text,1,60) from chapters where work_id=13 and ord is null"):
    print(' ', r['id'], r['title'], r['chars'])
print()
print('== 全库 ord NULL 明细 ==')
for r in c.execute("select w.seed_title, c.title from chapters c join works w on w.id=c.work_id where c.ord is null order by c.work_id"):
    print(' ', r['seed_title'], '|', r['title'])
