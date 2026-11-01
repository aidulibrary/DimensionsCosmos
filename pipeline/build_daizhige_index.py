#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描本地殆知阁归档 data/sources/daizhige/*.md 的 YAML front matter，
生成书名索引，供 33 部入围书目做本地渠道匹配。

输出：data/sources/daizhige_index.csv
字段：file,title_zh,title_hant,category,kanripo_id,edition,license,bytes

用法：python build_daizhige_index.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SRC = Path(r"D:\DimensionsCosmos\data\sources\daizhige")
OUT = Path(r"D:\DimensionsCosmos\data\sources\daizhige_index.csv")

RE_ZH = re.compile(r"^\s{2}zh-hans:\s*(.+)$", re.M)
RE_HANT = re.compile(r"^\s{2}zh-hant:\s*(.+)$", re.M)
RE_CAT = re.compile(r"^category:\s*(.+)$", re.M)
RE_KR = re.compile(r"ID:\s*(KR[0-9a-zA-Z]+)")
RE_ED = re.compile(r"底本:\s*(\w+)")


def parse_head(path: Path) -> dict | None:
    with open(path, encoding="utf-8", errors="ignore") as fh:
        head = fh.read(1400)
    if not head.startswith("---"):
        return None
    end = head.find("\n---", 3)
    fm = head[3:end] if end > 0 else head[:1200]
    m_cat = RE_CAT.search(fm)
    if not m_cat:
        return None
    m_zh = RE_ZH.search(fm)
    m_hant = RE_HANT.search(fm)
    m_kr = RE_KR.search(fm)
    m_ed = RE_ED.search(fm)
    return {
        "file": path.name,
        "title_zh": (m_zh.group(1).strip() if m_zh else ""),
        "title_hant": (m_hant.group(1).strip() if m_hant else ""),
        "category": m_cat.group(1).strip(),
        "kanripo_id": (m_kr.group(1) if m_kr else ""),
        "edition": (m_ed.group(1) if m_ed else ""),
        "license": "CC BY-SA 4.0",
        "bytes": path.stat().st_size,
    }


def main() -> int:
    rows = []
    files = sorted(SRC.glob("*.md"))
    for i, p in enumerate(files, 1):
        try:
            r = parse_head(p)
        except Exception as e:  # noqa: BLE001
            print(f"[warn] {p.name}: {e}")
            continue
        if r:
            rows.append(r)
        if i % 4000 == 0:
            print(f"  scanned {i}/{len(files)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"[index] {len(rows)} 条 -> {OUT}")
    # 粗略统计各藏
    from collections import Counter
    c = Counter(r["category"].split("/")[1] if "/" in r["category"] else "?" for r in rows)
    print("[藏] ", dict(c.most_common()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
