#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""殆知阁归档 → 古籍库统一导入器（配置化切章）。

用法：
  python import_daizhige_corpus.py --list                 # 查看已配置书目
  python import_daizhige_corpus.py --title 坛经            # dry-run 单部
  python import_daizhige_corpus.py --batch 1 --apply      # 批次写库
  python import_daizhige_corpus.py --title 坛经 --apply

切章模式（mode）：
  hui      第X回（允许空格/三位数字），回目跨两行时合并
  chu      第X出
  juan     卷X（可带卷名）
  pian_num 篇名+汉序（更法第一 / 行由第一 / 天官冢宰第一）
  yinyan   导言X / 论X
  mark     指定单字标记开头的行（○ ● ◎ △ 【x】）
  tiao     序号独占行（人间词话「一」「二」…）
  list     固定标题清单（按出现顺序切；允许前缀模糊）

每条配置字段：
  file     归档文件名（data/sources/daizhige/ 下）
  work_id  目标 works.id（None 表示新建）
  prefix   章标题前缀（书名）
  mode/…   切章参数
  min_chars 单章最小字数（低于记为 incomplete）
  note     底本说明（写入 work_profiles.version_text）
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

# ---------------------------------------------------------------- 切章模板
RE_HUI = re.compile(rf"^第\s*[{CN}0-9]{{1,4}}\s*回")
RE_CHU = re.compile(rf"^第\s*[{CN}0-9]{{1,3}}\s*出")
RE_JUAN = re.compile(rf"^卷\s*第?[{CN}0-9]{{1,4}}(.*)$")
RE_PIAN = re.compile(rf"^(\S{{1,8}}?)第([{CN}0-9]{{1,4}})(亡佚|阙佚|缺)?$")
RE_YINYAN = re.compile(rf"^(导言|论)([{CN}0-9]{{1,3}})\s*(.*)$")
RE_PIN = re.compile(r"^[【〔\[]([^】〕\]]{1,8})[】〕\]]$")
RE_TIAO = re.compile(rf"^[{CN}0-9]{{1,3}}$")

DUP_TITLE_MAX = 24   # 目录区标题行最大字数


def read_lines(name: str) -> list[str]:
    raw = (SRC / name).read_text(encoding="utf-8", errors="ignore")
    body = raw.split("---", 2)[-1]
    out = []
    for l in body.splitlines():
        s = RE_TAG.sub("", RE_PUA.sub("", l))
        s = s.replace("\u3000", " ").strip()
        out.append(s)
    return out


def strip_toc(lines: list[str]) -> list[str]:
    """切除目录区：从「目录/目次/总目」行起，丢弃其后连续短行（标题）至第一段长正文。"""
    for i, l in enumerate(lines[:400]):
        if l in ("目录", "目次", "总目", "總目", "回目录", "目录终"):
            j = i + 1
            while j < len(lines) and (not lines[j] or len(lines[j]) <= DUP_TITLE_MAX):
                j += 1
            if j < len(lines):
                head = [x for x in lines[:i] if x]
                return head + lines[j:]
    return lines


def detect(lines: list[str], cfg: dict) -> list[tuple[int, str, str]]:
    """返回 [(行号, 章标题, 分组)]"""
    mode = cfg["mode"]
    hits: list[tuple[int, str, str]] = []
    if mode == "list":
        want = cfg["titles"]
        k = 0
        for i, l in enumerate(lines):
            if not l or len(l) > 20:
                continue
            if k < len(want) and l.replace(" ", "").startswith(want[k].replace(" ", "")):
                hits.append((i, l, ""))
                k += 1
        if k < len(want):
            print(f"   [warn] list 模式仅命中 {k}/{len(want)}：{[w for w in want[k:]]}")
        return hits
    marks = cfg.get("marks", "")
    group_mark = cfg.get("group_mark", "")
    group = ""
    for i, l in enumerate(lines):
        if not l:
            continue
        if group_mark and l.startswith(group_mark):
            group = l.lstrip(group_mark).strip()
            continue
        ok = False
        if mode == "hui":
            ok = bool(RE_HUI.match(l)) and len(l) <= 40
        elif mode == "chu":
            ok = bool(RE_CHU.match(l)) and len(l) <= 20
        elif mode == "juan":
            ok = bool(RE_JUAN.match(l)) and len(l) <= 20
        elif mode == "pian_num":
            m = RE_PIAN.match(l)
            ok = bool(m) and (not cfg.get("only_names") or m.group(1) in cfg["only_names"])
        elif mode == "yinyan":
            ok = bool(RE_YINYAN.match(l)) and len(l) <= 20
        elif mode == "mark":
            ok = l[0] in marks and 1 < len(l) <= DUP_TITLE_MAX
        elif mode == "tiao":
            ok = bool(RE_TIAO.match(l))
        elif mode == "pin":
            ok = bool(RE_PIN.match(l))
        if ok:
            hits.append((i, l, group))
    return hits


def build_chapters(lines: list[str], hits: list[tuple[int, str, str]], cfg: dict) -> list[dict]:
    prefix = cfg["prefix"]
    out = []
    for k, (i, title, group) in enumerate(hits):
        end = hits[k + 1][0] if k + 1 < len(hits) else len(lines)
        # hui 模式：回目可能拆成两行，标题行不含回目文字时并入下一短行
        title_line = title
        start = i + 1
        if cfg["mode"] == "hui":
            parts = [title]
            j = i + 1
            while j < end and j < i + 3 and lines[j] and len(lines[j]) <= 24:
                parts.append(lines[j])
                j += 1
            title_line = " ".join(parts).strip()
            start = j
        sep = cfg.get("sep", "/")
        name = title_line.lstrip(cfg.get("strip", "")).strip()
        full = f"{prefix}{sep}{group}{sep}{name}" if group else f"{prefix}{sep}{name}"
        body = "\n".join(lines[start:end]).strip()
        out.append({"title": full, "raw": body, "group": group})
    return out


MODES_NOTE = {"hui": "章回", "chu": "出目", "juan": "卷", "pian_num": "篇",
              "yinyan": "导言/论", "mark": "标记条目", "tiao": "条", "pin": "品"}


# ---------------------------------------------------------------- 配置表
CONFIG: dict[str, dict] = {
    # ===== 批次 1：第二批建议 8 部 =====
    "坛经": dict(file="六祖大师法宝坛经_1.md", work_id=None, mode="pian_num",
                 prefix="坛经", sep="/",
                 only_names={"行由", "般若", "疑问", "定慧", "坐禅", "忏悔",
                             "机缘", "顿渐", "宣诏", "付嘱"},
                 min_chars=200,
                 note="元 宗宝编《六祖大师法宝坛经》，一卷十品（行由第一至付嘱第十）；"
                      "底本：殆知阁归档（源自漢籍リポジトリ），CC BY-SA 4.0"),
    "明夷待访录": dict(file="明夷待访录.md", work_id=None, mode="list", prefix="明夷待访录",
                    sep="/",
                    titles=["原君", "原臣", "原法", "置相", "学校", "取士上", "取士下",
                            "建都", "方镇", "田制一", "田制二", "田制三", "兵制一",
                            "兵制二", "兵制三", "财计一", "财计二", "财计三",
                            "胥吏", "奄宦上", "奄宦下"],
                    min_chars=300,
                    note="清 黄宗羲撰，二十一篇（原君至奄宦下）；底本：殆知阁归档，CC BY-SA 4.0"),
    "传习录": dict(file="传习录.md", work_id=None, mode="list", prefix="传习录", sep="/",
                   titles=["卷上", "以下门人陆澄录", "以下门人薛侃录", "传习录卷中",
                           "钱德洪序", "答顾东挢书", "答周道通书", "答陆原静书",
                           "答欧阳崇一", "答罗整庵少宰书", "答聂文蔚",
                           "右南大吉录", "训蒙大意示教读刘伯颂等", "教约",
                           "传习录卷下", "门人漺丸川录", "门人黄直录",
                           "以下门人黄省曾录", "钱德洪跋"],
                   min_chars=200,
                   note="明 王阳明撰，门人辑录；底本：殆知阁归档（三卷本），CC BY-SA 4.0"),
    "商君书": dict(file="商子.md", work_id=None, mode="pian_num", prefix="商君书", sep="/",
                   min_chars=200,
                   note="战国 商鞅及其后学，二十六篇（更法第一至定分第二十六，含亡佚篇）；"
                        "底本：殆知阁归档《商子》，CC BY-SA 4.0"),
    "人间词话": dict(file="人间词话.md", work_id=None, mode="tiao", prefix="人间词话", sep="/",
                  min_chars=15,
                  note="清末 王国维撰，通行六十四则本；底本：殆知阁归档，CC BY-SA 4.0"),
    "二十四诗品": dict(file="二十四诗品.md", work_id=None, mode="pin", prefix="二十四诗品",
                   sep="/", min_chars=40,
                   note="唐 司空图撰，二十四品（雄浑至流动）；底本：殆知阁归档，CC BY-SA 4.0"),
    "文史通义": dict(file="文史通义.md", work_id=None, mode="mark", marks="○", group_mark="●",
                  prefix="文史通义", sep="/", min_chars=150,
                  note="清 章学诚撰，内篇分卷（易教上至外篇）；底本：殆知阁归档，CC BY-SA 4.0"),
    "天演论": dict(file="天演论.md", work_id=None, mode="yinyan", prefix="天演论", sep="/",
                 min_chars=300,
                 note="清末 严复译赫胥黎《进化论与伦理学》，导言十八篇、论十七篇；"
                      "底本：殆知阁归档，CC BY-SA 4.0"),
}


# ---------------------------------------------------------------- 主流程
def prep(title: str, cfg: dict) -> tuple[list[dict], dict]:
    lines = read_lines(cfg["file"])
    lines = strip_toc(lines)
    hits = detect(lines, cfg)
    chapters = build_chapters(lines, hits, cfg)
    rows, total = [], 0
    for c in chapters:
        cleaned = clean_text(c["raw"])
        blocks = to_blocks(cleaned)
        chars = sum(len(b["x"]) for b in blocks if b["t"] == "p")
        q = "ok" if chars >= cfg.get("min_chars", 80) else ("empty" if chars == 0 else "incomplete")
        rows.append({"title": c["title"], "text": c["raw"], "clean": cleaned,
                     "blocks": blocks, "chars": chars, "quality": q,
                     "note": "" if q == "ok" else f"{chars}字", "group": c["group"]})
        total += chars
    return rows, {"chars": total, "n": len(rows)}


def grade(rows: list[dict], min_chars: int) -> tuple[str, str]:
    valid = [r for r in rows if r["chars"] > 0]
    if not valid:
        return "unavailable", "未获取到可用正文"
    total = sum(r["chars"] for r in valid)
    bad = [r for r in rows if r["quality"] != "ok"]
    avg = total / len(valid)
    if len(valid) == 1:
        return "incomplete", f"全书单页 {total} 字，未分章"
    if len(bad) > max(2, len(rows) * 0.15) or avg < min_chars * 1.5:
        return "incomplete", f"{len(valid)} 章 {total} 字（均 {avg:.0f}），{len(bad)} 章待核"
    return "ok", f"{len(valid)} 章 {total} 字（均 {avg:.0f}）" + (
        f"，{len(bad)} 章偏短" if bad else "")


def save(title: str, cfg: dict, rows: list[dict], apply: bool) -> None:
    con = sqlite3.connect(DB)
    wid = cfg.get("work_id")
    if not wid:
        r = con.execute("select id from works where seed_title=?", (title,)).fetchone()
        if r:
            wid = r[0]
        elif apply:
            cur = con.execute("insert into works (seed_title, bu, dynasty, status) values(?,?,?,?)",
                              (title, cfg.get("bu", ""), cfg.get("dynasty", ""), "pending"))
            wid = cur.lastrowid
        else:
            wid = -1
    wq, wnote = grade(rows, cfg.get("min_chars", 80))
    if not apply:
        print(f"[dry-run] work_id={wid} quality={wq} {wnote}")
        return
    con.execute("delete from chapters where work_id=?", (wid,))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    total = 0
    for ordn, r in enumerate(rows, 1):
        if r["chars"] <= 0:
            continue
        con.execute("""insert or ignore into chapters
            (work_id,title,text,chars,clean_text,blocks,quality,quality_note,ord,ord_source,noise_ratio,ord_group)
            values(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (wid, r["title"], r["text"], r["chars"], r["clean"],
             json.dumps(r["blocks"], ensure_ascii=False), r["quality"], r["note"],
             ordn, "daizhige", 0.0, r["group"]))
        total += r["chars"]
    con.execute("""update works set status='ok', quality=?, total_chars=?, chapter_count=?,
                   fetched_at=?, last_error=NULL where id=?""",
                (wq, total, sum(1 for r in rows if r["chars"] > 0), now, wid))
    # 底本信息
    con.execute("""insert into work_profiles (work_id, version_text, version_source, confidence, updated_at)
                   values (?,?,?,?,?)
                   on conflict(work_id) do update set version_text=excluded.version_text,
                     version_source=excluded.version_source, confidence='draft', updated_at=excluded.updated_at""",
                (wid, cfg["note"], "https://daizhige.org/ （CC BY-SA 4.0）", "draft", now))
    con.commit()
    print(f"[apply] work={wid} 《{title}》 {len([r for r in rows if r['chars']>0])} 章 {total} 字 quality={wq}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title")
    ap.add_argument("--batch", type=int)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        for t, c in CONFIG.items():
            print(f'{t:<8} {c["file"]:<22} {c["mode"]:<9} {MODES_NOTE[c["mode"]]}')
        return 0
    titles = [a.title] if a.title else list(CONFIG)
    for t in titles:
        cfg = CONFIG[t]
        print(f"\n===== 《{t}》 {cfg['file']} mode={cfg['mode']} =====")
        rows, meta = prep(t, cfg)
        print(f"  章数={meta['n']} 总字={meta['chars']}")
        for r in rows[:3]:
            print(f"   + {r['title'][:40]:<40} {r['chars']:>6} {r['quality']}")
        for r in rows[-2:]:
            print(f"   - {r['title'][:40]:<40} {r['chars']:>6} {r['quality']}")
        bad = [(r["title"][:26], r["chars"]) for r in rows if r["quality"] != "ok"]
        if bad:
            print(f"   [待核 {len(bad)}]", bad[:8])
        save(t, cfg, rows, a.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
