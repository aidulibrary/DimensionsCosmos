"""Standard Ebooks 批量下载器。
Gutenberg 文本的精排版：现代封面、精校文本、EPUB/KEPUB/AZW3 多格式。
全部 CC0（公有领域奉献），可直接作为成品分发——比 Gutenberg 原文更适合"卖电子书"。

策略：opds-client 索引中获取全部书目 → 下载 EPUB。

用法：
    python scripts/download_standard_ebooks.py           # 下载精选
    python scripts/download_standard_ebooks.py --limit N  # 限制数量
"""
import json
import sys
import time
import urllib.request
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "sources" / "standard_ebooks"
INDEX_FILE = OUT / "index.json"
USER_AGENT = "DimensionsCosmosBot/0.1 (contact via github.com/aidulibrary/DimensionsCosmos)"

OPDS_URL = "https://standardebooks.org/opds/all"


class OPDSLinkParser(HTMLParser):
    """解析 OPDS feed 中的 <entry> + <link> 标签。"""
    def __init__(self):
        super().__init__()
        self.entries = []
        self._in_entry = False
        self._in_title = False
        self._in_author = False
        self._current = {}

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "entry":
            self._in_entry = True
            self._current = {"id": "", "title": "", "author": "Unknown", "epub_url": "", "cover_url": ""}
        elif self._in_entry:
            if tag == "title":
                self._in_title = True
            elif tag == "name":
                self._in_author = True
            elif tag == "link" and attrs_dict.get("rel") == "http://opds-spec.org/acquisition":
                href = attrs_dict.get("href", "")
                mime = attrs_dict.get("type", "")
                if "epub" in mime and not self._current["epub_url"]:
                    self._current["epub_url"] = href
                if "image" in mime and not self._current["cover_url"]:
                    self._current["cover_url"] = href

    def handle_data(self, data):
        if self._in_title:
            self._current["title"] = data.strip()
        elif self._in_author:
            self._current["author"] = data.strip()

    def handle_endtag(self, tag):
        if tag == "entry" and self._in_entry:
            if self._current.get("epub_url"):
                self.entries.append(self._current)
            self._in_entry = False
            self._current = {}
        elif tag == "title":
            self._in_title = False
        elif tag == "name":
            self._in_author = False


def _get_opds(url):
    time.sleep(1.0)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def _download_epub(entry):
    url = entry["epub_url"]
    if not url.startswith("http"):
        url = "https://standardebooks.org" + url
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="限制下载数量")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    print("[standard_ebooks] 获取 OPDS 书目 ...")
    xml = _get_opds(OPDS_URL)
    parser_obj = OPDSLinkParser()
    parser_obj.feed(xml)

    entries = parser_obj.entries
    print(f"[standard_ebooks] OPDS 共 {len(entries)} 部书")

    if args.limit:
        entries = entries[:args.limit]

    index_entries = json.loads(INDEX_FILE.read_text(encoding="utf-8")) if INDEX_FILE.exists() else []
    done_titles = {b["title"] for b in index_entries}

    remaining = [e for e in entries if e["title"] not in done_titles]
    print(f"[standard_ebooks] 已下载 {len(done_titles)} 本，剩余 {len(remaining)} 本")

    for i, entry in enumerate(remaining):
        print(f"[standard_ebooks] ({i+1}/{len(remaining)}) 「{entry['title'][:50]}」...", end=" ", flush=True)
        try:
            epub_bytes = _download_epub(entry)
            safe_name = entry["title"].replace("/", "-").replace(":", " -")[:80]
            fname = f"{safe_name}.epub"
            (OUT / fname).write_bytes(epub_bytes)
            entry["file"] = fname
            entry["size_mb"] = round(len(epub_bytes) / 1024 / 1024, 1)
            entry["license"] = "CC0 (public domain dedication)"
            print(f"{entry['size_mb']} MB")
            index_entries.append(entry)
        except Exception as exc:
            print(f"失败: {exc}")

        if (i + 1) % 5 == 0:
            INDEX_FILE.write_text(json.dumps(index_entries, ensure_ascii=False, indent=2), encoding="utf-8")

    INDEX_FILE.write_text(json.dumps(index_entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[standard_ebooks] 完成：{len(index_entries)} 本 → {OUT}")


if __name__ == "__main__":
    main()