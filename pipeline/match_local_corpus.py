#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把入围书目（33 部）与「三条断线补书目」对本地殆知阁归档做渠道匹配。

本地归档结构：data/sources/daizhige/<书名>.md（分卷多在 title 里，文件名即书名；
类书/实录等大书才出现 卷XXX.md 的编排）。故匹配键取「文件名主干」+「title 首段」。

输入：data/sources/daizhige_index.csv（build_daizhige_index.py 产出）
      data/corpus_scores_ranked.csv（33 部入围）
输出：data/corpus_local_match.csv + 控制台报表
"""
from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import zhconv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

IDX = Path(r"D:\DimensionsCosmos\data\sources\daizhige_index.csv")
SCORES = Path(r"D:\DimensionsCosmos\data\corpus_scores_ranked.csv")
OUT = Path(r"D:\DimensionsCosmos\data\corpus_local_match.csv")

RE_SUFFIX = re.compile(r"(_\d+|卷[〇零一二三四五六七八九十百千0-9]+|第[〇零一二三四五六七八九十百千0-9]+[回卷篇])$")

ALIAS: dict[str, list[str]] = {
    "坛经": ["壇經", "六祖大師法寶壇經", "法寶壇經", "六祖壇經"],
    "红楼梦": ["紅樓夢", "石頭記"],
    "三国演义": ["三國演義", "三國志演義", "三國志通俗演義"],
    "儒林外史": ["儒林外史"],
    "牡丹亭": ["牡丹亭", "牡丹亭還魂記", "還魂記"],
    "聊斋志异": ["聊齋志異", "聊齋"],
    "明夷待访录": ["明夷待訪錄", "明夷待訪録"],
    "传习录": ["傳習錄", "傳習録"],
    "人间词话": ["人間詞話"],
    "二十四诗品": ["二十四詩品", "詩品二十四則"],
    "商君书": ["商君書", "商子"],
    "文史通义": ["文史通義"],
    "天演论": ["天演論"],
    "管子": ["管子", "管子校正"],
    "列子": ["列子", "沖虛至德真經", "列子張湛注"],
    "金刚经": ["金剛經", "金剛般若波羅蜜經", "金剛般若經"],
    "九章算术": ["九章算術"],
    "人物志": ["人物志"],
    "读通鉴论": ["讀通鑑論", "讀通鑒論"],
    "近思录": ["近思錄", "近思録"],
    "东京梦华录": ["東京夢華錄", "東京夢華録"],
    "公孙龙子": ["公孫龍子"],
    "洛阳伽蓝记": ["洛陽伽藍記"],
    "花间集": ["花間集"],
    "春秋繁露": ["春秋繁露"],
    "海国图志": ["海國圖志"],
    "廿二史札记": ["廿二史札記", "二十二史劄記", "廿二史劄記", "二十二史札記"],
    "徐霞客游记": ["徐霞客遊記"],
    "纪效新书": ["紀效新書"],
    "乐府诗集": ["樂府詩集"],
    "三字经": ["三字經"],
    "幼学琼林": ["幼學瓊林"],
    "日知录": ["日知錄", "日知録"],
    "周礼": ["周禮", "周官", "周禮注疏"],
    "仪礼": ["儀禮", "儀禮注疏"],
    "公羊传": ["公羊傳", "春秋公羊傳", "春秋公羊經傳解詁"],
    "谷梁传": ["穀梁傳", "谷梁傳", "春秋穀梁傳", "春秋穀梁傳注疏"],
    "礼记": ["禮記"],
    "文献通考": ["文獻通考"],
    "通典": ["通典"],
    "通志": ["通志"],
}

EXTRA_LINE = [
    ("周礼", "经部", "经线·三礼缺"), ("仪礼", "经部", "经线·三礼缺"),
    ("公羊传", "经部", "经线·春秋三传缺"), ("谷梁传", "经部", "经线·春秋三传缺"),
    ("文献通考", "史部", "史线·政书缺"), ("通典", "史部", "史线·政书缺"),
]


def keys_of(r: dict) -> set[str]:
    """一个文件可能对应的书名词（归一化繁体）。"""
    out = set()
    stem = r["file"][:-3] if r["file"].lower().endswith(".md") else r["file"]
    base = RE_SUFFIX.sub("", stem)
    for k in (stem, base):
        if k:
            out.add(zhconv.convert(k, "zh-hant"))
    for t in (r["title_zh"], r["title_hant"]):
        if not t:
            continue
        head = re.split(r"[\s　·]+", t.strip())[0]
        head = RE_SUFFIX.sub("", head)
        if head:
            out.add(zhconv.convert(head, "zh-hant"))
    return out


def load_index() -> dict[str, list[dict]]:
    by_key: dict[str, list[dict]] = defaultdict(list)
    with open(IDX, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            for k in keys_of(r):
                by_key[k].append(r)
    return by_key


def match(title: str, by_key: dict[str, list[dict]]) -> tuple[str, list[dict], str]:
    cands = ALIAS.get(title) or [zhconv.convert(title, "zh-hant")]
    for c in cands:  # 1) 精确
        if c in by_key:
            return "exact", by_key[c], c
    for c in cands:  # 2) 包含（吸收「…注疏」「欽定…」等）
        hits = [k for k in by_key if c in k and len(k) - len(c) <= 8]
        if hits:
            hits.sort(key=lambda b: len(b))
            files = []
            for h in hits[:3]:
                files += by_key[h]
            return "contains", files, hits[0]
    return "miss", [], ""


def main() -> int:
    by_key = load_index()
    print(f"[index] 匹配键 {len(by_key)} 个\n")

    rows = []
    with open(SCORES, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            rows.append({"rank": r["rank"], "title": r["title"], "bu": r["bu"],
                         "tier": r["tier"], "src": "33部入围"})
    for i, (t, bu, why) in enumerate(EXTRA_LINE, 1):
        rows.append({"rank": f"L{i}", "title": t, "bu": bu, "tier": "-", "src": why})

    out, stat = [], defaultdict(int)
    for r in rows:
        how, files, key = match(r["title"], by_key)
        seen, uniq = set(), []
        for f in files:
            if f["file"] not in seen:
                seen.add(f["file"])
                uniq.append(f)
        nbytes = sum(int(f["bytes"] or 0) for f in uniq)
        kr = ";".join(sorted({f["kanripo_id"] for f in uniq if f["kanripo_id"]}))[:80]
        stat[how] += 1
        out.append({**r, "match": how, "local_key": key, "n_files": len(uniq),
                    "bytes": nbytes, "kanripo_id": kr,
                    "files": ";".join(f["file"] for f in uniq)[:400]})
        flag = "OK  " if how != "miss" else "MISS"
        print(f'[{flag}] {r["rank"]:>3} {r["title"]:<8} {how:<9} 文件{len(uniq):>3} '
              f'{nbytes/1024:>9.0f}KB  {key or "-"}')

    with open(OUT, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"\n[stat] {dict(stat)}  合计 {len(out)} 部 -> {OUT}")
    print("[miss]", [r["title"] for r in out if r["match"] == "miss"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
