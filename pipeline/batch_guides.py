"""36 篇导读的批量调度器（v1.1，跨机可搬运）。

设计目标：让「生成」这一步可以搬到任何一台机器上跑，跑完只回传一个 JSON。

子命令
    --plan            只打印 4 部书 × 9 法 覆盖矩阵（已有/缺失），不调模型
    --run             生成缺失项（默认动作，已有则跳过＝断点续跑）
    --export PATH     导出导读为单文件 JSON（异机跑完后回传这个文件）
    --import PATH     把异机回传的 JSON 合并入库（按书名映射，幂等，先备份）

常用
    python pipeline/batch_guides.py --plan
    python pipeline/batch_guides.py --run --max-seconds 28800      # 8 小时预算，夜里跑
    python pipeline/batch_guides.py --export output/guides.json    # 异机：跑完导出
    python pipeline/batch_guides.py --import output/guides.json    # 本机：回灌
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from db import connect  # noqa: E402
from method_plugins import METHODS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "guji.db"

# 36 篇 = 这 4 部书 × 这 9 法（multimodal 不计入正篇）
PLAN_BOOKS = ("论语", "老子", "颜氏家训", "世说新语")
PLAN_METHODS = ("zhuxi", "sushi", "qianzhongshu", "wangyangming", "adler",
                "feynman", "socratic", "arendt", "ibn_khaldun")
TARGET = len(PLAN_BOOKS) * len(PLAN_METHODS)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fix_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def load_matrix(conn):
    """返回 {book: {method_id: row|None}}，row 取自 ai_guides。"""
    books = {}
    for title in PLAN_BOOKS:
        w = conn.execute("SELECT id, seed_title, author, dynasty FROM works WHERE seed_title=?",
                         (title,)).fetchone()
        books[title] = {"work": w, "methods": {}}
        for mid in PLAN_METHODS:
            row = None
            if w:
                row = conn.execute(
                    "SELECT generated_at, model_used, citations, result FROM ai_guides "
                    "WHERE work_id=? AND method_id=?", (w[0], mid)).fetchone()
            books[title]["methods"][mid] = row
    return books


def print_plan(conn) -> dict:
    books = load_matrix(conn)
    have = 0
    print(f"36 篇导读矩阵（目标 {TARGET} 篇）\n")
    head = f"{'书':<8}" + "".join(f"{mid[:10]:<12}" for mid in PLAN_METHODS)
    print(head)
    for title, info in books.items():
        cells = []
        for mid in PLAN_METHODS:
            row = info["methods"][mid]
            if row:
                have += 1
                cells.append(f"{'✓':<12}")
            else:
                cells.append(f"{'·':<12}")
        print(f"{title:<8}" + "".join(cells))
    missing = []
    for title, info in books.items():
        for mid in PLAN_METHODS:
            if not info["methods"][mid]:
                missing.append((title, mid))
    print(f"\n已有 {have}/{TARGET}，缺 {len(missing)} 篇")
    for title, mid in missing:
        print(f"  - {title} × {METHODS[mid]['name_zh']}")
    return {"have": have, "missing": missing}


def do_batch(conn, *, force=False, only_book=None, only_method=None,
             max_seconds=None, max_tokens=3200, sleep=1.0) -> dict:
    from gen_guides_cited import generate_one  # 延迟导入，避免 --plan 也加载模型依赖

    books = load_matrix(conn)
    todo = []
    for title, info in books.items():
        if only_book and title != only_book:
            continue
        w = info["work"]
        if not w:
            print(f"⚠ 库中无《{title}》，跳过")
            continue
        for mid in PLAN_METHODS:
            if only_method and mid != only_method:
                continue
            if info["methods"][mid] and not force:
                continue
            todo.append({"id": w[0], "title": w[1], "author": w[2], "dynasty": w[3]}, )
            todo[-1]["method_id"] = mid
    if not todo:
        print("没有待生成项（36 篇已齐；要重写请加 --force）")
        return {"total": 0, "ok": 0, "failed": [], "skipped": TARGET}

    print(f"待生成 {len(todo)} 篇\n")
    prog_path = ROOT / "temp" / f"batch_progress_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
    prog_path.parent.mkdir(parents=True, exist_ok=True)
    ok, failed = 0, []
    t_start = time.time()

    for i, item in enumerate(todo, 1):
        if max_seconds and time.time() - t_start > max_seconds:
            print(f"\n⏱ 已达时间预算 {max_seconds}s，停止；剩余 {len(todo) - i + 1} 篇下次续跑")
            failed.append({"pending": True, "rest": len(todo) - i + 1})
            break
        w = {"id": item["id"], "title": item["title"],
             "author": item["author"], "dynasty": item["dynasty"]}
        mid = item["method_id"]
        print(f"[{i}/{len(todo)}] {item['title']} × {METHODS[mid]['name_zh']} ", end="", flush=True)
        t0 = time.time()
        try:
            res = generate_one(conn, w, mid, max_blocks=30, max_tokens=max_tokens,
                               dry_run=False, force=force, quote_mode="auto",
                               segmented=True)
        except Exception as exc:  # noqa: BLE001
            res = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        rec = {"ts": _now(), "book": item["title"], "method_id": mid,
               "seconds": round(time.time() - t0, 1)}
        if res.get("ok"):
            ok += 1
            rec.update({"ok": True, "paragraphs": res.get("paragraphs"),
                        "body_chars": res.get("body_chars"), "citations": res.get("citations"),
                        "model": res.get("model"), "warnings": res.get("warnings")})
            print(f"✅ {res.get('paragraphs')} 段 / {res.get('body_chars', 0)} 字 / "
                  f"{len(res.get('citations') or [])} 引证 / {rec['seconds']}s")
            for warn in (res.get("warnings") or [])[:3]:
                print(f"    ⚠ {warn}")
        else:
            rec.update({"ok": False, "error": res.get("error")})
            failed.append({"book": item["title"], "method_id": mid, "error": res.get("error")})
            print(f"❌ {res.get('error')}")
        with prog_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if sleep:
            time.sleep(sleep)

    summary = {"total": len(todo), "ok": ok, "failed": failed,
               "elapsed": round(time.time() - t_start, 1), "progress": str(prog_path)}
    report = ROOT / "temp" / f"batch_report_{datetime.now():%Y%m%d_%H%M%S}.json"
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完成 {ok}/{len(todo)}；失败 {len([f for f in failed if not f.get('pending')])} 项")
    print(f"进度档 {prog_path}\n汇总 {report}")
    return summary


def do_export_pack(conn, out_path: Path) -> Path:
    """导出异机生成用的最小数据集：只留 4 部书 + 方法义理，体积从 110 MB 降到十几 MB。"""
    if out_path.exists():
        out_path.unlink()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    conn.execute("VACUUM INTO ?", (str(out_path),))
    pk = sqlite3.connect(out_path)
    pk.execute("PRAGMA foreign_keys=OFF")
    ids = [r[0] for r in pk.execute(
        f"SELECT id FROM works WHERE seed_title IN ({','.join('?' * len(PLAN_BOOKS))})",
        PLAN_BOOKS).fetchall()]
    if not ids:
        pk.close()
        raise SystemExit("库中找不到 4 部目标书，无法打包")
    ph = ",".join("?" * len(ids))
    for table, col in (("chapters", "work_id"), ("ai_guides", "work_id"),
                       ("glosses", "work_id"), ("work_profiles", "work_id"),
                       ("graph_nodes", "work_id")):
        try:
            pk.execute(f"DELETE FROM {table} WHERE {col} IS NOT NULL AND {col} NOT IN ({ph})", ids)
        except sqlite3.OperationalError:
            pass
    pk.execute(f"DELETE FROM works WHERE id NOT IN ({ph})", ids)
    try:
        pk.execute("DELETE FROM chapter_notes WHERE chapter_id NOT IN (SELECT id FROM chapters)")
    except sqlite3.OperationalError:
        pass
    pk.commit()
    pk.execute("VACUUM")
    pk.commit()
    kept = pk.execute("SELECT count(*) FROM chapters").fetchone()[0]
    guides = pk.execute("SELECT count(*) FROM ai_guides").fetchone()[0]
    pk.close()
    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"已打包异机数据集 → {out_path}（{size_mb:.1f} MB，{len(ids)} 部书 / "
          f"{kept} 章 / 已有导读 {guides} 篇）")
    return out_path


def do_export(conn, out_path: Path) -> Path:
    rows = conn.execute(
        "SELECT g.work_id, w.seed_title, g.method_id, g.result, g.generated_at, "
        "g.model_used, g.citations FROM ai_guides g JOIN works w ON w.id = g.work_id "
        "ORDER BY w.seed_title, g.method_id").fetchall()
    items = []
    for work_id, seed_title, mid, result, gen_at, model_used, cites in rows:
        try:
            payload = json.loads(result) if result else None
        except Exception:
            payload = None
        try:
            citations = json.loads(cites) if cites else []
        except Exception:
            citations = []
        items.append({
            "work_key": seed_title, "work_id": work_id, "method_id": mid,
            "method_name": (METHODS.get(mid) or {}).get("name_zh") or mid,
            "generated_at": gen_at, "model_used": model_used,
            "citations": citations, "result": payload,
        })
    doc = {"schema": 1, "exported_at": _now(), "count": len(items), "items": items}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已导出 {len(items)} 篇 → {out_path}（{out_path.stat().st_size / 1024:.1f} KB）")
    return out_path


def do_import(conn, in_path: Path, dry_run=False) -> dict:
    doc = json.loads(in_path.read_text(encoding="utf-8"))
    items = doc.get("items") or []
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = ROOT / "temp" / "backups" / f"import_{stamp}"
    added, replaced, skipped = 0, 0, []
    for it in items:
        title, mid = it.get("work_key"), it.get("method_id")
        if not title or not mid or mid not in METHODS:
            skipped.append({"work_key": title, "method_id": mid, "why": "未知方法或键缺失"})
            continue
        row = conn.execute("SELECT id FROM works WHERE seed_title=?", (title,)).fetchone()
        if not row:
            skipped.append({"work_key": title, "method_id": mid, "why": "本地无此书"})
            continue
        wid = row[0]
        old = conn.execute("SELECT result, generated_at, model_used, citations FROM ai_guides "
                           "WHERE work_id=? AND method_id=?", (wid, mid)).fetchone()
        if old:
            replaced += 1
            if not dry_run:
                backup_dir.mkdir(parents=True, exist_ok=True)
                (backup_dir / f"{title}_{mid}.json").write_text(
                    json.dumps({"result": old[0], "generated_at": old[1],
                                "model_used": old[2], "citations": old[3]},
                               ensure_ascii=False, indent=1), encoding="utf-8")
        else:
            added += 1
        if dry_run:
            continue
        conn.execute(
            "INSERT OR REPLACE INTO ai_guides (work_id, method_id, result, generated_at, "
            "model_used, citations) VALUES (?, ?, ?, ?, ?, ?)",
            (wid, mid,
             json.dumps(it.get("result"), ensure_ascii=False) if it.get("result") is not None else None,
             it.get("generated_at") or _now(), it.get("model_used"),
             json.dumps(it.get("citations") or [], ensure_ascii=False)))
    if not dry_run:
        conn.commit()
    res = {"added": added, "replaced": replaced, "skipped": skipped,
           "backup": str(backup_dir) if replaced else None, "dry_run": dry_run}
    tag = "（dry-run 未写库）" if dry_run else ""
    print(f"导入完成{tag}：新增 {added}、覆盖 {replaced}、跳过 {len(skipped)}")
    if replaced:
        print(f"被覆盖的旧导读已备份到 {backup_dir}")
    for s in skipped[:10]:
        print(f"  ⚠ {s}")
    return res


def main() -> None:
    _fix_stdout()
    ap = argparse.ArgumentParser(description="36 篇导读批量调度器")
    ap.add_argument("--plan", action="store_true", help="只打印覆盖矩阵")
    ap.add_argument("--run", action="store_true", help="生成缺失项（默认动作）")
    ap.add_argument("--export", type=str, default=None, metavar="PATH")
    ap.add_argument("--export-pack", type=str, default=None, metavar="PATH",
                    help="导出异机生成用的最小数据集（只含 4 部书）")
    ap.add_argument("--import", dest="import_path", type=str, default=None, metavar="PATH")
    ap.add_argument("--dry-run", action="store_true", help="配合 --import：只校验不写库")
    ap.add_argument("--force", action="store_true", help="连同已有项一起重写")
    ap.add_argument("--only-book", type=str, default=None)
    ap.add_argument("--only-method", type=str, default=None)
    ap.add_argument("--max-seconds", type=int, default=None, help="时间预算，到点优雅停止")
    ap.add_argument("--max-tokens", type=int, default=3200)
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--db", type=str, default=None, help="指定 guji.db 路径（默认 data/guji.db）")
    args = ap.parse_args()

    db_path = Path(args.db) if args.db else DB
    conn = connect(db_path)

    if args.plan:
        print_plan(conn)
    elif args.export_pack:
        do_export_pack(conn, Path(args.export_pack))
    elif args.export:
        do_export(conn, Path(args.export))
    elif args.import_path:
        do_import(conn, Path(args.import_path), dry_run=args.dry_run)
    else:
        do_batch(conn, force=args.force, only_book=args.only_book,
                 only_method=args.only_method, max_seconds=args.max_seconds,
                 max_tokens=args.max_tokens, sleep=args.sleep)
    conn.close()


if __name__ == "__main__":
    main()
