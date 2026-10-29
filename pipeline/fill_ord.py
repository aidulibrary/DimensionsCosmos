# -*- coding: utf-8 -*-
"""P0 篇目序还原：写入 chapters.ord / ord_group（零算力，纯规则 + 人工表）。

判定优先级：
  1) 前置附文（序跋/校勘/进书表等）→ ord 取负值，排全书最前
  2) 标题自带编号（卷001 / 卷第1 / 01 / 卷一 / 第十二 / 素問第一卷）→ 解析
  3) 正文自带卦序（周易「第X卦」）→ 解析
  4) 人工权威表（ord_tables.py）：周易十翼 / 诗经三级 / 诸子篇次
  5) 皆不命中 → ord=NULL 并报告，绝不臆造
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ord_tables import (  # noqa: E402
    CANON,
    EXTRA_ORD,
    FRONT_PAT,
    FRONT_SUFFIX,
    NAME_ALIAS,
    SJ_GROUP_ALIAS,
    ZHUAN_ORD,
    expand_shijing,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "guji.db")

CN_NUM = {"零": 0, "〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
          "六": 6, "七": 7, "八": 8, "九": 9, "壹": 1, "貳": 2, "參": 3,
          "肆": 4, "伍": 5, "陸": 6, "柒": 7, "捌": 8, "玖": 9}


def cn2int(s: str):
    if not s:
        return None
    if s.isdigit():
        return int(s)
    total, section, num = 0, 0, 0
    for ch in s:
        if ch in CN_NUM:
            num = CN_NUM[ch]
        elif ch in "十拾":
            section += (num or 1) * 10
            num = 0
        elif ch in "百佰":
            section += (num or 1) * 100
            num = 0
        elif ch in "千仟":
            section += (num or 1) * 1000
            num = 0
        else:
            return None
    return total + section + num


# ------------------------------------------------------------------ 1) 标题编号
NUM_TITLE = {
    13: r"卷\s*(\d+)",                        # 史記/卷001
    16: r"卷\s*(\d+)",                        # 三國志/卷01
    17: r"卷\s*(\d+)",                        # 資治通鑑/卷001
    20: r"卷\s*(\d+)",                        # 貞觀政要/卷01
    21: r"^(\d+)$",                           # 水經注/01
    39: r"卷\s*(\d+)",                        # 夢溪筆談/卷01
    50: r"卷\s*(\d+)",                        # 杜工部集/卷08
    32: r"卷\s*第?\s*(\d+)",                   # 顏氏家訓/卷第1
    22: r"卷\s*([一二三四五六七八九十百]+)",     # 史通/卷一
    1: r"第([一二三四五六七八九十]+)$",         # 論語/先進第十一
}
NUM_TITLE_FH = re.compile(r"卷\s*(\d+)\s*(上|下)?")          # 後漢書/卷1上
NUM_TITLE_HN = re.compile(r"(素問|靈樞)\s*第?\s*([一二三四五六七八九十百\d]+)\s*卷")


def parse_number_ord(work_id: int, title: str):
    leaf = title.split("/")[-1].strip()
    if work_id == 15:
        m = NUM_TITLE_FH.search(leaf)
        if m:
            return (int(m.group(1)), 1 if m.group(2) == "下" else 0), ""
        return None
    if work_id == 36:
        m = NUM_TITLE_HN.search(leaf)
        if m:
            g = 0 if m.group(1) == "素問" else 1
            v = cn2int(m.group(2))
            if v:
                return (g, v, 0), m.group(1)
        return None
    pat = NUM_TITLE.get(work_id)
    if not pat:
        return None
    m = re.search(pat, leaf)
    if not m:
        return None
    v = cn2int(m.group(1))
    return ((v, 0), "") if v else None


# ------------------------------------------------------------------ 诗经索引
SJ = expand_shijing()
SJ_KEY = {(g, grp, nm): o for o, g, grp, nm in SJ}
SJ_BY_NAME = {}
for o, g, grp, nm in SJ:
    SJ_BY_NAME.setdefault(nm, []).append(o)
_GATE_OF_GROUP = {}
for o, g, grp, nm in SJ:
    _GATE_OF_GROUP.setdefault(grp, g)
_GATE_OF_GROUP.update({"周南": "風", "召南": "風", "邶": "風", "鄘": "風", "衞": "風",
                       "王": "風", "鄭": "風", "齊": "風", "魏": "風", "唐": "風",
                       "秦": "風", "陳": "風", "檜": "風", "曹": "風", "豳": "風"})


def norm_group(gate: str, raw: str) -> str:
    raw = raw.strip().replace("⋅", "‧")
    raw = SJ_GROUP_ALIAS.get(raw, raw)
    if gate == "頌":
        if raw == "清廟之什":
            return "周頌清廟"
        if raw == "臣工之什":
            return "周頌臣工"
        if raw == "閔予小子之什":
            return "周頌閔予"
        if raw in ("周頌", "魯頌", "商頌"):
            return raw
        return "周頌" + raw
    return raw


def sj_ord_from_heading(head: str):
    parts = re.split(r"[‧·]", head)
    if len(parts) < 2:
        return None
    name = parts[-1].strip()
    h = parts[0].strip()
    if h.startswith("國風") or "國風" in h:
        gate = "風"
    elif h.startswith("小雅"):
        gate = "小雅"
    elif h.startswith("大雅"):
        gate = "大雅"
    elif "頌" in h:
        gate = "頌"
    else:
        return None
    group = norm_group(gate, parts[1].strip())
    o = SJ_KEY.get((gate, group, name))
    if o:
        return o
    cands = [x for x in SJ_BY_NAME.get(name, []) if SJ[x - 1][1] == gate]
    return cands[0] if len(cands) == 1 else None


# ------------------------------------------------------------------ 主流程
def ensure_columns(cur):
    cols = {r[1] for r in cur.execute("PRAGMA table_info(chapters)")}
    if "ord" not in cols:
        cur.execute("ALTER TABLE chapters ADD COLUMN ord INTEGER")
    if "ord_group" not in cols:
        cur.execute("ALTER TABLE chapters ADD COLUMN ord_group TEXT")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chapters_work_ord ON chapters(work_id, ord)")


def flatten(v):
    """元组序 → 可排序整数（高位主序，低位次序）。"""
    if isinstance(v, tuple):
        f = 0
        for i, x in enumerate(v):
            f += int(x) * (1000 ** (3 - i))
        return int(f)
    return int(v)


WID2CANON = {2: "孟子", 24: "莊子", 25: "荀子", 27: "墨子", 33: "世說新語",
             34: "山海經", 46: "文心雕龍", 30: "淮南子", 26: "韓非子", 8: "周易"}

# 韓非子的合卷页/总目页：内容与分篇重复，不参与篇序
CANON_HFZ_CONTAINER = {"外儲說"}


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    ensure_columns(cur)

    works = {r["id"]: r["seed_title"] for r in cur.execute("select id, seed_title from works")}
    rows = cur.execute("select id, work_id, title, text, blocks from chapters").fetchall()

    hit, miss, front_cnt = 0, {}, {}
    src_stat = {}

    for r in rows:
        wid, title = r["work_id"], r["title"] or ""
        leaf = title.split("/")[-1].strip()
        leaf = re.sub(r"[（(].*?[）)]", "", leaf).strip()
        ordv, grouptag, src = None, "", None

        # ---- 1) 前置附文（序跋/校勘/进书表，一律排最前）
        is_front = leaf and (
            any(leaf.startswith(p) or leaf == p for p in FRONT_PAT)
            or (len(leaf) >= 3 and leaf.endswith(FRONT_SUFFIX))
        )
        if is_front:
            n = front_cnt.get(wid, 0) + 1
            front_cnt[wid] = n
            ordv, src, grouptag = -n, "front-matter", "附文"

        # ---- 2) 标题编号
        if ordv is None:
            num = parse_number_ord(wid, title)
            if num:
                ordv, grouptag = num[0], num[1]
                src = "title-number"

        # ---- 3) 周易卦序 / 十翼
        if ordv is None and wid == 8:
            nm = NAME_ALIAS.get(leaf, leaf)
            if nm in ZHUAN_ORD:
                ordv, src, grouptag = ZHUAN_ORD[nm], "canon-zhuan", "易傳"
            else:
                m = re.search(r"第\s*([一二三四五六七八九十百]+)\s*卦", r["text"] or "")
                v = cn2int(m.group(1)) if m else None
                if v:
                    ordv, src, grouptag = (v, 0), "text-gua", "易經"

        # ---- 4) 诗经
        if ordv is None and wid == 5:
            b = json.loads(r["blocks"] or "[]")
            h2 = next((x["x"] for x in b if x["t"] == "h" and x.get("l") == 2), None)
            if h2:
                o = sj_ord_from_heading(h2)
                if o:
                    ordv, src, grouptag = o, "canon-shijing", SJ[o - 1][2]
            if ordv is None:
                m = re.search(r"[（(]([^）)]+)[）)]", title.split("/")[-1])
                hint = m.group(1).strip() if m else None
                cands = SJ_BY_NAME.get(leaf, [])
                if hint:
                    gate = _GATE_OF_GROUP.get(hint, "風")
                    o = SJ_KEY.get((gate, norm_group(gate, hint), leaf))
                    if o:
                        ordv, src, grouptag = o, "canon-shijing", SJ[o - 1][2]
                if ordv is None and len(cands) == 1:
                    ordv, src, grouptag = cands[0], "canon-shijing-unique", SJ[cands[0] - 1][2]

        # ---- 5) 人工表
        if ordv is None and wid in WID2CANON and wid != 8:
            cname = WID2CANON[wid]
            seq = CANON.get(cname, [])
            nm = NAME_ALIAS.get(leaf, leaf)
            if nm in seq:
                ordv, src = seq.index(nm) + 1, "canon"

        # ---- 5b) 个别补录（无卷号但篇次明确）
        if ordv is None:
            m = EXTRA_ORD.get(wid)
            if m and leaf in m:
                ordv, src, grouptag = m[leaf], "extra", ""

        # ---- 6) 未命中
        if ordv is None:
            note = "合卷页" if (wid == 26 and (leaf.isdigit() or leaf in CANON_HFZ_CONTAINER)) else None
            miss.setdefault(wid, []).append(title)
            cur.execute("update chapters set ord=NULL, ord_group=? where id=?",
                        (grouptag or note, r["id"]))
            continue

        hit += 1
        src_stat[src] = src_stat.get(src, 0) + 1
        cur.execute("update chapters set ord=?, ord_group=? where id=?",
                    (flatten(ordv), grouptag, r["id"]))

    total = len(rows)
    print(f"[ord] {hit}/{total} 章已定位篇序，未命中 {total - hit} 章")
    print("[ord] 来源分布:", ", ".join(f"{k}={v}" for k, v in sorted(src_stat.items())))
    for wid, lst in sorted(miss.items()):
        print(f"  ! {works[wid]}({wid}): {len(lst)} 章 → {lst[:8]}")

    # 连续性/重复校验
    print("\n[ord] 重复 ord 校验")
    dup_found = False
    for wid, name in works.items():
        rs = cur.execute(
            "select ord, count(*) c from chapters where work_id=? and ord is not null group by ord having c>1",
            (wid,)).fetchall()
        if rs:
            dup_found = True
            print(f"  ~ {name}: " + ", ".join(f"ord={x['ord']}×{x['c']}" for x in rs))
    if not dup_found:
        print("  无重复")

    print("\n[ord] 排序后前 6 章")
    for wid in (5, 8, 24, 46, 26, 1, 15, 25):
        rs = cur.execute(
            "select ord, title from chapters where work_id=? and ord is not null order by ord limit 6",
            (wid,)).fetchall()
        print(f"  {works[wid]}: " + " | ".join(f"{x['ord']}:{x['title'].split('/')[-1]}" for x in rs))
    con.commit()
    con.close()


if __name__ == "__main__":
    main()
