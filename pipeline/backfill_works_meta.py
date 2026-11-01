#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backfill_works_meta.py — 新增古籍元数据对齐（works 表）

作用
----
把批 1~3 新入库的 38 部（work_id >= 101）在 works 层对齐既有 50 部的交付标准：

1. bu 归一：经/史/子/集 → 经部/史部/子部/集部（前端按 bu 做筛选，口径必须统一）
2. author / dynasty 补全（旧书 50/50 有值，新书原为 0/38）
3. ws_title 繁体标题生成（opencc s2tw，仅补空值，不覆盖旧值）

字段口径与旧书保持一致：dynasty 用细分朝代（先秦/战国/西汉/唐/北宋/南宋/明/清 等）。

用法
----
    python pipeline/backfill_works_meta.py            # dry-run
    python pipeline/backfill_works_meta.py --apply    # 写库
"""
import argparse
import os
import sqlite3
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "data", "guji.db")

BU_MAP = {"经": "经部", "史": "史部", "子": "子部", "集": "集部"}

# seed_title -> (author, dynasty)
META = {
    "坛经": ("慧能说法，法海集记", "唐"),
    "明夷待访录": ("黄宗羲", "清"),
    "传习录": ("王守仁", "明"),
    "商君书": ("商鞅及后学", "战国"),
    "人间词话": ("王国维", "清"),
    "二十四诗品": ("司空图", "唐"),
    "文史通义": ("章学诚", "清"),
    "天演论": ("严复译", "清"),
    "周礼": ("佚名", "先秦"),
    "仪礼": ("佚名", "先秦"),
    "公羊传": ("公羊高", "先秦"),
    "谷梁传": ("穀梁赤", "先秦"),
    "通典": ("杜佑", "唐"),
    "文献通考": ("马端临", "元"),
    "东京梦华录": ("孟元老", "北宋"),
    "洛阳伽蓝记": ("杨衒之", "北魏"),
    "廿二史札记": ("赵翼", "清"),
    "读通鉴论": ("王夫之", "清"),
    "日知录": ("顾炎武", "清"),
    "三国演义": ("罗贯中", "明"),
    "红楼梦": ("曹雪芹", "清"),
    "儒林外史": ("吴敬梓", "清"),
    "聊斋志异": ("蒲松龄", "清"),
    "牡丹亭": ("汤显祖", "明"),
    "花间集": ("赵崇祚编", "五代"),
    "乐府诗集": ("郭茂倩编", "北宋"),
    "管子": ("管仲及稷下学者", "先秦"),
    "列子": ("列御寇及后学", "先秦"),
    "九章算术": ("佚名", "西汉"),
    "近思录": ("朱熹、吕祖谦编", "南宋"),
    "春秋繁露": ("董仲舒", "西汉"),
    "公孙龙子": ("公孙龙", "战国"),
    "纪效新书": ("戚继光", "明"),
    "徐霞客游记": ("徐弘祖", "明"),
    "海国图志": ("魏源", "清"),
    "幼学琼林": ("程登吉撰，邹圣脉增补", "清"),
    "三字经": ("王应麟", "南宋"),
    "金刚经": ("鸠摩罗什译", "后秦"),
}


def to_trad(s):
    try:
        from opencc import OpenCC
    except Exception:
        return None
    return OpenCC("s2twp").convert(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    rows = cur.execute(
        "SELECT id, seed_title, bu, author, dynasty, ws_title FROM works WHERE id >= 101 ORDER BY id"
    ).fetchall()

    plan = []
    for r in rows:
        title = r["seed_title"]
        bu = BU_MAP.get((r["bu"] or "").strip(), r["bu"])
        author, dynasty = META.get(title, (r["author"], r["dynasty"]))
        ws = r["ws_title"]
        if not ws:
            ws = to_trad(title)
        missing = title not in META
        plan.append((r["id"], title, bu, author, dynasty, ws, missing))

    print("| id | 书名 | bu | author | dynasty | ws_title |")
    print("|---|---|---|---|---|---|")
    for p in plan:
        print("| %d | %s | %s | %s | %s | %s |" % (p[0], p[1], p[2], p[3] or "-", p[4] or "-", p[5] or "-"))

    unmapped = [p[1] for p in plan if p[6]]
    print("\n未配置元数据：", unmapped or "无")
    print("待更新：%d 部" % len(plan))

    if not args.apply:
        print("[dry-run] 未写库，加 --apply 生效")
        return

    for pid, title, bu, author, dynasty, ws, _ in plan:
        cur.execute(
            "UPDATE works SET bu=?, author=COALESCE(NULLIF(author,''), ?), "
            "dynasty=COALESCE(NULLIF(dynasty,''), ?), "
            "ws_title=COALESCE(NULLIF(ws_title,''), ?) WHERE id=?",
            (bu, author, dynasty, ws, pid),
        )
    con.commit()

    chk = cur.execute(
        "SELECT COUNT(*) FROM works WHERE id>=101 AND (author IS NULL OR author='' )"
    ).fetchone()[0]
    chk2 = cur.execute(
        "SELECT COUNT(*) FROM works WHERE id>=101 AND (dynasty IS NULL OR dynasty='')"
    ).fetchone()[0]
    chk3 = cur.execute(
        "SELECT COUNT(*) FROM works WHERE id>=101 AND bu IN ('经','史','子','集')"
    ).fetchone()[0]
    print("[apply] 写入完成；author 空缺=%d，dynasty 空缺=%d，bu 未归一=%d" % (chk, chk2, chk3))


if __name__ == "__main__":
    main()
