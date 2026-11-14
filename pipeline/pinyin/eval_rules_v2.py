# -*- coding: utf-8 -*-
"""T2.2 离线评测：L05_rules_v1(92) vs L05_rules_v2(302+)

口径与 build_pinyin.py 完全一致：
  · 语料：chapters.COALESCE(clean_text,text)
  · 逐字 t2s 归一后以简体查规则
  · 句窗 WINDOW=12
差异：v2 启用 position_check=center —— 正则匹配串必须覆盖目标字位，
      消除「窗口内同名他字错位赋值」的误判（v1 遗留缺陷）。

产出：reports/rules_v2_eval.json
  1) 两版规则在高危存疑位上的解率、置信加权后残余存疑
  2) 每字解率表
  3) v2 仍未命中的高频搭配 top（供第三批规则挖掘）
"""
import json, pathlib, re, sqlite3, time
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).parent
DB = pathlib.Path(r"D:\DimensionsCosmos\data\guji.db")
RULES_V1 = HERE / "rules" / "L05_rules_v1.json"
RULES_V2 = HERE / "rules" / "L05_rules_v2.json"
OUT = HERE / "reports" / "rules_v2_eval.json"

HIGH_RISK = set("为 王 中 相 与 见 从 将 食 女 弟 说 乐 数 卒 乘 告 共 间 语 好 恶 长 少 行 强 知 有 亡 冠 衣 雨 处 传".split())
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
WINDOW = 12


def load(path, position_check=False):
    data = json.loads(path.read_text(encoding="utf-8"))
    by = {}
    for i, r in enumerate(data["rules"], 1):
        rec = dict(r)
        rec["_rid"] = i
        rec["_re"] = re.compile(rec["pattern"])
        by.setdefault(rec["surface"], []).append(rec)
    for v in by.values():
        v.sort(key=lambda x: -x.get("priority", 50))
    return by, len(data["rules"]), position_check


def pick(cands, win, center, position_check):
    best = None
    for rc in cands:
        m = rc["_re"].search(win)
        if not m:
            continue
        if position_check:
            if not (m.start() <= center < m.end()):
                continue
        else:
            if win[center] not in m.group(0):
                continue
        if best is None or rc.get("priority", 50) > best.get("priority", 50):
            best = rc
    return best


def main():
    try:
        from opencc import OpenCC
        cc = OpenCC("t2s")
    except Exception:
        cc = None
    _c = {}

    def t2s(ch):
        if ch not in _c:
            if cc is None:
                _c[ch] = ch
            else:
                try:
                    r = cc.convert(ch)
                    _c[ch] = r if len(r) == 1 else ch
                except Exception:
                    _c[ch] = ch
        return _c[ch]

    b1, n1, pc1 = load(RULES_V1, False)
    b2, n2, pc2 = load(RULES_V2, True)

    con = sqlite3.connect(str(DB))
    con.execute("PRAGMA journal_mode=WAL")
    cur = con.cursor()
    # 只看 v5 构建里被判 uncertain 的章节与位点：直接扫全语料重新算更稳（规则变了）
    rows = cur.execute(
        "SELECT id, work_id, COALESCE(clean_text,text) FROM chapters "
        "WHERE COALESCE(clean_text,text) IS NOT NULL ORDER BY id").fetchall()
    print(f"章数 {len(rows)}", flush=True)

    st = {"v1_hit": 0, "v2_hit": 0, "total": 0}
    per = defaultdict(lambda: {"total": 0, "v1": 0, "v2": 0})
    conf_sum = {"v1": 0.0, "v2": 0.0}
    miss_pair = defaultdict(Counter)   # surface -> Counter("l2|r2")
    rule_use = Counter()
    t0 = time.time()

    for n, (cid, wid, text) in enumerate(rows, 1):
        raw = text or ""
        simp = [t2s(ch) for ch in raw]
        L = len(raw)
        for i, sc in enumerate(simp):
            if sc not in HIGH_RISK:
                continue
            st["total"] += 1
            per[sc]["total"] += 1
            lo, hi = max(0, i - WINDOW), min(L, i + WINDOW + 1)
            win = "".join(simp[lo:hi])
            c = i - lo
            r1 = pick(b1.get(sc, ()), win, c, pc1)
            r2 = pick(b2.get(sc, ()), win, c, pc2)
            if r1:
                st["v1_hit"] += 1
                per[sc]["v1"] += 1
                conf_sum["v1"] += r1.get("confidence", 0.88)
            if r2:
                st["v2_hit"] += 1
                per[sc]["v2"] += 1
                conf_sum["v2"] += r2.get("confidence", 0.88)
                rule_use[r2["rule_key"]] += 1
            else:
                l2 = "".join(simp[max(0, i - 2):i])
                r2s = "".join(simp[i + 1:i + 3])
                miss_pair[sc][l2 + "|" + r2s] += 1
        if n % 2000 == 0:
            print(f"  {n}/{len(rows)}  {time.time()-t0:.1f}s", flush=True)

    def rate(a, b):
        return round(a / b, 4) if b else 0.0

    total = st["total"]
    residual = total - st["v2_hit"]
    report = {
        "build_source": "b20261111_L05rule_v5 corpus",
        "rules": {"v1": n1, "v2": n2},
        "high_risk_positions": total,
        "hit": {"v1": st["v1_hit"], "v2": st["v2_hit"]},
        "coverage": {"v1": rate(st["v1_hit"], total), "v2": rate(st["v2_hit"], total)},
        "mean_confidence": {
            "v1": round(conf_sum["v1"] / st["v1_hit"], 3) if st["v1_hit"] else 0,
            "v2": round(conf_sum["v2"] / st["v2_hit"], 3) if st["v2_hit"] else 0,
        },
        "residual_uncertain": {
            "v1": total - st["v1_hit"],
            "v2": residual,
            "v2_uncertain_ratio_over_all_chars": round(residual / 1420371, 4),
        },
        "per_char": {
            k: {**v, "v1_rate": rate(v["v1"], v["total"]), "v2_rate": rate(v["v2"], v["total"])}
            for k, v in sorted(per.items(), key=lambda x: -x[1]["total"])
        },
        "top_rules": rule_use.most_common(30),
        "top_missing_pairs": {
            k: [[c, n] for c, n in v.most_common(30)]
            for k, v in sorted(miss_pair.items(), key=lambda x: -per[x[0]]["total"])[:20]
        },
        "elapsed_sec": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: report[k] for k in
                      ("rules", "high_risk_positions", "hit", "coverage",
                       "mean_confidence", "residual_uncertain")},
                     ensure_ascii=False, indent=1))
    print("输出：", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
