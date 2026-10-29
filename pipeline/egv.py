#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EGV — Evidence-Graded Verification（综合论证审核模型）
以权威信源（CIP 国家出版备案 / 出版社官网 / 国图 / 原典库）为标准参照，
对 work_profiles 的版本档案做**确定性加权裁决**，替代人工逐条标记 verified。

裁决结构 = 锚定 + 校验 + 异本归并（Anchor / Corroborate / Merge）
  · 锚定 Anchor     ：主版本实体由最高权威源（A1：CIP / 国家版本数据中心 / 国图）确立
  · 校验 Corroborate：其它源只做一致/佐证/异本三态标记，参与加分不改判
  · 异本归并 Merge  ：同著作的不同印本（不同 ISBN / 不同年份）记 editions[]，不算冲突
  · 真冲突 Conflict ：整理者互斥（不同人校注）或 高等级源出版社互斥，才降级为"存疑"
  · 无锚不定论      ：无 A1 源时最高只能到 reference，绝不升 verified

三层职责分离：
  1. 取证层 ingest  : web_search 原始结果 -> evidence JSON（保留 url / quote / 源分级，可追溯）
  2. 裁决层 verify  : evidence JSON -> 纯函数打分（可复算、可审计、无 LLM 生成内容）
  3. 呈现层 apply   : 按 grade 落库（verified / reference / conflict），前端据此决定措辞

用法：
  python egv.py ingest --work-id 1 --search <web_search结果json>
  python egv.py verify [--apply]
  python egv.py report
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "guji.db"
DEFAULT_EVIDENCE = ROOT / "data" / "evidence"

# ---------------------------------------------------------------- 源分级 ----
SOURCE_RULES = [
    ("A1", 1.00, ("cppinfo.cn", "cnpub.com.cn"),
     ("国家出版发行信息公共服务平台", "国家版本数据中心", "全国新书目")),
    ("A1", 1.00, ("nlc.cn", "opac.nlc.cn"), ("国家图书馆", "中国国家图书馆")),
    ("A2", 0.90, ("zhbc.com.cn",), ("中华书局",)),
    ("A2", 0.90, ("guji.com.cn",), ("上海古籍出版社",)),
    ("A2", 0.90, ("cp.com.cn", "spph.com.cn"), ("商务印书馆", "中国出版集团")),
    ("B", 0.85, ("ctext.org", "guoxue.com"), ("中国哲学书电子化计划", "国学网")),
    ("B", 0.85, ("kanripo.org",), ("Kanripo", "漢籍リポジトリ", "汉籍リポジトリ")),
    ("B", 0.80, ("daizhige.org", "daizhigev20", "daizhige-org"), ("殆知阁", "daizhige")),
    ("B", 0.80, ("gov.cn", "edu.cn", "org.cn", "ac.cn"),
     ("图书馆", "陕西省图书馆", "深圳图书馆", "宁波图书馆", "中国科学院")),
    ("C", 0.60, ("wikipedia.org", "wikisource.org", "wikidata.org"), ("维基",)),
    ("D", 0.35, ("baike.baidu.com", "douban.com", "dangdang.com", "jd.com",
                 "kongfz.com", "sogou.com", "haosou.com", "so.com"), ("百科", "豆瓣", "当当", "京东", "孔夫子")),
]
DEFAULT_GRADE = ("D", 0.30)
ANCHOR_GRADES = ("A1",)
STRONG_GRADES = ("A1", "A2")

# 出版年必须带上下文，避免把成书年/生卒年当出版年
RE_YEAR_CTX = re.compile(
    r"(?:出版时间|出版日期|出版发行|出版年|出版|版次|印次)\s*[:：]?\s*((?:19|20)\d{2})\s*年?\s*(?:(\d{1,2})\s*月)?"
)
RE_YEAR_NEAR_PUB = re.compile(
    r"(中华书局|上海古籍出版社|商务印书馆|岳麓书社|凤凰出版社|人民文学出版社|齐鲁书社|"
    r"巴蜀书社|浙江古籍出版社|黄山书社|华东师范大学出版社|北京大学出版社)[^。；]{0,40}?((?:19|20)\d{2})\s*年?"
)
RE_ISBN = re.compile(r"97[89][-\s]?\d[\d\-\s]{8,17}[\dXx]")
RE_PUB = re.compile(
    r"(中华书局|上海古籍出版社|商务印书馆|岳麓书社|凤凰出版社|人民文学出版社|"
    r"齐鲁书社|巴蜀书社|浙江古籍出版社|黄山书社|华东师范大学出版社|北京大学出版社)"
)
# CIP 结构化著者字段：定位到"著者:"到"编者/译者/出版社"之间的片段
RE_AUTHOR_FIELD = re.compile(r"著者[:：]\s*(.{0,140}?)(?=编者[:：]|译者[:：]|出版社[:：]|责任编辑|出版时间|目录|ISBN|$)")
RE_PERSON_DYN = re.compile(
    r"[(\[（]\s*(?:汉|魏|晋|南朝宋|南朝梁|北朝|唐|宋|元|明|清|战国|春秋|秦|五代|近代|当代)\s*[)\]）]"
    r"\s*([\u4e00-\u9fa5]{2,4})"
)
RE_PERSON_VERB = re.compile(
    r"([\u4e00-\u9fa5]{2,4})\s*(撰|著|译注|点校|校释|校注|校勘|集解|集释|笺注|编著|编注|注译|今译)"
)
NAME_STOP = {
    "关于", "做好", "本书", "该书", "全书", "读者", "先生", "弟子", "中国", "中华", "国学",
    "文库", "收入", "新编", "诸子", "集成", "以上", "上下", "中下", "上册", "下册", "本书目录",
    "道德经注", "老子道德经", "第三十三", "译注", "点校", "校释", "集释", "原著", "编者",
    "译者", "著者", "出版社", "出版", "责任编辑", "内容提要", "作者简介", "简体", "精装", "平装",
}
YEAR_WINDOW = (1850, 2030)


def grade_of(url: str, source_name: str) -> tuple[str, float]:
    u = (url or "").lower()
    s = source_name or ""
    for g, w, hosts, names in SOURCE_RULES:
        if any(h in u for h in hosts) or any(n in s for n in names):
            return g, w
    return DEFAULT_GRADE


def _isbn13_ok(d: str) -> bool:
    """ISBN-13 校验位验证，避免正则贪婪吞入相邻价格/年份数字。"""
    if len(d) != 13 or not d.isdigit():
        return False
    tot = sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(d[:12]))
    return (10 - tot % 10) % 10 == int(d[12])


def _norm_isbn(raw: str) -> str:
    """归一化：优先取校验通过的 13 位串；正则可能吞入后随数字（如价格）。"""
    d = re.sub(r"[-\s]", "", raw).upper()
    if len(d) == 13:
        return d
    digits = re.sub(r"[^0-9]", "", d)
    for i in range(max(0, len(digits) - 12)):
        c = digits[i:i + 13]
        if _isbn13_ok(c):
            return c
    return d


def _norm_name(name: str) -> str:
    """人名归一：去职衔、去括号朝代，供别名比对。"""
    n = re.sub(r"[(\[（].*?[)\]）]", "", name or "")
    n = re.sub(r"(先生|女士|氏|撰|著|等)$", "", n.strip())
    return n.strip()


def _valid_name(name: str, title: str) -> bool:
    n = _norm_name(name)
    if not (2 <= len(n) <= 4):
        return False
    if n in NAME_STOP or n in title or title in n:
        return False
    if any(ch in n for ch in "第之其此本全该的了与和"):
        return False
    if re.search(r"\d", n):
        return False
    return True


def _window(text: str, title: str, span: int = 160) -> str:
    """只保留书名出现位置附近的文本，避免同页书目（书单/丛书页）串入他书信息。"""
    idxs = [m.start() for m in re.finditer(re.escape(title), text)]
    if not idxs:
        return text
    best, best_score = text, -1
    for i in idxs:
        seg = text[max(0, i - span): i + span]
        sc = seg.count("著者") * 3 + seg.count("ISBN") * 2 + seg.count("出版时间") * 2
        if sc > best_score:
            best, best_score = seg, sc
    return best


ALIAS = {                                 # 检索名与通行整理本名不一致时的放行别名
    "杜工部集": ["杜诗详注", "杜甫诗"],
    "李太白集": ["李太白全集", "李白诗", "李白集"],
    "陶渊明集": ["陶渊明诗", "陶集", "陶渊明"],
    "诗品": ["诗品注", "钟嵘诗品"],
    "文选": ["昭明文选"],
    "宋词三百首": ["宋词三百首笺注"],
    "楚辞": ["楚辞补注"],
    "伤寒杂病论": ["伤寒论"],
    "黄帝内经": ["素问", "灵枢"],
}

PUB_OFFICIAL = {"zhbc.com.cn": "中华书局", "zhbc.com": "中华书局",
                "spph.com.cn": "上海古籍出版社", "cppinfo.cn": "中华书局",
                "cnpubg.com": "中华书局"}

KIND_RANK = {"点校": 3, "校释": 3, "校注": 3, "校勘": 3, "译注": 3,
             "集解": 3, "集释": 3, "笺注": 3, "今注": 3, "新注": 3, "注译": 3,
             "编": 2, "编著": 2, "编注": 2, "撰": 1, "著": 1}


def _pick_editor(text: str, title: str) -> tuple[str, str] | None:
    """返回 (整理者串, 角色)。整理者优先于原著者；多人以、连接。"""
    cands: list[tuple[str, str]] = []   # (name, kind)

    m = RE_AUTHOR_FIELD.search(text)
    scope = m.group(1) if m else ""
    if scope:
        for seg in re.split(r"[;；、,，/]", scope):
            seg = seg.strip()
            if not seg:
                continue
            dm = RE_PERSON_DYN.search(seg)
            if dm and _valid_name(dm.group(1), title):
                km = RE_PERSON_VERB.search(seg)
                kind = km.group(2) if km else ("校释" if "校释" in seg else
                       ("点校" if "点校" in seg else ("译注" if "译注" in seg else "著")))
                cands.append((_norm_name(dm.group(1)), kind))
                continue
            vm = RE_PERSON_VERB.search(seg)
            if vm and _valid_name(vm.group(1), title):
                cands.append((_norm_name(vm.group(1)), vm.group(2)))
                continue
            plain = re.sub(r"[（(\[].*?[)）\]]", "", seg).strip()
            if _valid_name(plain, title):
                cands.append((_norm_name(plain), "著"))
    if not cands:
        # 无 CIP 著者字段时，只认"带朝代括号前缀 + 紧邻整理动词"的强模式
        for dm in RE_PERSON_DYN.finditer(text):
            tail = text[dm.end(): dm.end() + 6]
            km = re.match(r"\s*(撰|著|译注|点校|校释|校注|集解|集释|笺注|编著)", tail)
            if km and _valid_name(dm.group(1), title):
                cands.append((_norm_name(dm.group(1)), km.group(1)))
    if not cands:
        return None

    # 署名是"撰者 + 整理者"的组合，全部保留（顺序即 CIP 著者字段原序）
    names, seen = [], set()
    for n, _ in cands:
        if n not in seen:
            seen.add(n)
            names.append(n)
    kind = max((k for _, k in cands), key=lambda k: KIND_RANK.get(k, 0))
    return "、".join(names[:4]), kind


def extract_fields(text: str, title: str) -> dict:
    """确定性抽取。抽不到即不产出（宁缺不猜）。"""
    seg = _window(text, title)
    out: dict = {}
    m = None
    for scope in (text, seg):               # 先在全文按书名就近取，再退窗口
        for tm in re.finditer(re.escape(title), scope):
            mm = RE_ISBN.search(scope[tm.start(): tm.start() + 180])
            if mm:
                m = mm
                break
        if m:
            break
    if not m:
        m = RE_ISBN.search(seg)
    if m:
        v = _norm_isbn(m.group(0))
        if len(v) == 13:
            out["isbn"] = v
    m = RE_PUB.search(seg)
    if m:
        out["publisher"] = m.group(1)

    year = None
    m = RE_YEAR_CTX.search(seg)
    if m:
        year = m.group(1) + ("-" + m.group(2).zfill(2) if m.group(2) else "")
    else:
        m = RE_YEAR_NEAR_PUB.search(seg)
        if m:
            year = m.group(2)
    distinct_isbn = {_norm_isbn(x) for x in RE_ISBN.findall(seg)} - {""}
    if len(distinct_isbn) > 1:              # 书目列表页：年份易串到邻行书，宁可缺项
        year = None
    if year and YEAR_WINDOW[0] <= int(year[:4]) <= YEAR_WINDOW[1]:
        out["year"] = year

    ed = _pick_editor(seg, title)
    if ed:
        out["editor"], out["edition"] = ed
    return out


# ---------------------------------------------------------------- 取证层 ----
def cmd_ingest(args) -> int:
    work = _load_work(args.db, args.work_id)
    raw = json.loads(Path(args.search).read_text(encoding="utf-8"))
    title = work["seed_title"]
    entries, rejected = [], 0
    for r in raw.get("results", []):
        url = r.get("url", "")
        snippet = (r.get("title", "") + " " + r.get("snippet", "")).strip()
        hit = next((kw for kw in [title] + ALIAS.get(title, []) if kw in snippet), None)
        if not hit:                       # 主题一致性闸门，滤掉串书噪声（含别名放行）
            rejected += 1
            continue
        grade, weight = grade_of(url, r.get("source", ""))
        fields = extract_fields(snippet, hit)
        if r.get("base_text"):            # 开源可读本：只带底本描述，无纸本出版字段
            fields["base_text"] = r["base_text"]
        # 出版社官网书目页：所列条目必为该社出版物，有 ISBN 即可确定性回填 publisher
        if "publisher" not in fields and "isbn" in fields:
            for dom, pub in PUB_OFFICIAL.items():
                if dom in url:
                    fields["publisher"] = pub
                    break
        if not fields:
            continue
        entries.append({
            "grade": grade, "weight": weight,
            "source_name": r.get("source", ""), "url": url,
            "fields": fields, "quote": snippet[:300],
            "grabbed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
    entries.sort(key=lambda e: -e["weight"])
    payload = {"work_id": args.work_id, "title": title,
               "entries": entries, "rejected_noise": rejected}
    out_dir = Path(args.out_dir or DEFAULT_EVIDENCE)
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f"work_{args.work_id}.json"
    dst.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ingest] work={args.work_id} 《{title}》 有效证据 {len(entries)} 条，"
          f"剔除噪声 {rejected} 条 -> {dst.name}")
    return 0


# ---------------------------------------------------------------- 裁决层 ----
def adjudicate(entries: list[dict], title: str) -> dict:
    """
    锚定隔离裁决：
      · 以最高等级源（A1 优先）为锚，主版本实体只由锚内证据确立
      · 非锚源只做佐证计数（一致加分、异值只记 divergent 不改判）
      · 锚内互斥（整理者不同 / 强源出版社不同）才判 conflict
      · 无 A1 锚时最高只能 reference
    """
    if not entries:
        return {"fields": {}, "score": 0.0, "grade": "conflict", "editions": [],
                "anchored": False, "anchor_source": None}

    ranked = sorted(entries, key=lambda e: -e["weight"])
    anchor_grade = ranked[0]["grade"]
    anchors = [e for e in ranked if e["grade"] == anchor_grade][:8]
    others = [e for e in ranked if e["grade"] != anchor_grade]
    anchored = anchor_grade in ANCHOR_GRADES

    fields: dict[str, dict] = {}
    for f in ("editor", "publisher", "year", "edition"):
        votes = [(e["fields"][f], e) for e in anchors if f in e["fields"]]
        if not votes:
            continue
        if f == "editor":
            # CIP 记录详略不一（"王弼注" vs "王弼、楼宇烈校释"）：按人名集合比，取信息最全者
            def _ns(x: str) -> set:
                return {t for t in re.split("、", x or "") if t}

            def _overlap(x: str, y: str) -> bool:
                # 同人异写（"王弼" / "王弼注"）按互为子串判同指
                return any(a == b or a in b or b in a for a in _ns(x) for b in _ns(y))
            best = max(votes, key=lambda v: len(_ns(v[0])))
            primary = best[0]
            pset = _ns(primary)
            ref_isbn = best[1]["fields"].get("isbn")   # 以主版本自身 ISBN 为隔离基准

            def _same_ed(e) -> bool:      # 异本（ISBN 不同）不构成互斥，另入 editions 归并
                ei = e["fields"].get("isbn")
                return not (ref_isbn and ei and ei != ref_isbn)

            same = [v for v, _ in votes if _overlap(v, primary)]
            diff = [v for v, e in votes if not _overlap(v, primary) and _same_ed(e)]
            base = best[1]["weight"]
            corroborated = sum(1 for e in others if _overlap(e["fields"].get("editor", ""), primary))
            divergent = [e["fields"]["editor"] for e in others
                         if "editor" in e["fields"] and not _overlap(e["fields"]["editor"], primary)]
        else:
            primary = votes[0][0]
            ref_isbn = votes[0][1]["fields"].get("isbn")

            def _same_ed2(e) -> bool:     # 异本（ISBN 不同）不构成互斥，另入 editions 归并
                ei = e["fields"].get("isbn")
                return not (ref_isbn and ei and ei != ref_isbn)

            same = [v for v, _ in votes if v == primary]
            diff = [v for v, e in votes if v != primary and _same_ed2(e)]
            base = votes[0][1]["weight"]
            corroborated = sum(1 for e in others if e["fields"].get(f) == primary)
            divergent = [e["fields"][f] for e in others
                         if f in e["fields"] and e["fields"][f] != primary]
        conflict = bool(diff) and f in ("editor", "publisher")
        score = min(1.0, base + 0.05 * (len(same) - 1) + min(0.10, 0.02 * corroborated))
        fields[f] = {"value": primary, "score": round(score, 3), "conflict": conflict,
                     "alt_values": sorted(set(diff))[:4],
                     "corroborated_by": corroborated,
                     "divergent_in_lower_sources": sorted(set(divergent))[:4],
                     "sources": [{"name": e["source_name"], "grade": e["grade"], "url": e["url"]}
                                 for _, e in votes[:5]]}

    # ISBN -> editions：同书异本全留档，主版本取锚内首条
    editions, seen = [], set()
    for e in anchors + others:
        isbn = e["fields"].get("isbn")
        if not isbn or isbn in seen:
            continue
        seen.add(isbn)
        editions.append({"isbn": isbn, "publisher": e["fields"].get("publisher"),
                         "year": e["fields"].get("year"), "editor": e["fields"].get("editor"),
                         "grade": e["grade"], "source": e["source_name"], "url": e["url"]})
    if editions:
        # 异本归并：同一书多个纸本按被支持次数排序，主版本取支持最多者（并列取高等级源）
        cnt = {}
        for e in anchors + others:
            k = e["fields"].get("isbn")
            if k:
                cnt[k] = cnt.get(k, 0) + 1
        wg = {"A1": 1.0, "A2": 0.9, "B": 0.8, "C": 0.6, "D": 0.35}
        editions.sort(key=lambda d: (-cnt.get(d["isbn"], 0),
                                     -wg.get(d["grade"], 0.3), d["isbn"]))
        fields["isbn"] = {"value": editions[0]["isbn"], "score": round(anchors[0]["weight"], 3),
                          "conflict": False,
                          "alt_values": [d["isbn"] for d in editions[1:]][:5],
                          "sources": [{"name": d["source"], "grade": d["grade"], "url": d["url"]}
                                      for d in editions[:5]]}

    # 底本（可读电子本所用版本）：只采最高等级源的一致描述，不做跨源拼合
    bt = [(e["fields"]["base_text"], e) for e in ranked if e["fields"].get("base_text")]
    if bt:
        top_w = max(e["weight"] for _, e in bt)
        primary_bt = next(v for v, e in bt if e["weight"] == top_w)
        fields["base_text"] = {
            "value": primary_bt, "score": round(top_w, 3), "conflict": False,
            "alt_values": sorted({v for v, _ in bt if v != primary_bt})[:3],
            "corroborated_by": len(bt) - 1,
            "sources": [{"name": e["source_name"], "grade": e["grade"], "url": e["url"]}
                        for _, e in bt[:5]],
        }

    # base_text 仅为可读本说明，不参与纸本版本分权
    w_map = {"isbn": 0.28, "publisher": 0.24, "year": 0.20, "editor": 0.18, "edition": 0.10,
             "base_text": 0.0}
    total_w = sum(w_map[f] for f in fields)
    if total_w == 0.0:
        # 仅有可读底本说明、无任何纸本字段：不是"证据冲突"，而是无纸本锚定的参考级
        bt_w = max((e["weight"] for _, e in bt), default=0.0) if bt else 0.0
        return {"fields": fields, "score": round(bt_w, 3), "grade": "reference",
                "editions": [], "anchored": False,
                "anchor_source": None, "anchor_count": 0,
                "lower_source_count": len(others)}
    score = round(sum(w_map[f] * (0.0 if r["conflict"] else r["score"])
                      for f, r in fields.items()) / total_w, 3) if total_w else 0.0
    has_conflict = any(r["conflict"] for r in fields.values())
    if has_conflict:
        grade = "conflict"
    elif score >= 0.80 and anchored:
        grade = "verified"
    else:
        # 四律之「互斥才降级」：低分只代表证据薄弱/未锚定，一律 reference，不得判 conflict
        grade = "reference"
    return {"fields": fields, "score": score, "grade": grade, "editions": editions,
            "anchored": anchored,
            "anchor_source": {"name": anchors[0]["source_name"], "grade": anchor_grade,
                              "url": anchors[0]["url"]},
            "anchor_count": len(anchors), "lower_source_count": len(others)}


def compose_version_text(title: str, adj: dict, author: str) -> str:
    """只拼装证据中确实存在的成分，缺项不臆造。"""
    f = adj["fields"]
    ed = f.get("editor", {}).get("value")
    kind = f.get("edition", {}).get("value") or ""
    pub = f.get("publisher", {}).get("value")
    yr = f.get("year", {}).get("value")
    base = f.get("base_text", {}).get("value")
    if not any([ed, pub, yr, base]):
        return ""
    VERB = re.compile(r"(注|校|译|编|撰|著|点校|校注|校证|笺注|评注|集解|整理|选)")
    if ed:
        parts = [x for x in re.split("、", ed) if x.strip()]
        if any(VERB.search(x) for x in parts):
            head = "、".join(parts)          # 已带"注/校释/译注"等动词，原样保留
        else:
            a = (author or "").strip()
            is_author = bool(a) and any(x in a or a in x for x in parts if x)
            head = "、".join(parts) + ("著" if is_author else "整理")
    else:
        head = author or ""
    tail = "，".join(x for x in [pub, (yr[:4] + "年") if yr else None] if x)
    if not (ed or pub or yr):
        # 无纸本出版信息时，只输出可读电子本的版本说明，不留空
        return f"《{title}》（{base}）"
    text = f"{head}《{title}》" + (f"，{tail}" if tail else "")
    if base:
        text += f"；本库正文底本：{base}"
    return text


def cmd_verify(args) -> int:
    db = Path(args.db or DEFAULT_DB)
    ev_dir = Path(args.evidence_dir or DEFAULT_EVIDENCE)
    con = sqlite3.connect(db)
    _ensure_columns(con)
    done = skipped = 0
    for p in sorted(ev_dir.glob("work_*.json")):
        payload = json.loads(p.read_text(encoding="utf-8"))
        wid, title, entries = payload["work_id"], payload["title"], payload["entries"]
        if not entries:
            skipped += 1
            continue
        row = con.execute("select author from works where id=?", (wid,)).fetchone()
        author = (row[0] if row else "") or ""
        adj = adjudicate(entries, title)
        vtext = compose_version_text(title, adj, author)
        vurls = sorted({e["url"] for e in entries if e["grade"] in ("A1", "A2")}) or [entries[0]["url"]]
        evidence_json = json.dumps({
            "grade": adj["grade"], "score": adj["score"], "anchored": adj["anchored"],
            "anchor_source": adj["anchor_source"], "fields": adj["fields"],
            "editions": adj["editions"], "source_count": len(entries),
            "source_mix": sorted({e["grade"] for e in entries}),
        }, ensure_ascii=False)
        conflict_note = "; ".join(
            f"{f} 互斥：{r['value']} vs {r['alt_values']}"
            for f, r in adj["fields"].items() if r["conflict"]
        ) or None
        if args.apply:
            con.execute("""
                INSERT INTO work_profiles(work_id, version_text, version_source, compiled_year,
                    author_note, background, structure_note, reading_tip,
                    confidence, evidence, score, grade, conflict_note, updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(work_id) DO UPDATE SET
                    version_text=excluded.version_text, version_source=excluded.version_source,
                    compiled_year=excluded.compiled_year, confidence=excluded.confidence,
                    evidence=excluded.evidence, score=excluded.score, grade=excluded.grade,
                    conflict_note=excluded.conflict_note, updated_at=excluded.updated_at
            """, (wid, vtext, ", ".join(vurls), adj["fields"].get("year", {}).get("value"),
                  None, None, None, None, adj["grade"], evidence_json, adj["score"],
                  adj["grade"], conflict_note,
                  datetime.now(timezone.utc).isoformat(timespec="seconds")))
        done += 1
        flag = "" if adj["anchored"] else " (未锚定)"
        print(f"[verify] {wid:>3} 《{title}》 {adj['grade']:<9} score={adj['score']:.2f}{flag} "
              f"| {vtext or '(证据不足，不输出)'}"
              + (f" | ⚠ {conflict_note}" if conflict_note else ""))
    if args.apply:
        con.commit()
    print(f"[verify] 完成 {done} 部，跳过（无证据）{skipped} 部"
          + ("" if args.apply else "（dry-run，未写库）"))
    con.close()
    return 0


def cmd_report(args) -> int:
    con = sqlite3.connect(args.db or DEFAULT_DB)
    rows = con.execute("""
        select w.id, w.seed_title, p.grade, p.score, p.version_text, p.conflict_note
        from works w left join work_profiles p on p.work_id = w.id
        order by case p.grade when 'verified' then 0 when 'reference' then 1
                 when 'conflict' then 2 else 3 end, w.id
    """).fetchall()
    stat: dict[str, int] = {}
    for r in rows:
        stat[r[2] or "pending"] = stat.get(r[2] or "pending", 0) + 1
    print("状态分布：", stat)
    for r in rows:
        if r[2] is None:
            continue
        print(f"  {r[0]:>3} {r[1]:<8} {r[2]:<10} "
              f"{('%.2f' % r[3]) if r[3] is not None else '  - '}  {r[4] or ''}"
              + (f"  ⚠{r[5]}" if r[5] else ""))
    print(f"  待取证：{sum(1 for r in rows if r[2] is None)} 部")
    con.close()
    return 0


# ---------------------------------------------------------------- 工具 ----
def _ensure_columns(con: sqlite3.Connection) -> None:
    cols = {r[1] for r in con.execute("PRAGMA table_info(work_profiles)")}
    for name, ddl in (("evidence", "TEXT"), ("score", "REAL"),
                      ("grade", "TEXT"), ("conflict_note", "TEXT")):
        if name not in cols:
            con.execute(f"ALTER TABLE work_profiles ADD COLUMN {name} {ddl}")
    con.commit()


def _load_work(db: str, wid: int) -> dict:
    con = sqlite3.connect(db or DEFAULT_DB)
    r = con.execute("select id, seed_title, author from works where id=?", (wid,)).fetchone()
    con.close()
    if not r:
        raise SystemExit(f"work_id {wid} 不存在")
    return {"id": r[0], "seed_title": r[1], "author": r[2]}


def main() -> int:
    ap = argparse.ArgumentParser(description="EGV 综合论证审核模型")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("ingest")
    p1.add_argument("--work-id", type=int, required=True)
    p1.add_argument("--search", required=True)
    p1.add_argument("--out-dir")
    p1.set_defaults(func=cmd_ingest)

    p2 = sub.add_parser("verify")
    p2.add_argument("--evidence-dir")
    p2.add_argument("--apply", action="store_true")
    p2.set_defaults(func=cmd_verify)

    p3 = sub.add_parser("report")
    p3.set_defaults(func=cmd_report)

    a = ap.parse_args()
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
