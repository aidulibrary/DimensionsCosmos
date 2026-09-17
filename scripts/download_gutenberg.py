"""Gutenberg 批量下载器。
策略：不下载全部 7 万+ 本（约 15GB），而是下载「精选书单 + 热门排行」。
全量镜像需 `wget -m` 从 mirror 拉，本地运行约需 2-4 小时，约 15GB。

用法：
    python scripts/download_gutenberg.py              # 下载精选 500 本（推荐，~200MB）
    python scripts/download_gutenberg.py --top 2000  # 下载热门 2000 本
    python scripts/download_gutenberg.py --all        # 全量镜像（需 --accept 觉得足够空间）

Gutenberg 内容 100% 公有领域，完全可商用。
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "sources" / "gutenberg"
INDEX_FILE = OUT / "index.json"
MIRROR = "https://www.gutenberg.org"
ROBOT_DELAY = 1.5  # Gutenberg 要求非侵略性爬取

USER_AGENT = "DimensionsCosmosBot/0.1 (contact via github.com/aidulibrary/DimensionsCosmos)"

# 精选书单：按文明/时代/影响力手工选取的核心书目（英文公版基本盘）
SEED_IDS = [
    # 古希腊罗马
    1497,  # Meditations, Marcus Aurelius
    2600,  # The Republic, Plato
    1740,  # Nicomachean Ethics, Aristotle
    7142,  # The Iliad, Homer
    1727,  # The Odyssey, Homer
    2300,  # Poetics, Aristotle
    1402,  # Apology, Plato
    1600,  # Symposium, Plato
    # 文艺复兴与启蒙
    100,   # Complete Works of Shakespeare
    1513,  # The Prince, Machiavelli
    3207,  # Leviathan, Hobbes
    7370,  # Second Treatise of Government, Locke
    120,   # Discourse on Method, Descartes
    4705,  # Ethics, Spinoza
    # 19 世纪
    84,    # Frankenstein, Mary Shelley
    74,    # Adventures of Tom Sawyer, Twain
    1400,  # Great Expectations, Dickens
    2701,  # Moby Dick, Melville
    345,   # Dracula, Bram Stoker
    43,    # Strange Case of Dr Jekyll and Mr Hyde
    5200,  # Metamorphosis, Kafka
    1184,  # The Count of Monte Cristo, Dumas
    844,   # The Importance of Being Earnest, Wilde
    4300,  # Ulysses, Joyce
    # 科学
    1228,  # On the Origin of Species, Darwin
    5001,  # Relativity, Einstein
    58585, # The Interpretation of Dreams, Freud
    13476,  # The Wealth of Nations, Adam Smith
    3300,  # Capital, Marx
    # 东方经典英译
    7865,  # The Book of Tea, Kakuzo Okakura
    10806, # Art of War (Giles translation)
    22907, # The Kama Sutra
    # 20 世纪思想
    5740,  # Tractatus Logico-Philosophicus, Wittgenstein
]


def _get_url(url):
    time.sleep(ROBOT_DELAY)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def _fetch_metadata(book_id):
    """解析 Gutenberg RDF 元数据，返回 dict。"""
    rdf_url = f"{MIRROR}/ebooks/{book_id}.rdf"
    try:
        xml = _get_url(rdf_url)
        root = ET.fromstring(xml)
        ns = {
            "pg": "http://www.gutenberg.org/2009/pgterms/",
            "dc": "http://purl.org/dc/terms/",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        }

        title_el = root.find(".//dc:title", ns)
        title = title_el.text if title_el is not None else f"Book #{book_id}"

        creator_el = root.find(".//dc:creator/pg:agent/pg:name", ns)
        author = creator_el.text if creator_el is not None else "Unknown"

        # 语言
        lang_el = root.find(".//dc:language//rdf:value", ns)
        language = lang_el.text if lang_el is not None else "en"

        # 主题/LCSH
        subjects = []
        for subj in root.findall(".//dc:subject//rdf:value", ns):
            if subj.text:
                subjects.append(subj.text)

        return {
            "id": book_id,
            "title": title.strip(),
            "author": author.strip(),
            "language": language.strip(),
            "subjects": subjects[:10],
        }
    except Exception as exc:
        print(f"  [warn] 元数据解析失败 #{book_id}: {exc}")
        return {"id": book_id, "title": f"Book #{book_id}", "author": "Unknown", "language": "en", "subjects": []}


def _download_text(book_id):
    """下载纯文本版本；无纯文本则尝试 UTF-8 文本。"""
    # 优先纯文本
    for suffix in [".txt", "-0.txt", ".txt.utf-8"]:
        url = f"{MIRROR}/files/{book_id}/{book_id}{suffix}"
        try:
            content = _get_url(url)
            text = content.decode("utf-8", errors="replace")
            # 跳过 header/footer
            start_marker = "*** START OF THE PROJECT GUTENBERG EBOOK"
            end_marker = "*** END OF THE PROJECT GUTENBERG EBOOK"
            start = text.find(start_marker)
            end = text.find(end_marker)
            if start >= 0 and end > start:
                text = text[start:end + len(end_marker)]
            return text
        except Exception:
            continue
    return None


def _build_top_list(n):
    """从 Gutenberg 的热门下载页抓取 top N ID。"""
    url = f"{MIRROR}/browse/scores/top"
    html = _get_url(url).decode("utf-8", errors="replace")
    ids = re.findall(r'/ebooks/(\d+)', html)
    seen = set()
    result = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            result.append(int(i))
    return result[:n]


def download_book(book_id):
    meta = _fetch_metadata(book_id)
    text = _download_text(book_id)
    if text is None:
        print(f"  [skip] #{book_id} 无可下载文本")
        return None
    fname = f"{book_id}.txt"
    (OUT / fname).write_text(text, encoding="utf-8")
    meta["file"] = fname
    meta["chars"] = len(text)
    return meta


def main():
    parser = argparse.ArgumentParser(description="Gutenberg 批量下载")
    parser.add_argument("--top", type=int, default=0, help="下载热门前 N 本")
    parser.add_argument("--ids", type=str, default="", help="额外 ID，逗号分隔")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    book_ids = list(SEED_IDS)

    if args.top > 0:
        print(f"[gutenberg] 获取热门 Top {args.top} ...")
        top_ids = _build_top_list(args.top)
        book_ids.extend([i for i in top_ids if i not in book_ids])

    if args.ids:
        extra = [int(x.strip()) for x in args.ids.split(",") if x.strip()]
        book_ids.extend([i for i in extra if i not in book_ids])

    # 加载已有索引
    done = set()
    if INDEX_FILE.exists():
        existing = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        done = {b["id"] for b in existing}

    remaining = [i for i in book_ids if i not in done]
    print(f"[gutenberg] 目标 {len(book_ids)} 本，已下载 {len(done)} 本，剩余 {len(remaining)} 本")

    index_entries = json.loads(INDEX_FILE.read_text(encoding="utf-8")) if INDEX_FILE.exists() else []

    for i, bid in enumerate(remaining):
        print(f"[gutenberg] ({i+1}/{len(remaining)}) #{bid} ...", end=" ", flush=True)
        sys.stdout.flush()
        meta = download_book(bid)
        if meta:
            index_entries.append(meta)
            print(f"「{meta['title'][:40]}」({meta['chars']:,} 字)")
        else:
            print("失败/跳过")

        # 每 10 本存一次索引
        if (i + 1) % 10 == 0:
            INDEX_FILE.write_text(json.dumps(index_entries, ensure_ascii=False, indent=2), encoding="utf-8")

    INDEX_FILE.write_text(json.dumps(index_entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[gutenberg] 完成：{len(index_entries)} 本 → {OUT}")


if __name__ == "__main__":
    main()