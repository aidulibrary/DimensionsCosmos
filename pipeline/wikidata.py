"""按书名解析 Wikidata QID（CC0，无条件可商用）。
不硬编码 QID——运行时解析。两道过滤防张冠李戴：
1. match.text 必须与书名一致（label 或 alias，简繁由 Wikidata 自己归一）；
2. 多个候选时优先描述里带书籍特征的（排除"围棋手史记"这类同名干扰）。
"""
import requests

API_URL = "https://www.wikidata.org/w/api.php"
USER_AGENT = ("DimensionsCosmosBot/0.1 "
              "(https://github.com/aidulibrary/DimensionsCosmos; contact via repo issues)")
HEADERS = {"User-Agent": USER_AGENT, "Api-User-Agent": USER_AGENT}

BOOK_HINTS = ("书", "書", "籍", "典", "著", "史", "集", "经", "經",
              "诗", "詩", "小说", "小說", "作品", "文献", "文獻")


def search_qid(name):
    """返回 QID 字符串；找不到可信匹配返回 None（留空比填错好，人工复核兜底）。"""
    try:
        resp = requests.get(
            API_URL,
            params={
                "action": "wbsearchentities",
                "search": name,
                "language": "zh",
                "uselang": "zh",
                "type": "item",
                "limit": "5",
                "format": "json",
            },
            headers=HEADERS,
            timeout=20,
        )
        target = name.replace(" ", "")
        candidates = []
        for hit in resp.json().get("search", []):
            match_text = hit.get("match", {}).get("text", "").replace(" ", "")
            if match_text == target:
                candidates.append((hit["id"], hit.get("description", "")))
        if not candidates:
            return None
        for qid, desc in candidates:
            if any(h in desc for h in BOOK_HINTS):
                return qid
        return candidates[0][0]
    except Exception:  # noqa: BLE001
        return None
