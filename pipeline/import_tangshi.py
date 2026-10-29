# -*- coding: utf-8 -*-
"""《唐诗三百首》导入：318 首（guwendao 唐诗三百首频道，与蘅塘退士原编 313 首体系一致，
「塞下曲」等组诗按首拆分）。每首一章，标题带体裁与作者。"""
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from import_daizhige_generic import build_rows, grade_work  # noqa: E402

DB = r"D:\DimensionsCosmos\data\guji.db"
SRC = Path(r"D:\DimensionsCosmos\data\temp\tangshi_poems.json")
WORK_ID = 43


def main() -> int:
    apply = "--apply" in sys.argv
    poems = json.loads(SRC.read_text(encoding="utf-8"))
    chapters = [{"title": f"唐诗三百首/{p['cat']}·{p['title']}（{p['author']}）",
                 "text": p["text"]} for p in poems]
    rows = build_rows(chapters, min_chars=10, min_avg=40)
    total = sum(r["chars"] for r in rows)
    wq, wnote = grade_work(rows, min_avg=40, min_total=15000)
    print(f"[parse] 唐诗三百首 首数={len(rows)} 总字数={total} work_quality={wq} {wnote}")
    short = [(r["title"], r["chars"]) for r in rows if r["chars"] < 15]
    if short:
        print("   [warn] 短篇:", short[:5])
    if not apply:
        print("[dry-run] 加 --apply 写库")
        return 0
    con = sqlite3.connect(DB)
    con.execute("delete from chapters where work_id=?", (WORK_ID,))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for ordn, r in enumerate(rows, 1):
        con.execute("""insert into chapters
            (work_id,title,text,chars,clean_text,blocks,quality,quality_note,ord,ord_source,noise_ratio,ord_group)
            values(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (WORK_ID, r["title"], r["text"], r["chars"], r["clean"],
                     json.dumps(r["blocks"], ensure_ascii=False), r["quality"], r["note"],
                     ordn, "guwendao-catalog", 0.0, ""))
    con.execute("""update works set status='ok', quality=?, total_chars=?, chapter_count=?,
                   fetched_at=?, last_error=NULL where id=?""",
                (wq, total, len(rows), now, WORK_ID))
    con.commit()
    print(f"[apply] work={WORK_ID} 唐诗三百首 写入 {len(rows)} 首 {total} 字，quality={wq}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
