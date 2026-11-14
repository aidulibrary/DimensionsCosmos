#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0 治理工具：只读本机 guji.db，生成可复现的验收 / 抽样框 / 重排产物。

设计约束（与主 AI 复核报告硬禁令一致）：
  * 只读 data/guji.db（sqlite mode=ro），不写任何表；
  * 不改 pipeline/pinyin/rules/L05_rules_v2_5.json；
  * 不写 public/，不覆盖 public/collation/pinyin-review/data.json；
  * 只向 pipeline/pinyin/output/ 写新文件；
  * 不联网、不调模型、不训练、不上传任何未刊稿。

可复现性：所有抽样用 sha256(seed|rule_id|chapter_id|char_offset) 的确定性序，
不依赖 random 全局状态；seed 固定为 20261113，换 seed 即换样本，但任何一次结果可重放。

用法：
  python pipeline/pinyin/p0_governance_tools.py ci          # 22 条规则双轴复核 + Wilson CI
  python pipeline/pinyin/p0_governance_tools.py frame       # 21 条规则各 30 位全库随机分层抽样框
  python pipeline/pinyin/p0_governance_tools.py rebalance   # 128 位近等分重排（真 JSONL + 标注台替换件）
  python pipeline/pinyin/p0_governance_tools.py all
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "guji.db"
OUT = ROOT / "pipeline" / "pinyin" / "output"
REVIEW = ROOT / "public" / "collation" / "pinyin-review" / "data.json"

SEED = "20261113"
N_PER_RULE = 30
TARGET_PER_BUCKET = 32
CTX_L, CTX_R = 16, 20
BUCKET_CN = {
    "B1_lexical": "语词汇",
    "B2_poDu": "破读",
    "B3_tongJia": "通假",
    "B4_defaultAssert": "默认读音组",
}
TARGET_ACTIONS = ("DISABLE_OR_NARROW", "NARROW")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rank(*parts) -> str:
    """确定性排序键：同一 seed 与同一位点永远得到同一顺序。"""
    return hashlib.sha256("|".join([SEED] + [str(p) for p in parts]).encode("utf-8")).hexdigest()


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 1.0
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, center - half), min(1.0, center + half)


def open_ro() -> sqlite3.Connection:
    if not DB.exists():
        raise SystemExit(f"[FATAL] 本机无 {DB}；本工具不适用于 WorkBuddy worktree 副本")
    return sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)


def chapter_meta(conn) -> dict[int, dict]:
    """chapter_id -> (work_id, chapter_title, work_title, text)。"""
    out = {}
    for cid, wid, ctitle, wtitle, clean in conn.execute(
        "SELECT ch.id, ch.work_id, ch.title, w.seed_title, COALESCE(ch.clean_text, ch.text) "
        "FROM chapters ch JOIN works w ON w.id = ch.work_id"
    ):
        out[cid] = {
            "work_id": wid,
            "chap": ctitle,
            "work": wtitle,
            # chapter_pinyin.char_offset 的基准是 clean_text，不是 text。
            # 用 text 取上下文会在两字段有差异的章里整体错位，人工判读会判错。
            "clean": clean or "",
        }
    return out


def make_ctx(meta: dict, cid: int, off: int, surface: str) -> dict:
    txt = meta.get(cid, {}).get("clean", "")
    lo = max(0, off - CTX_L)
    ctx = txt[lo: off + CTX_R + 1]
    ti = min(CTX_L, off)
    return {
        "ctx": ctx,
        "ti": ti,
        "tl": off > CTX_L,
        "tr": off + CTX_R + 1 < len(txt),
        "ctx_source": "chapters.clean_text (ctxL=16, ctxR=20)",
        "offset_basis": "chapter_pinyin.char_offset = chapters.clean_text 下标",
        # fail-closed：对不上就如实标 false，不硬填上下文
        "ctx_surface_aligned": bool(ctx) and ctx[ti:ti + 1] == surface,
    }


# --------------------------------------------------------------------------- ci
def run_ci() -> Path:
    conn = open_ro()
    table = load_json(OUT / "rule_evidence_table.json")
    rows = [r for r in table if r.get("action") in TARGET_ACTIONS]
    state_counts = {}
    for rid, state, n in conn.execute(
        "SELECT rule_id, state, count(*) FROM chapter_pinyin GROUP BY rule_id, state"
    ):
        state_counts.setdefault(rid, {})[state] = n

    result = []
    for r in rows:
        rid = r.get("rule_id")
        n, acc = r["seed_n"], r["seed_acc"]
        k = round(acc * n)
        lo, hi = wilson(k, n)
        asserted = r["lib_asserted"]
        wrong_lo = round(asserted * (1 - hi)) if rid is not None else None
        wrong_hi = round(asserted * (1 - lo)) if rid is not None else None
        db = state_counts.get(rid, {}) if rid is not None else {}
        db_asserted = db.get("asserted", 0)
        db_uncertain = db.get("uncertain", 0)
        db_total = sum(db.values())
        result.append({
            "rule_id": rid,
            "action": r["action"],
            "type": r["type"],
            "pattern": r["pattern"],
            "seed_n": n,
            "seed_k": k,
            "seed_acc": acc,
            "wilson95": [round(lo, 4), round(hi, 4)],
            "table_lib_asserted": asserted,
            "table_est_wrong_point": r["est_wrong"],
            "est_wrong_interval": [wrong_lo, wrong_hi],
            "db_asserted": db_asserted,
            "db_uncertain": db_uncertain,
            "db_variant": db.get("variant", 0),
            "db_total_hits": db_total,
            "lib_asserted_matches_db": (asserted == db_asserted) if rid is not None else None,
            "impact_axis": "asserted" if db_asserted > 0 else ("uncertain" if db_uncertain > 0 else "none"),
            "is_real_rule": rid is not None,
            "note": "D_null 默认音型态，非规则，不可『缩窄』" if rid is None else "",
            "s3_disable_candidate": (hi < 0.9) if rid is not None else False,
            "s3_rule": "仅当 Wilson 95% 精度上界 < 0.9 才进禁用候选；否则维持 INSUFFICIENT_SAMPLE",
            "sample_frame_reachable": db_total >= N_PER_RULE,
        })

    payload = {
        "generated_by": "p0_governance_tools.py ci",
        "seed": SEED,
        "source": "rule_evidence_table.json + data/guji.db (read-only)",
        "z": 1.96,
        "n_rows": len(result),
        "summary": {
            "rows_with_asserted": sum(1 for x in result if x["db_asserted"] > 0),
            "rows_with_uncertain_only": sum(1 for x in result if x["db_asserted"] == 0 and x["db_uncertain"] > 0),
            "rows_lib_asserted_zero": sum(1 for x in result if x["table_lib_asserted"] == 0),
            "rows_not_a_rule": sum(1 for x in result if not x["is_real_rule"]),
            "asserted_sum": sum(x["db_asserted"] for x in result),
            "uncertain_sum": sum(x["db_uncertain"] for x in result),
            "s3_disable_candidates": sum(1 for x in result if x["s3_disable_candidate"]),
        },
        "rows": result,
    }
    path = OUT / "P0_rule_ci_recheck.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    conn.close()
    return path


# ------------------------------------------------------------------------ frame
def run_frame() -> Path:
    conn = open_ro()
    meta = chapter_meta(conn)
    table = load_json(OUT / "rule_evidence_table.json")
    rules = [r for r in table if r.get("action") in TARGET_ACTIONS and r.get("rule_id") is not None]
    ids = [r["rule_id"] for r in rules]
    placeholders = ",".join("?" * len(ids))
    hits = defaultdict(list)
    for cid, off, surface, reading, state, rid in conn.execute(
        f"SELECT chapter_id, char_offset, surface, reading, state, rule_id "
        f"FROM chapter_pinyin WHERE rule_id IN ({placeholders})", ids
    ):
        hits[rid].append((cid, off, surface, reading, state))
    conn.close()

    out_rules = []
    for r in rules:
        rid = r["rule_id"]
        pool = hits.get(rid, [])
        # 分层：先按 work_id 各取 1 位（保证跨书覆盖），余下名额按全局确定性序补足。
        by_work = defaultdict(list)
        for h in pool:
            by_work[meta.get(h[0], {}).get("work_id", -1)].append(h)
        for w in by_work:
            by_work[w].sort(key=lambda h: rank(rid, h[0], h[1]))
        picked, used = [], set()
        for w in sorted(by_work, key=lambda x: rank(rid, "work", x)):
            if len(picked) >= N_PER_RULE:
                break
            h = by_work[w][0]
            key = (h[0], h[1])
            if key not in used:
                picked.append(h)
                used.add(key)
        rest = sorted(
            (h for h in pool if (h[0], h[1]) not in used),
            key=lambda h: rank(rid, "rest", h[0], h[1]),
        )
        for h in rest:
            if len(picked) >= N_PER_RULE:
                break
            picked.append(h)
            used.add((h[0], h[1]))
        picked.sort(key=lambda h: rank(rid, "final", h[0], h[1]))

        items = []
        for cid, off, surface, reading, state in picked:
            m = meta.get(cid, {})
            c = make_ctx(meta, cid, off, surface)
            items.append({
                "chapter_id": cid,
                "offset": off,
                "work_id": m.get("work_id"),
                "work": m.get("work"),
                "chap": m.get("chap"),
                "surface": surface,
                "reading": reading,
                "state": state,
                "ctx": c["ctx"],
                "ti": c["ti"],
                "tl": c["tl"],
                "tr": c["tr"],
                "offset_basis": c["offset_basis"],
                "ctx_surface_aligned": c["ctx_surface_aligned"],
                "sample_rank": rank(rid, cid, off)[:12],
            })
        out_rules.append({
            "rule_id": rid,
            "action": r["action"],
            "type": r["type"],
            "pattern": r["pattern"],
            "seed_n_existing": r["seed_n"],
            "seed_acc_existing": r["seed_acc"],
            "frame_size": len(pool),
            "frame_state_dist": dict(Counter(h[4] for h in pool)),
            "frame_work_count": len(by_work),
            "n_sampled": len(items),
            "items": items,
        })

    payload = {
        "generated_by": "p0_governance_tools.py frame",
        "seed": SEED,
        "sampling_frame": "chapter_pinyin 中该 rule_id 命中的全部字位（asserted/uncertain/variant 全纳入）",
        "excluded": "t23_batch1 等定向疑难判读池 —— 不从老池补样",
        "stratification": "按 work_id 每书先取 1 位，余下名额按 sha256 确定性序全局补足",
        "reproducible": True,
        "n_per_rule": N_PER_RULE,
        "n_rules": len(out_rules),
        "ctx_offset_basis": "chapter_pinyin.char_offset = chapters.clean_text 下标",
        "ctx_surface_aligned_count": sum(1 for r in out_rules for i in r["items"] if i["ctx_surface_aligned"]),
        "ctx_surface_total": sum(len(r["items"]) for r in out_rules),
        "excluded_rows": "rule_id=null 的 D_null 默认音型态（非规则，无命中位点可抽）",
        "hard_constraint": "本文件不进入 public/；不改动任何 state 与规则库",
        "rules": out_rules,
    }
    path = OUT / "P0_rule_sample_frame_30.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ------------------------------------------------------------------- rebalance
def run_rebalance() -> list[Path]:
    conn = open_ro()
    meta = chapter_meta(conn)
    silver = load_json(OUT / "P0_silver_636.jsonl")
    old_ticket = load_json(OUT / "P0_verify_ticket_128.jsonl")
    review = load_json(REVIEW)

    by_bucket = defaultdict(list)
    for s in silver:
        by_bucket[s["bucket"]].append(s)

    plan = {
        "B1_lexical": {"target": 32, "by_rtype": None},
        "B2_poDu": {"target": 32, "by_rtype": None},
        "B3_tongJia": {"target": 32, "by_rtype": {"R_whitelist": 14, "R_other": 18}},
        "B4_defaultAssert": {"target": 32, "by_rtype": None},
    }
    chosen = []
    for b, cfg in plan.items():
        pool = by_bucket[b]
        if cfg["by_rtype"]:
            for rt, k in cfg["by_rtype"].items():
                sub = sorted(
                    (x for x in pool if x["rtype_group"] == rt),
                    key=lambda x: rank("rebalance", b, rt, x["chapter_id"], x["offset"]),
                )
                assert len(sub) >= k, f"{b}/{rt} 池不足：{len(sub)} < {k}"
                chosen.extend(sub[:k])
        else:
            sub = sorted(pool, key=lambda x: rank("rebalance", b, x["chapter_id"], x["offset"]))
            assert len(sub) >= cfg["target"], f"{b} 池不足"
            chosen.extend(sub[: cfg["target"]])
    chosen.sort(key=lambda x: rank("rebalance", "final", x["chapter_id"], x["offset"]))

    keys = [(x["chapter_id"], x["offset"]) for x in chosen]
    assert len(keys) == len(set(keys)) == 128, "重排后位点应 128 个且无重复"
    silver_keys = {(x["chapter_id"], x["offset"]) for x in silver}
    assert set(keys) <= silver_keys, "重排越出 636 银标池"
    old_keys = {(x["chapter_id"], x["offset"]) for x in old_ticket}
    retained = len(set(keys) & old_keys)

    # 真 JSONL：每行一个独立 JSON 对象（修正 X6「.jsonl 实为 JSON 数组」缺陷）
    lines = []
    for i, s in enumerate(chosen, 1):
        rec = dict(s)
        rec["ticket_id"] = i
        rec["rebalance_target_per_bucket"] = 32
        rec["rebalance_note"] = "按桶近等分；B3 内部按银标型态比例 14:18；确定性 sha256 抽样"
        rec["sample_seed"] = SEED
        lines.append(json.dumps(rec, ensure_ascii=False))
    p1 = OUT / "P0_verify_ticket_128_rebalanced.jsonl"
    p1.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 标注台替换件（不覆盖 data.json）
    items = []
    for i, s in enumerate(chosen, 1):
        cid, off = s["chapter_id"], s["offset"]
        m = meta[cid]
        c = make_ctx(meta, cid, off, s["surface"])
        assert c["ctx_surface_aligned"], f"上下文与目标字不对齐：cid={cid} off={off} surface={s['surface']}"
        items.append({
            "id": i,
            "bucket": s["bucket"],
            "bucketCn": BUCKET_CN[s["bucket"]],
            "chId": cid,
            "off": off,
            "surface": s["surface"],
            "machine": s["machine_reading"],
            "ruleId": s["rule_id"],
            "state": s["state"],
            "ctx": c["ctx"],
            "ti": c["ti"],
            "tl": c["tl"],
            "tr": c["tr"],
            "work": m["work"],
            "slug": f"{m['work_id']}-{m['work']}",
            "chap": m["chap"],
        })
    new_meta = dict(review["meta"])
    new_meta["total"] = 128
    new_meta["note"] = (
        review["meta"]["note"]
        + " 【重排 v2】按桶近等分 32/32/32/32；B3 通假桶由 11→32，层内 Wilson 半宽由 ±30% 收至约 ±17%。"
    )
    new_meta["rebalance_seed"] = SEED
    new_meta["rebalance_source"] = "P0_verify_ticket_128_rebalanced.jsonl"
    new_meta["ctx_offset_basis"] = "chapter_pinyin.char_offset = chapters.clean_text 下标"
    payload = {
        "meta": new_meta,
        "strata": [
            {"key": b, "cn": BUCKET_CN[b], "n": 32}
            for b in ("B1_lexical", "B2_poDu", "B3_tongJia", "B4_defaultAssert")
        ],
        "items": items,
    }
    p2 = OUT / "P0_data_rebalanced.json"
    p2.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "generated_by": "p0_governance_tools.py rebalance",
        "seed": SEED,
        "pool": "P0_silver_636.jsonl（未引入池外位点、未改任何判据）",
        "old_bucket_dist": dict(Counter(x["bucket"] for x in old_ticket)),
        "new_bucket_dist": dict(Counter(x["bucket"] for x in chosen)),
        "new_b3_rtype_dist": dict(Counter(x["rtype_group"] for x in chosen if x["bucket"] == "B3_tongJia")),
        "retained_from_old_ticket": retained,
        "new_from_silver_pool": 128 - retained,
        "format": "真 JSONL（每行一对象）",
        "review_console_replacement": "P0_data_rebalanced.json —— 未覆盖 data.json，需业主确认后再替换",
        "unlabeled": True,
    }
    p3 = OUT / "P0_rebalance_report.json"
    p3.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    conn.close()
    return [p1, p2, p3]


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    if mode in ("ci", "all"):
        made.append(run_ci())
    if mode in ("frame", "all"):
        made.append(run_frame())
    if mode in ("rebalance", "all"):
        made.extend(run_rebalance())
    for p in made:
        print(f"OK {p.name}  {p.stat().st_size} bytes")
