import sqlite3, json, os, sys

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'guji.db')
c = sqlite3.connect(DB)
out = []
out.append('=== SCHEMA ===')
for r in c.execute("select type,name,sql from sqlite_master where type in ('table','index') order by name"):
    out.append(f'-- {r[0]} {r[1]}')
    if r[2]:
        out.append(r[2])
out.append('=== COUNTS ===')
for t in ['works', 'chapters', 'ai_guides', 'taxonomy']:
    try:
        out.append(f'{t}: ' + str(c.execute(f'select count(*) from {t}').fetchone()[0]))
    except Exception as e:
        out.append(f'{t}: ERR {e}')
out.append('=== WORKS ===')
for r in c.execute('select id,seed_title,ws_title,bu,author,status from works order by id'):
    n = c.execute('select count(*), coalesce(sum(chars),0) from chapters where work_id=?', (r[0],)).fetchone()
    out.append(f'{r[0]}\t{r[1]}\t{r[2]}\t{r[3]}\t{r[4]}\t{r[5]}\tch={n[0]}\tchars={n[1]}')
out.append('=== SAMPLE CHAPTERS ===')
for r in c.execute('select id,work_id,title,chars,substr(text,1,150) from chapters order by work_id,id limit 6'):
    out.append(repr(r))
print('\n'.join(out))
