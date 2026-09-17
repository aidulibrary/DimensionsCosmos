"""中文维基文库 API 客户端。
内容许可：CC BY-SA 4.0（可商用，需署名+相同方式共享）——分发时标注来源即可。
只取公版原始文本自行加工，不触碰任何平台的整理成果（识典/ctext 等）。
"""
import time

import requests

API_URL = "https://zh.wikisource.org/w/api.php"
USER_AGENT = "OpenGujiMVP/0.1 (personal open-knowledge project)"

# 维基文库的"全覽"页是整部书的聚合页，抓它会把全书重复存一遍
SKIP_SUBPAGE_MARKERS = ("全覽", "全文")

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


def _get(params, retries=4):
    payload = {"format": "json", "formatversion": "2", "maxlag": "5"}
    payload.update(params)
    delay = 1.0
    last_err = None
    for _ in range(retries):
        try:
            resp = _session.get(API_URL, params=payload, timeout=30)
            if resp.status_code == 429 or resp.status_code >= 500:
                raise RuntimeError(f"HTTP {resp.status_code}")
            data = resp.json()
            if "error" in data:
                raise RuntimeError(data["error"].get("info", "api error"))
            return data
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"wikisource api failed: {last_err}")


def fetch_page(title):
    """返回 {'title', 'text'}；页面不存在返回 None。redirects=1 自动处理简繁重定向。"""
    data = _get({
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


def list_subpages(title, limit=500):
    """列出 '书名/...' 形式的全部章节子页面（如 论语/学而第一）。"""
    found = []
    cont = {}
    while True:
        data = _get({
            "action": "query",
            "list": "allpages",
            "apprefix": f"{title}/",
            "aplimit": "max",
            **cont,
        })
        found.extend(
            p["title"]
            for p in data.get("query", {}).get("allpages", [])
            if not any(m in p["title"] for m in SKIP_SUBPAGE_MARKERS)
        )
        if "continue" not in data or len(found) >= limit:
            return found[:limit]
        cont = data["continue"]


def fetch_book(title, max_chapters=None, sleep=0.4):
    """抓取一部书：主页面 + 章节纯文本。返回 dict；书不存在返回 None。"""
    main = fetch_page(title)
    if main is None:
        return None
    real_title = main["title"]
    sub = list_subpages(real_title)
    chapters = []
    if sub:
        for sub_title in sub[: max_chapters or len(sub)]:
            page = fetch_page(sub_title)
            if page and page["text"].strip():
                chapters.append(page)
            time.sleep(sleep)
    elif main["text"].strip():
        # 单页成书（短章），主页面即正文
        chapters.append(main)
    return {"title": real_title, "chapters": chapters}
