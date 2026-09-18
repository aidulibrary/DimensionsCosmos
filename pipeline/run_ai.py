"""AI 加工引擎：把「内容 × 方法」变成可售卖的知识产品。

核心概念：每部作品不是被"导读"一次，而是被每种方法"解读"一次——
《论语》× 朱熹 = 理学解读
《论语》× 费曼 = 大白话版
《论语》× 苏格拉底 = 追问版
……

用法：
    python pipeline/run_ai.py                           # 全量加工
    python pipeline/run_ai.py --book "论语" --method feynman  # 单书单法
    python pipeline/run_ai.py --book "史记" --method zhuxi,adler,feynman  # 单书多法
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

from ai_client import chat, get_last_model  # noqa: E402
from db import connect  # noqa: E402
from method_plugins import METHODS, list_methods  # noqa: E402

SCHEMA_UPGRADE = """
CREATE TABLE IF NOT EXISTS ai_guides (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  work_id    INTEGER NOT NULL REFERENCES works(id),
  method_id  TEXT NOT NULL,           -- 方法插件 ID (e.g. 'zhuxi', 'feynman')
  result     TEXT,                    -- JSON: {method_name, generated_at, content: {...}}
  generated_at TEXT,
  model_used   TEXT,                   -- 实际使用的模型名（用于追溯）
  UNIQUE (work_id, method_id)
);
"""


def ensure_schema(conn):
    conn.executescript(SCHEMA_UPGRADE)
    conn.commit()


def get_works(conn, book_filter=None):
    """获取所有有正文的作品列表。"""
    if book_filter:
        rows = conn.execute(
            "SELECT id, seed_title, ws_title, bu, author, dynasty FROM works WHERE status='ok' AND seed_title LIKE ?",
            (f"%{book_filter}%",),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, seed_title, ws_title, bu, author, dynasty FROM works WHERE status='ok'"
        ).fetchall()
    return [dict(zip(["id", "title", "ws_title", "bu", "author", "dynasty"], r)) for r in rows]


def get_chapters(conn, work_id, max_chars=8000):
    """获取作品的章节文本（截断到 max_chars 以控制 Token 消耗）。"""
    rows = conn.execute(
        "SELECT title, text FROM chapters WHERE work_id=? ORDER BY id", (work_id,)
    ).fetchall()
    chapters = []
    total = 0
    for title, text in rows:
        if total >= max_chars:
            break
        snippet = text[: max_chars - total] if text else ""
        chapters.append({"title": title, "text": snippet})
        total += len(snippet)
    return chapters


def get_existing_guides(conn, work_id):
    """获取已生成的方法列表。"""
    rows = conn.execute(
        "SELECT method_id FROM ai_guides WHERE work_id=?", (work_id,)
    ).fetchall()
    return {r[0] for r in rows}


def build_prompt(method, book_meta, chapters_text):
    """构建 AI 提示：方法插件 + 书名/信息 + 正文。"""
    summary = f"《{book_meta['title']}》，{book_meta.get('author', '佚名')}，{book_meta.get('dynasty', '')}"
    return f"""{method['system_prompt']}

---
现在请你以上述方法解读以下文本：

【书名】{summary}
【门类】{book_meta.get('bu', '')}

【正文】
{chapters_text}

请严格按照以下 JSON 格式输出（只输出 JSON，不要任何解释）：

{{
  "method": "{method['name_zh']}",
  "book": "{book_meta['title']}",
  "generated_at": "{datetime.now(timezone.utc).isoformat()}",
  "content": {json.dumps(method.get('output_schema', {}), ensure_ascii=False)}
}}

content 字段中的每一个 key 都要有内容。如果某个字段确实无法分析（例如原文没有提供足够信息），请写「此维度需要阅读更完整的原文才能判断」，而不是空着。"""


def extract_json(text):
    """从模型输出中提取最外层完整 JSON 对象。

    qwen3 关闭 thinking 后，content 开头仍可能混入思考文本
    （以 </think> 或闲聊文字结尾），因此优先取 </think> 之后
    的部分；再从每个 '{' 处尝试 raw_decode，取解析跨度最长
    （end 最大）的对象——即最外层的完整 JSON。
    """
    from json import JSONDecoder
    text = text.strip()
    idx = text.rfind("</think>")
    if idx != -1:
        text = text[idx + len("</think>"):]
    decoder = JSONDecoder()
    best, best_end = None, -1
    for i in range(len(text)):
        if text[i] != "{":
            continue
        try:
            obj, end = decoder.raw_decode(text[i:])
            if end > best_end:
                best, best_end = obj, end
        except Exception:
            continue
    return best


def generate_guide(conn, work_id, method_id, model_tracker):
    """为一部书生成一种方法的解读。返回 (ok, error_msg)。"""
    method = METHODS[method_id]
    book_meta = conn.execute(
        "SELECT seed_title, bu, author, dynasty FROM works WHERE id=?", (work_id,)
    ).fetchone()
    if not book_meta:
        return False, "作品不存在"

    book = {"title": book_meta[0], "bu": book_meta[1], "author": book_meta[2], "dynasty": book_meta[3]}
    chapters = get_chapters(conn, work_id)
    if not chapters:
        return False, "无正文"

    # 拼接章节文本（每章标注标题）
    text_parts = [f"## {ch['title']}\n{ch['text']}" for ch in chapters]
    chapters_text = "\n\n".join(text_parts)

    prompt = build_prompt(method, book, chapters_text)

    print(f"    提示长度: {len(prompt):,} 字符", end="", flush=True)

    try:
        result_text = chat(prompt, max_tokens=4096)
        model_used = get_last_model() or model_tracker.get("last_model", "unknown")
        # 尝试从响应中提取 JSON（从末尾取最后一个完整对象）
        parsed = extract_json(result_text)
        if parsed is None:
            parsed = {"raw": result_text[:8000]}

        conn.execute(
            "INSERT OR REPLACE INTO ai_guides (work_id, method_id, result, generated_at, model_used) "
            "VALUES (?, ?, ?, ?, ?)",
            (work_id, method_id, json.dumps(parsed, ensure_ascii=False),
             datetime.now(timezone.utc).isoformat(), model_used),
        )
        conn.commit()
        print(f" → {model_used}")
        return True, None
    except Exception as exc:
        return False, str(exc)[:200]


def main():
    parser = argparse.ArgumentParser(description="AI 加工引擎")
    parser.add_argument("--book", type=str, default=None, help="只加工指定书名（模糊匹配）")
    parser.add_argument("--method", type=str, default=None, help="只使用指定方法（逗号分隔）")
    parser.add_argument("--limit", type=int, default=None, help="限制加工数量")
    args = parser.parse_args()

    conn = connect(ROOT / "data" / "guji.db")
    ensure_schema(conn)

    # 确定方法列表
    if args.method:
        method_ids = [m.strip() for m in args.method.split(",")]
        invalid = [m for m in method_ids if m not in METHODS]
        if invalid:
            print(f"未知方法: {invalid}. 可用: {', '.join(METHODS.keys())}")
            sys.exit(1)
    else:
        method_ids = list(METHODS.keys())

    # 确定作品列表
    works = get_works(conn, args.book)
    print(f"[run_ai] {len(works)} 部作品 × {len(method_ids)} 种方法 = {len(works) * len(method_ids)} 次调用")
    print(f"        可用方法: {', '.join(method_ids)}")

    # 追踪实际使用的模型
    model_tracker = {"last_model": "unknown"}

    processed = 0
    for work in works:
        existing = get_existing_guides(conn, work["id"])
        todo = [m for m in method_ids if m not in existing]
        if not todo:
            print(f"[skip] 「{work['title']}」全部 {len(method_ids)} 种方法已有")
            continue

        print(f"\n[guide] 「{work['title']}」({work['bu']}·{work.get('author','佚名')}) "
              f"待生成: {len(todo)} 种方法")

        for mid in todo:
            method_name = METHODS[mid]["name_zh"]
            print(f"  [{mid}] {method_name} ...", end="", flush=True)
            ok, err = generate_guide(conn, work["id"], mid, model_tracker)
            if ok:
                print(f" ✅")
            else:
                print(f" ❌ {err}")

            processed += 1
            if args.limit and processed >= args.limit:
                print(f"\n已达限制 {args.limit} 次，停止。")
                conn.close()
                return

            time.sleep(1.0)  # API 友好间隔

    conn.close()
    stats = conn.execute(
        "SELECT COUNT(DISTINCT work_id), COUNT(*) FROM ai_guides"
    ).fetchone() if False else (0, 0)

    conn = connect(ROOT / "data" / "guji.db")
    stats = conn.execute(
        "SELECT COUNT(DISTINCT work_id), COUNT(*) FROM ai_guides"
    ).fetchone()
    conn.close()
    print(f"\n[run_ai] 完成：{stats[0]} 部书有 AI 解读，共 {stats[1]} 条")


if __name__ == "__main__":
    main()