# -*- coding: utf-8 -*-
"""把历次 web_search 落盘的 tool-results 合并为一个候选证据池，并按书名切出 search JSON 供 egv ingest 使用。"""
import glob
import json
import pathlib
import re
import sys

D = (r"C:\Users\LENOVO\AppData\Roaming\Tencent\Marvis\User\oAN1i2TLaWh8g0cZFh0NNd26qb-Y"
     r"\workspace\conv_99d25f1991834fc6967cb70099f17330\temp\.tool-results")
OUT = pathlib.Path(r"D:\DimensionsCosmos\data\search")
POOL = pathlib.Path(r"D:\DimensionsCosmos\data\search\pool.json")

# 书名 -> work_id 需取证清单（可由 guji.db 覆盖，这里仅兜底）
BOOKS = {
    3: "大学", 10: "孝经", 11: "尔雅", 15: "后汉书", 16: "三国志", 17: "资治通鉴",
    18: "战国策", 19: "国语", 20: "贞观政要", 21: "水经注", 22: "史通", 27: "墨子",
    29: "吕氏春秋", 30: "淮南子", 31: "论衡", 32: "颜氏家训", 33: "世说新语",
    34: "山海经", 35: "搜神记", 36: "黄帝内经", 37: "伤寒杂病论", 38: "齐民要术",
    39: "梦溪笔谈", 40: "天工开物", 41: "楚辞", 42: "文选", 44: "宋词三百首",
    45: "古文观止", 46: "文心雕龙", 47: "诗品", 48: "陶渊明集", 49: "李太白集",
    50: "杜工部集",
}
NEG = ("不推荐", "盗版")


def load_pool() -> list[dict]:
    if POOL.exists():
        return json.loads(POOL.read_text(encoding="utf-8"))
    pool, seen = [], set()
    for f in sorted(glob.glob(str(pathlib.Path(D) / "*.txt"))):
        try:
            d = json.loads(pathlib.Path(f).read_text(encoding="utf-8", errors="ignore"))
        except Exception:  # noqa: BLE001
            continue
        for r in d.get("results", []) or []:
            url = r.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)
            pool.append({"title": r.get("title", ""), "url": url,
                         "snippet": r.get("snippet", ""), "source": r.get("source", "")})
    POOL.parent.mkdir(parents=True, exist_ok=True)
    POOL.write_text(json.dumps(pool, ensure_ascii=False, indent=1), encoding="utf-8")
    return pool


def fieldy(text: str) -> bool:
    return bool(re.search(r"(ISBN|出版社|出版时间|中华书局|上海古籍|岳麓书社|北京大学出版社)", text))


def main() -> int:
    ids = [int(x) for x in sys.argv[1:]] or list(BOOKS)
    pool = load_pool()
    print(f"[pool] {len(pool)} 条候选")
    OUT.mkdir(parents=True, exist_ok=True)
    for wid in ids:
        name = BOOKS[wid]
        # 短书名（大学/孝经/诗品等）与常用词冲突，必须带书名号或组合书名才采信
        pat = re.compile(r"《" + re.escape(name) + r"》|" + re.escape(name) + r"[··、]")
        hits = []
        for r in pool:
            blob = r["title"] + " " + r["snippet"]
            if not pat.search(blob) or not fieldy(blob):
                continue
            # 主题位置闸门：书名必须出现在标题区或题名/书名栏（前 120 字），
            # 避免「十三经注疏」这类合集目录里顺带提及而被误当作本书的版本证据
            head = (r["title"] + " " + r["snippet"][:120])
            if not (name in head or f"书名: {name}" in blob or f"题名" in head and name in head):
                continue
            if any(n in blob for n in NEG):
                continue
            hits.append(r)
        hits.sort(key=lambda r: (0 if "cppinfo" in r["url"] or "zhbc.com.cn" in r["url"] else 1))
        dst = OUT / f"work_{wid}.json"
        dst.write_text(json.dumps({"work_id": wid, "results": hits},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  {wid:>3} 《{name}》 命中 {len(hits)} 条 -> {dst.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
