# -*- coding: utf-8 -*-
"""《文選》白文导入（维基文库 昭明文選，CC BY-SA）

底本：https://zh.wikisource.org/wiki/昭明文選/卷N （清胡克家重刊宋淳熙本李善注本）
处理：剥离 {{*|注}}、<ref>校勘</ref>、[[链接]]、{{ProperNoun|}} 等标记，保留白文，
      按卷切章写入 guji.db work_id=42。

用法：
    python pipeline/import_wikisource_wenxuan.py --dry-run 3
    python pipeline/import_wikisource_wenxuan.py --apply
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "guji.db"
CACHE = ROOT / "data" / "sources" / "wikisource" / "wenxuan"
WORK_ID = 42
API = "https://zh.wikisource.org/w/api.php"
UA = "DimensionsCosmos/1.0 (local pipeline; contact: local)"


def fetch_wikitext(title: str) -> str:
    q = urllib.parse.urlencode({
        "action": "query", "titles": title, "prop": "revisions",
        "rvprop": "content", "rvslots": "main", "format": "json", "formatversion": "2",
    })
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=45).read().decode("utf-8"))
            pg = d["query"]["pages"][0]
            if "revisions" not in pg:
                raise RuntimeError(f"页面缺失: {title}")
            return pg["revisions"][0]["slots"]["main"]["content"]
        except Exception:
            if attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))
    return ""


# ---------- wikitext 清洗 ----------

def _strip_template(text: str, name_pat: str) -> str:
    """删除指定模板（支持嵌套 {{ }}），如 {{*|...}}。"""
    out = []
    i = 0
    while True:
        m = re.compile(name_pat).search(text, i)
        if not m:
            out.append(text[i:])
            break
        out.append(text[i:m.start()])
        # 从 m.start() 起做括号平衡
        depth = 0
        j = m.start()
        while j < len(text):
            if text.startswith("{{", j):
                depth += 1
                j += 2
            elif text.startswith("}}", j):
                depth -= 1
                j += 2
                if depth == 0:
                    break
            else:
                j += 1
        i = j
    return "".join(out)


def _unwrap_template(text: str, name: str) -> str:
    """把 {{name|value}} 解成 value（含嵌套或竖线时取末段）。"""
    pat = re.compile(r"\{\{\s*" + name + r"\s*\|")
    while True:
        m = pat.search(text)
        if not m:
            return text
        depth = 0
        j = m.start()
        while j < len(text):
            if text.startswith("{{", j):
                depth += 1
                j += 2
            elif text.startswith("}}", j):
                depth -= 1
                j += 2
                if depth == 0:
                    break
            else:
                j += 1
        inner = text[m.end(): j - 2]
        # 取最后一个顶层竖线之后的片段（兼容 {{ProperNoun|A|B}}）
        text = text[:m.start()] + inner + text[j:]


def clean_wikitext(raw: str) -> str:
    t = re.sub(r"<ref[^>]*?/>", "", raw)
    t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = _strip_template(t, r"\{\{\s*\*")
    t = re.sub(r"\{\{\s*(Main|main|wikipedia|Wikipedia|w|W|Wikisource)\s*\|[^}]*\}\}", "", t)
    t = _unwrap_template(t, "ProperNoun")
    t = _unwrap_template(t, "PN")
    t = _unwrap_template(t, "WavyBookTitle")
    t = re.sub(r"-\{[A-Za-z]*\|([^}]*)\}", r"\1", t)  # -{A|zh-hans:卷;zh-hant:卷}- 类
    t = re.sub(r"-\{([^}]*)\}-", r"\1", t)
    t = re.sub(r"\[\[([^\]|]*)\|([^\]]*)\]\]", r"\2", t)
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", t)
    t = re.sub(r"'{2,}", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"\{\{[^{}]*\}\}", "", t)  # 残留简单模板
    # 去掉 header/header2 之外的标题层级，用卷标题替代
    lines = []
    for ln in t.split("\n"):
        ln = ln.rstrip()
        if re.match(r"^\s*\{\{header", ln):
            continue
        if re.match(r"^\s*[|}]", ln):  # header 参数残留
            continue
        if re.match(r"^\s*=+\s*", ln):
            continue
        ln = ln.lstrip(":：　 ")
        ln = ln.strip()
        if not ln:
            continue
        lines.append(ln)
    return "\n".join(lines)


def split_paragraphs(text: str):
    out = []
    for ln in text.split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        if len(ln) <= 12 and not re.search(r"[。！？；]$", ln):
            out.append({"t": "h", "x": ln})
        else:
            out.append({"t": "p", "x": ln})
    return out


CN_NUM = "零一二三四五六七八九十"


def cn_num(n: int) -> str:
    if n <= 10:
        return CN_NUM[n] if n < 10 else "十"
    if n < 20:
        return "十" + CN_NUM[n - 10]
    if n < 100:
        s = CN_NUM[n // 10] + "十"
        if n % 10:
            s += CN_NUM[n % 10]
        return s
    return str(n)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", type=int, default=0, help="只处理前 N 卷并打印")
    ap.add_argument("--apply", action="store_true", help="写入数据库")
    args = ap.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    max_juan = args.dry_run if args.dry_run else 60
    chapters = []
    for n in range(1, max_juan + 1):
        title = f"昭明文選/卷{n}"
        cache = CACHE / f"vol{n:02d}.txt"
        if cache.exists():
            raw = cache.read_text(encoding="utf-8")
        else:
            raw = fetch_wikitext(title)
            cache.write_text(raw, encoding="utf-8")
            time.sleep(0.4)
        body = clean_wikitext(raw)
        try:
            import zhconv
            body = zhconv.convert(body, "zh-hans")
        except Exception:
            pass
        blocks = split_paragraphs(body)
        chars = sum(len(b["x"]) for b in blocks if b["t"] == "p")
        ch_title = f"文选/卷{cn_num(n)}"
        chapters.append({"title": ch_title, "text": body, "blocks": blocks, "chars": chars})
        print(f"  {ch_title}: {chars} 字 / {len(blocks)} 块")

    total = sum(c["chars"] for c in chapters)
    print(f"[wenxuan] {len(chapters)} 卷 · {total} 字 · 均 {total // max(len(chapters), 1)}")

    if args.dry_run:
        print("\n--- 卷1 前 900 字 ---")
        print(chapters[0]["text"][:900])
        return

    if not args.apply:
        print("[dry] 未写入；加 --apply 落库")
        return

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("delete from chapters where work_id=?", (WORK_ID,))
    for i, c in enumerate(chapters, 1):
        clean = c["text"]
        cur.execute(
            "insert into chapters (work_id,title,text,chars,clean_text,blocks,quality,quality_note,ord,ord_source,noise_ratio,ord_group)"
            " values (?,?,?,?,?,?,?,?,?,?,?,?)",
            (WORK_ID, c["title"], c["text"], c["chars"], clean,
             json.dumps(c["blocks"], ensure_ascii=False), "ok", "",
             i, "wikisource-vol", 0.0, ""),
        )
    avg = total // max(len(chapters), 1)
    quality = "ok" if total >= 300000 and avg >= 2000 else "incomplete"
    cur.execute(
        "update works set status='ok', quality=?, total_chars=?, chapter_count=?, fetched_at=datetime('now'), last_error=NULL where id=?",
        (quality, total, len(chapters), WORK_ID),
    )
    con.commit()
    con.close()
    print(f"[apply] 写入 {len(chapters)} 卷 {total} 字 quality={quality}")


if __name__ == "__main__":
    main()
