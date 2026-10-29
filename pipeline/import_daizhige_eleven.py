#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为 11 部仅有版本档案、无正文的古籍，从本地殆知阁归档切章导入正文。

书目与切章依据：
  11 尔雅      释诂第一…释畜第十九（19 篇，目录后正文重起）
  12 说文解字  说文条目行「编号:N  部  字  拼音  释文  反切」，按部首切 540 章
  19 国语      卷一 周语上…卷二十一 越语下（21 卷，目录后正文重起）
  38 齐民要术  ●序 / ●耕田第一…●笔墨第九十一（92 篇）
  41 楚辞      离骚 / 九歌 X / 天问 / 九章 X …（篇名白名单，目录后正文重起）
  42 文选      文选卷第一…文选卷第六十（正文卷标题；前置序、目录不入正文）
  44 宋词三百首 词牌+作者行「宴山亭　赵佶」，按词牌切章
  45 古文观止  【郑伯克段于鄢】（…《左传》）222 篇
  47 诗品      ◎卷上 / ◎卷中 / ◎卷下（3 章，前置序文单独成章）
  48 陶渊明集  卷一 诗四言…卷七 疏祭文（7 卷，目录后正文重起）
  49 李太白集  ○　篇名（831 篇）

用法：
  python import_daizhige_eleven.py --work-id 11            # dry-run
  python import_daizhige_eleven.py --work-id 11 --apply    # 写库
  python import_daizhige_eleven.py --all [--apply]
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

SRC_DIR = Path(r"D:\DimensionsCosmos\data\sources\daizhige")
DB = r"D:\DimensionsCosmos\data\guji.db"
RE_PUA = re.compile(r"[\ue000-\uf8ff]")
# 底本网页抓取残留导航行（国语等）
RE_NAV = re.compile(r"(上一页|下一页|回目录|返回目录|手机版|扫码|微信公众号|分享到|新闻\s+网页|贴吧|MP3|全文\s+书名)")


def body_lines(name: str) -> list[str]:
    raw = (SRC_DIR / name).read_text(encoding="utf-8", errors="ignore")
    parts = raw.split("---", 2)
    text = parts[2] if len(parts) > 2 else raw
    out = []
    for l in text.splitlines():
        l = RE_PUA.sub("", l).replace("\ufeff", "").strip()
        if not l:
            continue
        if RE_NAV.search(l):
            # 网页导航行常吞掉正文标题（国语卷五）：抢救行尾的卷题
            m = re.search(r"(卷[一二三四五六七八九十]+[\s　]+\S{2,8})\s*$", l)
            if m:
                out.append(m.group(1).strip())
            continue
        out.append(l)
    return out


def drop_toc(lines: list[str], hits: list[int], key) -> list[int]:
    """剥离前置目录：目录是同一组标题的连续复现，正文从首条目再次出现处开始。"""
    if not hits:
        return hits
    first = key(lines[hits[0]])
    for k in range(1, len(hits)):
        if key(lines[hits[k]]) == first:
            # 仅当前置区条目彼此紧邻（纯目录）时才认定
            gap_ok = all(hits[j + 1] - hits[j] <= 2 for j in range(k - 1))
            if gap_ok:
                return hits[k:]
            break
    return hits


def split_by(lines: list[str], pat: re.Pattern, title_of) -> list[dict]:
    hits = [i for i, l in enumerate(lines) if pat.match(l)]
    if not hits:
        raise SystemExit(f"[fail] 无标题命中：{pat.pattern}")
    hits = drop_toc(lines, hits, lambda l: l)
    out = []
    for k, i in enumerate(hits):
        end = hits[k + 1] if k + 1 < len(hits) else len(lines)
        out.append({"title": title_of(lines[i], k),
                    "text": "\n".join(lines[i + 1:end])})
    return out


# ---------- 各书切章 ----------
def ch_erya():
    pat = re.compile(r"^释\S{1,2}第[一二三四五六七八九十]+$")
    return split_by(body_lines("尔雅.md"), pat, lambda l, k: f"尔雅/{l}")


def ch_shuowen():
    item = re.compile(r"^编号[:：]\s*(\d+)\s+(\S+?部)\s+(\S+)\s+(\S+)\s+(.+)$")
    lines = body_lines("说文解字.md")
    chapters, cur, cur_bu, buf, first_no = [], None, None, [], None

    def flush():
        if cur is not None:
            title = cur
            # 底本对生僻部首字用 □ 占位：补首条编号便于回查 ExternalSource
            if "□" in title:
                title = f"{title}·编号{first_no}"
            chapters.append({"title": f"说文解字/{title}", "text": "\n".join(buf)})

    miss = 0
    for l in lines:
        m = item.match(l)
        if not m:
            miss += 1
            continue
        no, bu, zi, py, rest = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        rest = re.sub(r"\s{2,}", "；", rest.strip()).rstrip("；")
        rest = re.sub(r"^(.+?)；(.+)$", r"\1（\2）", rest) if "；" in rest else rest
        if bu != cur_bu:
            flush()
            cur_bu, cur, buf, first_no = bu, bu, [], no
        buf.append(f"{zi}：{rest}")
    flush()
    print(f"   [shuowen] 非条目行={miss} 部首章={len(chapters)}")
    return chapters


def ch_guoyu():
    pat = re.compile(r"^卷[一二三四五六七八九十]+[\s　]+\S{2,8}$")
    return split_by(body_lines("国语.md"), pat, lambda l, k: f"国语/{l}")


def ch_qimin():
    """● 行即篇标题（含「瞿麦附」等后缀）；●卷X 为分卷标记，不入章。"""
    lines = body_lines("齐民要术.md")
    hits = [i for i, l in enumerate(lines) if l.startswith("●")]
    out = []
    for k, i in enumerate(hits):
        name = lines[i][1:].strip()
        name = re.sub(r"[\s　]{2,}", "·", name)
        if re.match(r"^卷[一二三四五六七八九十]+$", name):
            continue
        end = hits[k + 1] if k + 1 < len(hits) else len(lines)
        out.append({"title": f"齐民要术/{name}", "text": "\n".join(lines[i + 1:end])})
    return out


CHUCI_NAMES = ("离骚|天问|远游|卜居|渔父|九辩|招魂|大招|惜誓|招隐士|哀时命")


def ch_chuci():
    pat = re.compile(rf"^({CHUCI_NAMES}|(?:九歌|九章|七谏|九怀|九叹|九思)[\s　]\S{{1,4}})$")
    return split_by(body_lines("楚辞.md"), pat, lambda l, k: f"楚辞/{l}")


def ch_wenxuan():
    """底本把第十九卷拆成「卷第十九」「卷第十九续」两次打印，合并同卷。"""
    lines = body_lines("文选.md")
    pat = re.compile(r"^文选卷第[一二三四五六七八九十百]+(?:续)?$")
    hits = [i for i, l in enumerate(lines) if pat.match(l)]
    hits = drop_toc(lines, hits, lambda l: l.replace("续", ""))
    out = []
    for k, i in enumerate(hits):
        end = hits[k + 1] if k + 1 < len(hits) else len(lines)
        title = lines[i].replace("续", "")
        body = "\n".join(lines[i + 1:end])
        if out and out[-1]["title"] == f"文选/{title}":
            out[-1]["text"] += "\n" + body.strip()
        else:
            out.append({"title": f"文选/{title}", "text": body})
    return out


def ch_songci():
    """词牌行形如「宴山亭　赵佶」「戚　氏　柳永」：按全角/半角空格分段，
    末段为作者（>=2 字），前段拼为词牌；单字段为副题，不切章。"""
    lines = body_lines("宋词三百首.md")
    juan = re.compile(r"^卷[一二三四五六七八九十]+$")

    def title_of(l: str):
        if "【" in l or re.search(r"[，。？！、；：“”]", l):
            return None
        seg = [s for s in re.split(r"[\s　]+", l) if s]
        if not (2 <= len(seg) <= 3) or len(l) > 18:
            return None
        if len(seg[-1]) < 2 or len(seg[-1]) > 4:
            return None
        return "".join(seg[:-1]) + "·" + seg[-1]

    hits = []
    for i, l in enumerate(lines):
        if juan.match(l):
            hits.append((i, None))
            continue
        t = title_of(l)
        if t:
            hits.append((i, t))
    out = []
    for k, (i, t) in enumerate(hits):
        if t is None:
            continue
        end = hits[k + 1][0] if k + 1 < len(hits) else len(lines)
        out.append({"title": f"宋词三百首/{t}", "text": "\n".join(lines[i + 1:end])})
    return out


def ch_guwen():
    pat = re.compile(r"^【[^】]{2,30}】")
    lines = body_lines("古文观止.md")
    hits = [i for i, l in enumerate(lines) if pat.match(l)]

    def t(l, k):
        m = re.match(r"^【([^】]+)】\s*(?:（(.+?)）)?", l)
        name, src = m.group(1), (m.group(2) or "")
        src = re.sub(r"[《》]", "", src).strip()
        return f"古文观止/{name}" + (f"（{src}）" if src else "")

    out = []
    for k, i in enumerate(hits):
        end = hits[k + 1] if k + 1 < len(hits) else len(lines)
        out.append({"title": t(lines[i], k), "text": "\n".join(lines[i + 1:end])})
    return out


def ch_shipin():
    lines = body_lines("诗品.md")
    pat = re.compile(r"^[◎](\S{2,4})$")
    hits = [i for i, l in enumerate(lines) if pat.match(l)]
    out = []
    if hits and hits[0] > 0:
        pre = [l for l in lines[:hits[0]] if not re.match(r"^诗品[\s　]", l)]
        out.append({"title": "诗品/序", "text": "\n".join(pre)})
    for k, i in enumerate(hits):
        end = hits[k + 1] if k + 1 < len(hits) else len(lines)
        out.append({"title": f"诗品/{lines[i][1:]}", "text": "\n".join(lines[i + 1:end])})
    return out


def ch_tao():
    pat = re.compile(r"^卷[一二三四五六七八九十]+[\s　]+\S{1,6}$")
    return split_by(body_lines("陶渊明集.md"), pat, lambda l, k: f"陶渊明集/{l}")


def ch_taibai():
    """篇名行「○　远别离」；部分行内联首句与注文（「○　东武吟　　一作…」），
    需拆出篇名、保留内联正文，避免整章落空。"""
    lines = body_lines("李太白集.md")
    hits = [i for i, l in enumerate(lines) if l.startswith("○")]
    out = []
    for k, i in enumerate(hits):
        raw = lines[i].lstrip("○").strip()
        segs = [s.strip() for s in re.split(r"[\s　]{2,}", raw) if s.strip()]
        name = segs[0] if segs else raw
        name = re.split(r"(?:[\s　]+(?=一作|又作|二首|三首|四首|五首))", name)[0]
        name = re.sub(r"[\s　]+", "·", name).strip("·")
        inline = []
        for s in segs[1:]:
            # 注文（一作/二首/长安/上元…）与正文混排：长段保留并剥离注语
            if len(s) <= 10:
                continue
            s = re.sub(r"^(一作|又作|二首|三首|四首|五首)[^\s　]*[\s　]+", "", s)
            inline.append(s)
        end = hits[k + 1] if k + 1 < len(hits) else len(lines)
        body = "\n".join(inline + lines[i + 1:end]).strip()
        if not body and len(raw) > len(name):
            body = raw[len(name):].strip()
        out.append({"title": f"李太白集/{name}", "text": body})
    return out


BOOKS: dict[int, dict] = {
    11: dict(book="尔雅", fn=ch_erya, min_chars=20, min_avg=150, min_total=8000,
             src="data/sources/daizhige/尔雅.md"),
    12: dict(book="说文解字", fn=ch_shuowen, min_chars=5, min_avg=200, min_total=100000,
             src="data/sources/daizhige/说文解字.md"),
    19: dict(book="国语", fn=ch_guoyu, min_chars=50, min_avg=300, min_total=40000,
             src="data/sources/daizhige/国语.md"),
    38: dict(book="齐民要术", fn=ch_qimin, min_chars=30, min_avg=200, min_total=50000,
             src="data/sources/daizhige/齐民要术.md"),
    41: dict(book="楚辞", fn=ch_chuci, min_chars=30, min_avg=150, min_total=15000,
             src="data/sources/daizhige/楚辞.md"),
    42: dict(book="文选", fn=ch_wenxuan, min_chars=100, min_avg=1000, min_total=300000,
             src="data/sources/daizhige/文选.md"),
    44: dict(book="宋词三百首", fn=ch_songci, min_chars=10, min_avg=60, min_total=20000,
             src="data/sources/daizhige/宋词三百首.md"),
    45: dict(book="古文观止", fn=ch_guwen, min_chars=30, min_avg=150, min_total=60000,
             src="data/sources/daizhige/古文观止.md"),
    47: dict(book="诗品", fn=ch_shipin, min_chars=30, min_avg=500, min_total=6000,
             src="data/sources/daizhige/诗品.md"),
    48: dict(book="陶渊明集", fn=ch_tao, min_chars=50, min_avg=500, min_total=20000,
             src="data/sources/daizhige/陶渊明集.md"),
    49: dict(book="李太白集", fn=ch_taibai, min_chars=10, min_avg=60, min_total=100000,
             src="data/sources/daizhige/李太白集.md"),
}


def build_rows(chapters, min_chars):
    rows = []
    for c in chapters:
        cleaned = clean_text(c["text"])
        blocks = to_blocks(cleaned)
        chars = sum(len(b["x"]) for b in blocks if b["t"] == "p")
        if chars == 0:
            q, note = "empty", "原文为空"
        elif chars < min_chars:
            q, note = "incomplete", f"仅 {chars} 字，疑为残缺底本"
        else:
            q, note = "ok", ""
        rows.append({"title": c["title"], "text": c["text"], "clean": cleaned,
                     "blocks": blocks, "chars": chars, "quality": q, "note": note})
    return rows


def grade_work(rows, min_avg, min_total):
    valid = [r for r in rows if r["chars"] > 0]
    if not valid:
        return "unavailable", "未获取到可用正文"
    total = sum(r["chars"] for r in valid)
    avg = total / len(valid)
    empty = len(rows) - len(valid)
    tail = f"，另 {empty} 章无正文已跳过" if empty else ""
    if total < min_total or avg < min_avg:
        return "incomplete", f"共 {len(valid)} 章 {total} 字（均 {avg:.0f} 字），疑有缺失{tail}"
    return "ok", tail.lstrip("，")


def dedup_titles(rows: list[dict]) -> list[dict]:
    """chapters 表 (work_id,title) 唯一：同名词牌/篇名追加〔n〕序号。"""
    seen: dict[str, int] = {}
    for r in rows:
        t = r["title"]
        if t in seen:
            seen[t] += 1
            r["title"] = f"{t}〔{seen[t]}〕"
        else:
            seen[t] = 1
    dup = {k: v for k, v in seen.items() if v > 1}
    if dup:
        print(f"     [dedup] {len(dup)} 个重名标题已加序号，如 {list(dup)[:3]}")
    return rows


def run(wid: int, apply: bool, db: str) -> None:
    cfg = BOOKS[wid]
    chapters = cfg["fn"]()
    rows = dedup_titles(build_rows(chapters, cfg["min_chars"]))
    total = sum(r["chars"] for r in rows)
    wq, note = grade_work(rows, cfg["min_avg"], cfg["min_total"])
    print(f"\n[{wid}] {cfg['book']} 章数={len(rows)} 总字数={total} "
          f"均={total/max(1,len(rows)):.0f} quality={wq} {note}")
    print("     首:", [r["title"] for r in rows[:2]])
    print("     末:", [r["title"] for r in rows[-2:]])
    bad = [(r["title"], r["chars"]) for r in rows if r["chars"] < 20]
    if bad:
        print("     [warn] 极短章:", bad[:8], f"(共{len(bad)})")
    if not apply:
        print("     [dry-run]")
        return
    con = sqlite3.connect(db)
    con.execute("delete from chapters where work_id=?", (wid,))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for ordn, r in enumerate(rows, 1):
        con.execute(
            """insert into chapters
               (work_id,title,text,chars,clean_text,blocks,quality,quality_note,ord,ord_source,noise_ratio,ord_group)
               values(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (wid, r["title"], r["text"], r["chars"], r["clean"],
             json.dumps(r["blocks"], ensure_ascii=False), r["quality"], r["note"],
             ordn, "daizhige", 0.0, ""))
    con.execute("""update works set status='ok', quality=?, total_chars=?, chapter_count=?,
                   fetched_at=?, last_error=NULL where id=?""",
                (wq, total, len(rows), now, wid))
    con.commit()
    print(f"     [apply] 写入 {len(rows)} 章 {total} 字 quality={wq}")
    print(f"     底本: {cfg['src']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-id", type=int, action="append")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--db", default=DB)
    a = ap.parse_args()
    ids = list(BOOKS) if a.all else (a.work_id or [])
    if not ids:
        raise SystemExit("need --work-id 或 --all")
    for wid in ids:
        run(wid, a.apply, a.db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
