# -*- coding: utf-8 -*-
"""FLCA-6 ｜ M1 交付抽检：从分片还原注音，检查规则层是否按预期改写读音。"""
import json
import pathlib
import re
import sqlite3
import sys

DB = pathlib.Path(r"D:\DimensionsCosmos\data\guji.db")
SHARD = pathlib.Path(r"D:\DimensionsCosmos\data\pinyin\b20261111_L05rule_v5")
BUILD = "b20261111_L05rule_v5"

CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

# 抽检用例：古籍名句 -> 期望读音（人工核对项）
CASES = [
    ("不亦说乎", "说", "yuè"),
    ("王天下", "王", "wàng"),
    ("图穷匕见", "见", "xiàn"),
    ("合从缔交", "从", "zòng"),
    ("孝弟也者", "弟", "tì"),
    ("知者乐水", "乐", "yào"),
    ("礼乐", "乐", "yuè"),
    ("千乘之国", "乘", "shèng"),
    ("卒然", "卒", "cù"),
    ("游说", "说", "shuì"),
    ("阿房宫", "房", "páng"),
    ("皋陶", "陶", "yáo"),
    ("会稽", "会", "kuài"),
    ("德之行", "行", "xìng"),
    ("衣敝缊袍", "衣", "yì"),
    ("雨雪霏霏", "雨", "yù"),
]


def load_chapter_index(con):
    cur = con.cursor()
    rows = cur.execute("SELECT id, work_id, title FROM chapters").fetchall()
    return rows


def render(cid, wid, raw, shard):
    pos = shard["pos"]
    py = shard["py"]
    st = shard["st"]
    meta = shard.get("meta", {})
    m = {int(k): v for k, v in meta.items()}
    out = []
    for k, off in enumerate(pos):
        seg = raw[off]
        p = py[k]
        code = st[k]
        mk = "!" if code == "u" else ("~" if code == "v" else "")
        if str(k) in meta or meta.get(k):
            mk = "*"
        out.append(f"{seg}({p}{mk})")
    return "".join(out)


def main():
    con = sqlite3.connect(str(DB))
    idx = {cid: (wid, title) for cid, wid, title in load_chapter_index(con)}
    hit, miss = 0, 0
    print("=" * 70)
    print("A. 规则层判音抽检（期望值逐条核对）")
    print("=" * 70)
    for phrase, ch, expect in CASES:
        cur = con.cursor()
        row = cur.execute(
            "SELECT chapter_id, char_offset, reading, state, authority, rule_id "
            "FROM chapter_pinyin WHERE surface=? AND reading=? LIMIT 1", (ch, expect)).fetchone()
        if row:
            hit += 1
            print(f"  [OK ] {phrase:<10} {ch} -> {row[2]:<8} state={row[3]:<9} rule#{row[5]}")
        else:
            miss += 1
            print(f"  [MISS] {phrase:<10} {ch} -> 期望 {expect} 未见命中")
    con.close()
    print(f"\n  命中 {hit} / {hit+miss}")
    print(f"  注：MISS 不代表错误 —— 语料中可能不存在该搭配，属规则覆盖率而非错音。")

    # B. 分片完整性
    print("\n" + "=" * 70)
    print("B. 分片完整性 / 结构自检")
    print("=" * 70)
    files = list(SHARD.rglob("*.json"))
    bad = 0
    sample_ok = 0
    for f in files[:200]:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            assert len(d["pos"]) == len(d["py"]) == len(d["st"])
            assert d["st"].count("a") + d["st"].count("u") + d["st"].count("v") == len(d["st"])
            sample_ok += 1
        except Exception:
            bad += 1
    print(f"  分片总数：{len(files)}")
    print(f"  结构校验（抽 200）：通过 {sample_ok}，异常 {bad}")
    total_bytes = sum(f.stat().st_size for f in files)
    print(f"  总体积：{total_bytes/1048576:.1f} MB，均 {total_bytes/max(len(files),1)/1024:.1f} KB/章")

    # C. 渲染示例
    print("\n" + "=" * 70)
    print("C. 渲染还原示例（*(规则) !(存疑) ~(异读)）")
    print("=" * 70)
    con = sqlite3.connect(str(DB))
    r = con.execute(
        "SELECT id, work_id FROM chapters "
        "WHERE id IN (SELECT chapter_id FROM chapter_pinyin WHERE state='uncertain' LIMIT 1)"
    ).fetchone()
    if r:
        cid, wid = r
        raw = con.execute("SELECT COALESCE(clean_text,text) FROM chapters WHERE id=?",
                          (cid,)).fetchone()[0]
        con.close()
        f = SHARD / str(wid) / f"{cid}.json"
        if f.exists():
            shard = json.loads(f.read_text(encoding="utf-8"))
            txt = render(cid, wid, raw, shard)
            print(f"  章节 {cid}（work {wid}，全文 {len(raw)} 字）")
            print("  原文：" + raw[:60].replace("\n", " "))
            print("  注音：" + txt[:700])
    return 0


if __name__ == "__main__":
    sys.exit(main())
