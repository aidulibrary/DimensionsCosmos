# -*- coding: utf-8 -*-
"""
T2.1 主导音先验统计（M2 波 1）

目的：为"高危字一律存疑"这条保守口径寻找可撤除的依据。
方法：以语料内部证据为准 —— 若某高危字在全部出现位中，规则层改写（即非默认读法）
      的占比低于阈值，说明该字在本语料中确实以默认音为绝对主导，
      其"未命中规则的位"可降为低置信断言（source=dominant），confidence 0.85。

判据说明：这不是循环论证。信号是"规则层在该字上的改写密度"，
      规则改写为 0 次的字，说明全库从未出现需要异读的语境。
"""
import json
import pathlib
import sqlite3
import sys
from collections import Counter, defaultdict

SHARD_ROOT = pathlib.Path(r"D:\DimensionsCosmos\data\pinyin")
DB = r"D:\DimensionsCosmos\data\guji.db"
OUT = pathlib.Path(r"D:\DimensionsCosmos\pipeline\pinyin\rules\dominant_reading_v1.json")

HIGH_RISK = set("为王中相与见从将食女弟说乐数卒乘告共间语好恶长少行强知有亡冠衣雨处传")

MIN_SAMPLES = 500
MAX_REWRITE_RATIO = 0.005


def main(build_id):
    d = SHARD_ROOT / build_id
    if not d.exists():
        print(f"[FAIL] 分片目录不存在：{d}")
        return 1
    files = sorted(d.glob("*/*.json"))
    print(f"分片：{len(files)} 个（{build_id}）", flush=True)

    con = sqlite3.connect(DB)
    texts = {cid: (txt or "") for cid, txt in con.execute("SELECT id, COALESCE(clean_text, text) FROM chapters")}
    con.close()
    print(f"章节文本：{len(texts)} 章", flush=True)

    total = Counter()
    rewritten = Counter()
    rule_reading = defaultdict(Counter)
    base_reading = defaultdict(Counter)

    for i, p in enumerate(files, 1):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        text = texts.get(obj.get("chapter_id"))
        if not text:
            continue
        pos = obj.get("pos") or []
        py = obj.get("py") or []
        meta = obj.get("meta") or {}
        for k, off in enumerate(pos):
            if k >= len(py) or off >= len(text):
                continue
            ch = text[off]
            r = py[k]
            if not r:
                continue
            total[ch] += 1
            if (str(k) in meta) or (k in meta):
                rewritten[ch] += 1
                rule_reading[ch][r] += 1
            else:
                base_reading[ch][r] += 1
        if i % 2500 == 0:
            print(f"  [{i}/{len(files)}]", flush=True)

    rows = []
    for ch in HIGH_RISK:
        t = total.get(ch, 0)
        rw = rewritten.get(ch, 0)
        if t == 0:
            continue
        ratio = rw / t
        top_base = base_reading[ch].most_common(1)[0] if base_reading[ch] else ("", 0)
        rows.append({
            "char": ch,
            "total": t,
            "rewritten": rw,
            "rewrite_ratio": round(ratio, 6),
            "default_reading": top_base[0],
            "default_share": round(top_base[1] / t, 4),
            "rule_readings": dict(rule_reading[ch].most_common(6)),
            "demotable": bool(t >= MIN_SAMPLES and ratio < MAX_REWRITE_RATIO),
        })

    rows.sort(key=lambda x: -x["total"])
    summary = {
        "build_id": build_id,
        "high_risk_chars": len(rows),
        "total_positions": sum(r["total"] for r in rows),
        "rewritten_positions": sum(r["rewritten"] for r in rows),
        "overall_rewrite_ratio": round(
            sum(r["rewritten"] for r in rows) / max(1, sum(r["total"] for r in rows)), 6),
        "demotable_chars": [r["char"] for r in rows if r["demotable"]],
        "demotable_positions": sum(r["total"] - r["rewritten"] for r in rows if r["demotable"]),
        "thresholds": {"min_samples": MIN_SAMPLES, "max_rewrite_ratio": MAX_REWRITE_RATIO},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"summary": summary, "rows": rows},
                              ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== 高危字主导音先验（按出现位数 TOP 20）===")
    print(f"{'字':<3}{'总位':>10}{'规则改写':>10}{'改写率':>10}  {'默认音':<10}{'默认占比':>8}  可降态")
    for r in rows[:20]:
        print(f"{r['char']:<3}{r['total']:>10,}{r['rewritten']:>10,}"
              f"{r['rewrite_ratio']*100:>9.3f}%  {r['default_reading']:<10}"
              f"{r['default_share']*100:>7.2f}%  {'是' if r['demotable'] else '否'}")

    print(f"\n可降态字数：{len(summary['demotable_chars'])} / {len(rows)}")
    print(f"可降态位数：{summary['demotable_positions']:,}")
    print(f"可降态字：{''.join(summary['demotable_chars'])}")
    print(f"\n[OK] {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "b20261111_L05rule_v5"))
