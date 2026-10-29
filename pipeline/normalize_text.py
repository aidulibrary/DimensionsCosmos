"""P0 清洗管线：把维基文库原始 wikitext 清洗为可稳定排版的段落 blocks。

设计原则
--------
1. 只读 chapters.text，写入 chapters.clean_text / blocks / quality，永不修改原文。
2. 幂等：可重复执行，结果一致。
3. 零算力：纯规则，单章 < 10ms。
4. 不臆造：清洗只做「删除标记 + 按原文换行分段」，绝不自动断句、绝不改字。

用法
----
    python pipeline/normalize_text.py            # 执行清洗并写库
    python pipeline/normalize_text.py --dry-run  # 只出报告，不写库
"""
from __future__ import annotations

import html
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "guji.db"
REPORT_PATH = ROOT / "output" / "p0_normalize_report.json"

# ---------------------------------------------------------------- 清洗规则

_RE_COMMENT = re.compile(r"<!--.*?-->", re.S)
_RE_REF = re.compile(r"<ref[^>]*?/>", re.S)
_RE_REF_PAIR = re.compile(r"<ref[^>]*?>.*?</ref>", re.S)
_RE_DROP_TAG_BLOCK = re.compile(
    r"<(?:noinclude|includeonly|onlyinclude|gallery|math|score|timeline|poem)\b[^>]*>.*?</(?:noinclude|includeonly|onlyinclude|gallery|math|score|timeline|poem)>",
    re.S | re.I,
)
_RE_TABLE = re.compile(r"\{\|.*?\|\}", re.S)  # {| wikitable |}
_RE_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}", re.S)
_RE_LINK_FILE = re.compile(
    r"\[\[(?:File|Image|圖像|图|文件|分類|分类|Category)[^\[\]]*(?:\[\[[^\]]*\]\][^\[\]]*)*\]\]",
    re.S | re.I,
)
_RE_LINK_PIPE = re.compile(r"\[\[[^\[\]|]*\|([^\[\]]*)\]\]")
_RE_LINK_PLAIN = re.compile(r"\[\[([^\[\]]*)\]\]")
_RE_EXTLINK = re.compile(r"\[(?:https?:)?//[^\s\]]+\s+([^\]]*)\]")
_RE_EXTLINK_BARE = re.compile(r"\[(?:https?:)?//[^\s\]]+\]")
_RE_BR = re.compile(r"<br\s*/?>", re.I)
_RE_TAG = re.compile(r"<[^>]{1,80}>")
_RE_TOC = re.compile(r"__[A-Z]+__")
_RE_QUOTE_MARK = re.compile(r"'{2,5}")
_RE_ENTITY = re.compile(r"&[a-zA-Z]+;|&#\d+;")
_RE_BULLET = re.compile(r"^[\*#:\s]+", re.M)
_RE_SPACES = re.compile(r"[ \t\u3000]+")
_RE_MULTI_NL = re.compile(r"\n{3,}")

# 维基文库页面残留在正文里的结构性噪声行（整行等于这些才丢）
_NOISE_LINES = {
    "註疏",
    "注疏",
    "原文",
    "校勘",
    "目錄",
    "目录",
    "編輯",
    "编辑",
    "维基文库",
    "維基文庫",
    "餘杭章太炎",
}
_NOISE_PREFIX = ("本作品收錄於", "本作品收录于", "此作品在", "Public domain", "本作品在全世界都屬於公有領域")


def _strip_templates(text: str) -> str:
    """自内向外剥离 {{...}} 模板，最多 12 轮，防止死循环。"""
    for _ in range(12):
        new = _RE_TEMPLATE.sub("", text)
        if new == text:
            break
        text = new
    return text


def clean_text(raw: str) -> str:
    """去掉维基标记，保留文字与原有换行结构。"""
    if not raw:
        return ""
    t = raw.replace("\r\n", "\n").replace("\r", "\n")
    t = _RE_COMMENT.sub("", t)
    t = _RE_REF_PAIR.sub("", t)
    t = _RE_REF.sub("", t)
    t = _RE_DROP_TAG_BLOCK.sub("\n", t)
    t = _RE_TABLE.sub("\n", t)
    t = _strip_templates(t)
    t = _RE_LINK_FILE.sub("", t)
    for _ in range(6):
        new = _RE_LINK_PIPE.sub(r"\1", t)
        if new == t:
            break
        t = new
    t = _RE_LINK_PLAIN.sub(r"\1", t)
    t = _RE_EXTLINK.sub(r"\1", t)
    t = _RE_EXTLINK_BARE.sub("", t)
    t = _RE_BR.sub("\n", t)
    t = _RE_TAG.sub("", t)
    t = _RE_TOC.sub("", t)
    t = _RE_QUOTE_MARK.sub("", t)
    t = _RE_ENTITY.sub(lambda m: html.unescape(m.group(0)), t)
    t = _RE_BULLET.sub("", t)
    t = _RE_SPACES.sub(" ", t)
    t = clean_residue(t)
    t = _RE_SPACES.sub(" ", t)
    t = re.sub(r"[ \t]+(?=\n)", "", t)
    t = _RE_MULTI_NL.sub("\n\n", t)
    return t.strip()


# ---------------------------------------------------------------- 残留清洗 v2
# 首轮 clean_text 之后仍会残留的维基文库特有标记，逐类消解。
# 原则：能保信息的保留（校勘异文转为括注），纯标记噪声删除，缺字统一为 □。

_RE_EDIT_LEAK = re.compile(r"(?i)true character resembles[^\n]*|should be replaced with[^\n]*|UTF-[0-9A-F]{2,6}[^\n]*")
_RE_NS_RESIDUE = re.compile(r"(?:Template|模板|Category|分类|分類)\s*[:：]\s*[^\s，。；、）\]】]{0,12}")
_RE_URL = re.compile(r"https?://[^\s，。；]+")
_RE_TMPL_RESIDUE = re.compile(r"\{\{[^{}\n]{0,40}?\|([^{}|\n]{1,20})\}?\}?")
_RE_ITALIC_STAR = re.compile(r"\*\(([^()\n]{1,12})\)\*|\*([^*\n]{1,12})\*")
_RE_FOOTNOTE_NUM = re.compile(r"\[[一二三四五六七八九十百千０-９0-9]{1,6}\]")
_RE_MISSING_CODEPOINT = re.compile(r"\[([0-9A-F]{4,6})\]")
_RE_FFFD_BRACKET = re.compile(r"\[[^\]\n]{0,4}\ufffd[^\]\n]{0,4}\]")
_RE_SUPPLEMENT_CHAR = re.compile(r"\[([\u4e00-\u9fff]{1,6})\]")
_RE_SUPPLEMENT_LIST = re.compile(r"\[([\u4e00-\u9fff、，；：]{1,10})\]")
_RE_EMPTY_VARIANT = re.compile(r"[（(]一[本]?作[「『]\s*[」』][）)]")
_RE_ANY_BRACE = re.compile(r"[{}]")
_RE_BRACKET_ANY = re.compile(r"\[([^\[\]\n]{1,40})\]")
_RE_STRAY_STAR = re.compile(r"\*")
_RE_EMPTY_ANY = re.compile(r"〈[\s\u3000]*〉|[（(][\s\u3000]*[）)]|[「『][\s\u3000]*[」』]")
_RE_UNDERSCORE_BLANK = re.compile(r"\[\s*[_＿\s]{1,3}\s*\]")
_RE_PROPER_NOUN = re.compile(r"〖([^〗\n]{1,12})〗")
_RE_EMPTY_ANGLE = re.compile(r"〈\s*〉")
_RE_VARIANT = re.compile(r"([^\s（(])一[本]?作「([^」\n]{1,40})」")
_RE_VARIANT_ALT = re.compile(r"([^\s（(])一[本]?作『([^』\n]{1,40})』")
_RE_STRAY_BRACE = re.compile(r"\{\{|\}\}")
_RE_COMPONENT_BRACE = re.compile(r"\{([\u4e00-\u9fff]{1,4})\}")
_RE_BRACE_BEFORE_PUNCT = re.compile(r"\}(?=[，。、；：！？」』）】])")
_RE_BRACE_AFTER_OPEN = re.compile(r"(?<=[「『（【])\{")
_RE_INLINE_EQ = re.compile(r"={2,6}")
_RE_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]")
_RE_MULTI_SPACE2 = re.compile(r"[ \t\u3000]{2,}")
# 全角方/花括号归一为半角，交给下方统一规则处理（维基文库两套混用）
_FULLWIDTH_BRACKETS = str.maketrans({"［": "[", "］": "]", "｛": "{", "｝": "}"})
# 汉字段间游离的闭合括号（原文漏开括号），直接删
_RE_STRAY_CLOSE = re.compile(r"(?<=[\u4e00-\u9fff，。、；：）」』])\s*[\]}](?=[\u4e00-\u9fff])")


def clean_residue(t: str) -> str:
    """消解首轮清洗后的维基残留标记（顺序敏感，勿随意调整）。"""
    if not t:
        return ""
    t = t.translate(_FULLWIDTH_BRACKETS)
    t = _RE_EDIT_LEAK.sub("", t)
    t = _RE_NS_RESIDUE.sub("", t)
    t = _RE_URL.sub("", t)
    t = _RE_ZERO_WIDTH.sub("", t)
    # 模板残片 {{ProperNoun|殷} / {{*|簡文} → 取管道后内容
    for _ in range(4):
        new = _RE_TMPL_RESIDUE.sub(r"\1", t)
        if new == t:
            break
        t = new
    t = _RE_ITALIC_STAR.sub(lambda m: m.group(1) or m.group(2), t)
    t = _RE_EMPTY_ANGLE.sub("", t)
    # 校勘异文：一作「X」→（一作「X」），保留学术信息
    t = _RE_VARIANT.sub(r"\1（一作「\2」）", t)
    t = _RE_VARIANT_ALT.sub(r"\1（一作「\2」）", t)
    # 脚注标号与缺字
    t = _RE_FOOTNOTE_NUM.sub("", t)
    t = _RE_MISSING_CODEPOINT.sub("□", t)
    t = _RE_FFFD_BRACKET.sub("□", t)
    t = _RE_UNDERSCORE_BLANK.sub("□", t)
    t = _RE_SUPPLEMENT_CHAR.sub(r"\1", t)
    t = _RE_SUPPLEMENT_LIST.sub(r"\1", t)
    t = _RE_PROPER_NOUN.sub(r"\1", t)
    t = _RE_EMPTY_VARIANT.sub("", t)
    # 花括号：{單心} 这类部件合字（底本缺该字码位）→ 保留部件并加角标〔單心〕，再清游离符号
    t = _RE_COMPONENT_BRACE.sub(lambda m: f"〔{m.group(1)}〕", t)
    t = _RE_STRAY_BRACE.sub("", t)
    t = _RE_BRACE_BEFORE_PUNCT.sub("", t)
    t = _RE_BRACE_AFTER_OPEN.sub("", t)
    t = _RE_ANY_BRACE.sub("", t)
    # 残余方括号：内容即补文，去括号保内容；空者补缺字符
    t = _RE_BRACKET_ANY.sub(lambda m: m.group(1).strip() or "□", t)
    t = _RE_STRAY_CLOSE.sub("", t)
    t = _RE_EMPTY_ANY.sub("", t)
    t = _RE_STRAY_STAR.sub("", t)
    # 表格/模板残片竖线（表格已在首轮整体删除，此处剩余均为残片）
    t = t.replace("|", "").replace("｜", "")
    t = t.replace("\ufffd", "□")
    t = _RE_MULTI_SPACE2.sub(" ", t)
    return t


# 维基标题：== x == / === x === / ==== x ====
_RE_HEADING = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$")
# 正文内的辅助小节（注释放置，前端折叠）
_NOTE_SECTIONS = ("註釋", "註解", "注释", "注解", "校勘記", "校勘记", "參考", "参考", "外部連結")


def to_blocks(cleaned: str) -> list[dict]:
    """按原文换行分段，保留维基标题层级。

    不做自动断句：一段 = 原文一个换行块。
    块类型：h（标题，带 level）/ p（正文段落）
    """
    blocks: list[dict] = []
    in_note = False
    for line in cleaned.split("\n"):
        s = line.strip()
        if not s:
            continue
        m = _RE_HEADING.match(s)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            in_note = any(text.startswith(k) for k in _NOTE_SECTIONS)
            if in_note:
                continue
            blocks.append({"t": "h", "l": level, "x": text})
            continue
        if in_note:
            continue
        if s in _NOISE_LINES:
            continue
        if len(s) <= 24 and s.startswith(_NOISE_PREFIX):
            continue
        s = _RE_INLINE_EQ.sub("", s).strip()
        if not re.search(r"[\u4e00-\u9fff0-9A-Za-z]", s):
            continue  # 纯标点/装饰
        blocks.append({"t": "p", "x": s})
    return blocks


# 消歧义 / 目录页特征：正文实为版本索引，而非古籍内容
_RE_INDEX_HINT = re.compile(r"(帛書本|帛书版|匯校版|汇校本|校勘版|影印本|點校本|点校本)\s*[），)]")
_RE_INDEX_HEADING = ("原文", "版本", "目錄", "目录")


def is_index_page(raw: str, blocks: list[dict]) -> bool:
    """判断该章是否为维基文库的版本消歧义/目录页（不是正文）。"""
    heads = [b["x"] for b in blocks if b["t"] == "h"]
    if heads and all(h in _RE_INDEX_HEADING for h in heads):
        return True
    index_hits = len(_RE_INDEX_HINT.findall(raw))
    paragraphs = [b for b in blocks if b["t"] == "p"]
    if index_hits >= 2 and len(paragraphs) <= 24:
        # 段落短且密集出现版本标记 → 目录页
        avg_len = sum(len(p["x"]) for p in paragraphs) / max(1, len(paragraphs))
        if avg_len < 60:
            return True
    return False


# ---------------------------------------------------------------- 质量闸门

CHAPTER_MIN_CHARS = 80
WORK_MIN_TOTAL = 4000
WORK_MIN_AVG = 150


def blocks_text_len(blocks: list[dict]) -> int:
    return sum(len(re.sub(r"\s", "", b["x"])) for b in blocks)


def chapter_quality(blocks: list[dict], chars: int, index_page: bool) -> tuple[str, str]:
    if index_page:
        return "empty", "维基文库该页为版本目录/消歧义页，非正文"
    if not blocks or chars == 0:
        return "empty", "原文为空"
    if chars < CHAPTER_MIN_CHARS:
        return "incomplete", f"仅 {chars} 字，疑为残缺底本"
    return "ok", ""


def work_quality(chapter_rows: list[dict]) -> tuple[str, str]:
    valid = [r for r in chapter_rows if r["chars"] > 0]
    empty = len(chapter_rows) - len(valid)
    n = len(valid)
    if n == 0:
        return "unavailable", "未获取到可用正文（底本缺失或为目录页）"
    total = sum(r["chars"] for r in valid)
    avg = total / n
    empty_note = f"，另 {empty} 章无正文已跳过" if empty else ""
    if n == 1:
        # 单章整本：可能底本按全书一页保存，可读但无法分章
        if total < 100:
            return "unavailable", f"底本仅 {total} 字，不可用"
        return "incomplete", f"底本为全书单页（{total} 字），未分章"
    if total < WORK_MIN_TOTAL or avg < WORK_MIN_AVG:
        return "incomplete", f"共 {n} 章 {total} 字（均 {avg:.0f} 字），疑有缺失{empty_note}"
    return "ok", empty_note.lstrip("，")


# ---------------------------------------------------------------- 主流程


MIGRATIONS = (
    "ALTER TABLE chapters ADD COLUMN clean_text TEXT",
    "ALTER TABLE chapters ADD COLUMN blocks TEXT",
    "ALTER TABLE chapters ADD COLUMN quality TEXT",
    "ALTER TABLE chapters ADD COLUMN quality_note TEXT",
    "ALTER TABLE chapters ADD COLUMN ord INTEGER",
    "ALTER TABLE chapters ADD COLUMN ord_source TEXT",
    "ALTER TABLE chapters ADD COLUMN noise_ratio REAL",
    "ALTER TABLE works ADD COLUMN quality TEXT",
    "ALTER TABLE works ADD COLUMN total_chars INTEGER",
    "ALTER TABLE works ADD COLUMN chapter_count INTEGER",
)


def ensure_schema(conn: sqlite3.Connection) -> None:
    for sql in MIGRATIONS:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chapters_ord ON chapters(work_id, ord)")


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    rows = conn.execute(
        "SELECT id, work_id, title, text, chars FROM chapters ORDER BY work_id, id"
    ).fetchall()
    works = conn.execute("SELECT id, seed_title, bu FROM works ORDER BY id").fetchall()

    t0 = time.time()
    per_work: dict[int, list[dict]] = {}
    updates: list[tuple] = []
    truncated_samples: list[dict] = []

    for r in rows:
        raw = r["text"] or ""
        cleaned = clean_text(raw)
        blocks = to_blocks(cleaned)
        index_page = is_index_page(raw, blocks)
        chars = blocks_text_len(blocks)
        q, note = chapter_quality(blocks, chars, index_page)
        noise = 0.0 if not raw else max(0.0, 1 - chars / max(1, len(re.sub(r"\s", "", raw))))
        updates.append(
            (
                cleaned,
                json.dumps(blocks, ensure_ascii=False, separators=(",", ":")),
                q,
                note,
                round(noise, 4),
                r["id"],
            )
        )
        per_work.setdefault(r["work_id"], []).append({"chars": chars, "quality": q})
        if q != "ok" and len(truncated_samples) < 40:
            truncated_samples.append(
                {
                    "chapter_id": r["id"],
                    "title": r["title"],
                    "raw_chars": len(raw),
                    "clean_chars": chars,
                    "quality": q,
                    "note": note,
                }
            )

    work_updates = []
    work_report = []
    for w in works:
        chs = per_work.get(w["id"], [])
        q, note = work_quality(chs)
        total = sum(c["chars"] for c in chs)
        work_updates.append((q, total, len(chs), w["id"]))
        work_report.append(
            {
                "work_id": w["id"],
                "title": w["seed_title"],
                "bu": w["bu"],
                "chapters": len(chs),
                "total_chars": total,
                "quality": q,
                "note": note,
                "chapter_not_ok": sum(1 for c in chs if c["quality"] != "ok"),
            }
        )

    elapsed = time.time() - t0

    if not dry_run:
        conn.executemany(
            "UPDATE chapters SET clean_text=?, blocks=?, quality=?, quality_note=?, noise_ratio=? WHERE id=?",
            updates,
        )
        conn.executemany(
            "UPDATE works SET quality=?, total_chars=?, chapter_count=? WHERE id=?",
            work_updates,
        )
        conn.commit()

    total_chars = sum(w["total_chars"] for w in work_report)
    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "dry_run": dry_run,
        "chapters": len(rows),
        "works": len(works),
        "total_clean_chars": total_chars,
        "elapsed_sec": round(elapsed, 2),
        "ms_per_chapter": round(elapsed * 1000 / max(1, len(rows)), 2),
        "works_detail": work_report,
        "chapter_issues": truncated_samples,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    ok_w = sum(1 for w in work_report if w["quality"] == "ok")
    inc_w = sum(1 for w in work_report if w["quality"] == "incomplete")
    un_w = sum(1 for w in work_report if w["quality"] == "unavailable")
    print(f"[normalize] {len(rows)} 章 / {len(works)} 部 / {total_chars:,} 字  ({elapsed:.2f}s, {report['ms_per_chapter']}ms/章)")
    print(f"[normalize] 书级质量 ok={ok_w} incomplete={inc_w} unavailable={un_w}")
    print(f"[normalize] 报告 → {REPORT_PATH}")
    for w in work_report:
        if w["quality"] != "ok" and w["chapters"] > 0:
            print(f"   - {w['title']}: {w['quality']} · {w['note']}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

