# -*- coding: utf-8 -*-
"""FLCA-6 ｜ 合并各批次统计 -> 全库总账，回写 pinyin_build。"""
import json
import pathlib
import sqlite3
import sys
from collections import Counter

HERE = pathlib.Path(__file__).parent
REPORT_DIR = HERE / "reports"
DB = pathlib.Path(r"D:\DimensionsCosmos\data\guji.db")
BUILD = sys.argv[1] if len(sys.argv) > 1 else "b20261111_L05rule_v2"

files = [p for p in sorted(REPORT_DIR.glob(f"pinyin_stats_{BUILD}_*.json")) if "smoke" not in p.name]
tot, rule, unc = Counter(), Counter(), Counter()
han = chars = rules_total = 0
for f in files:
    d = json.loads(f.read_text(encoding="utf-8"))
    han += d["han_chars"]
    chars += d["chapters"]
    rules_total += d.get("rule_hits_total", 0)
    for k, v in d["state_counts"].items():
        tot[k] += v
    for k, v in d.get("rule_hits_top", {}).items():
        rule[k] += v
    for k, v in d.get("uncertain_top", {}).items():
        unc[k] += v

total = sum(tot.values()) or 1
summary = {
    "build_id": BUILD,
    "batches": len(files),
    "chapters": chars,
    "han_chars": han,
    "state_counts": dict(tot),
    "state_ratio": {k: round(v / total, 5) for k, v in tot.items()},
    "rule_hits_total": rules_total,
    "rule_hits_top": dict(rule.most_common(20)),
    "uncertain_top": dict(unc.most_common(20)),
}
print(json.dumps(summary, ensure_ascii=False, indent=2))

con = sqlite3.connect(str(DB))
con.execute("UPDATE pinyin_build SET stats_json=? WHERE build_id=?",
            (json.dumps(summary, ensure_ascii=False), BUILD))
con.commit()
con.close()
out = REPORT_DIR / f"{BUILD}_TOTAL.json"
out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[OK] 全库总账：{out}")
