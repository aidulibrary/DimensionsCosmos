import sqlite3, os, json, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__))
c = sqlite3.connect(os.path.join(ROOT, 'data', 'guji.db'))
c.row_factory = sqlite3.Row
targets = {2:'孟子',24:'庄子',25:'荀子',27:'墨子',33:'世说新语',34:'山海经',46:'文心雕龙',30:'淮南子'}
for wid, nm in targets.items():
    rows = c.execute('select id,title from chapters where work_id=? order by id', (wid,)).fetchall()
    short = [r['title'].split('/')[-1] for r in rows]
    print(f'## {nm} ({wid}) n={len(short)}')
    print('  ' + ' | '.join(short))
