#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_ref.py — 维点图书馆 P0-1「稳定引用层」迁移脚本

目标
----
为 chapters 表增加可长期引用的稳定标识 ref（章节级 URN），与自增主键 id 彻底解耦。

规范（REF-SPEC v1）
------------------
    dc:<work-key>/c<chapNo>          章节级
    dc:<work-key>/c<chapNo>/b<block> 块级（不入库，由前端按块下标派生）
    dc:<work-key>/c<chapNo>/b<block>/k<item>  句元级（预留）

    work-key = Wikidata QID（如 Q276015）；缺失时退化为 `x` + sha1(seed_title)[:8]
    chapNo   = 该书内按 (ord, id) 升序的 1-based 序号，零填充 3 位
               注意：不是 chapters.id，重导入不会漂移

用法
----
    python scripts/migrate_ref.py                # dry-run：只读，打印规范/样例/校验
    python scripts/migrate_ref.py --apply        # 备份 → 加列 → 回填 → 唯一索引 → 复核
    python scripts/migrate_ref.py --verify       # 仅复核当前库
    python scripts/migrate_ref.py --export out.json   # 导出 chapter_id -> ref 映射

回滚
----
    python scripts/rollback_ref.py               # 逻辑回滚：DROP INDEX + DROP COLUMN
    python scripts/rollback_ref.py --restore <bak>  # 文件级恢复

安全
----
    * 全程不触碰 chapters.id、不动既有列、不重排 ord
    * --apply 前自动备份整库到 temp/backups/
    * ref 为纯派生字段：即使无备份，按同一算法重算即完全复原
"""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import time

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "guji.db")
BACKUP_DIR = os.environ.get("REF_BACKUP_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "temp", "backups"
)

PREFIX = "dc"
COL = "ref"
IDX = "idx_chapters_ref"


# ---------- 规范实现 ----------

def work_key(wikidata_qid, seed_title):
    qid = (wikidata_qid or "").strip()
    if qid:
        return qid
    h = hashlib.sha1((seed_title or "untitled").encode("utf-8")).hexdigest()[:8]
    return "x" + h


def chap_no(i):
    return f"{i:03d}"


def chapter_ref(wk, n):
    return f"{PREFIX}:{wk}/c{chap_no(n)}"


def block_ref(ch_ref, block):
    return f"{ch_ref}/b{int(block):03d}"


def parse_ref(urn):
    """解析 URN，返回 (work_key, chap_no:int|None, block:int|None, item:int|None)；非法返回 None。"""
    if not isinstance(urn, str) or not urn.startswith(PREFIX + ":"):
        return None
    body = urn[len(PREFIX) + 1:]
    segs = body.split("/")
    if not segs or not segs[0]:
        return None
    wk = segs[0]
    cn = bn = it = None
    for s in segs[1:]:
        if s.startswith("c") and s[1:].isdigit():
            cn = int(s[1:])
        elif s.startswith("b") and s[1:].isdigit():
            bn = int(s[1:])
        elif s.startswith("k") and s[1:].isdigit():
            it = int(s[1:])
        else:
            return None
    return (wk, cn, bn, it)


# ---------- 计算 ----------

def build_rows(con):
    """返回 [(chapter_id, ref, work_key, chap_no, work_id, seed_title, ord)]，按书内顺序编号。"""
    cur = con.cursor()
    works = cur.execute("SELECT id, seed_title, wikidata_qid FROM works ORDER BY id").fetchall()
    wk_map = {w[0]: work_key(w[2], w[1]) for w in works}
    title_map = {w[0]: w[1] for w in works}

    out = []
    for wid in wk_map:
        rows = cur.execute(
            "SELECT id, ord FROM chapters WHERE work_id=? ORDER BY ord ASC, id ASC", (wid,)
        ).fetchall()
        for i, (cid, _ord) in enumerate(rows, start=1):
            out.append((cid, chapter_ref(wk_map[wid], i), wk_map[wid], i, wid, title_map[wid], _ord))
    return out


def cols_of(con, table):
    return [r[1] for r in con.execute(f"PRAGMA table_info({table})")]


def indexes_of(con):
    return [r[1] for r in con.execute("PRAGMA index_list(chapters)")]


# ---------- 校验 ----------

def verify(con, planned=None):
    problems = []
    cur = con.cursor()
    cols = cols_of(con, "chapters")
    has_col = COL in cols
    if not has_col:
        problems.append("chapters.ref 列不存在（尚未 apply）")

    total = cur.execute("SELECT COUNT(*) FROM chapters").fetchone()[0]
    stats = {"chapters": total, "has_col": has_col}

    if has_col:
        nulls = cur.execute("SELECT COUNT(*) FROM chapters WHERE ref IS NULL OR ref=''").fetchone()[0]
        distinct = cur.execute("SELECT COUNT(DISTINCT ref) FROM chapters").fetchone()[0]
        stats.update({"ref_null": nulls, "ref_distinct": distinct})
        if nulls:
            problems.append(f"ref 空值 {nulls} 条")
        if distinct != total - nulls:
            problems.append(f"ref 重复：distinct={distinct} 应为 {total - nulls}")

    # 与算法重算结果比对（幂等性 / 正确性）
    rows = build_rows(con)
    stats["planned"] = len(rows)
    if has_col:
        cur_ref = dict(cur.execute("SELECT id, ref FROM chapters").fetchall())
        diff = [(cid, ref, cur_ref.get(cid)) for cid, ref, *_ in rows if cur_ref.get(cid) != ref]
        stats["mismatch_vs_algorithm"] = len(diff)
        if diff:
            problems.append(f"与算法重算不一致 {len(diff)} 条，例如 {diff[:3]}")

    # URN 可解析性
    bad_parse = [r[1] for r in rows if parse_ref(r[1]) is None]
    if bad_parse:
        problems.append(f"URN 解析失败 {len(bad_parse)} 条")

    # 唯一索引
    idxs = indexes_of(con)
    stats["unique_index"] = IDX in idxs
    if has_col and IDX not in idxs:
        problems.append("唯一索引缺失")

    stats["problems"] = problems
    return stats


# ---------- 主流程 ----------

def dry_run(con):
    rows = build_rows(con)
    print("REF-SPEC v1")
    print("  章节: dc:<work-key>/c<chapNo>")
    print("  块级: dc:<work-key>/c<chapNo>/b<block>")
    print(f"\n待生成 {len(rows)} 条，示例（每部书首章）：")
    seen = set()
    shown = 0
    for cid, ref, wk, n, wid, title, ordv in rows:
        if wid in seen:
            continue
        seen.add(wid)
        print(f"  {title:<12} id={cid:<6} ord={ordv:<12} -> {ref}")
        shown += 1
        if shown >= 10:
            break
    print("\n块级示例：", block_ref(rows[0][1], 3), " / ", block_ref(rows[0][1], 12))
    print("解析反查：", parse_ref(block_ref(rows[0][1], 3)))
    print("\n--- 当前库状态 ---")
    print(json.dumps(verify(con), ensure_ascii=False, indent=1))
    print("\n（dry-run 未写入任何数据。执行加 --apply）")


def apply(con):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    bak = os.path.join(BACKUP_DIR, f"guji.db.{ts}.bak")
    # 用 SQLite 在线备份 API，避免 WAL 不一致
    with sqlite3.connect(bak) as bcon:
        con.backup(bcon)
    print(f"[1/5] 已备份 -> {bak} ({os.path.getsize(bak)/1048576:.1f} MB)")

    cols = cols_of(con, "chapters")
    cur = con.cursor()
    try:
        cur.execute("BEGIN IMMEDIATE")
        if COL not in cols:
            cur.execute(f"ALTER TABLE chapters ADD COLUMN {COL} TEXT")
            print(f"[2/5] 已新增列 chapters.{COL}（既有列与 id 未变）")
        else:
            print(f"[2/5] 列已存在，跳过新增（幂等）")

        rows = build_rows(con)
        cur.executemany("UPDATE chapters SET ref=? WHERE id=?", [(r[1], r[0]) for r in rows])
        print(f"[3/5] 已回填 {len(rows)} 条 ref")

        cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {IDX} ON chapters({COL})")
        print(f"[4/5] 已建唯一索引 {IDX}")

        con.commit()
        print("[5/5] 提交完成")
    except Exception as e:
        con.rollback()
        print(f"[FATAL] 已回滚事务：{e}")
        raise

    st = verify(con)
    print("\n--- 复核 ---")
    print(json.dumps(st, ensure_ascii=False, indent=1))
    return st, bak


def export_map(con, path):
    rows = build_rows(con)
    data = {
        "spec": "dc-urn/1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "count": len(rows),
        "items": [
            {"chapter_id": cid, "ref": ref, "work_key": wk, "chap_no": n, "work_id": wid,
             "work_title": title, "ord": ordv}
            for cid, ref, wk, n, wid, title, ordv in rows
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"已导出 {len(rows)} 条 -> {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--export", metavar="PATH")
    ap.add_argument("--db", default=DB)
    a = ap.parse_args()

    if not os.path.exists(a.db):
        sys.exit(f"找不到数据库：{a.db}")

    con = sqlite3.connect(a.db)
    try:
        if a.apply:
            st, bak = apply(con)
            print(f"\n回滚：python scripts/rollback_ref.py   （或 --restore \"{bak}\"）")
            if st["problems"]:
                sys.exit(1)
        elif a.verify:
            print(json.dumps(verify(con), ensure_ascii=False, indent=1))
        else:
            dry_run(con)
        if a.export:
            export_map(con, a.export)
    finally:
        con.close()


if __name__ == "__main__":
    main()
