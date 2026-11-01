#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探测短行候选标题（≤14 字、无句读结尾），用于给每部书定制切章规则。

用法：python probe_headings.py [书名.md ...]
输出：data/temp/headings_probe.txt
"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SRC = Path(r"D:\DimensionsCosmos\data\sources\daizhige")
MATCH = Path(r"D:\DimensionsCosmos\data\corpus_local_match.csv")
OUT = Path(r"D:\DimensionsCosmos\data\temp\headings_probe.txt")

BAN = ("。", "，", "；", "：", "？", "！", "、", "”", "（")


def cand(name: str) -> tuple[list[str], int]:
    p = SRC / name
    txt = p.read_text(encoding="utf-8", errors="ignore")
    body = txt.split("---", 2)[-1]
    lines = [l.strip() for l in body.splitlines() if l.strip()]
    hits = []
    for l in lines:
        s = re.sub(r"^[#>\s]+", "", l)
        s = re.sub(r"<[^>]+>", "", s).strip()
        if not s or len(s) > 14:
            continue
        if any(b in s for b in BAN):
            continue
        hits.append(s)
    return hits, len(lines)


def main() -> int:
    names = sys.argv[1:]
    if not names:
        rows = list(csv.DictReader(open(MATCH, encoding="utf-8-sig")))
        names = []
        for r in rows:
            for f in (r["files"] or "").split(";"):
                if f and f not in names:
                    names.append(f)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    buf = []
    for n in names:
        if not (SRC / n).exists():
            continue
        hits, nline = cand(n)
        c = Counter(hits)
        buf.append(f"\n===== {n} ({nline}行, 短行 {len(hits)}, 去重 {len(c)}) =====")
        buf.append("  样例: " + " | ".join(h[:14] for h in hits[:40]))
        buf.append("  高频: " + " | ".join(f"{k}×{v}" for k, v in c.most_common(12)))
    OUT.write_text("\n".join(buf), encoding="utf-8")
    print(f"[probe] {len(names)} 部 -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
