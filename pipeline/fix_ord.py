# -*- coding: utf-8 -*-
"""P0 篇目序兜底：把 ord 未命中的章节归位，并把重复/附录章节移出正文序列。

规则（按顺序执行，幂等）：
  1. 单章整本（全书仅 1 章且可阅读）→ ord=1
  2. 卷次合卷页（标题形如 /01 … /20 且 ord_group='合卷页'）→ 负 ord 保序，移入附文折叠区
  3. 附录词表命中（序說/知道/提要/校勘/跋…）→ 负 ord，ord_group='附文'
  4. 同书内 ord 重复（异名同篇，如 揚榷/揚權）→ 保留字数最多者，其余负 ord + '異本'
  5. 剩余仍无 ord → 按 id 顺序接在正文末尾，ord_source='fallback'

用法：python pipeline/fix_ord.py [--dry-run]
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "guji.db"
STEP = 1_000_000_000

APPENDIX_WORDS = ("序說", "序说", "敘錄", "叙录", "提要", "目錄", "目录", "校勘", "後記", "后记", "附錄", "附录", "跋", "知道")
_RE_VOL = re.compile(r"/(\d{1,2})$")


def _is_appendix(title: str) -> bool:
    """整名末段命中附录词才算，避免「狼跋」「序志」等正篇被误伤。"""
    tail = re.split(r"[/·・]", (title or "").strip())[-1].strip()
    return any(tail == w for w in APPENDIX_WORDS)


def main() -> int:
    dry = "--dry-run" in sys.argv
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    log: list[str] = []

    works = conn.execute("SELECT id, seed_title FROM works ORDER BY id").fetchall()
    total_fixed = 0

    for w in works:
        rows = conn.execute(
            "SELECT id, title, ord, ord_group, chars, quality FROM chapters WHERE work_id=? ORDER BY id",
            (w["id"],),
        ).fetchall()
        if not rows:
            continue
        readable = [r for r in rows if r["quality"] != "unavailable" and (r["chars"] or 0) > 0]
        updates: list[tuple] = []

        # 1) 单章整本
        if len(rows) == 1 and rows[0]["ord"] is None and (rows[0]["chars"] or 0) > 100:
            updates.append((STEP, "single", rows[0]["id"]))
            log.append(f"[单章整本] {w['seed_title']} · {rows[0]['title']} → ord=1")
            rows = [dict(rows[0], ord=STEP)]

        # 2) 卷次合卷页 → 负 ord（保住卷序，移出正文）
        vols = [r for r in rows if r["ord"] is None and r["ord_group"] == "合卷页"]
        if vols:
            def _vkey(x):
                m = _RE_VOL.search(x["title"] or "")
                return (0, int(m.group(1))) if m else (1, 0)
            ordered = sorted(vols, key=_vkey)
            n = len(ordered)
            for i, r in enumerate(ordered, start=1):
                updates.append((-STEP * (n - i + 1), "卷次", r["id"]))
            log.append(f"[合卷页] {w['seed_title']} · {n} 卷移入附文折叠区")
            rows = [dict(r, ord=-1) if r["id"] in {v["id"] for v in vols} else r for r in rows]

        # 3) 附录词表
        for r in rows:
            if r["ord"] is not None and r["ord"] > 0 and _is_appendix(r["title"]):
                updates.append((-STEP, "附录", r["id"]))
                log.append(f"[附录] {w['seed_title']} · {r['title']} → 移入附文")

        # 4) 同书 ord 重复 → 保留最长者
        by_ord: dict[int, list] = {}
        for r in rows:
            if isinstance(r["ord"], int) and r["ord"] > 0:
                by_ord.setdefault(r["ord"], []).append(r)
        for o, group in by_ord.items():
            if len(group) < 2:
                continue
            keep = max(group, key=lambda x: x["chars"] or 0)
            for r in group:
                if r["id"] != keep["id"]:
                    updates.append((-STEP * 2, "異本", r["id"]))
                    log.append(f"[異本] {w['seed_title']} · {r['title']}（保留 {keep['title']}）")

        # 4.5) 消歧页/残片：标题被同书更长的标题包含（如「無衣」⊂「無衣 (唐風)」）→ 異本
        all_titles = [(r["title"] or "") for r in rows]
        for r in rows:
            if r["ord"] is None:
                t = (r["title"] or "").split("/")[-1].strip()
                if not t:
                    continue
                longer = [x for x in all_titles
                          if x != (r["title"] or "") and x.split("/")[-1].strip().startswith(t + " ")
                          or x.split("/")[-1].strip().startswith(t + "(") or x.split("/")[-1].strip().startswith(t + "（")]
                if longer:
                    updates.append((-STEP * 2, "異本", r["id"]))
                    log.append(f"[異本-消歧] {w['seed_title']} · {r['title']}（已有 {longer[0]}）")

        # 5) 剩余兜底：优先落到同分组末尾，其次按 id 邻居插值，最后接正文末尾
        assigned = {u[2] for u in updates}
        rest = [r for r in readable if (r["ord"] is None and r["id"] not in assigned)]
        if rest:
            pos_ords = [r["ord"] for r in rows if isinstance(r["ord"], int) and r["ord"] > 0 and r["id"] not in assigned]
            base = (max(pos_ords) if pos_ords else 0)
            group_max: dict[str, int] = {}
            for r in rows:
                if isinstance(r["ord"], int) and r["ord"] > 0 and r["ord_group"]:
                    group_max[r["ord_group"]] = max(group_max.get(r["ord_group"], 0), r["ord"])
            for j, r in enumerate(sorted(rest, key=lambda x: x["id"]), start=1):
                g = r["ord_group"] or ""
                if g and g in group_max:
                    new_ord, src = group_max[g] + STEP // 1000, "组内兜底"
                else:
                    prev = [x["ord"] for x in rows
                            if isinstance(x["ord"], int) and x["ord"] > 0 and x["id"] < r["id"]]
                    new_ord, src = ((max(prev) + STEP // 1000) if prev else (base + STEP * j)), "fallback"
                updates.append((new_ord, src, r["id"]))
                log.append(f"[{src}] {w['seed_title']} · {r['title']} → ord={new_ord}")

        # 6) 负 ord 去重：附文/異本/卷次可能撞同一档位，按出现顺序递增错位，保证组内稳定排序
        last: dict[int, tuple] = {}
        for val, src, cid in updates:
            last[cid] = (val, src, cid)
        taken = {r["ord"] for r in rows if isinstance(r["ord"], int) and r["ord"] < 0}
        uniq: list[tuple] = []
        for val, src, cid in last.values():
            if val < 0:
                while val in taken:
                    val += 1
                taken.add(val)
            uniq.append((val, src, cid))
        updates = uniq

        if updates:
            total_fixed += len(updates)
            if not dry:
                conn.executemany("UPDATE chapters SET ord=?, ord_source=? WHERE id=?", updates)

    if not dry:
        conn.commit()

    print(f"[fix_ord] 修正 {total_fixed} 章 ({'dry-run' if dry else '已写库'})")
    for line in log:
        print("  " + line)

    # 复核
    print("\n=== 复核 ===")
    print("  仍无 ord:", conn.execute("SELECT COUNT(*) FROM chapters WHERE ord IS NULL").fetchone()[0])
    print("  正文可阅读章:", conn.execute(
        "SELECT COUNT(*) FROM chapters WHERE ord > 0 AND quality != 'unavailable'").fetchone()[0])
    print("  附文/異本:", conn.execute("SELECT COUNT(*) FROM chapters WHERE ord < 0").fetchone()[0])
    for r in conn.execute(
        "SELECT w.seed_title, COUNT(*) n FROM chapters c JOIN works w ON w.id=c.work_id "
        "WHERE c.ord IS NULL GROUP BY w.id"
    ):
        print(f"   未定位: {r[0]} {r[1]} 章")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
