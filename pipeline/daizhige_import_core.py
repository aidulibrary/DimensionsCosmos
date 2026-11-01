#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""殆知阁归档 → 古籍库统一导入器（配置化切章，v2）。

用法：
  python import_daizhige_corpus.py --list
  python import_daizhige_corpus.py --title 坛经            # dry-run
  python import_daizhige_corpus.py --batch 1 --apply
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize_text import clean_text, to_blocks  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SRC = Path(r"D:\DimensionsCosmos\data\sources\daizhige")
DB = r"D:\DimensionsCosmos\data\guji.db"
RE_PUA = re.compile(r"[\ue000-\uf8ff]")
RE_TAG = re.compile(r"<[^>]+>")
CN = "〇零一二三四五六七八九十百千"
MAXT = 24

RE_HUI = re.compile(rf"^第\s*[{CN}0-9]{{1,4}}\s*回")
RE_CHU = re.compile(rf"^第\s*[{CN}0-9]{{1,3}}\s*出")
RE_JUAN = re.compile(rf"^卷\s*第?[{CN}0-9]{{1,4}}")
RE_PIAN = re.compile(rf"^(\S{{1,9}}?)第([{CN}0-9]{{1,4}})(亡佚|阙佚|缺)?$")
RE_YINYAN = re.compile(rf"^(导言|论)([{CN}0-9]{{1,3}})\s*(.*)$")
RE_PIN = re.compile(r"^[【〔\[]([^】〕\]]{1,8})[】〕\]]$")
RE_TIAO = re.compile(rf"^[{CN}0-9]{{1,3}}$")
# 篇名允许尾部夹注/版心记号（如「五辅第十【谓六兴七体】　外言一」）
RE_PIAN_IN = re.compile(rf"^(\S{{1,8}}?)第([{CN}0-9]{{1,4}})")
SYM = "○●◎◆△▲＊*【】〔〕[]　 ·•"


def read_lines(name: str) -> list[str]:
    raw = (SRC / name).read_text(encoding="utf-8", errors="ignore")
    body = raw.split("---", 2)[-1]
    out = []
    for l in body.splitlines():
        s = RE_TAG.sub("", RE_PUA.sub("", l)).replace("\u3000", " ").strip()
        out.append(s)
    return out



_CNS = {"〇":0,"零":0,"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9}

def cn2int(sx):
    if not sx: return None
    if sx.isdigit(): return int(sx)
    if sx == "十": return 10
    if "百" in sx:
        a, b = sx.split("百", 1)
        return (cn2int(a) if a else 1) * 100 + (cn2int(b) if b else 0)
    if "十" in sx:
        a, b = sx.split("十", 1)
        return (cn2int(a) if a else 1) * 10 + (cn2int(b) if b else 0)
    return _CNS.get(sx)

_NUM_RE = re.compile(r"第([0-9]+|[〇零一二三四五六七八九十百千]+)(回|出|折|卷|篇|章)")

def key_of(s):
    """标题归一化：去空白 + 回/出/卷序号统一为阿拉伯数字（第001回 == 第一回）。"""
    t = re.sub(r"\s+", "", s)
    def _f(m):
        v = cn2int(m.group(1))
        return "第%s%s" % (v if v is not None else m.group(1), m.group(2))
    return _NUM_RE.sub(_f, t)


def cut_toc(lines: list[str]) -> list[str]:
    """切除「目录/目次」引导的目录区（至第一段长正文前）。"""
    for i, l in enumerate(lines[:600]):
        if l in ("目录", "目次", "总目", "總目", "回目录", "目録", "目录终"):
            j = i + 1
            while j < len(lines) and (not lines[j] or len(lines[j]) <= MAXT):
                j += 1
            if j < len(lines):
                return [x for x in lines[:i] if x] + lines[j:]
    return lines


def _nk(s: str) -> str:
    return re.sub(r"\s+", "", s)


def strip_dup_block(lines: list[str], maxlen: int = MAXT) -> list[str]:
    """切除无「目录」字样的重复标题块（如《商子》提要后的整段篇目）。"""
    n = len(lines)
    limit = min(600, max(60, int(n * 0.15)))
    for i in range(min(n, limit)):
        a = lines[i]
        if not a or len(a) > maxlen:
            continue
        key = _nk(a)
        for k in range(i + 5, min(n, i + 400)):
            if _nk(lines[k]) != key:
                continue
            mid = lines[i + 1:k]
            ne = [x for x in mid if x]
            short = sum(1 for x in ne if len(x) <= maxlen)
            if len(ne) >= 4 and short / len(ne) >= 0.85:
                print(f"   [dup] 切除重复标题块 {i}..{k}")
                return lines[:i] + lines[k:]
    return lines


def pre_clean(lines: list[str], cfg: dict) -> list[str]:
    skip = [re.compile(p) for p in cfg.get("skip", [])]
    end = [re.compile(p) for p in cfg.get("end", [])]
    out = []
    for l in lines:
        if any(e.search(l) for e in end):
            break
        out.append(l)
    out = [l for l in out if not (l and any(s.search(l) for s in skip))]
    out = cut_toc(out)
    if cfg["mode"] in ("pian_num", "pian_in", "juan", "mark", "re", "hui", "chu", "yinyan", "pin"):
        out = strip_dup_block(out, 40 if cfg["mode"] in ("hui", "chu") else MAXT)
        out = remove_toc_block(out, cfg)
        out = dedup_same(out, cfg)
    return out


def detect(lines: list[str], cfg: dict) -> list[tuple[int, str, str]]:
    mode = cfg["mode"]
    pat = re.compile(cfg["re"]) if cfg.get("re") else None
    gre = re.compile(cfg["group_re"]) if cfg.get("group_re") else None
    merged: list[tuple[int, str, str]] = []
    group = ""
    hits: list[tuple[int, str, str]] = []

    if mode == "list":
        want = cfg["titles"]
        k = 0
        for i, l in enumerate(lines):
            if not l or len(l) > 22:
                continue
            if k < len(want) and l.replace(" ", "").startswith(want[k].replace(" ", "")):
                hits.append((i, l, ""))
                k += 1
        if k < len(want):
            print(f"   [warn] list 仅命中 {k}/{len(want)}：{want[k:]}")
        return hits

    for i, l in enumerate(lines):
        if not l:
            continue
        if gre and gre.match(l):
            group = l
            continue
        marks = cfg.get("marks", "")
        if cfg.get("group_mark") and l.startswith(cfg["group_mark"]):
            group = l.lstrip(cfg["group_mark"]).strip()
            continue
        ok = False
        if mode == "hui":
            ok = bool(RE_HUI.match(l)) and len(l) <= 40
        elif mode == "chu":
            ok = bool(RE_CHU.match(l)) and len(l) <= 20
        elif mode == "juan":
            ok = bool(RE_JUAN.match(l)) and len(l) <= 22
        elif mode == "pian_num":
            m = RE_PIAN.match(l)
            ok = bool(m) and (not cfg.get("only_names") or m.group(1) in cfg["only_names"])
        elif mode == "pian_in":
            m = RE_PIAN_IN.match(l)
            ok = bool(m) and len(l) <= cfg.get("max_title", 60)
            if ok:
                hits.append((i, m.group(0), group))
                continue
        elif mode == "yinyan":
            ok = bool(RE_YINYAN.match(l)) and len(l) <= 20
        elif mode == "mark":
            ok = l[0] in marks and 1 < len(l) <= MAXT
        elif mode == "tiao":
            ok = bool(RE_TIAO.match(l))
        elif mode == "pin":
            ok = bool(RE_PIN.match(l))
        elif mode == "re":
            ok = bool(pat and pat.match(l)) and len(l) <= cfg.get("max_title", 26)
        elif mode == "shortline":
            lo, hi = cfg.get("len", (2, 14))
            nxt = next((x for x in lines[i + 1:i + 3] if x), "")
            ok = (lo <= len(l) <= hi and not any(c in l for c in "。，；：？！、")
                  and len(nxt) >= cfg.get("next_min", 40))
        if ok:
            hits.append((i, l, group))
    return hits


def remove_toc_block(lines, cfg):
    """整块目录切除：开头附近出现 ≥4 条密集标题，且该前缀的标题集体在后文再现（重合率≥0.8），切掉目录段。"""
    hits = detect(lines, cfg)
    n = len(lines)
    if len(hits) < 8:
        return lines
    blocks, cur = [], [hits[0]]
    for h in hits[1:]:
        if h[0] - cur[-1][0] <= 25:
            cur.append(h)
        else:
            blocks.append(cur); cur = [h]
    blocks.append(cur)
    cut = set()
    # 规则 C：块首起连续「其后无正文」的标题视为目录，切到第一个有正文的标题之前
    for b in blocks:
        if len(b) < 5 or b[0][0] >= max(300, int(n * 0.4)):
            continue
        body = [sum(len(x) for x in lines[b[k][0] + 1:b[k + 1][0]] if x) for k in range(len(b) - 1)]
        if not body or body[0] > 10:
            continue
        k = 0
        while k < len(body) and body[k] <= 10:
            k += 1
        if k >= 4:
            cut.update(range(b[0][0], b[k][0]))
            print("   [toc] 切目录段 %d..%d（%d 条无正文标题）" % (b[0][0] + 1, b[k][0], k))
    # 规则 A：密集（间距≤3）且每条之间正文极短 → 整块为目录，连同末条一并切除
    for b in blocks:
        if len(b) < 4 or b[0][0] >= max(300, int(n * 0.4)):
            continue
        if all(b[k + 1][0] - b[k][0] <= 3 for k in range(len(b) - 1)):
            body = [sum(len(x) for x in lines[b[k][0] + 1:b[k + 1][0]] if x) for k in range(len(b) - 1)]
            if body and max(body) <= 30:
                cut.update(range(b[0][0], b[-1][0]))
                print("   [toc] 密集目录块 %d..%d（%d 条）" % (b[0][0] + 1, b[-1][0] + 1, len(b)))
                continue
    for b in blocks:
        if any(i in cut for i in range(b[0][0], b[-1][0] + 1)):
            continue
        if len(b) < 4 or b[0][0] >= max(300, int(n * 0.4)):
            continue
        body = [sum(len(x) for x in lines[b[k][0] + 1:b[k + 1][0]] if x) for k in range(len(b) - 1)]
        if body and max(body) > 40:
            continue
        tail = {key_of(h[1]) for h in hits if h[0] > b[0][0]}
        p = 0
        for h in b:
            if key_of(h[1]) in tail:
                p += 1
            else:
                break
        if p < 4:
            continue
        cut_end = b[p][0] if p < len(b) else b[-1][0]
        if cut_end - b[0][0] >= 4:
            cut.update(range(b[0][0], cut_end))
            print("   [toc] 切除目录块 %d..%d（%d 条）" % (b[0][0] + 1, cut_end, cut_end - b[0][0]))
    if not cut:
        return lines
    return [l for i, l in enumerate(lines) if i not in cut]


def dedup_same(lines, cfg):
    """相邻同名标题（卷末复标题）只保留第一条，内容并入该章。"""
    hits = detect(lines, cfg)
    drop = set()
    for a, b in zip(hits, hits[1:]):
        if key_of(a[1]) == key_of(b[1]):
            drop.add(b[0])
    if not drop:
        return lines
    print("   [toc] 丢弃同名复标题 %d 条" % len(drop))
    return [l for i, l in enumerate(lines) if i not in drop]


def build_chapters(lines: list[str], hits: list[tuple[int, str, str]], cfg: dict) -> list[dict]:
    prefix = cfg["prefix"]
    # 相邻标题之间无任何正文（页尾版心卷题/重复标记）→ 丢弃前一条
    if len(hits) > 1:
        keep = []
        for k, h in enumerate(hits):
            if k + 1 < len(hits) and key_of(h[1]) != key_of(hits[k + 1][1]):
                if not [x for x in lines[h[0] + 1:hits[k + 1][0]] if x]:
                    print(f"   [toc] 丢弃页尾标记 {h[1]}")
                    continue
            keep.append(h)
        hits = keep
    as_group = set(cfg.get("as_group", []))
    rename = cfg.get("rename", {})
    out = []
    group = ""
    for k, (i, title, g) in enumerate(hits):
        if g:
            group = g
        name = title.strip(SYM).strip()
        if name in as_group:
            group = (group + "/" if group else "") + name
            continue
        name = rename.get(name, name)
        tc = cfg.get("title_clean")
        if tc:
            name = re.sub(tc, "", name).strip() or name
        end = hits[k + 1][0] if k + 1 < len(hits) else len(lines)
        start = i + 1
        if cfg["mode"] == "hui":
            parts = [title]
            j = i + 1
            while j < end and j < i + 3 and lines[j] and len(lines[j]) <= MAXT:
                parts.append(lines[j])
                j += 1
            name = " ".join(parts).strip()
            start = j
        sep = cfg.get("sep", "/")
        grp = group.strip(SYM).strip()
        if cfg.get("group_strip_prefix") and grp.startswith(prefix):
            grp = grp[len(prefix):].strip()
        full = f"{prefix}{sep}{grp}{sep}{name}" if grp else f"{prefix}{sep}{name}"
        body = "\n".join(lines[start:end]).strip()
        out.append({"title": full, "raw": body, "group": grp, "lost": "亡佚" in title or "阙佚" in title})
    # 文末尾标（页尾卷题）只留标题、无正文 → 丢弃，避免污染末章
    if len(out) > 1 and not out[-1]["raw"] and hits and hits[-1][0] >= len(lines) - 3:
        print(f"   [toc] 丢弃文末尾标 {out[-1]['title'].split('/')[-1]}")
        out.pop()
    return out


def prune_toc(chapters: list[dict]) -> list[dict]:
    """目录区去重：取「标题不重复的最长后缀」作为正文起点。"""
    names = [c["title"].split("/")[-1] for c in chapters]
    seen: dict[str, int] = {}
    start = 0
    for idx, n in enumerate(names):
        if n in seen:
            start = max(start, seen[n] + 1)
        seen[n] = idx
    if start and start < len(chapters):
        dropped = chapters[:start]
        if sum(c.get("chars", 999) for c in dropped) < 0.02 * max(1, sum(
                len(c["raw"]) for c in chapters)):
            print(f"   [toc] 丢弃目录区 {start} 条 → 正文 {len(chapters)-start} 章")
            return chapters[start:]
        print(f"   [toc] 检出重名 {start} 条但有正文，保留")
    return chapters


def prep(title: str, cfg: dict) -> tuple[list[dict], dict]:
    lines = pre_clean(read_lines(cfg["file"]), cfg)
    hits = detect(lines, cfg)
    chapters = build_chapters(lines, hits, cfg)
    mc = cfg.get("min_chars", 80)
    if cfg["mode"] == "single":
        chapters = [{"title": f'{cfg["prefix"]}/全文', "raw": "\n".join(lines), "group": "", "lost": False}]
    # 先算字数以支持 prune 判定
    for c in chapters:
        c["chars"] = len(c["raw"])
    chapters = prune_toc(chapters)
    rows, total = [], 0
    for c in chapters:
        cleaned = clean_text(c["raw"])
        blocks = to_blocks(cleaned)
        chars = sum(len(b["x"]) for b in blocks if b["t"] == "p")
        if c["lost"]:
            q, note = "lost", "底本原阙（亡佚篇）"
        elif chars == 0:
            q, note = "empty", "0字"
        elif chars < mc:
            q, note = "incomplete", f"{chars}字"
        else:
            q, note = "ok", ""
        rows.append({"title": c["title"], "text": c["raw"], "clean": cleaned, "blocks": blocks,
                     "chars": chars, "quality": q, "note": note, "group": c["group"]})
        total += chars
    return rows, {"chars": total, "n": len(rows)}


def grade(rows: list[dict], min_chars: int) -> tuple[str, str]:
    valid = [r for r in rows if r["chars"] > 0]
    if not valid:
        return "unavailable", "未获取到可用正文"
    total = sum(r["chars"] for r in valid)
    bad = [r for r in rows if r["quality"] not in ("ok", "lost")]
    avg = total / len(valid)
    if len(valid) == 1 and len(rows) == 1:
        if rows[0].get("quality") == "ok":
            return "ok", f"全书单页 {total} 字"
        return "incomplete", f"全书单页 {total} 字，未分章"
    if len(bad) > max(2, len(rows) * 0.15) or avg < min_chars * 1.5:
        return "incomplete", f"{len(valid)} 章 {total} 字（均 {avg:.0f}），{len(bad)} 章待核"
    return "ok", f"{len(valid)} 章 {total} 字（均 {avg:.0f}）" + (f"，{len(bad)} 章偏短" if bad else "")


def save(title: str, cfg: dict, rows: list[dict], apply: bool) -> dict:
    con = sqlite3.connect(DB)
    wid = cfg.get("work_id")
    if not wid:
        r = con.execute("select id from works where seed_title=?", (title,)).fetchone()
        if r:
            wid = r[0]
        elif apply:
            wid = con.execute("insert into works (seed_title, bu, status) values(?,?,?)",
                              (title, cfg.get("bu", ""), "pending")).lastrowid
        else:
            wid = -1
    wq, wnote = grade(rows, cfg.get("min_chars", 80))
    if not apply:
        print(f"[dry-run] work_id={wid} quality={wq} {wnote}")
        return {"title": title, "quality": wq, "note": wnote}
    con.execute("delete from chapters where work_id=?", (wid,))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    total, n = 0, 0
    seen = {}
    for ordn, r in enumerate(rows, 1):
        if r["chars"] <= 0:
            continue
        t = r["title"]
        if t in seen:
            seen[t] += 1
            t = "%s（%d）" % (t, seen[t])
        else:
            seen[t] = 1
        con.execute("""insert into chapters
            (work_id,title,text,chars,clean_text,blocks,quality,quality_note,ord,ord_source,noise_ratio,ord_group)
            values(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (wid, t, r["text"], r["chars"], r["clean"],
             json.dumps(r["blocks"], ensure_ascii=False), r["quality"], r["note"],
             ordn, "daizhige", 0.0, r["group"]))
        total += r["chars"]
        n += 1
    con.execute("""update works set status='ok', quality=?, total_chars=?, chapter_count=?,
                   fetched_at=?, last_error=NULL where id=?""", (wq, total, n, now, wid))
    con.execute("""insert into work_profiles (work_id, version_text, version_source, confidence, updated_at)
                   values (?,?,?,?,?)
                   on conflict(work_id) do update set version_text=excluded.version_text,
                     version_source=excluded.version_source, confidence='draft', updated_at=excluded.updated_at""",
                (wid, cfg["note"], "https://daizhige.org/ （CC BY-SA 4.0）", "draft", now))
    con.commit()
    print(f"[apply] work={wid} 《{title}》 {n} 章 {total} 字 quality={wq}")
    return {"title": title, "work_id": wid, "chapters": n, "chars": total, "quality": wq, "note": wnote}
