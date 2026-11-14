# -*- coding: utf-8 -*-
"""T2.2 验收：金标抽样 + position_check 有效性对照

A. 分层抽样（asserted / defaultAssert / variant），输出上下文供人工核对
B. center 锚定 on/off 的命中差 —— 量化「窗口内同名他字错位赋值」的规模
"""
import json, pathlib, random, re, sqlite3
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).parent
DB = pathlib.Path(r"D:\DimensionsCosmos\data\guji.db")
RULES_V2 = HERE / "rules" / "L05_rules_v2_1.json"
OUT = HERE / "reports" / "verify_r2v5.json"
B = "b20261111_L05rule_r2v5"
WINDOW = 12
HIGH_RISK = set("为 王 中 相 与 见 从 将 食 女 弟 说 乐 数 卒 乘 告 共 间 语 好 恶 长 少 行 强 知 有 亡 冠 衣 雨 处 传".split())
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

random.seed(20261111)
con = sqlite3.connect(str(DB))
cur = con.cursor()

# ---------- A. 抽样 ----------
samples = []
plan = [("asserted", 120), ("defaultAssert", 40), ("variant", 20)]
for state_or_type, n in plan:
    if state_or_type == "asserted":
        cond, args = "state='asserted'", ()
    elif state_or_type == "variant":
        cond, args = "state='variant'", ()
    else:
        cond, args = "reading_type='defaultAssert'", ()
    rows = cur.execute(
        f"SELECT chapter_id,char_offset,surface,reading,reading_alt,state,confidence,"
        f"reading_type,authority FROM chapter_pinyin WHERE build_id=? AND {cond} "
        f"ORDER BY RANDOM() LIMIT ?", (B, *args, n)).fetchall()
    for r in rows:
        samples.append({"group": state_or_type, "cid": r[0], "off": r[1], "surface": r[2],
                        "reading": r[3], "alt": r[4], "state": r[5], "conf": r[6],
                        "rtype": r[7], "auth": r[8]})

cache = {}
titles = dict(con.execute("SELECT id,title FROM chapters").fetchall())
for s in samples:
    cid = s["cid"]
    if cid not in cache:
        txt = cur.execute("SELECT COALESCE(clean_text,text) FROM chapters WHERE id=?",
                          (cid,)).fetchone()[0] or ""
        cache[cid] = txt
    txt = cache[cid]
    i = s["off"]
    s["ctx"] = txt[max(0, i - 14):i] + "【" + txt[i:i + 1] + "】" + txt[i + 1:i + 15]
    s["title"] = titles.get(cid, "")

# ---------- B. center on/off ----------
rules = json.loads(RULES_V2.read_text(encoding="utf-8"))["rules"]
by = defaultdict(list)
for i, r in enumerate(rules, 1):
    d = dict(r); d["_rid"] = i; d["_re"] = re.compile(r["pattern"])
    by[d["surface"]].append(d)
for v in by.values():
    v.sort(key=lambda x: -x.get("priority", 50))

try:
    from opencc import OpenCC
    cc = OpenCC("t2s")
except Exception:
    cc = None
_c = {}

def t2s(ch):
    if ch not in _c:
        _c[ch] = cc.convert(ch) if cc else ch
        if len(_c[ch]) != 1:
            _c[ch] = ch
    return _c[ch]

diff = Counter()
diff_samples = []
on = off = 0
for cid, wid, text in cur.execute(
        "SELECT id,work_id,COALESCE(clean_text,text) FROM chapters "
        "WHERE COALESCE(clean_text,text) IS NOT NULL ORDER BY id LIMIT 2500"):
    raw = text or ""
    simp = [t2s(c) for c in raw]
    L = len(raw)
    for i, sc in enumerate(simp):
        if sc not in HIGH_RISK:
            continue
        lo, hi = max(0, i - WINDOW), min(L, i + WINDOW + 1)
        win = "".join(simp[lo:hi])
        c = i - lo
        cands = by.get(sc, ())
        b_on = b_off = None
        for rc in cands:
            ms = list(rc["_re"].finditer(win))
            if not ms:
                continue
            if any(m.start() <= c < m.end() for m in ms):
                if b_on is None or rc.get("priority", 50) > b_on.get("priority", 50):
                    b_on = rc
            if any(sc in m.group(0) for m in ms):
                if b_off is None or rc.get("priority", 50) > b_off.get("priority", 50):
                    b_off = rc
        if b_on:
            on += 1
        if b_off:
            off += 1
        k_on = b_on["rule_key"] if b_on else None
        k_off = b_off["rule_key"] if b_off else None
        if k_on != k_off:
            diff[(k_off, k_on, sc)] += 1
            if len(diff_samples) < 40:
                diff_samples.append({
                    "surface": sc, "ctx": raw[max(0, i - 10):i] + "【" + raw[i:i + 1] + "】" + raw[i + 1:i + 11],
                    "center_rule": k_on, "center_reading": b_on["reading"] if b_on else None,
                    "loose_rule": k_off, "loose_reading": b_off["reading"] if b_off else None,
                })

res = {
    "build_id": B,
    "samples": samples,
    "center_check": {
        "scope_chapters": 2500,
        "hit_with_center": on,
        "hit_without_center": off,
        "same_key": on - sum(v for _, k_on, _ in [] ) if False else None,
        "divergent_positions": sum(diff.values()),
        "top_divergence": [[f"{k_off}->{k_on}", s, n] for (k_off, k_on, s), n in diff.most_common(20)],
        "examples": diff_samples,
    },
}
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("hit center/loose:", on, off, "divergent:", sum(diff.values()))
print("top:", [[f"{a}->{b}", s, n] for (a, b, s), n in diff.most_common(12)])
print("输出:", OUT, "样本数:", len(samples))
