"""阶段 0 数据管线：种子书单 → 维基文库抓全文 → SQLite → Wikidata QID。

用法：
    python pipeline/run.py                            # 全量抓取
    python pipeline/run.py --limit 3 --max-chapters 3 # 冒烟测试
"""
import argparse
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from db import connect  # noqa: E402
from taxonomy import seed_taxonomy  # noqa: E402
from wikidata import search_qid  # noqa: E402
from wikisource import fetch_book  # noqa: E402

DATA = ROOT / "data"


def load_seed():
    with (DATA / "seed_books.csv").open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def upsert_work(conn, row):
    conn.execute(
        "INSERT OR IGNORE INTO works (seed_title, bu, author, dynasty) VALUES (?, ?, ?, ?)",
        (row["title"], row["bu"], row["author"], row["dynasty"]),
    )
    return conn.execute(
        "SELECT id FROM works WHERE seed_title = ?", (row["title"],)
    ).fetchone()[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="只处理前 N 部书")
    parser.add_argument("--max-chapters", type=int, default=None,
                        help="每部书最多抓 N 章（调试用，正式跑去掉）")
    args = parser.parse_args()

    conn = connect(DATA / "guji.db")
    seed_taxonomy(conn)
    books = load_seed()[: args.limit]

    ok, missing = 0, []
    for row in books:
        work_id = upsert_work(conn, row)
        title = row["title"]
        print(f"[fetch] {title} ...", flush=True)
        try:
            book = fetch_book(title, max_chapters=args.max_chapters)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! 抓取失败：{exc}")
            book = None
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if book is None:
            conn.execute(
                "UPDATE works SET status = 'missing', fetched_at = ? WHERE id = ?",
                (now, work_id),
            )
            missing.append(title)
        else:
            conn.execute(
                "UPDATE works SET ws_title = ?, status = 'ok', fetched_at = ? WHERE id = ?",
                (book["title"], now, work_id),
            )
            for ch in book["chapters"]:
                conn.execute(
                    "INSERT INTO chapters (work_id, title, text, chars) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT (work_id, title) DO UPDATE SET text = excluded.text, chars = excluded.chars",
                    (work_id, ch["title"], ch["text"], len(ch["text"])),
                )
            ok += 1
            print(f"  -> {len(book['chapters'])} 章, 页面名「{book['title']}」")
        qid = search_qid(title)
        if qid:
            conn.execute("UPDATE works SET wikidata_qid = ? WHERE id = ?", (qid, work_id))
        conn.commit()
        time.sleep(0.5)

    print(f"\n完成：{ok} 部入库，{len(missing)} 部未找到: {', '.join(missing) or '无'}")
    print(f"数据库: {DATA / 'guji.db'}")


if __name__ == "__main__":
    main()
