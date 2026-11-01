#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按批次导入殆知阁底本到古籍库。

  python run_import.py --batch 1              # dry-run
  python run_import.py --batch 1 --apply      # 写库
  python run_import.py --title 红楼梦 --detail
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from daizhige_import_core import prep, save  # noqa: E402
from daizhige_corpus_config import CONFIG, SKIP_SRC  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
REPORT = Path(r"D:\DimensionsCosmos\data\temp\import_report.json")


def run(title: str, apply: bool, detail: bool) -> dict:
    cfg = CONFIG[title]
    print(f"\n===== 《{title}》 {cfg['file']} mode={cfg['mode']} =====")
    rows, meta = prep(title, cfg)
    print(f"  章数={meta['n']} 总字={meta['chars']}")
    show = rows if detail else rows[:3] + rows[-2:]
    for r in show:
        print(f"   {r['title'][:40]:<40} {r['chars']:>7} {r['quality']:<10} {r['note'][:12]}")
    bad = [(r["title"][:24], r["quality"], r["chars"]) for r in rows
           if r["quality"] not in ("ok", "lost")]
    if bad and not detail:
        print(f"   [待核 {len(bad)}]", bad[:8])
    res = save(title, cfg, rows, apply)
    res["batch"] = cfg["batch"]
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int)
    ap.add_argument("--title")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--detail", action="store_true")
    a = ap.parse_args()
    if a.title:
        titles = [a.title]
    elif a.batch:
        titles = [t for t, c in CONFIG.items() if c["batch"] == a.batch]
    else:
        titles = list(CONFIG)
    out = [run(t, a.apply, a.detail) for t in titles]
    if a.apply:
        old = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else []
        old.extend(out)
        REPORT.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for r in out if r["quality"] == "ok")
    print(f"\n[summary] {len(out)} 部，ok={ok}，非ok={len(out)-ok}；跳过源缺：{list(SKIP_SRC)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
