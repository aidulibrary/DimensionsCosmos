#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用：从本地殆知阁归档导入单书白文本并按「章/篇/卷」切章写库。

与 import_daizhige.py 的区别：切章规则配置化（BOOKS 表），新增书只需加一条配置。

用法：
  python import_daizhige_generic.py --work-id 23            # dry-run
  python import_daizhige_generic.py --work-id 23 --apply    # 写库
  python import_daizhige_generic.py --list                  # 查看已配置书目
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize_text import clean_text, to_blocks, chapter_quality, work_quality  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SRC_DIR = Path(r"D:\DimensionsCosmos\data\sources\daizhige")
DB = r"D:\DimensionsCosmos\data\guji.db"
RE_PUA = re.compile(r"[\ue000-\uf8ff]")

# 章标题行正则模板
#   zhang : 「体道章第一」（道德真经/河上公本分章）
#   pian  : 「计篇第一计篇」（孙子兵法，篇名重复）
#   juan  : 「卷一」「卷第一」
BOOKS: dict[int, dict] = {
    23: dict(book="老子", file="道德真经.md", mode="zhang", prefix="老子",
             min_chars=20, min_avg=50,
             note="《正统道藏》洞神部本文类《道德真经》无注本，分章同河上公本（八十一章）"),
    28: dict(book="孙子兵法", file="孙子兵法.md", mode="pian", prefix="孙子兵法",
             min_chars=80, min_avg=150,
             note="白文本十三篇（计篇至用间）"),
}

# 正文中需要整行剔除的结构性残行
DROP_LINE = re.compile(r"^(道德真经)?卷[上下]*(竟|终)?$|^道德真经卷[上下]$")
CN_NUM = "零一二三四五六七八九"


def cn_num(n: int) -> str:
    """1-999 转汉数字（仅用于章序号展示）。"""
    if n <= 10:
        return "十" if n == 10 else CN_NUM[n]
    if n < 20:
        return "十" + CN_NUM[n % 10]
    if n < 100:
        s = CN_NUM[n // 10] + "十"
        return s + (CN_NUM[n % 10] if n % 10 else "")
    return str(n)


def read_body(name: str) -> list[str]:
    raw = open(SRC_DIR / name, encoding="utf-8", errors="ignore").read()
    parts = raw.split("---", 2)
    body = parts[2] if len(parts) > 2 else raw
    return [RE_PUA.sub("", l) for l in body.splitlines()]


RE_MAP = {
    # 尾部允许 0-2 个残字：《道德真经》第五十八章原标题作「顺化章第五十入」
    # （"八"讹作"入"），故章号以出现次序为准，标题数字仅作人工核对参考
    "zhang": re.compile(r"^[\s　]*(?P<name>\S{2,6}?)章第(?P<num>[一二三四五六七八九十]+)\S{0,2}$"),
    "pian": re.compile(r"^[\s　]*(?P<name>\S{1,3}?篇)第(?P<num>[一二三四五六七八九十]+)"
                       r"(?P=name)?\s*$"),
    "juan": re.compile(r"^[\s　]*卷(?P<num>[一二三四五六七八九十百]+)\s*(?P<name>\S{0,20})\s*$"),
}


def parse_headings(file: str, mode: str, prefix: str) -> list[dict]:
    """按标题行切章，返回 [{title, text}]。"""
    lines = read_body(file)
    pat = RE_MAP[mode]
    hits = [(i, pat.match(l.strip())) for i, l in enumerate(lines)]
    hits = [(i, m) for i, m in hits if m]
    if not hits:
        raise SystemExit(f"[fail] {file} 未匹配到任何 {mode} 标题行")

    chapters: list[dict] = []
    for k, (i, m) in enumerate(hits):
        end = hits[k + 1][0] if k + 1 < len(hits) else len(lines)
        num, name = m.group("num"), (m.groupdict().get("name") or "").strip()
        body = [l for l in lines[i + 1:end] if not DROP_LINE.match(l.strip())]
        if mode == "zhang":
            seq = cn_num(k + 1)
            if num != seq:
                print(f"   [title-check] 第{k+1}章 标题原作「{num}」，按次序记为「{seq}」")
            title = f"{prefix}/第{seq}章·{name}" if name else f"{prefix}/第{seq}章"
        elif mode == "pian":
            title = f"{prefix}/{name}" if name else f"{prefix}/第{num}篇"
        else:
            title = f"{prefix}/卷{num}" + (f"·{name}" if name else "")
        chapters.append({"title": title, "text": "\n".join(body)})
    return chapters


def build_rows(chapters: list[dict], min_chars: int = 80,
               min_avg: int = 150, min_total: int = 4000) -> list[dict]:
    """清洗 + 分章定级。短章体裁（老子 81 章、中庸 33 章）按书收紧/放宽阈值。"""
    rows = []
    for c in chapters:
        cleaned = clean_text(c["text"])
        blocks = to_blocks(cleaned)
        chars = sum(len(b["x"]) for b in blocks if b["t"] == "p")
        if chars == 0:
            q, note = "empty", "原文为空"
        elif chars < min_chars:
            q, note = "incomplete", f"仅 {chars} 字，疑为残缺底本"
        else:
            q, note = "ok", ""
        rows.append({"title": c["title"], "text": c["text"], "clean": cleaned,
                     "blocks": blocks, "chars": chars, "quality": q, "note": note})
    return rows


def grade_work(rows: list[dict], min_avg: int, min_total: int) -> tuple[str, str]:
    valid = [r for r in rows if r["chars"] > 0]
    if not valid:
        return "unavailable", "未获取到可用正文（底本缺失或为目录页）"
    total = sum(r["chars"] for r in valid)
    avg = total / len(valid)
    empty = len(rows) - len(valid)
    tail = f"，另 {empty} 章无正文已跳过" if empty else ""
    if len(valid) == 1:
        return ("incomplete", f"底本为全书单页（{total} 字），未分章") if total >= 100 \
            else ("unavailable", f"底本仅 {total} 字，不可用")
    if total < min_total or avg < min_avg:
        return "incomplete", f"共 {len(valid)} 章 {total} 字（均 {avg:.0f} 字），疑有缺失{tail}"
    return "ok", tail.lstrip("，")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-id", type=int)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--db", default=DB)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for wid, cfg in BOOKS.items():
            print(wid, cfg["book"], cfg["file"], cfg["mode"])
        return 0
    if not args.work_id:
        raise SystemExit("need --work-id or --list")

    cfg = BOOKS[args.work_id]
    min_chars = int(cfg.get("min_chars", 80))
    min_avg = int(cfg.get("min_avg", 150))
    min_total = int(cfg.get("min_total", 4000))
    chapters = parse_headings(cfg["file"], cfg["mode"], cfg["prefix"])
    rows = build_rows(chapters, min_chars, min_avg, min_total)
    total = sum(r["chars"] for r in rows)
    wq, wnote = grade_work(rows, min_avg, min_total)
    print(f"[parse] {cfg['book']} 章数={len(rows)} 总字数={total} "
          f"卷均={total/max(1,len(rows)):.0f} work_quality={wq} {wnote}")
    for r in rows[:2] + rows[-2:]:
        print("   ", r["title"], r["chars"], r["quality"], r["note"])
    empty = [r["title"] for r in rows if r["chars"] == 0]
    tiny = [(r["title"], r["chars"]) for r in rows if 0 < r["chars"] < 30]
    if empty:
        print("   [warn] 空章:", empty[:10])
    if tiny:
        print("   [warn] 超短章:", tiny[:10])

    if not args.apply:
        print("[dry-run] 未写库；加 --apply 执行")
        return 0

    con = sqlite3.connect(args.db)
    con.execute("delete from chapters where work_id=?", (args.work_id,))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for ordn, r in enumerate(rows, 1):
        con.execute("""insert into chapters
            (work_id,title,text,chars,clean_text,blocks,quality,quality_note,ord,ord_source,noise_ratio,ord_group)
            values(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (args.work_id, r["title"], r["text"], r["chars"], r["clean"],
             json.dumps(r["blocks"], ensure_ascii=False), r["quality"], r["note"],
             ordn, "daizhige", 0.0, ""))
    con.execute("""update works set status='ok', quality=?, total_chars=?, chapter_count=?,
                   fetched_at=?, last_error=NULL where id=?""",
                (wq, total, len(rows), now, args.work_id))
    con.commit()
    print(f"[apply] work={args.work_id} {cfg['book']} 写入 {len(rows)} 章 {total} 字，quality={wq}")
    print(f"[底本] {cfg['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
