# -*- coding: utf-8 -*-
"""M2 波2：金标种子集抽样（3 万字位，分层比例抽样，剔除四类高频误标 相/亡/恶/将）

输出：
  reports/gold_batch2_seed_20261111.json   供标注流程使用（含上下文）
  reports/gold_batch2_seed_20261111.csv    便于表格查看/外部标注
  reports/gold_batch2_strata_20261111.json 分层统计

设计要点：
  1) 剔除集 EXCLUDE = 相亡恶将 + 繁体 將/惡（四类高频误标，留给 T2.3 规则层处理，不污染金标）
  2) 按 (state, reading_type) 分层，按各层在剔除后总体中的占比 × 30000 分配
  3) 分层内随机抽样（固定 seed 可复现）
  4) gold_reading 留空，label_status='pending'，供人工/AI 复核填写
"""
import json, pathlib, random, sqlite3
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).parent
DB = pathlib.Path(r"D:\DimensionsCosmos\data\guji.db")
B = "b20261111_L05rule_r2v5"
TOTAL = 30000
SEED = 20261111
CTX = 16
EXCLUDE = set("相亡恶将將惡")
OUTD = HERE / "reports"

random.seed(SEED)
con = sqlite3.connect(str(DB))
cur = con.cursor()
cur2 = con.cursor()   # 嵌套查询必须用独立游标，否则外层结果集被重置

# ---------- 1. 剔除后总体分层规模 ----------
ex_sql = "','".join(sorted(EXCLUDE))
strata = []
for st, rt, n_all in cur.execute(
        "SELECT state, reading_type, COUNT(*) FROM chapter_pinyin WHERE build_id=? "
        "GROUP BY state, reading_type", (B,)).fetchall():
    n_ex = cur2.execute(
        f"SELECT COUNT(*) FROM chapter_pinyin WHERE build_id=? AND state=? AND reading_type=? "
        f"AND surface IN ('{ex_sql}')", (B, st, rt)).fetchone()[0]
    strata.append({"state": st, "rtype": rt, "n_all": n_all,
                   "n_excluded": n_ex, "n_pool": n_all - n_ex})
pool_total = sum(s["n_pool"] for s in strata)

# ---------- 2. 按占比分配名额（最大余数法，保证合计=TOTAL） ----------
for s in strata:
    s["quota_f"] = TOTAL * s["n_pool"] / pool_total
    s["quota"] = int(s["quota_f"])
    s["_rem"] = s["quota_f"] - s["quota"]
short = TOTAL - sum(s["quota"] for s in strata)
for s in sorted(strata, key=lambda x: -x["_rem"])[:short]:
    s["quota"] += 1

# ---------- 3. 抽样 ----------
picked = []
for s in strata:
    q = min(s["quota"], s["n_pool"])
    if q <= 0:
        continue
    rows = cur.execute(
        f"SELECT chapter_id, char_offset, surface, reading, reading_alt, state, confidence, "
        f"reading_type, authority, rule_id FROM chapter_pinyin "
        f"WHERE build_id=? AND state=? AND reading_type=? AND surface NOT IN ('{ex_sql}') "
        f"ORDER BY RANDOM() LIMIT ?", (B, s["state"], s["rtype"], q)).fetchall()
    for r in rows:
        picked.append({"cid": r[0], "off": r[1], "surface": r[2], "pred": r[3], "alt": r[4],
                       "state": r[5], "conf": r[6], "rtype": r[7], "auth": r[8], "rule_id": r[9]})

# ---------- 4. 附上下文 ----------
cache, titles = {}, dict(con.execute("SELECT id,title FROM chapters"))
for i, p in enumerate(picked, 1):
    cid = p["cid"]
    if cid not in cache:
        cache[cid] = cur.execute(
            "SELECT COALESCE(clean_text,text) FROM chapters WHERE id=?", (cid,)).fetchone()[0] or ""
    t = cache[cid]
    o = p["off"]
    p["gid"] = f"G2-{i:05d}"
    p["title"] = titles.get(cid, "")
    p["pre"] = t[max(0, o - CTX):o]
    p["post"] = t[o + 1:o + 1 + CTX]
    p["gold"] = ""
    p["label_status"] = "pending"

# ---------- 5. 落盘 ----------
OUTD.mkdir(parents=True, exist_ok=True)
meta = {"build_id": B, "total": len(picked), "seed": SEED, "excluded": sorted(EXCLUDE),
        "pool_total": pool_total, "strata": [{k: v for k, v in s.items() if k != "_rem"} for s in strata]}
(OUTD / "gold_batch2_seed_20261111.json").write_text(json.dumps(
    {"meta": meta, "items": picked}, ensure_ascii=False, indent=1), encoding="utf-8")

import csv
with open(OUTD / "gold_batch2_seed_20261111.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["gid", "surface", "pred", "alt", "rtype", "state", "conf", "rule_id",
                "title", "pre", "post", "gold", "label_status", "cid", "off"])
    for p in picked:
        w.writerow([p["gid"], p["surface"], p["pred"], p["alt"], p["rtype"], p["state"],
                    p["conf"], p["rule_id"], p["title"], p["pre"], p["post"], "", "pending",
                    p["cid"], p["off"]])

(OUTD / "gold_batch2_strata_20261111.json").write_text(
    json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

print(f"pool_total(after exclude)={pool_total}  sampled={len(picked)}")
for s in strata:
    print(f"  {s['state']:<10}{s['rtype']:<14} all={s['n_all']:>8} excl={s['n_excluded']:>7} "
          f"quota={s['quota']:>6} rate={s['n_pool']/pool_total*100:>5.2f}%")
print("四字剔除合计:", sum(s["n_excluded"] for s in strata))
print("输出:", OUTD)
