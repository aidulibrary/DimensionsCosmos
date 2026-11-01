"""P0-5 引证式导读：原文候选池构建（refpack）。

职责：为「某书 × 某方法」抽取一组**可引用的原文块**，每块带 REF-SPEC v1 的
块级 URN（dc:<workKey>/c<chapNo>/b<blockNo>，blockNo 为 blocks 数组 1-based 序号）。
生成端的提示词只允许从该池内引证，校验端据此池做封闭性检查——
这样「导读里的每一处引证都能落到真实原文」不依赖模型自觉，而由池子边界保证。

设计要点：
- 块号一律取原始 blocks 数组下标 +1（与前端 hashFor 派生规则一致），
  不因过滤标题块而重编号。
- 只引正文块（p / v / q），标题块 h、表格 t 不进入可引用池（但保留在池外）。
- 选择策略确定性可复现：跨章覆盖优先（每章取首块 + 最长块），
  再按方法关键词命中度补足预算；同等分数按 (章序, 块序) 排序。
- ord < 0 的前置附文（如《论语》"序说"）默认不参与——那是注疏/传记，不是原典正文。
"""
from __future__ import annotations

import json
import re

# 方法 → 检索关键词（用于候选块打分；不追求完备，只求把相关段落顶上来）
METHOD_TERMS = {
    "zhuxi": ["仁", "禮", "礼", "君子", "學", "学", "心", "敬", "義", "义"],
    "sushi": ["人", "天", "物", "生", "死", "夢", "梦", "月", "情"],
    "qianzhongshu": ["喻", "比", "譬如", "如", "若", "猶", "犹"],
    "wangyangming": ["心", "知", "行", "良知", "誠", "诚", "意"],
    "adler": ["書", "书", "讀", "读", "篇", "章", "作者"],
    "feynman": ["何", "謂", "谓", "曰", "故", "是以", "所以"],
    "socratic": ["何", "奚", "安", "焉", "哉", "乎", "也"],
    "arendt": ["民", "眾", "众", "政", "君", "臣", "天下"],
    "ibn_khaldun": ["國", "国", "民", "政", "兵", "財", "财", "聚", "群"],
}
DEFAULT_TERMS = ["仁", "禮", "礼", "心", "政", "民", "學", "学"]

QUOTE_BLOCK_TYPES = {"p", "v", "q"}

_PUNCT = re.compile(r"[\s，。、；：！？「」『』“”‘’（）《》〈〉—…·,.!?;:\"'()\[\]<>~`\-]")


def normalize(s: str) -> str:
    return _PUNCT.sub("", s or "")


def load_chapters(conn, work_id: int, include_front: bool = False):
    """读取章节（含 ref 与 blocks），按 ord 排序（NULL 置后）。"""
    rows = conn.execute(
        "SELECT ref, title, blocks, ord FROM chapters WHERE work_id=? "
        "ORDER BY (ord IS NULL), ord, id",
        (work_id,),
    ).fetchall()
    out = []
    for ref, title, blocks_raw, ordv in rows:
        if not ref:
            continue
        if not include_front and ordv is not None and ordv < 0:
            continue
        try:
            blocks = json.loads(blocks_raw or "[]")
        except Exception:
            blocks = []
        if not isinstance(blocks, list):
            continue
        out.append({"ref": ref, "title": title, "blocks": blocks, "ord": ordv})
    return out


def block_urn(ref: str, block_no: int) -> str:
    return f"{ref}/b{block_no:03d}"


def build_refpack(conn, work_id: int, method_id: str, *, max_blocks: int = 30,
                  max_chars: int = 7000, per_chapter: int = 2,
                  include_front: bool = False):
    """构建候选原文池。

    返回 {"work_id", "method_id", "candidates": [{urn, chap, chap_title, block_no, text}],
          "stats": {...}}
    """
    chapters = load_chapters(conn, work_id, include_front=include_front)
    terms = METHOD_TERMS.get(method_id) or DEFAULT_TERMS
    pool = []

    for ch in chapters:
        picks = []
        for i, b in enumerate(ch["blocks"]):
            if not isinstance(b, dict):
                continue
            if b.get("t") not in QUOTE_BLOCK_TYPES:
                continue
            text = (b.get("x") or "").strip()
            if len(text) < 8:  # 太短的碎块引不动，也支撑不了论断
                continue
            picks.append({"i": i, "text": text})

        # 每章先取：首块 + 最长块（跨章覆盖是导读可信度的第一顺位）
        chosen = []
        if picks:
            chosen.append(picks[0])
            longest = max(picks, key=lambda p: len(p["text"]))
            if longest["i"] != picks[0]["i"]:
                chosen.append(longest)

        # 关键词命中补足 per_chapter
        scored = sorted(
            picks,
            key=lambda p: (-sum(p["text"].count(t) for t in terms), -len(p["text"]), p["i"]),
        )
        for p in scored:
            if len(chosen) >= max(per_chapter, 1):
                break
            if all(p["i"] != c["i"] for c in chosen):
                chosen.append(p)

        chap_no = int(ch["ref"].rsplit("/c", 1)[-1]) if "/c" in ch["ref"] else 0
        for p in sorted(chosen, key=lambda p: p["i"]):
            pool.append({
                "urn": block_urn(ch["ref"], p["i"] + 1),
                "chap": chap_no,
                "chap_title": ch["title"],
                "block_no": p["i"] + 1,
                "text": p["text"],
            })

    # 预算裁剪：按章序轮转取块，保证预算内各章都有代表
    by_chap = {}
    for c in pool:
        by_chap.setdefault(c["chap"], []).append(c)
    ordered, idx = [], 0
    while len(ordered) < len(pool):
        added = False
        for chap in sorted(by_chap):
            seq = by_chap[chap]
            if idx < len(seq):
                ordered.append(seq[idx])
                added = True
                if len(ordered) >= max_blocks:
                    break
        if not added or len(ordered) >= max_blocks:
            break
        idx += 1

    picked, total = [], 0
    for c in ordered:
        if total + len(c["text"]) > max_chars and picked:
            continue
        picked.append(c)
        total += len(c["text"])
        if len(picked) >= max_blocks:
            break

    return {
        "work_id": work_id,
        "method_id": method_id,
        "candidates": picked,
        "stats": {
            "chapters_total": len(chapters),
            "chapters_covered": len({c["chap"] for c in picked}),
            "blocks": len(picked),
            "chars": total,
        },
    }


def render_refpack(refpack: dict) -> str:
    """把候选池渲染成提示词里的「可引证原文」段。"""
    lines = []
    for c in refpack["candidates"]:
        lines.append(f'[{c["urn"]}] （{c["chap_title"]}）')
        lines.append(c["text"])
        lines.append("")
    return "\n".join(lines).strip()


if __name__ == "__main__":
    import sys as _sys
    _sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
    from db import connect
    conn = connect(__import__("pathlib").Path(__file__).resolve().parent.parent / "data" / "guji.db")
    rp = build_refpack(conn, 1, "zhuxi")
    print(json.dumps(rp["stats"], ensure_ascii=False))
    for c in rp["candidates"]:
        print(c["urn"], c["text"][:40])
