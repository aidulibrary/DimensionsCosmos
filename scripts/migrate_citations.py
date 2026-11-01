#!/usr/bin/env python3
"""ai_guides.citations 字段迁移与回填（P0-5 引证式导读 · 字段基础）

背景
----
REF-SPEC v1 已为 5531 章建立稳定 URN（chapters.ref）。导读（ai_guides）此前只输出
散文，正文里的引文与所指原文之间没有任何可点击、可校验的锚点。本脚本做两件事：

1. 迁移：为 ai_guides 增加 citations 列（TEXT，存 JSON 字符串数组，元素为 REF-SPEC URN）。
2. 回填：用**确定性、可复核**的三级匹配从导读正文里提取锚点，写回该列：
   - T1 引文：正文中「」『』“”"" 包裹、去标点后 ≥6 字的片段，在原文中逐字命中 → 块级 URN
   - T2 篇名：散文里直接提到的章名（如"子路第十三"）→ 章级 URN
   - T3 术语：导读 keywords[].term 在原文中出现 → 章级 URN（每术语限 3 章，防泛词淹没）
   三条都不命中就留空数组——不做任何推测性填充，宁可空也不编锚点。

用法
----
    python scripts/migrate_citations.py            # dry-run，只打印将写入什么
    python scripts/migrate_citations.py --apply    # 备份 + 迁移 + 回填
    python scripts/migrate_citations.py --verify   # 只校验现有 citations 是否都能解析到真实章节
回滚：脚本会打印备份文件路径，直接覆盖回来即可（SQLite <3.35 不支持 DROP COLUMN）。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "guji.db"
MAX_CITES = 12
PUNCT = re.compile(r"[\s\u3000，。、；：？！「」『』“”‘’（）()《》〈〉【】…—·,.;:?!\"'\-]")
QUOTE = re.compile(r"[「『“\"]([^「」『』“”\"]{6,60})[」』”\"]")
REF_RE = re.compile(r"^dc:([^/]+)/c(\d+)(?:/b(\d+))?(?:/k(\d+))?$")


def norm(s: str) -> str:
    return PUNCT.sub("", s or "")


def parse_ref(urn: str):
    m = REF_RE.match(urn or "")
    if not m:
        return None
    return {
        "workKey": m.group(1),
        "chapNo": int(m.group(2)),
        "block": int(m.group(3)) if m.group(3) else None,
        "item": int(m.group(4)) if m.group(4) else None,
    }


def has_column(conn, table: str, col: str) -> bool:
    return any(r[1] == col for r in conn.execute(f"PRAGMA table_info({table})"))


def blocks_text(ch) -> list[str]:
    try:
        blocks = json.loads(ch["blocks"] or "[]")
    except Exception:
        return []
    return [str(b.get("x") or "") for b in blocks]


def derive(conn, guide) -> tuple[list[str], list[dict]]:
    """返回 (citations, 证据明细)。证据明细仅用于 dry-run 人工复核，不入库。"""
    work_id = guide["work_id"]
    try:
        payload = json.loads(guide["result"] or "{}")
    except Exception:
        payload = {}
    content = payload.get("content", payload)
    gtext = json.dumps(content, ensure_ascii=False)

    chapters = conn.execute(
        "SELECT id, title, ref, blocks, clean_text FROM chapters "
        "WHERE work_id=? AND ref IS NOT NULL ORDER BY id",
        (work_id,),
    ).fetchall()
    if not chapters:
        return [], []

    cites: list[str] = []
    evidence: list[dict] = []

    def push(urn: str, tier: str, why: str):
        if urn and urn not in cites and len(cites) < MAX_CITES:
            cites.append(urn)
            evidence.append({"tier": tier, "urn": urn, "why": why[:60]})

    # T1 引文逐字命中（块级）
    for raw in QUOTE.findall(gtext):
        q = norm(raw)
        if len(q) < 6:
            continue
        done = False
        for ch in chapters:
            for bi, bt in enumerate(blocks_text(ch), start=1):
                if q and q in norm(bt):
                    push(f"{ch['ref']}/b{bi}", "quote", raw)
                    done = True
                    break
            if done:
                break
        if len(cites) >= MAX_CITES:
            break

    # T2 篇名提及（章级）
    for ch in chapters:
        name = (ch["title"] or "").split("/")[-1].strip()
        if len(name) >= 2 and name in gtext:
            push(ch["ref"], "title", name)

    # T3 术语命中（章级，每术语限 3 章）
    terms = []
    kws = content.get("keywords") if isinstance(content, dict) else None
    if isinstance(kws, list):
        for k in kws:
            if isinstance(k, dict) and k.get("term"):
                terms.append(str(k["term"]))
    for t in terms:
        hit = 0
        for ch in chapters:
            if t and t in (ch["clean_text"] or ""):
                push(ch["ref"], "term", t)
                hit += 1
                if hit >= 3:
                    break

    return cites, evidence


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="实际写入（默认 dry-run）")
    ap.add_argument("--verify", action="store_true", help="只校验现有 citations")
    args = ap.parse_args()

    if not DB.exists():
        sys.exit(f"数据库不存在：{DB}")
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # 合法 URN 集合，用于校验
    valid = {r["ref"] for r in conn.execute("SELECT ref FROM chapters WHERE ref IS NOT NULL")}

    if args.verify:
        if not has_column(conn, "ai_guides", "citations"):
            sys.exit("ai_guides 尚无 citations 列")
        bad = 0
        total = 0
        for g in conn.execute("SELECT work_id, method_id, citations FROM ai_guides"):
            try:
                arr = json.loads(g["citations"] or "[]")
            except Exception:
                print(f"  ✗ {g['work_id']}/{g['method_id']} citations 不是合法 JSON")
                bad += 1
                continue
            for urn in arr:
                total += 1
                base = "/".join(urn.split("/")[:2])
                if urn not in valid and base not in valid:
                    print(f"  ✗ 无法解析：{g['work_id']}/{g['method_id']} → {urn}")
                    bad += 1
        print(f"[verify] 共 {total} 条引用，异常 {bad} 条")
        return

    has_col = has_column(conn, "ai_guides", "citations")
    print(f"[info] citations 列：{'已存在' if has_col else '不存在（将新增）'}")

    rows = conn.execute(
        "SELECT work_id, method_id, result" + (", citations" if has_col else "") + " FROM ai_guides "
        "ORDER BY work_id, method_id"
    ).fetchall()

    plan = []
    for g in rows:
        cites, evidence = derive(conn, g)
        plan.append((g["work_id"], g["method_id"], cites, evidence))

    filled = sum(1 for p in plan if p[2])
    print(f"[info] 12 篇导读中可确定性提取锚点：{filled}/{len(plan)} 篇")
    for work_id, method_id, cites, evidence in plan:
        print(f"  · {work_id}/{method_id}  {len(cites)} 条")
        for e in evidence:
            print(f"      [{e['tier']}] {e['urn']}  ← {e['why']}")

    if not args.apply:
        print("\n[dry-run] 未写入。确认无误后加 --apply 执行。")
        return

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DB.with_name(f"guji.db.bak-citations-{stamp}")
    conn.close()
    shutil.copy2(DB, backup)
    print(f"[backup] {backup}")

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    if not has_col:
        conn.execute("ALTER TABLE ai_guides ADD COLUMN citations TEXT DEFAULT '[]'")
        print("[migrate] 已新增 ai_guides.citations")
    n = 0
    for work_id, method_id, cites, _ in plan:
        conn.execute(
            "UPDATE ai_guides SET citations=? WHERE work_id=? AND method_id=?",
            (json.dumps(cites, ensure_ascii=False), work_id, method_id),
        )
        n += 1
    conn.commit()
    print(f"[apply] 已写入 {n} 篇导读 citations")
    print(f"[rollback] 如需回滚：copy \"{backup}\" \"{DB}\"")


if __name__ == "__main__":
    main()
