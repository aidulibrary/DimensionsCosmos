# -*- coding: utf-8 -*-
"""FLCA-6 ｜ 渲染器参考实现（M1 验收 + 前端对照）

用法：
  python render_chapter.py --chapter-id 2 --build-id b20261111_L05rule_v2
  python render_chapter.py --chapter-id 2 --format html
  python render_chapter.py --chapter-id 2 --format text --limit 200
"""
import argparse
import html
import json
import pathlib
import sqlite3
import sys

DB = pathlib.Path(r"D:\DimensionsCosmos\data\guji.db")
SHARD_ROOT = pathlib.Path(r"D:\DimensionsCosmos\data\pinyin")
STATE_LABEL = {"a": "确定", "v": "异读", "u": "存疑"}


def load(chapter_id, build_id):
    con = sqlite3.connect(str(DB))
    row = con.execute("SELECT id, work_id, COALESCE(clean_text,text) FROM chapters WHERE id=?",
                      (chapter_id,)).fetchone()
    con.close()
    if not row:
        sys.exit(f"章节 {chapter_id} 不存在")
    cid, wid, raw = row
    f = SHARD_ROOT / build_id / str(wid) / f"{cid}.json"
    if not f.exists():
        sys.exit(f"分片缺失：{f}")
    shard = json.loads(f.read_text(encoding="utf-8"))
    shard["meta"] = {int(k): v for k, v in shard.get("meta", {}).items()}
    return cid, wid, raw, shard


def render_text(raw, shard):
    """纯文本：原文(读音) ｜ * 规则命中／~ 异读／! 存疑"""
    out, prev_off = [], -1
    for k, off in enumerate(shard["pos"]):
        if off > prev_off + 1:
            out.append(raw[prev_off + 1:off])
        code = shard["st"][k]
        mk = "*" if k in shard["meta"] else ""
        if code == "u":
            mk += "!"
        elif code == "v":
            mk += "~"
        out.append(f"{raw[off]}({shard['py'][k]}{mk})")
        prev_off = off
    out.append(raw[prev_off + 1:])
    return "".join(out)


def render_html(raw, shard, title=""):
    """HTML ruby：三态以 class 区分，存疑可展开 alt 音（D5-b：默认显示确定音，存疑虚线）"""
    parts = [f'<article class="guji-chapter"><h3>{html.escape(title)}</h3><p class="guji-text">']
    prev_off = -1
    for k, off in enumerate(shard["pos"]):
        if off > prev_off + 1:
            parts.append(html.escape(raw[prev_off + 1:off]))
        code = shard["st"][k]
        cls = {"a": "py-a", "v": "py-v", "u": "py-u"}[code]
        if k in shard["meta"]:
            cls += " py-rule"
        alt = ""
        if code == "v" and len(shard["meta"].get(k) or []) == 4 and shard["meta"][k][3]:
            alt = f' title="异读：{html.escape("/".join(shard["meta"][k][3]))}"'
        elif code == "u":
            alt = ' title="读音存疑，点击可展开候选"'
        parts.append(
            f'<ruby class="{cls}"{alt}>{html.escape(raw[off])}'
            f'<rt>{html.escape(shard["py"][k])}</rt></ruby>')
        prev_off = off
    parts.append(html.escape(raw[prev_off + 1:]))
    parts.append("</p></article>")
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapter-id", type=int, required=True)
    ap.add_argument("--build-id", default="b20261111_L05rule_v2")
    ap.add_argument("--format", choices=["text", "html"], default="text")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    cid, wid, raw, shard = load(a.chapter_id, a.build_id)
    if a.format == "text":
        s = render_text(raw, shard)
        print(f"章节 {cid}（work {wid}，{len(raw)} 字，build {a.build_id}）")
        print(s[:a.limit] if a.limit else s)
    else:
        con = sqlite3.connect(str(DB))
        title = con.execute("SELECT title FROM chapters WHERE id=?", (cid,)).fetchone()[0] or ""
        con.close()
        print(render_html(raw, shard, title))
    return 0


if __name__ == "__main__":
    sys.exit(main())
