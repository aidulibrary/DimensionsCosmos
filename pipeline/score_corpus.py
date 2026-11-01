"""古籍扩容筛选模型的评分引擎（对应 docs/CORPUS-SELECTION-MODEL.md v1.0）。

用法:
    python pipeline/score_corpus.py --report                  # 校验 + 排名 + 分档
    python pipeline/score_corpus.py --backfill-impact         # 联网环境回填 D3（Wikidata sitelinks）
    python pipeline/score_corpus.py --backfill-impact --dry-run

设计原则:
1. 分数只能来自 corpus_scores.csv，本脚本不做任何主观打分。
2. D3 未核验（status=UNVERIFIED）时不计入排序，改用其余四维重归一化得 provisional 分，
   避免用印象分污染排名。
3. 任何分数越界、书目不在候选池、篇幅违反约束 A 的情况一律报错而非静默跳过。
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAND = ROOT / "data" / "corpus_candidates.csv"
SCORES = ROOT / "data" / "corpus_scores.csv"
RANKED = ROOT / "data" / "corpus_scores_ranked.csv"

W = {"d1": 0.30, "d2": 0.25, "d3": 0.20, "d4": 0.15, "d5": 0.10}
SIZE_SCORE = {"S1": 2.0, "S2": 1.0, "S3": 0.5, "S4": 0.0}
TIERS = [(4.20, "S"), (3.60, "A"), (3.00, "B"), (0.0, "C")]


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return [{k.strip(): (v or "").strip() for k, v in r.items()} for r in rows]


def tier_of(score):
    for cut, name in TIERS:
        if score >= cut:
            return name
    return "C"


def compute():
    cands = {r["title"]: r for r in read_csv(CAND)}
    scores = read_csv(SCORES)
    errors, rows = [], []

    for r in scores:
        title = r["title"]
        c = cands.get(title)
        if not c:
            errors.append(f"[候选池缺失] {title} 不在 corpus_candidates.csv")
            continue
        sc = c.get("size_class", "")
        if sc not in SIZE_SCORE:
            errors.append(f"[篇幅分级非法] {title} size_class={sc!r}")
            continue
        try:
            d1, d2, d5 = float(r["d1"]), float(r["d2"]), float(r["d5"])
            avail = float(r["d4_avail"])
        except (KeyError, ValueError):
            errors.append(f"[分数非数字] {title}")
            continue
        bad = [f"{n}={v}" for n, v in (("d1", d1), ("d2", d2), ("d5", d5)) if not 0 <= v <= 5]
        if bad:
            errors.append(f"[分数越界] {title} " + ", ".join(bad))
            continue
        if avail not in (0, 1, 2):
            errors.append(f"[可得性非法] {title} d4_avail={avail}")
            continue

        d4 = (avail + SIZE_SCORE[sc]) / 4 * 5
        d3_raw = r.get("d3", "")
        verified = bool(d3_raw) and r.get("status", "").upper() == "VERIFIED"

        if verified:
            d3 = float(d3_raw)
            total_w = sum(W.values())
            score = sum(W[k] * v for k, v in
                        (("d1", d1), ("d2", d2), ("d3", d3), ("d4", d4), ("d5", d5)))
            provisional = False
        else:
            total_w = W["d1"] + W["d2"] + W["d4"] + W["d5"]
            raw = W["d1"] * d1 + W["d2"] * d2 + W["d4"] * d4 + W["d5"] * d5
            score = raw / total_w
            d3 = None
            provisional = True

        rows.append({
            "title": title, "bu": c.get("bu", ""), "author": c.get("author", ""),
            "dynasty": c.get("dynasty", ""), "gap": c.get("gap", ""),
            "size_class": sc, "d1": d1, "d2": d2,
            "d3": "" if d3 is None else round(d3, 2),
            "d4": round(d4, 2), "d5": d5,
            "score": round(score, 2), "tier": tier_of(score),
            "provisional": "Y" if provisional else "N",
            "gate_note": c.get("gate_note", ""), "note": r.get("note", ""),
            "d3_evidence": r.get("d3_evidence", ""),
        })

    rows.sort(key=lambda x: (-x["score"], x["title"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows, errors, cands


def print_report(rows, errors, cands):
    print(f"候选池 {len(cands)} 部，已评分 {len(rows)} 部，校验错误 {len(errors)} 条\n")
    for e in errors[:20]:
        print("  ERR", e)
    if errors:
        print()

    print("| 排名 | 书 | 部类 | 朝代 | D1 | D2 | D3 | D4 | D5 | 综合 | 档 | 状态 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['rank']} | {r['title']} | {r['bu']} | {r['dynasty']} | {r['d1']:.0f} | "
              f"{r['d2']:.0f} | {r['d3'] if r['d3'] != '' else '—'} | {r['d4']:.2f} | "
              f"{r['d5']:.0f} | {r['score']:.2f} | {r['tier']} | "
              f"{'临时' if r['provisional'] == 'Y' else '已核验'} |")

    from collections import Counter
    c = Counter(r["tier"] for r in rows)
    print("\n分档：" + " / ".join(f"{k} {c.get(k, 0)}" for k in "SABC"))
    prov = sum(1 for r in rows if r["provisional"] == "Y")
    if prov:
        print(f"注意：{prov} 部 D3（全球影响力）未核验，综合分为 provisional（按其余四维归一化）。"
              f"联网后执行 --backfill-impact 重算。")


def write_ranked(rows):
    cols = ["rank", "title", "bu", "author", "dynasty", "gap", "size_class", "d1", "d2",
            "d3", "d4", "d5", "score", "tier", "provisional", "gate_note", "note", "d3_evidence"]
    with RANKED.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})
    print(f"\n已写出 {RANKED.relative_to(ROOT)}")


def backfill(dry_run=False):
    """用 Wikidata sitelinks 数给出 D3 客观分（对应模型 §7.3）。"""
    import requests
    H = {"User-Agent": "DimensionsCosmosBot/0.1 (https://github.com/aidulibrary/DimensionsCosmos)"}
    API = "https://www.wikidata.org/w/api.php"
    rows = read_csv(SCORES)
    titles = [r["title"] for r in rows]
    qids = {}
    for t in titles:
        try:
            resp = requests.get(API, params={"action": "wbsearchentities", "search": t,
                                             "language": "zh", "uselang": "zh",
                                             "type": "item", "limit": "5", "format": "json"},
                                headers=H, timeout=20)
            for hit in resp.json().get("search", []):
                if hit.get("match", {}).get("text", "").replace(" ", "") == t.replace(" ", ""):
                    qids[t] = hit["id"]
                    break
        except Exception as e:
            print(f"  [解析失败] {t}: {type(e).__name__}")
    print(f"QID 解析 {len(qids)}/{len(titles)}")

    links = {}
    ids = list(qids.values())
    for i in range(0, len(ids), 45):
        chunk = ids[i:i + 45]
        try:
            resp = requests.get(API, params={"action": "wbgetentities", "ids": "|".join(chunk),
                                             "props": "sitelinks", "format": "json"},
                                headers=H, timeout=30)
            for qid, ent in resp.json().get("entities", {}).items():
                links[qid] = len(ent.get("sitelinks", {}))
        except Exception as e:
            print(f"  [sitelinks 失败] {type(e).__name__}")

    def to_score(n):
        if n >= 45:
            return 5
        if n >= 25:
            return 4
        if n >= 12:
            return 3
        if n >= 5:
            return 2
        return 1

    for r in rows:
        qid = qids.get(r["title"])
        if not qid or qid not in links:
            continue
        n = links[qid]
        r["d3"] = str(to_score(n))
        r["d3_evidence"] = f"Wikidata {qid} sitelinks={n}"
        r["status"] = "VERIFIED"
        print(f"  {r['title']}: {qid} sitelinks={n} -> D3={to_score(n)}")

    if dry_run:
        print("dry-run，不写回")
        return
    cols = ["title", "d1", "d2", "d3", "d4_avail", "d5", "d3_evidence", "status", "note"]
    with SCORES.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})
    print(f"已写回 {SCORES.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--backfill-impact", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.backfill_impact:
        backfill(a.dry_run)
        return
    rows, errors, cands = compute()
    print_report(rows, errors, cands)
    write_ranked(rows)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
