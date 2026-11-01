#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探测殆知阁归档单书正文的切章结构：统计各类标题模板命中数并给出样例。

用法：python probe_structure.py [书名.md ...]   # 缺省探测 data/corpus_local_match.csv 全部书目
输出：data/temp/structure_probe.txt + 控制台摘要
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SRC = Path(r"D:\DimensionsCosmos\data\sources\daizhige")
MATCH = Path(r"D:\DimensionsCosmos\data\corpus_local_match.csv")
OUT = Path(r"D:\DimensionsCosmos\data\temp\structure_probe.txt")

PATS = {
    "hui":   re.compile(r"^第[〇零一二三四五六七八九十百千0-9]+回"),
    "juan":  re.compile(r"^卷[〇零一二三四五六七八九十百千0-9]+"),
    "pian":  re.compile(r"^.+?篇第[〇零一二三四五六七八九十0-9]+"),
    "pian2": re.compile(r"^[〇零一二三四五六七八九十0-9]{1,3}[、．.]\s*\S{1,10}$"),
    "zhang": re.compile(r"^.+?章第[〇零一二三四五六七八九十0-9]+"),
    "pin":   re.compile(r"^.+?品$"),
    "chu":   re.compile(r"^第[〇零一二三四五六七八九十百千0-9]+出"),
    "tiao":  re.compile(r"^[〇零一二三四五六七八九十百0-9]{1,4}\s{0,3}\S{2,}$"),
    "mulu":  re.compile(r"^(目録|目錄|目录|提要|序|敘|跋)$"),
}


def probe(name: str) -> dict:
    p = SRC / name
    if not p.exists():
        return {"file": name, "err": "缺失"}
    txt = p.read_text(encoding="utf-8", errors="ignore")
    body = txt.split("---", 2)[-1]
    lines = [l.strip() for l in body.splitlines() if l.strip()]
    stats = {}
    for k, pat in PATS.items():
        hits = [l for l in lines if pat.match(l)]
        stats[k] = (len(hits), hits[:5])
    return {"file": name, "chars": len(txt), "lines": len(lines), "stats": stats}


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
        r = probe(n)
        if "err" in r:
            buf.append(f"[{n}] 缺失")
            print(f"[缺失] {n}")
            continue
        top = sorted(((k, v[0]) for k, v in r["stats"].items()), key=lambda x: -x[1])[:3]
        buf.append(f"\n===== {n}  {r['chars']}字 {r['lines']}行 =====")
        buf.append("  命中:" + " ".join(f"{k}={v}" for k, v in top if v))
        for k, (cnt, samples) in r["stats"].items():
            if cnt:
                buf.append(f"  [{k}] {cnt}: " + " | ".join(s[:34] for s in samples))
                print(f"{n:<22} {k}={cnt:<5} " + " | ".join(s[:22] for s in samples[:2]))
    OUT.write_text("\n".join(buf), encoding="utf-8")
    print(f"\n[probe] {len(names)} 部 -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
