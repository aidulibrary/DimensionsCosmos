# -*- coding: utf-8 -*-
"""
维点图书馆 · FLCA-6 ｜ T1.1 构建 pinyin_lexicon（音项集合 P(c)）
数据源：pypinyin 0.55.0 内置 pinyin_dict（MIT）+ PHRASES_DICT（MIT）
        + L0.5 规则库（破读/通假/专名音项，来源见 rules/L05_rules_v1.json）

口径说明：
  · 单字音项来自 pinyin_dict，多音字一行一音，rank 依数据源顺序（1 为默认高频音）。
  · 规则库出现的 (surface, reading) 会在 lexicon 中占据对应 reading_type，
    并与 normal 音项并存 —— 这构成 L1 约束解码的合法音集合 P(c)。
  · 许可：pypinyin / pinyin-data 均 MIT，可商用可闭源，无传染风险。

执行：python pipeline\pinyin\build_lexicon.py
幂等：先 DROP 再建（lexicon 是派生数据，可随时重建）
"""
import json
import pathlib
import sqlite3
import sys
import hashlib
import time

DB = pathlib.Path(r"D:\DimensionsCosmos\data\guji.db")
HERE = pathlib.Path(__file__).parent
RULE_FILE = HERE / "rules" / "L05_rules_v1.json"

# ---- 数字声调 -> 带调拼音（自带实现，避免依赖版本差异） ----
_TONE_MAP = {
    "a": "āáǎà", "e": "ēéěè", "i": "īíǐì", "o": "ōóǒò", "u": "ūúǔù", "v": "ǖǘǚǜ",
}


def num2tone(s: str) -> str:
    """'lu:4'/'lv4'/'zhong1' -> 'lǜ'/'lǚ'/'zhōng'"""
    if not s:
        return s
    s = s.replace("u:", "v").replace("U:", "v")
    tone = 5
    if s and s[-1].isdigit():
        tone = int(s[-1])
        s = s[:-1]
    if tone == 5 or tone == 0:
        s = s.replace("v", "ü")
        return s
    idx = tone - 1
    # 标调优先序：a > o > e > 最后一个元音（iu/ui 标后者）
    target = -1
    for ch in ("a", "o", "e"):
        if ch in s:
            target = s.index(ch)
            break
    if target < 0:
        for i in range(len(s) - 1, -1, -1):
            if s[i] in "iuv":
                target = i
                break
    if target < 0:
        return s.replace("v", "ü")
    ch = s[target]
    if ch in _TONE_MAP:
        rep = _TONE_MAP[ch][idx]
    else:
        rep = ch
    out = s[:target] + rep + s[target + 1:]
    return out.replace("v", "ü")


def main() -> int:
    t0 = time.time()
    from pypinyin import pinyin_dict
    from pypinyin.constants import PHRASES_DICT

    rules = json.loads(RULE_FILE.read_text(encoding="utf-8"))["rules"]
    # 规则音项索引：(surface, reading) -> [(reading_type, authority)]
    rule_lex = {}
    for r in rules:
        k = (r["surface"], r["reading"])
        rule_lex.setdefault(k, set()).add((r["reading_type"], r["authority"]))

    con = sqlite3.connect(str(DB))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=OFF")
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS pinyin_lexicon")
    cur.executescript(
        """
        CREATE TABLE pinyin_lexicon (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          surface TEXT NOT NULL,
          reading TEXT NOT NULL,
          reading_type TEXT NOT NULL DEFAULT 'normal',
          authority TEXT NOT NULL,
          source_ref TEXT,
          rank INTEGER DEFAULT 99,
          UNIQUE(surface, reading, reading_type)
        );
        CREATE INDEX idx_lex_surface ON pinyin_lexicon(surface);
        """
    )

    rows = []
    n_char = 0
    n_poly = 0
    for code, py in pinyin_dict.pinyin_dict.items():
        ch = chr(code)
        parts = [p.strip() for p in py.split(",") if p.strip()]
        if len(parts) > 1:
            n_poly += 1
        n_char += 1
        for i, p in enumerate(parts):
            rows.append((ch, num2tone(p), "normal", "pypinyin-data(MIT)",
                         "pypinyin/pinyin_dict.py", i + 1))

    # 词级（D4-b 词级数据，供 TTS / 检索 / 导出）
    n_word = 0
    for word, readings in PHRASES_DICT.items():
        if not readings:
            continue
        first = readings[0]
        if isinstance(first, str):
            first = [first]
        joined = " ".join(num2tone(x) for x in first)
        if not joined.strip():
            continue
        rows.append((word, joined, "normal", "pypinyin-data(MIT)-phrases",
                     "pypinyin/phrases_dict.py", 1))
        n_word += 1

    # 规则库音项补录（确保 P(c) 含破读/通假/专名音）
    have = {(r[0], r[1], r[2]) for r in rows}
    n_rule_add = 0
    for (surface, reading), types in rule_lex.items():
        for rt, auth in types:
            if (surface, reading, rt) not in have:
                rows.append((surface, reading, rt, auth,
                             "rules/L05_rules_v1.json", 90))
                have.add((surface, reading, rt))
                n_rule_add += 1

    cur.executemany(
        "INSERT OR IGNORE INTO pinyin_lexicon(surface,reading,reading_type,authority,source_ref,rank) "
        "VALUES (?,?,?,?,?,?)", rows)
    con.commit()

    # lexicon 指纹（进 pinyin_build，供可复现校验）
    cur.execute("SELECT surface,reading,reading_type FROM pinyin_lexicon ORDER BY surface,reading,reading_type")
    h = hashlib.sha256()
    n = 0
    for s, r, t in cur.fetchall():
        h.update(f"{s}\t{r}\t{t}\n".encode("utf-8"))
        n += 1
    lex_hash = h.hexdigest()

    # 多音字统计（P(c) 基数分布，L1 输出维度依据）
    cur.execute("SELECT COUNT(*) FROM (SELECT surface FROM pinyin_lexicon GROUP BY surface HAVING COUNT(*)>1)")
    poly = cur.fetchone()[0]
    cur.execute("SELECT MAX(c) FROM (SELECT COUNT(*) c FROM pinyin_lexicon GROUP BY surface)")
    maxc = cur.fetchone()[0]

    stats = {
        "rows": n, "char_entries": n_char, "polyphone_chars": n_poly,
        "phrase_entries": n_word, "rule_added": n_rule_add,
        "surface_polyphone": poly, "max_reading_per_surface": maxc,
        "lexicon_sha256": lex_hash,
    }
    (HERE / "lexicon_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    con.close()
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"[OK] 用时 {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
