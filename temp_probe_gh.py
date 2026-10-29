import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')
URLS = [
    'https://raw.githubusercontent.com/chinese-poetry/chinese-poetry/master/shijing/shijing.json',
    'https://cdn.jsdelivr.net/gh/chinese-poetry/chinese-poetry@master/shijing/shijing.json',
    'https://gitee.com/mirrors_chinese-poetry/chinese-poetry/raw/master/shijing/shijing.json',
]
for u in URLS:
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as r:
            b = r.read()
        print('OK', u, len(b))
        d = json.loads(b.decode('utf-8'))
        print('  items=', len(d), 'first=', json.dumps(d[0], ensure_ascii=False)[:200])
        break
    except Exception as e:
        print('FAIL', u, type(e).__name__, e)
