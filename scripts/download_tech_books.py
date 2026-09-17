"""免费正版技术书/AI书批量克隆。
来源：awesome-free-ai-books + free-programming-books（EbookFoundation, 30 万+ star）。
原则："只收录作者官方免费放出的来源"——法律安全。

策略：浅克隆（--depth 1）关键 Git 仓库，不占大量空间。

用法：
    python scripts/download_tech_books.py
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "sources" / "tech_books"
INDEX_FILE = OUT / "index.json"

# 作者官方免费放出的 AI/技术经典书（Git 仓库）
REPOS = [
    # 深度学习/机器学习
    {
        "title": "Dive into Deep Learning",
        "author": "Aston Zhang, Zack Lipton, Mu Li, Alex Smola",
        "url": "https://github.com/d2l-ai/d2l-en",
        "license": "CC BY-SA 4.0",
    },
    {
        "title": "Dive into Deep Learning (中文)",
        "author": "阿斯顿·张 等",
        "url": "https://github.com/d2l-ai/d2l-zh",
        "license": "CC BY-SA 4.0",
    },
    {
        "title": "Pattern Recognition and Machine Learning (Notes)",
        "author": "Christopher Bishop (notes by various)",
        "url": "https://github.com/geronm/handson-ml3",
        "license": "Apache 2.0",
    },
    # 编程/计算机科学
    {
        "title": "Structure and Interpretation of Computer Programs (JS)",
        "author": "Abelson, Sussman, et al.",
        "url": "https://github.com/source-academy/sicp",
        "license": "CC BY-SA 4.0",
    },
    {
        "title": "The Missing Semester of Your CS Education",
        "author": "MIT",
        "url": "https://github.com/missing-semester/missing-semester",
        "license": "CC BY-NC-SA 4.0",
    },
    {
        "title": "Crafting Interpreters",
        "author": "Robert Nystrom",
        "url": "https://github.com/munificent/craftinginterpreters",
        "license": "MIT",
    },
    # LLM / AI 前沿
    {
        "title": "LLM Book (中文大模型入门)",
        "author": "多位作者",
        "url": "https://github.com/datawhalechina/llm-cookbook",
        "license": "CC BY-NC-SA 4.0",
    },
    {
        "title": "Build a Large Language Model (From Scratch)",
        "author": "Sebastian Raschka",
        "url": "https://github.com/rasbt/LLMs-from-scratch",
        "license": "Apache 2.0",
    },
    # 数学/统计
    {
        "title": "Mathematics for Machine Learning",
        "author": "Deisenroth, Faisal, Ong",
        "url": "https://github.com/mml-book/mml-book.github.io",
        "license": "CC BY-NC-SA 4.0",
    },
    # 系统/工程
    {
        "title": "The Art of Command Line",
        "author": "Joshua Levy",
        "url": "https://github.com/jlevy/the-art-of-command-line",
        "license": "CC BY-SA 4.0",
    },
]


def clone_repo(repo_info):
    name = repo_info["url"].rstrip("/").split("/")[-1]
    target = OUT / name
    if target.exists():
        return True, "已存在"
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_info["url"], str(target)],
            check=True, capture_output=True, text=True, timeout=120,
        )
        return True, "ok"
    except subprocess.CalledProcessError as e:
        return False, e.stderr[:200]
    except Exception as e:
        return False, str(e)[:200]


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    index_entries = json.loads(INDEX_FILE.read_text(encoding="utf-8")) if INDEX_FILE.exists() else []
    done = {b["url"] for b in index_entries}

    for repo in REPOS:
        if repo["url"] in done:
            print(f"[tech_books] skip 「{repo['title']}」")
            continue

        print(f"[tech_books] clone 「{repo['title']}」...", end=" ", flush=True)
        ok, msg = clone_repo(repo)
        print(msg if ok else f"失败: {msg}")

        if ok:
            repo["cloned"] = True
            index_entries.append(repo)
        else:
            repo["cloned"] = False
            repo["error"] = msg
            index_entries.append(repo)

        INDEX_FILE.write_text(json.dumps(index_entries, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n[tech_books] 完成：{sum(1 for r in index_entries if r.get('cloned'))}/{len(index_entries)} 本 → {OUT}")


if __name__ == "__main__":
    main()