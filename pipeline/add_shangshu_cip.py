#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为《尚书》补中华书局官网 A2 级单书书目证据（王世舜、王翠叶译注本）。"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

P = Path(r"D:\DimensionsCosmos\data\evidence\work_6.json")
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

NEW = [
    {
        "grade": "A2", "weight": 0.90, "source_name": "中华书局",
        "url": "http://www.zhbc.com.cn/zhsj/fg/book/bookinfo.html?bookid=402885967f8affff017fab3766e000e7",
        "fields": {"isbn": "9787101083033", "publisher": "中华书局",
                   "editor": "王世舜、王翠叶", "edition": "译注"},
        "quote": "第五辑·书目：尚书 ISBN 978-7-101-08303-3 王世舜、王翠叶译注 36.00（中华经典名著全本全注全译丛书）",
    },
    {
        "grade": "A2", "weight": 0.90, "source_name": "中华书局",
        "url": "http://www.zhbc.com.cn/zhsj/pad/news/info.html?newsid=297ec13d94fe0ac9019517b99062020c",
        "fields": {"isbn": "9787101083033", "publisher": "中华书局", "year": "2012",
                   "editor": "王世舜、王翠叶", "edition": "译注"},
        "quote": "书名 书号 定价 出版时间 分类：5 尚书 978-7-101-08303-3 42 2012 历史/地理",
    },
]


def main() -> int:
    payload = json.loads(P.read_text(encoding="utf-8"))
    urls = {e["url"] for e in payload["entries"]}
    n = 0
    for e in NEW:
        if e["url"] in urls:
            continue
        payload["entries"].append({**e, "grabbed_at": NOW})
        n += 1
    payload["entries"].sort(key=lambda x: -x["weight"])
    P.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[evid] work=6 《尚书》 新增 A2 证据 {n} 条，累计 {len(payload['entries'])} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
