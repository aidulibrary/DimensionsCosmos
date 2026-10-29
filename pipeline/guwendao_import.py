# -*- coding: utf-8 -*-
"""古文岛（原古诗文网）古籍频道书籍抓取入库。

用法:
  python guwendao_import.py --work 3            # dry-run
  python guwendao_import.py --work 3 --apply    # 写库
  python guwendao_import.py --work 3,10 --apply --maxchap 60
"""
import json
import re
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from import_daizhige_generic import build_rows, grade_work  # noqa: E402

DB = r"D:\DimensionsCosmos\data\guji.db"
CACHE = Path(r"D:\DimensionsCosmos\data\temp\guwendao")
BASE = "https://www.gushiwen.cn"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
IDX = Path(r"D:\DimensionsCosmos\data\gushiwen_index.json")
# 全本字数下限（用于短篇经典的完整度判定；低于此值才判 incomplete）
ALIAS = {37: "伤寒论"}  # work_id -> 古文岛书名（底本为伤寒论部分）
EXPECT = {3: 1500, 10: 1500, 47: 1200, 40: 15000, 7: 60000, 9: 150000, 18: 80000,
          29: 100000, 31: 150000, 35: 20000}


def get(url: str, tries: int = 2, timeout: int = 12) -> str:
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as f:
                raw = f.read()
            for enc in ("utf-8", "gb18030"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", "ignore")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.0)
    raise last


def catalog(book_hash: str) -> list[tuple[str, str]]:
    html = get(f"{BASE}/guwen/book_{book_hash}.aspx")
    items = re.findall(r'href="(/guwen/bookv_[0-9a-f]+\.aspx)"[^>]*>\s*([^<]{1,24})\s*</a>', html)
    seen, out = set(), []
    for href, name in items:
        if href in seen:
            continue
        seen.add(href)
        out.append((href, name.strip()))
    return out


def chapter_text(href: str) -> str:
    html = get(BASE + href)
    m = re.search(r'<div class="contson"[^>]*>(.*?)</div>', html, re.S)
    if not m:
        return ""
    t = re.sub(r"<br\s*/?>", "\n", m.group(1))
    t = re.sub(r"<[^>]+>", "", t)
    t = t.replace("\u3000", "").replace("&nbsp;", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def write_work(wid: int, rows: list[dict], total: int, wq: str, merge: bool = False) -> None:
    con = sqlite3.connect(DB)
    if merge:
        old = con.execute("select title,text,chars,clean_text,blocks,quality,quality_note"
                          " from chapters where work_id=? order by ord", (wid,)).fetchall()
        seen = {r["title"] for r in rows}
        keep = [{"title": t, "text": x, "chars": c, "clean": cl, "blocks": json.loads(b),
                 "quality": q, "note": n} for t, x, c, cl, b, q, n in old if t not in seen]
        rows = keep + rows
    total = sum(r["chars"] for r in rows)
    exp = EXPECT.get(wid)
    if exp and total >= exp:
        wq = "ok"
    elif exp and total < exp:
        wq = "incomplete"
    con.execute("delete from chapters where work_id=?", (wid,))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for ordn, r in enumerate(rows, 1):
        con.execute("""insert into chapters
            (work_id,title,text,chars,clean_text,blocks,quality,quality_note,ord,ord_source,noise_ratio,ord_group)
            values(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (wid, r["title"], r["text"], r["chars"], r["clean"],
                     json.dumps(r["blocks"], ensure_ascii=False), r["quality"], r["note"],
                     ordn, "guwendao-catalog", 0.0, ""))
    con.execute("""update works set status='ok', quality=?, total_chars=?, chapter_count=?,
                   fetched_at=?, last_error=NULL where id=?""", (wq, total, len(rows), now, wid))
    con.commit()


def run(ids: list[int], apply: bool, maxchap: int) -> int:
    argv = sys.argv
    start = int(argv[argv.index("--start") + 1]) if "--start" in argv else 0
    end = int(argv[argv.index("--end") + 1]) if "--end" in argv else None
    idx = json.loads(IDX.read_text(encoding="utf-8"))
    con = sqlite3.connect(DB)
    CACHE.mkdir(parents=True, exist_ok=True)
    for wid in ids:
        row = con.execute("select seed_title from works where id=?", (wid,)).fetchone()
        if not row:
            print(f"[{wid}] works 中不存在")
            continue
        name = row[0]
        book = None
        alias = ALIAS.get(wid)
        if alias and alias in idx:
            book = (alias, idx[alias])
        for n, h in (idx.items() if not book else []):
            if n == name or n.startswith(name) or name.startswith(n) \
                    or (len(n) >= 3 and n in name) or (len(name) >= 3 and name in n):
                book = (n, h)
                break
        if not book:
            print(f"[{wid}] 《{name}》 古文岛未收录，跳过")
            continue
        cat_cache = CACHE / f"cat_{book[1]}.json"
        try:
            if cat_cache.exists():
                items = json.loads(cat_cache.read_text(encoding="utf-8"))
            else:
                items = catalog(book[1])
                cat_cache.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            print(f"[{wid}] 《{name}》 目录抓取失败 {type(e).__name__}")
            continue
        if not items:
            print(f"[{wid}] 《{name}》 目录为空")
            continue
        total_items = len(items)
        if total_items > maxchap:
            items = items[:maxchap]
        items = items[start:end]
        print(f"     [catalog] 《{name}》共 {total_items} 章，本批 {start}~{start + len(items)}（{len(items)} 章）", flush=True)
        chapters, fails = [], 0
        for k, (href, ename) in enumerate(items):
            cache = CACHE / (href.rsplit("/", 1)[-1].replace(".aspx", ".txt"))
            if cache.exists():
                body = cache.read_text(encoding="utf-8")
            else:
                try:
                    body = chapter_text(href)
                    cache.write_text(body, encoding="utf-8")
                    time.sleep(0.2)
                except Exception:  # noqa: BLE001
                    fails += 1
                    continue
            if len(body) < 20:
                continue
            chapters.append({"title": f"{book[0]}·{ename}", "text": body})
            if k % 20 == 19:
                print(f"       ...{k + 1}/{len(items)}", flush=True)
        rows = build_rows(chapters, min_chars=10, min_avg=100)
        total = sum(r["chars"] for r in rows)
        exp = EXPECT.get(wid)
        wq, wnote = grade_work(rows, min_avg=100, min_total=exp or 5000)
        if exp and total >= exp and len(rows) >= 2:
            wq = "ok"
        print(f"[{wid}] 《{name}》 本章={len(rows)} 字={total} quality={wq} {wnote} 失败={fails}", flush=True)
        if apply and total >= 200:
            write_work(wid, rows, total, wq, merge=True)
            db_total, db_cnt = con.execute(
                "select coalesce(total_chars,0), coalesce(chapter_count,0) from works where id=?",
                (wid,)).fetchone()
            print(f"     -> 已合并写入 work={wid}：全 {db_cnt} 章 {db_total} 字", flush=True)
    return 0


def main() -> int:
    apply = "--apply" in sys.argv
    maxchap = int(sys.argv[sys.argv.index("--maxchap") + 1]) if "--maxchap" in sys.argv else 200
    if "--work" in sys.argv:
        ids = [int(x) for x in sys.argv[sys.argv.index("--work") + 1].split(",")]
    else:
        print(__doc__)
        return 1
    return run(ids, apply, maxchap)


if __name__ == "__main__":
    raise SystemExit(main())
