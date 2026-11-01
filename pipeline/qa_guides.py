"""导读体检器：对 ai_guides 逐篇做可复算的硬校验与分布统计。

与生成器里的 `validate()` 不同，这里**不复用生成时上下文**，只从库里重新解析 URN、重新取块原文，
因此能发现"生成时通过、事后数据被改动"的漂移。

用法
    python pipeline/qa_guides.py                      # 全部篇目，控制台摘要
    python pipeline/qa_guides.py --json output/x.json --md output/x.md
    python pipeline/qa_guides.py --strict             # 有硬错误时退出码 1
    python pipeline/qa_guides.py --db output/guidepack.db
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "guji.db"

PUNCT_RE = re.compile(r"[\s\u3000，。、；：？！“”‘’「」『』（）《》〈〉—…·,.;:?!”\"'()\[\]{}<>/\\|~`@#$%^&*+=_-]+")
# 注意：JSON 正文里的 `}}` 是合法结束符，不能当占位符；只抓真正的模板/偷懒痕迹。
PLACEHOLDER_RE = re.compile(r"(材料\s*\d+|TODO|FIXME|xxx+|\{\{|待补充|此处略)")
CLICHE = ("对今天的读者而言", "对今天的读者来说", "值得注意的是", "总的来说")


def norm(text: str) -> str:
    """去空白与标点，用于逐字比对（保留字形，不做繁简转换）。"""
    return PUNCT_RE.sub("", text or "")


def connect(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


def urn_parts(urn: str):
    """dc:Q276015/c002/b002 → ('Q276015', 2, 2)"""
    m = re.match(r"^dc:(Q\d+)/c(\d+)/b(\d+)$", (urn or "").strip())
    if not m:
        return None
    return m.group(1), int(m.group(2)), int(m.group(3))


def load_blocks(conn, qid: str):
    """返回 {章序: [块文本, ...]}，按 chapters.ord 相对同书内序号。"""
    row = conn.execute(
        "SELECT id FROM works WHERE wikidata_qid=?", (qid,)).fetchone()
    if not row:
        return None
    wid = row[0]
    out = {}
    for r in conn.execute("SELECT ref, blocks, ord FROM chapters WHERE work_id=? ORDER BY ord", (wid,)):
        m = re.search(r"/c(\d+)$", r["ref"] or "")
        if not m:
            continue
        idx = int(m.group(1))
        try:
            blocks = json.loads(r["blocks"] or "[]")
        except Exception:
            blocks = []
        out[idx] = [b.get("x", "") if isinstance(b, dict) else str(b) for b in blocks]
    return out


def extract_quote(para: str):
    """段首「…」内为引文；返回 (引文, 论述)。"""
    m = re.match(r"^\s*[「『]([^」』]{4,})[」』]\s*(.*)$", para or "", re.S)
    if not m:
        return None, para or ""
    return m.group(1), m.group(2)


def check_one(conn, row, *, min_paras=5, min_chars=1000, min_body=120) -> dict:
    wid, mid = row["work_id"], row["method_id"]
    book = conn.execute("SELECT seed_title, wikidata_qid FROM works WHERE id=?", (wid,)).fetchone()
    report = {
        "work_id": wid, "book": book["seed_title"] if book else "?",
        "method_id": mid, "model": row["model_used"],
        "generated_at": row["generated_at"],
        "errors": [], "warnings": [], "paragraphs": [],
    }
    try:
        doc = json.loads(row["result"] or "{}")
    except Exception as exc:
        report["errors"].append(f"result 不是合法 JSON：{exc}")
        return report

    paras = doc.get("paragraphs") or []
    body_chars = 0
    cross_chapters, block_positions = set(), []
    qid = book["wikidata_qid"] if book else None
    blocks_map = load_blocks(conn, qid) if qid else None
    if blocks_map is None:
        report["errors"].append(f"找不到作品对应的 wikidata_qid 或章节数据（qid={qid}）")

    for i, p in enumerate(paras):
        text = p.get("text") or ""
        cites = p.get("cites") or []
        item = {"i": i + 1, "chars": len(norm(text)), "cites": cites, "ok": True, "notes": []}
        quote, body = extract_quote(text)
        body_chars += len(norm(body))
        if quote is None:
            item["notes"].append("段首无引文")
            item["ok"] = False
        if len(norm(body)) < min_body:
            item["notes"].append(f"论述仅 {len(norm(body))} 字 < {min_body}")
            item["ok"] = False
        if not cites:
            item["notes"].append("无引证")
            item["ok"] = False
        for urn in cites:
            parts = urn_parts(urn)
            if not parts:
                item["notes"].append(f"URN 格式非法：{urn}")
                item["ok"] = False
                continue
            cq, cidx, bidx = parts
            if blocks_map is not None:
                chap = blocks_map.get(cidx)
                if not chap:
                    item["notes"].append(f"章不存在：{urn}")
                    item["ok"] = False
                    continue
                if not (1 <= bidx <= len(chap)):
                    item["notes"].append(f"块越界：{urn}（该章 {len(chap)} 块）")
                    item["ok"] = False
                    continue
                block_text = chap[bidx - 1]
                if quote and norm(quote) not in norm(block_text):
                    item["notes"].append(f"引文不在块内：{urn}")
                    item["ok"] = False
                cross_chapters.add(cidx)
                block_positions.append(bidx)
            if quote and len(norm(quote)) < 12:
                item["notes"].append(f"引文过短（{len(norm(quote))} 字）：{urn}")
        if not item["ok"]:
            report["errors"].extend(f"第{i + 1}段：{n}" for n in item["notes"])
        report["paragraphs"].append(item)

    report["stats"] = {
        "paragraphs": len(paras),
        "body_chars": body_chars,
        "citations": sum(len(p.get("cites") or []) for p in paras),
        "chapters_covered": len(cross_chapters),
        "all_first_block": bool(block_positions) and set(block_positions) == {1},
        "cliche_hits": {c: (row["result"] or "").count(c) for c in CLICHE if (row["result"] or "").count(c)},
        "placeholders": sorted(set(PLACEHOLDER_RE.findall(row["result"] or ""))),
    }

    if len(paras) < min_paras:
        report["errors"].append(f"段落数 {len(paras)} < {min_paras}")
    if body_chars < min_chars:
        report["errors"].append(f"正文 {body_chars} 字 < {min_chars}")
    if report["stats"]["chapters_covered"] < 3:
        report["warnings"].append(f"只跨 {report['stats']['chapters_covered']} 章（建议 ≥3）")
    if report["stats"]["all_first_block"]:
        report["warnings"].append("所有引证都落在各章首块 b001，块位过于单一")
    if report["stats"]["placeholders"]:
        report["errors"].append(f"出现占位符：{report['stats']['placeholders']}")
    for c, n in report["stats"]["cliche_hits"].items():
        if n >= 2:
            report["warnings"].append(f"套语「{c}」出现 {n} 次")

    content = doc.get("content") or {}
    empty = [k for k, v in content.items() if not v]
    if empty:
        report["warnings"].append(f"content 字段为空：{', '.join(empty)}")
    if not content:
        report["errors"].append("content 整体缺失")
    return report


def render_md(reports, meta) -> str:
    lines = ["# 导读体检报告", ""]
    lines.append(f"- 生成时间：{meta['at']}")
    lines.append(f"- 数据库：`{meta['db']}`")
    lines.append(f"- 篇目：{len(reports)}")
    ok = [r for r in reports if not r["errors"]]
    lines.append(f"- 通过：{len(ok)} / {len(reports)}")
    total_paras = sum(r["stats"]["paragraphs"] for r in reports if r.get("stats"))
    total_chars = sum(r["stats"]["body_chars"] for r in reports if r.get("stats"))
    total_cites = sum(r["stats"]["citations"] for r in reports if r.get("stats"))
    lines.append(f"- 合计：{total_paras} 段 / {total_chars} 字 / {total_cites} 处引证")
    lines += ["", "## 逐篇", "", "| 书 | 方法 | 段 | 字 | 引证 | 跨章 | 硬错误 | 警告 |", "|---|---|---|---|---|---|---|---|"]
    for r in reports:
        s = r.get("stats") or {}
        lines.append("| {book} | {m} | {p} | {c} | {ci} | {ch} | {e} | {w} |".format(
            book=r["book"], m=r["method_id"], p=s.get("paragraphs", "-"), c=s.get("body_chars", "-"),
            ci=s.get("citations", "-"), ch=s.get("chapters_covered", "-"),
            e=len(r["errors"]), w=len(r["warnings"])))
    bad = [r for r in reports if r["errors"] or r["warnings"]]
    if bad:
        lines += ["", "## 问题明细", ""]
        for r in bad:
            lines.append(f"### {r['book']} × {r['method_id']}")
            for e in r["errors"]:
                lines.append(f"- ❌ {e}")
            for w in r["warnings"]:
                lines.append(f"- ⚠ {w}")
            lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="导读体检器")
    ap.add_argument("--db", default=str(DB))
    ap.add_argument("--json", dest="json_path", default=None)
    ap.add_argument("--md", dest="md_path", default=None)
    ap.add_argument("--gate", dest="gate_path", default=None,
                    help="导出前端发布闸门白名单（gen-data.mjs 消费）")
    ap.add_argument("--min-paras", type=int, default=5)
    ap.add_argument("--min-chars", type=int, default=1000)
    ap.add_argument("--min-body", type=int, default=120)
    ap.add_argument("--work-id", type=int, default=None)
    ap.add_argument("--method", default=None)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    db = Path(args.db)
    conn = connect(db)
    sql = ("SELECT g.*, w.seed_title FROM ai_guides g JOIN works w ON w.id=g.work_id")
    where, params = [], []
    if args.work_id:
        where.append("g.work_id=?")
        params.append(args.work_id)
    if args.method:
        where.append("g.method_id=?")
        params.append(args.method)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY w.seed_title, g.method_id"

    rows = conn.execute(sql, params).fetchall()
    if not rows:
        print("库里没有导读记录")
        return
    reports = [check_one(conn, r, min_paras=args.min_paras, min_chars=args.min_chars,
                         min_body=args.min_body) for r in rows]
    conn.close()

    ok = [r for r in reports if not r["errors"]]
    print(f"体检 {len(reports)} 篇：通过 {len(ok)}、有硬错误 {len(reports) - len(ok)}")
    for r in reports:
        s = r.get("stats") or {}
        flag = "✅" if not r["errors"] else "❌"
        print(f"  {flag} {r['book']:<6}{r['method_id']:<12} {s.get('paragraphs', '?')}段 "
              f"{s.get('body_chars', '?')}字 {s.get('citations', '?')}引证 "
              f"跨{s.get('chapters_covered', '?')}章"
              + (f"  ⚠{len(r['warnings'])}" if r["warnings"] else ""))

    meta = {"at": datetime.now().isoformat(timespec="seconds"), "db": str(db)}
    payload = {"meta": meta, "reports": reports}
    if args.json_path:
        p = Path(args.json_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"JSON → {p}")
    if args.md_path:
        p = Path(args.md_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render_md(reports, meta), encoding="utf-8")
        print(f"Markdown → {p}")
    if args.gate_path:
        p = Path(args.gate_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        gate = {
            "at": meta["at"],
            "rules": {"min_paras": args.min_paras, "min_chars": args.min_chars,
                      "min_body": args.min_body},
            "items": [{"work_id": r["work_id"], "method_id": r["method_id"],
                       "pass": not r["errors"],
                       "errors": r["errors"][:6], "warnings": r["warnings"][:6]}
                      for r in reports],
            "passed": len(ok), "total": len(reports),
        }
        p.write_text(json.dumps(gate, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Gate → {p}（放行 {len(ok)}/{len(reports)}）")
    if args.strict and len(ok) != len(reports):
        sys.exit(1)


if __name__ == "__main__":
    main()
