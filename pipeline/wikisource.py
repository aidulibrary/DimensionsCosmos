"""多语维基文库 API 客户端。
内容许可：CC BY-SA 4.0（可商用，需署名+相同方式共享）。
只取公版原始文本自行加工，不触碰任何平台的整理成果。
支持语言：zh / en / de / fr / es / ja / ar / ru / it / pt
"""
import time

import requests

# 多语 Wikisource API URL 映射
LANG_APIS = {
    "zh": "https://zh.wikisource.org/w/api.php",
    "en": "https://en.wikisource.org/w/api.php",
    "de": "https://de.wikisource.org/w/api.php",
    "fr": "https://fr.wikisource.org/w/api.php",
    "es": "https://es.wikisource.org/w/api.php",
    "ja": "https://ja.wikisource.org/w/api.php",
    "ar": "https://ar.wikisource.org/w/api.php",
    "ru": "https://ru.wikisource.org/w/api.php",
    "it": "https://it.wikisource.org/w/api.php",
    "pt": "https://pt.wikisource.org/w/api.php",
    "la": "https://la.wikisource.org/w/api.php",
    "ko": "https://ko.wikisource.org/w/api.php",
}

USER_AGENT = ("DimensionsCosmosBot/0.2 "
              "(https://github.com/aidulibrary/DimensionsCosmos; contact via repo issues)")

# 每语种的"全览"标记词（用于跳过聚合页）
SKIP_MARKERS = {
    "zh": ("全覽", "全文"),
    "en": ("/Contents", "/Full text"),
    "de": ("/Inhaltsverzeichnis", "/Gesamt"),
    "fr": ("/Table", "/Sommaire"),
    "es": ("/Índice", "/Todo"),
    "ja": ("/全覧", "/全文"),
    "ar": ("فهرس",),
    "ru": ("/Содержание",),
    "it": ("/Indice", "/Sommario"),
    "pt": ("/Índice", "/Sumário"),
    "la": ("/Index",),
    "ko": ("/전체", "/목차"),
}

_session_cache = {}

def _get_session(lang):
    if lang not in _session_cache:
        s = requests.Session()
        s.headers.update({"User-Agent": USER_AGENT, "Api-User-Agent": USER_AGENT})
        _session_cache[lang] = s
    return _session_cache[lang]

def get_api_url(lang):
    return LANG_APIS.get(lang, LANG_APIS["en"])

def get_skip_markers(lang):
    return SKIP_MARKERS.get(lang, SKIP_MARKERS["en"])

def _get(lang, params, retries=4):
    session = _get_session(lang)
    payload = {"format": "json", "formatversion": "2"}
    payload.update(params)
    delay = 1.0
    last_err = None
    for _ in range(retries):
        try:
            resp = session.get(get_api_url(lang), params=payload, timeout=30)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise RuntimeError(f"HTTP {resp.status_code}")
            data = resp.json()
            if "error" in data:
                raise RuntimeError(data["error"].get("info", "api error"))
            return data
        except Exception as exc:
            last_err = exc
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"wikisource api failed for lang={lang}: {last_err}")


def fetch_page(lang, title):
    """返回 {'title', 'text'}；页面不存在返回 None。"""
    data = _get(lang, {
        "action": "query",
        "prop": "extracts|info",
        "explaintext": "1",
        "redirects": "1",
        "titles": title,
    })
    pages = data.get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        return None
    page = pages[0]
    return {"title": page["title"], "text": page.get("extract", "")}


def list_subpages(lang, title, limit=500):
    """列出 '书名/...' 形式的全部章节子页面。"""
    found = []
    cont = {}
    markers = get_skip_markers(lang)
    while True:
        data = _get(lang, {
            "action": "query",
            "list": "allpages",
            "apprefix": f"{title}/",
            "aplimit": "max",
            **cont,
        })
        found.extend(
            p["title"]
            for p in data.get("query", {}).get("allpages", [])
            if not any(m in p["title"] for m in markers)
        )
        if "continue" not in data or len(found) >= limit:
            return found[:limit]
        cont = data["continue"]


def fetch_book(lang, title, max_chapters=None, sleep=0.4):
    """抓取一部书：主页面 + 章节纯文本。lang 如 'zh' 'en' 'de'。"""
    main = fetch_page(lang, title)
    if main is None:
        return None
    real_title = main["title"]
    sub = list_subpages(lang, real_title)
    chapters = []
    if sub:
        for sub_title in sub[: max_chapters or len(sub)]:
            page = fetch_page(lang, sub_title)
            if page and page["text"].strip():
                chapters.append(page)
            time.sleep(sleep)
    elif main["text"].strip():
        chapters.append(main)
    return {"title": real_title, "lang": lang, "chapters": chapters}


# ---- 向下兼容：中文默认调用 ----
def fetch_book_zh(title, max_chapters=None, sleep=0.4):
    """中文维基文库抓书（向下兼容旧调用）。"""
    return fetch_book("zh", title, max_chapters=max_chapters, sleep=sleep)


def fetch_page_zh(title):
    """中文维基文库取单页（向下兼容）。"""
    return fetch_page("zh", title)


def list_subpages_zh(title, limit=500):
    """中文章节列表（向下兼容）。"""
    return list_subpages("zh", title, limit=limit)