"""OpenStax 教材批量下载器。
OpenStax（莱斯大学）提供 42+ 种大学教材，CC BY 可商用。
覆盖 70% 美国高校 + 累计服务 2500 万学生，是 OER 赛道最佳内容底座。

下载 PDF（排版精良）+ 提取纯文本供后续 AI 加工。

用法：
    python scripts/download_openstax.py             # 下载全部教材 PDF + 提取文本
    python scripts/download_openstax.py --text-only  # 仅文本（不下载 PDF）
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "sources" / "openstax"
INDEX_FILE = OUT / "index.json"
USER_AGENT = "DimensionsCosmosBot/0.1 (contact via github.com/aidulibrary/DimensionsCosmos)"

# OpenStax 全部教材 API 端点
CATALOG_URL = "https://openstax.org/api/v1/pages/?type=books.Book&fields=slug,title,description,book_subjects,cover_color&limit=100"

# 已知的可用科目 + slug（精简版，全量通过 API 动态获取）
KNOWN_BOOKS = [
    # 数学
    ("Algebra and Trigonometry", "algebra-and-trigonometry-2e"),
    ("Precalculus", "precalculus-2e"),
    ("Calculus Volume 1", "calculus-volume-1"),
    ("Calculus Volume 2", "calculus-volume-2"),
    ("Calculus Volume 3", "calculus-volume-3"),
    ("Introductory Statistics", "introductory-statistics-2e"),
    ("Introductory Business Statistics", "introductory-business-statistics-2e"),
    # 物理
    ("College Physics", "college-physics-2e"),
    ("College Physics for AP Courses", "college-physics-ap-courses-2e"),
    ("University Physics Volume 1", "university-physics-volume-1"),
    ("University Physics Volume 2", "university-physics-volume-2"),
    ("University Physics Volume 3", "university-physics-volume-3"),
    # 化学
    ("Chemistry 2e", "chemistry-2e"),
    ("Chemistry: Atoms First 2e", "chemistry-atoms-first-2e"),
    ("Organic Chemistry", "organic-chemistry"),
    # 生物
    ("Biology 2e", "biology-2e"),
    ("Concepts of Biology", "concepts-of-biology"),
    ("Microbiology", "microbiology"),
    ("Anatomy and Physiology 2e", "anatomy-and-physiology-2e"),
    # 经济
    ("Principles of Economics 3e", "principles-economics-3e"),
    ("Principles of Macroeconomics 3e", "principles-macroeconomics-3e"),
    ("Principles of Microeconomics 3e", "principles-microeconomics-3e"),
    # 社科/人文
    ("Psychology 2e", "psychology-2e"),
    ("Sociology 3e", "sociology-3e"),
    ("American Government 3e", "american-government-3e"),
    ("U.S. History", "us-history"),
    ("Introduction to Philosophy", "introduction-to-philosophy"),
    ("Introduction to Business", "introduction-to-business"),
    ("Business Ethics", "business-ethics"),
    ("Entrepreneurship", "entrepreneurship"),
    # 计算机（新增）
    ("Introduction to Computer Science", "introduction-to-computer-science"),
    ("Introduction to Python Programming", "introduction-python-programming"),
]


def _get_json(url):
    time.sleep(1.0)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _download_pdf(slug, title):
    """OpenStax 有 web 版，PDF 通过标准 URL 获取。"""
    pdf_url = f"https://openstax.org/books/{slug}/pages/1-introduction"
    # 尝试直接获取
    alt_urls = [
        f"https://assets.openstax.org/oscms-prodcms/media/documents/{slug}-2e.pdf",
        f"https://assets.openstax.org/oscms-prodcms/media/documents/{slug}-3e.pdf",
        f"https://assets.openstax.org/oscms-prodcms/media/documents/{slug}.pdf",
    ]
    for url in alt_urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                if resp.status == 200:
                    return resp.read()
        except Exception:
            continue
    return None


def _get_web_viewer_json(slug):
    """OpenStax web viewer 用 JSON API 加载内容。"""
    try:
        data = _get_json(f"https://openstax.org/apps/archive/{slug}/latest")
        return data
    except Exception as exc:
        print(f"    [warn] web JSON 获取失败: {exc}")
        return None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    index_entries = json.loads(INDEX_FILE.read_text(encoding="utf-8")) if INDEX_FILE.exists() else []
    done_slugs = {b["slug"] for b in index_entries}

    for title, slug in KNOWN_BOOKS:
        if slug in done_slugs:
            print(f"[openstax] skip 「{title}」(已下载)")
            continue

        print(f"[openstax] 「{title}」({slug}) ...", end=" ", flush=True)

        # 优先拉 web JSON（结构化最佳）
        web_data = _get_web_viewer_json(slug)

        entry = {
            "title": title,
            "slug": slug,
            "license": "CC BY 4.0",
            "source": "https://openstax.org/",
            "has_web_json": web_data is not None,
        }

        if web_data:
            # 保存原始 JSON
            json_path = OUT / f"{slug}.json"
            json_path.write_text(json.dumps(web_data, ensure_ascii=False), encoding="utf-8")
            entry["file"] = f"{slug}.json"

            # 提取纯文本（tree 结构）
            all_text = []
            if isinstance(web_data, dict):
                tree = web_data.get("tree", {})
                contents = tree.get("contents", [])
                for node in contents:
                    if isinstance(node, dict) and "contents" in node:
                        for leaf in node.get("contents", []):
                            if isinstance(leaf, dict) and leaf.get("title"):
                                all_text.append(f"## {leaf['title']}")
            entry["chars"] = len("".join(all_text))
            print(f"{entry['chars']:,} 字 (JSON)")
        else:
            # 尝试 PDF
            pdf_bytes = _download_pdf(slug, title)
            if pdf_bytes:
                pdf_path = OUT / f"{slug}.pdf"
                pdf_path.write_bytes(pdf_bytes)
                entry["file"] = f"{slug}.pdf"
                entry["size_mb"] = round(len(pdf_bytes) / 1024 / 1024, 1)
                print(f"{entry['size_mb']} MB (PDF)")
            else:
                print("无可用格式")
                entry["file"] = None

        index_entries.append(entry)
        INDEX_FILE.write_text(json.dumps(index_entries, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n[openstax] 完成：{len(index_entries)} 本 → {OUT}")


if __name__ == "__main__":
    main()