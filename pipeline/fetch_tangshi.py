# -*- coding: utf-8 -*-
"""抓取 guwendao.net《唐诗三百首》318 首诗文，分批运行：--start N --end M"""
import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
BASE = "https://www.guwendao.net"
IDX = Path(r"D:\DimensionsCosmos\data\temp\tangshi_index.json")
OUT = Path(r"D:\DimensionsCosmos\data\temp\tangshi_poems.json")


def fetch(url: str, tries: int = 3, timeout: int = 20) -> str:
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.2 * (i + 1))
    raise last


def extract(html: str) -> tuple[str, str]:
    """返回 (正文, 注释以外的纯诗行)。"""
    m = re.search(r'<div class="contson"[^>]*>(.*?)</div>', html, re.S)
    if not m:
        return "", ""
    raw = m.group(1)
    raw = re.sub(r"<br\s*/?>", "\n", raw)
    raw = re.sub(r"</p>", "\n", raw)
    raw = re.sub(r"<[^>]+>", "", raw)
    text = "\n".join(x.strip() for x in raw.splitlines() if x.strip())
    return raw, text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=0)
    args = ap.parse_args()
    items = json.loads(IDX.read_text(encoding="utf-8"))
    end = args.end or len(items)
    done = {}
    if OUT.exists():
        done = {d["url"]: d for d in json.loads(OUT.read_text(encoding="utf-8"))}
    t0 = time.time()
    for k in range(args.start, min(end, len(items))):
        it = items[k]
        if it["url"] in done and len(done[it["url"]].get("text", "")) > 10:
            continue
        try:
            html = fetch(BASE + it["url"])
            _, text = extract(html)
        except Exception as e:  # noqa: BLE001
            print(f"  [fail] {k} {it['title']}: {e}")
            continue
        rec = dict(it, text=text, chars=len(re.sub(r"\s", "", text)))
        done[it["url"]] = rec
        if rec["chars"] < 10:
            print(f"  [short] {k} {it['title']} {rec['chars']}")
        time.sleep(0.25)
    recs = [done[i["url"]] for i in items if i["url"] in done]
    OUT.write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[batch] {args.start}-{min(end,len(items))} 完成，累计 {len(recs)}/{len(items)}，"
          f"耗时 {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
