import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

def get(u, timeout=20):
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

cands = [
    'https://gitee.com/api/v5/search/repositories?q=chinese-poetry&page=1&per_page=10',
    'https://registry.npmmirror.com/chinese-poetry',
]
for u in cands:
    try:
        b = get(u)
        print('OK', u, len(b))
        print(b.decode('utf-8', 'ignore')[:800])
        print('---')
    except Exception as e:
        print('FAIL', u, type(e).__name__, e)
