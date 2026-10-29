# -*- coding: utf-8 -*-
"""从古文岛（原古诗文网）古籍频道建立 书名 -> book hash 索引。"""
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

OUT = pathlib.Path(r"D:\DimensionsCosmos\data\gushiwen_index.json")
TARGETS = ["大学", "礼记", "左传", "孝经", "尔雅", "说文解字", "战国策", "国语", "吕氏春秋",
           "论衡", "搜神记", "伤寒杂病论", "齐民要术", "天工开物", "楚辞", "文选",
           "宋词三百首", "古文观止", "诗品", "陶渊明集", "李太白集"]
SECTIONS = ["经部", "史部", "子部", "集部"]
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


def get(url: str, tries: int = 3, timeout: int = 20) -> str:
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
            time.sleep(1.2)
    raise last


def scan_section(sec: str, max_page: int = 12) -> dict[str, str]:
    found: dict[str, str] = {}
    for p in range(1, max_page + 1):
        url = f"https://www.gushiwen.cn/guwen/Default.aspx?p={p}&type={urllib.parse.quote(sec)}"
        try:
            html = get(url)
        except Exception as e:  # noqa: BLE001
            print(f"  [{sec} p{p}] 失败 {type(e).__name__}")
            continue
        # 书籍条目：<a href="/guwen/book_<hash>.aspx" ...>书名</a>（PlayBook 参数被 HTML 实体转义，不用）
        pairs = re.findall(
            r'<a[^>]+href="/guwen/book_([0-9a-f]+)\.aspx"[^>]*>\s*([^<]{1,24})\s*</a>', html)
        if not pairs:
            pairs = [(h, "") for h in re.findall(r"/guwen/book_([0-9a-f]+)\.aspx", html)]
        before = len(found)
        for h, name in pairs:
            if name:
                found.setdefault(name.strip(), h)
        new = len(found) - before
        print(f"  [{sec} p{p}] 新增 {new} 部，累计 {len(found)}")
        if new == 0 and p > 1:
            break
        time.sleep(0.6)
    return found


def main() -> int:
    argv = sys.argv[1:]
    secs = [x for x in argv if not x.startswith("-")] or SECTIONS
    idx: dict[str, str] = {}
    if OUT.exists():
        idx = json.loads(OUT.read_text(encoding="utf-8"))
        print(f"[reuse] 已缓存 {len(idx)} 部")
    for sec in secs:
        print(f"[scan] {sec}")
        idx.update(scan_section(sec))
    OUT.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[save] {len(idx)} 部 -> {OUT}")

    print("\n目标命中情况：")
    hit = {}
    for t in TARGETS:
        cand = [(n, h) for n, h in idx.items() if n == t or n.startswith(t)]
        if cand:
            n, h = max(cand, key=lambda x: len(x[0]))
            hit[t] = h
            print(f"  ✔ {t} -> {n} ({h})")
        else:
            print(f"  ✘ {t} 未收录")
    pathlib.Path(r"D:\DimensionsCosmos\data\gushiwen_hit.json").write_text(
        json.dumps(hit, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
