import urllib.request, urllib.parse, json, sys

def api(**params):
    p = {'format': 'json', 'formatversion': '2'}
    p.update(params)
    url = 'https://zh.wikisource.org/w/api.php?' + urllib.parse.urlencode(p)
    req = urllib.request.Request(url, headers={'User-Agent': 'DimensionsCosmos/0.5 (build; contact: local)'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8'))

for page in ['詩經/關雎', '詩經/七月', '周易/乾', '莊子/逍遙遊']:
    try:
        d = api(action='parse', page=page, prop='wikitext', section='0')
        wt = d['parse']['wikitext']
        print('=====', page)
        print(wt[:900])
    except Exception as e:
        print('=====', page, 'ERR', e)
