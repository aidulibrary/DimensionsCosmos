#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从本地已归档开源古籍库（daizhige / 殆知阁 v20，源自漢籍リポジトリ等公开文本）
导入单书正文到 guji.db，并按卷/篇切章。

用法：
  python import_daizhige.py --work-id 6  --file 尚书.md  --mode shangshu [--apply]
  python import_daizhige.py --work-id 14 --file 汉书.md  --mode hanshu   [--apply]
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from normalize_text import clean_text, to_blocks, chapter_quality, work_quality  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SRC_DIR = r"D:\DimensionsCosmos\data\sources\daizhige"
DB = r"D:\DimensionsCosmos\data\guji.db"

RE_SHANG = re.compile(r"^(虞书|夏书|商书|周书)\s+(\S+?)第([一二三四五六七八九十]+)$")
RE_JUAN = re.compile(
    r"^卷([一二三四五六七八九十百]+)(中之上|中之下|下之上|下之下|中|上|下)?\s*(.*)$")
RE_PUA = re.compile(r"[\ue000-\uf8ff]")  # 殆知阁文本夹带私用区缺字符，剔除


def read_body(name: str) -> list[str]:
    raw = open(f"{SRC_DIR}\\{name}", encoding="utf-8", errors="ignore").read()
    parts = raw.split("---", 2)
    return (parts[2] if len(parts) > 2 else raw).splitlines()


def parse_shangshu() -> list[dict]:
    lines = read_body("尚书.md")
    toc = [m for m in (RE_SHANG.match(l.strip()) for l in lines) if m]
    # 目录为首次连续出现的 58 条，正文标题在此之后
    toc_names = [f"{m.group(2)}第{m.group(3)}" for m in toc[:58]]
    body_start = 0
    for i, l in enumerate(lines):
        s = l.strip()
        if s.startswith(toc_names[-1]) and i > 60:
            body_start = i
            break
    # 定位每篇起点（篇名+"第X" 在正文中的首次出现，允许与上文同排）
    cuts: list[tuple[int, int, str]] = []
    cursor = 60
    for name in toc_names:
        pat = re.compile(re.escape(name))
        for i in range(cursor, len(lines)):
            m = pat.search(lines[i])
            if m:
                cuts.append((i, m.start(), name))
                cursor = i
                break
    chapters = []
    for k, (li, col, name) in enumerate(cuts):
        end_li = cuts[k + 1][0] if k + 1 < len(cuts) else len(lines)
        buf = []
        for i in range(li, end_li + (1 if k + 1 < len(cuts) else 0)):
            if i >= len(lines):
                break
            seg = lines[i]
            if i == li:
                seg = seg[col + len(name):]
            if k + 1 < len(cuts) and i == end_li:
                seg = seg[: cuts[k + 1][1]]
            buf.append(seg)
        title = re.sub(r"第[一二三四五六七八九十]+$", "", name)
        chapters.append({"title": f"尚书/{title}", "text": "\n".join(buf)})
    return chapters


def parse_hanshu() -> list[dict]:
    lines = [RE_PUA.sub("", l) for l in read_body("汉书.md")]
    heads = [i for i, l in enumerate(lines) if RE_JUAN.match(l.strip())]
    # 目录在前，正文从首卷重复出现处开始
    first = RE_JUAN.match(lines[heads[0]].strip())
    key = f"卷{first.group(1)}{first.group(2) or ''}"
    body_start = next(i for i in heads if i > heads[0] and lines[i].strip().startswith(key))
    # 目录：卷号 -> 篇名（作为正文章名的权威补全来源）
    toc: dict[str, str] = {}
    for i in heads:
        if i >= body_start:
            break
        m = RE_JUAN.match(lines[i].strip())
        if m.group(3).strip():
            toc[f"卷{m.group(1)}{m.group(2) or ''}"] = m.group(3).strip()
    starts = [i for i in heads if i >= body_start]
    raw: list[dict] = []
    for k, si in enumerate(starts):
        m = RE_JUAN.match(lines[si].strip())
        label = f"卷{m.group(1)}{m.group(2) or ''}"
        name = m.group(3).strip()
        body_from = si + 1
        if not name and body_from < len(lines):
            nxt = lines[body_from].strip()
            if (nxt and len(nxt) <= 16 and not nxt.endswith("。")
                    and not nxt.startswith("《") and not nxt.startswith("（")):
                name, body_from = nxt, body_from + 1
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        name = toc.get(label) or name
        raw.append({"label": label, "name": name,
                    "text": "\n".join(lines[body_from:end])})
    # 同一卷号被拆成多段时合并
    merged: list[dict] = []
    for r in raw:
        if merged and merged[-1]["label"] == r["label"]:
            merged[-1]["text"] += "\n" + r["text"]
        else:
            merged.append(dict(r))
    return [{"title": f"汉书/{r['label']}·{r['name']}" if r["name"] else f"汉书/{r['label']}",
             "text": r["text"]} for r in merged]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-id", type=int, required=True)
    ap.add_argument("--mode", choices=["shangshu", "hanshu"], required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--db", default=DB)
    args = ap.parse_args()

    chapters = parse_shangshu() if args.mode == "shangshu" else parse_hanshu()
    rows = []
    for c in chapters:
        cleaned = clean_text(c["text"])
        blocks = to_blocks(cleaned)
        chars = sum(len(b["x"]) for b in blocks if b["t"] == "p")
        q, note = chapter_quality(blocks, chars, False)
        rows.append({"title": c["title"], "text": c["text"], "clean": cleaned,
                     "blocks": blocks, "chars": chars, "quality": q, "note": note})
    wq, wnote = work_quality(rows)
    total = sum(r["chars"] for r in rows)
    print(f"[parse] 章数={len(rows)} 总字数={total} 卷均={total/max(1,len(rows)):.0f} "
          f"work_quality={wq} {wnote}")
    for r in rows[:3] + rows[-2:]:
        print("   ", r["title"], r["chars"], r["quality"], r["note"])
    empty = [r["title"] for r in rows if r["chars"] == 0]
    if empty:
        print("   [warn] 空章:", empty[:10])

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
    print(f"[apply] work={args.work_id} 写入 {len(rows)} 章 {total} 字，quality={wq}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
