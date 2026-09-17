"""内容层一键下载编排器。
依次调用各下载脚本，自动跳过已完成的部分（各脚本内部有增量判断）。

用法：
    python scripts/download_all.py                    # 全部
    python scripts/download_all.py --skip tech_books  # 跳过指定来源
    python scripts/download_all.py --only openstax    # 仅指定来源

来源清单：
    1. wikisource   —— 中文维基文库（已有 pipeline/run.py）
    2. gutenberg    —— Project Gutenberg 精选 500+ 本英文公版
    3. standard_ebooks —— Standard Ebooks 精排版 EPUB
    4. openstax     —— OpenStax 大学教材（CC BY）
    5. tech_books   —— 免费正版技术书/AI 书 Git 仓库

未自动化但有计划的：
    - Wikisource 多语版（英/法/德/日/韩）：复用 wikisource.py API 模式，逐一建语种子列表
    - OER Commons API：10 万+ 资源，需按学科筛选后下载
    - ctext.org：API 需申请，手动下载后放到 data/sources/ctext/
    - 殆知阁：用户已下载到本地，放置到 data/sources/daizhige/
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

SOURCES = {
    "openstax": {
        "script": "download_openstax.py",
        "desc": "OpenStax 大学教材 (CC BY)",
    },
    "gutenberg": {
        "script": "download_gutenberg.py",
        "desc": "Gutenberg 英文公版精选",
    },
    "standard_ebooks": {
        "script": "download_standard_ebooks.py",
        "desc": "Standard Ebooks 精排版",
    },
    "tech_books": {
        "script": "download_tech_books.py",
        "desc": "免费正版技术书/AI 书",
    },
}


def run_script(name):
    path = SCRIPTS / name
    if not path.exists():
        print(f"  [err] 脚本不存在: {path}")
        return False
    result = subprocess.run([sys.executable, str(path)], cwd=str(ROOT))
    return result.returncode == 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="内容层一键下载")
    parser.add_argument("--skip", type=str, default="", help="跳过指定来源（逗号分隔）")
    parser.add_argument("--only", type=str, default="", help="仅下载指定来源（逗号分隔）")
    args = parser.parse_args()

    skip = set(args.skip.split(",")) if args.skip else set()
    only = set(args.only.split(",")) if args.only else set()

    if only:
        targets = {k: v for k, v in SOURCES.items() if k in only}
    else:
        targets = {k: v for k, v in SOURCES.items() if k not in skip}

    print("=" * 60)
    print("DimensionsCosmos 内容层批量下载")
    print(f"目标来源：{', '.join(targets.keys())}")
    print(f"输出目录：{ROOT / 'data' / 'sources'}")
    print("=" * 60)

    results = {}
    for key, info in targets.items():
        print(f"\n--- [{key}] {info['desc']} ---")
        ok = run_script(info["script"])
        results[key] = "✅" if ok else "❌"

    print("\n" + "=" * 60)
    for key, status in results.items():
        print(f"  {status} {key}")
    print("=" * 60)

    # 提示手动步骤
    print("""
手动步骤提醒：
  📁 殆知阁：将已下载的 TXT 全集放入 data/sources/daizhige/
  📁 ctext.org：通过 https://ctext.org/tools/api 获取 API 权限后下载
  🌐 Wikisource 多语版：pipeline/wikisource.py 已支持任意语言，
     修改 API_URL 即可。英/日/法/德/韩 各建一份 seeds 后批量抓。
  🌐 OER Commons：https://oercommons.org/api 可供后续增量拉取。
""")


if __name__ == "__main__":
    main()