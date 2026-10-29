# -*- coding: utf-8 -*-
"""维基文库（zh.wikisource）古籍底本抓取与入库。

用法：
  python wikisource_import.py --probe            # 只探测各书页面结构
  python wikisource_import.py --work 3 --apply   # 抓取并写库
  python wikisource_import.py --all --apply      # 批量
"""
import json
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from import_daizhige_generic import build_rows, grade_work  # noqa: E402

DB = r"D:\DimensionsCosmos\data\guji.db"
CACHE = Path(r"D:\DimensionsCosmos\data\temp\wikisource")
API = "https://zh.wikisource.org/w/api.php?"
UA = {"User-Agent": "DimensionsCosmosBot/1.0 (guji text pipeline; local)"}

# work_id -> (页面根名, 章数上限)
ROOTS = {
    3: ("禮記/大學", 1),
    7: ("禮記", 60),
    9: ("春秋左氏傳", 60),
    10: ("今文孝經", 1),
    11: ("爾雅", 40),
    12: ("說文解字", 60),
    18: ("戰國策", 40),
    19: ("國語", 40),
    29: ("呂氏春秋", 40),
    31: ("論衡", 90),
    35: ("搜神記", 30),
    37: ("傷寒論", 30),
    38: ("齊民要術", 20),
    40: ("天工開物", 20),
    41: ("楚辭", 30),
    42: ("文選", 70),
    44: ("宋詞三百首", 30),
    45: ("古文觀止", 25),
    47: ("詩品", 5),
    48: ("陶淵明集", 15),
    49: ("李太白全集", 40),
}


def api(params: dict, tries: int = 4) -> dict:
    url = API + urllib.parse.urlencode(params)
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as f:
                return json.loads(f.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5)
    raise last


def wikitext(title: str) -> str | None:
    d = api({"action": "query", "format": "json", "titles": title,
             "prop": "revisions", "rvprop": "content", "rvslots": "main", "redirects": 1})
    for _, p in d["query"]["pages"].items():
        if "missing" in p:
            return None
        return p["revisions"][0]["slots"]["main"]["*"]
    return None


def subpages(root: str, limit: int) -> list[str]:
    out, cont = [], None
    while len(out) < limit:
        params = {"action": "query", "format": "json", "list": "allpages",
                  "apprefix": root + "/", "aplimit": 50}
        if cont:
            params["apcontinue"] = cont
        d = api(params)
        out += [x["title"] for x in d["query"]["allpages"]]
        cont = d.get("continue", {}).get("apcontinue")
        if not cont:
            break
    return out[:limit]


TMPL = re.compile(r"\{\{[^{}]*\}\}")


def clean(text: str) -> str:
    t = text
    for _ in range(6):                       # 逐层剥模板
        t = TMPL.sub("", t)
    t = re.sub(r"<ref[^>]*/>", "", t)
    t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"</?(onlyinclude|noinclude|includeonly|poem|center|div|span|p|br)[^>]*>", "\n", t)
    t = re.sub(r"<[^>]{1,40}>", "", t)
    t = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", t)     # [[a|b]] -> b
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)              # [[a]] -> a
    t = t.replace("'''", "").replace("''", "")
    t = re.sub(r"----+", "", t)
    t = re.sub(r"^[*#:;]+\s*", "", t, flags=re.M)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


H2 = re.compile(r"^(={2,4})\s*(.+?)\s*\1\s*$", re.M)


def split_chapters(text: str, page_title: str) -> list[dict]:
    """按 == 标题切章；无标题则整页一章。"""
    marks = list(H2.finditer(text))
    if len(marks) < 2:
        body = clean(text)
        return [{"title": page_title.split("/")[-1], "text": body}] if body else []
    out = []
    for i, m in enumerate(marks):
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = clean(text[start:end])
        if len(body) < 30:
            continue
        out.append({"title": f"{page_title.split('/')[-1]}·{m.group(2).strip()}", "text": body})
    return out


def collect(root: str, limit: int) -> list[dict]:
    root_txt = wikitext(root)
    if root_txt is None:
        return []
    body = clean(root_txt)
    chapters: list[dict] = []
    # 消歧/目录页：正文极短且指向子页
    if len(body) < 600:
        subs = subpages(root, limit)
        if not subs:
            return []
        for t in subs:
            wt = wikitext(t)
            if not wt:
                continue
            chapters += split_chapters(wt, t)
            time.sleep(0.3)
    else:
        chapters = split_chapters(root_txt, root)
    return chapters


def probe() -> int:
    for wid, (root, limit) in ROOTS.items():
        try:
            wt = wikitext(root)
        except Exception as e:  # noqa: BLE001
            print(f"{wid:>3} {root:<14} 探测失败 {type(e).__name__}")
            continue
        if wt is None:
            print(f"{wid:>3} {root:<14} 页面缺失")
            continue
        body = clean(wt)
        subs = []
        if len(body) < 600:
            try:
                subs = subpages(root, limit)
            except Exception:  # noqa: BLE001
                subs = []
        print(f"{wid:>3} {root:<14} raw={len(wt):>6} clean={len(body):>6} 子页={len(subs)}"
              + (f" 例:{subs[:2]}" if subs else ""))
        time.sleep(0.2)
    return 0


def write_work(wid: int, rows: list[dict], total: int, wq: str) -> None:
    con = sqlite3.connect(DB)
    con.execute("delete from chapters where work_id=?", (wid,))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for ordn, r in enumerate(rows, 1):
        con.execute("""insert into chapters
            (work_id,title,text,chars,clean_text,blocks,quality,quality_note,ord,ord_source,noise_ratio,ord_group)
            values(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (wid, r["title"], r["text"], r["chars"], r["clean"],
                     json.dumps(r["blocks"], ensure_ascii=False), r["quality"], r["note"],
                     ordn, "wikisource", 0.0, ""))
    con.execute("""update works set status='ok', quality=?, total_chars=?, chapter_count=?,
                   fetched_at=?, last_error=NULL where id=?""", (wq, total, len(rows), now, wid))
    con.commit()


def run(ids: list[int], apply: bool) -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    for wid in ids:
        root, limit = ROOTS[wid]
        try:
            chapters = collect(root, limit)
        except Exception as e:  # noqa: BLE001
            print(f"[{wid}] {root} 抓取失败 {type(e).__name__}: {str(e)[:60]}")
            continue
        if not chapters:
            print(f"[{wid}] {root} 无可用正文")
            continue
        rows = build_rows(chapters, min_chars=10, min_avg=150)
        total = sum(r["chars"] for r in rows)
        wq, wnote = grade_work(rows, min_avg=150, min_total=5000)
        print(f"[{wid}] {root} 章={len(rows)} 字={total} quality={wq} {wnote} "
              f"首章={rows[0]['title']}({rows[0]['chars']})")
        if apply and total >= 1000:
            write_work(wid, rows, total, wq)
            print(f"     -> 已写入 work={wid}")
    return 0


def main() -> int:
    if "--probe" in sys.argv:
        return probe()
    apply = "--apply" in sys.argv
    if "--all" in sys.argv:
        ids = list(ROOTS)
    elif "--work" in sys.argv:
        ids = [int(x) for x in sys.argv[sys.argv.index("--work") + 1].split(",")]
    else:
        print(__doc__)
        return 1
    return run(ids, apply)


if __name__ == "__main__":
    raise SystemExit(main())
