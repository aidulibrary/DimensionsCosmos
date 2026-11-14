# -*- coding: utf-8 -*-
"""
维点图书馆 · FLCA-6 ｜ T1.4 + L0.5 基线流水线
engine = L0.5-rule-v1  （L0 词典默认音 + L0.5 规则层覆盖）

产物：
  1) data/pinyin/<build_id>/<work_id>/<chapter_id>.json   分片（前端按需加载，D7-b）
  2) guji.db chapter_pinyin / pinyin_build                落库（高危 + 规则命中 + 存疑项）
  3) pipeline/pinyin/reports/<build_id>_stats.json         构建统计（可复现记录）

三态口径（V3.0 §5.2 定版）：
  asserted  单音字 / 规则命中 / 多音字默认音（authority 标 pypinyin-default, conf 0.80）
  variant   规则命中但学界并存两读（alt 并列）
  uncertain V1.0 实测 33 高危破读字且规则未覆盖（conf 0.45）

执行：
  python pipeline\pinyin\build_pinyin.py --limit 50      # 冒烟
  python pipeline\pinyin\build_pinyin.py                 # 全库
"""
import argparse
import hashlib
import json
import pathlib
import re
import sqlite3
import sys
import time
from collections import Counter

HERE = pathlib.Path(__file__).parent
DB = pathlib.Path(r"D:\DimensionsCosmos\data\guji.db")
SHARD_ROOT = pathlib.Path(r"D:\DimensionsCosmos\data\pinyin")
REPORT_DIR = HERE / "reports"
RULE_FILE = HERE / "rules" / "L05_rules_v1.json"

# V1.0 实测的 33 个高危破读字：规则未命中时一律判 uncertain，不得以词典默认音冒充已消歧
HIGH_RISK = set("为 王 中 相 与 见 从 将 食 女 弟 说 乐 数 卒 乘 告 共 间 语 好 恶 长 少 行 强 知 有 亡 冠 衣 雨 处 传".split())

# 学界并存两读的规则：命中后标 variant（并列默认音）
VARIANT_KEYS = {
    "poDu.gao.gu", "tongJia.zhi.zhi", "tongJia.fan.return", "tongJia.heng.cross",
    "tongJia.li.suffer", "tongJia.que.lack", "tongJia.chang.once",
    "tongJia.hui.wisdom", "poDu.le.yao", "poDu.zhi.wise",
}

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
WINDOW = 12  # 规则匹配句窗半径


def load_rules(path=None):
    rf = pathlib.Path(path) if path else RULE_FILE
    data = json.loads(rf.read_text(encoding="utf-8"))
    by_surface = {}
    rule_rows = []
    for i, r in enumerate(data["rules"], start=1):
        rec = dict(r)
        rec["_rid"] = i
        rec["_re"] = re.compile(rec["pattern"])
        by_surface.setdefault(rec["surface"], []).append(rec)
        rule_rows.append((rec["rule_key"], rec["surface"], rec["reading"],
                          rec["reading_type"], rec["pattern"], rec.get("priority", 50),
                          rec["authority"], rec["source_ref"], rec.get("note", "")))
    for v in by_surface.values():
        v.sort(key=lambda x: -x.get("priority", 50))
    return by_surface, rule_rows, hashlib.sha256(
        rf.read_bytes()).hexdigest()


def load_reading_count(con):
    """surface -> 合法音项数（判定是否多音字）"""
    cur = con.cursor()
    cur.execute("SELECT surface, COUNT(DISTINCT reading) FROM pinyin_lexicon GROUP BY surface")
    return {s: c for s, c in cur.fetchall()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--build-id", default="")
    ap.add_argument("--no-db", action="store_true")
    ap.add_argument("--shard-limit", type=int, default=0, help="仅落前 N 章分片")
    ap.add_argument("--rule-file", default="", help="规则库路径（默认 L05_rules_v1.json）")
    ap.add_argument("--engine", default="", help="引擎标识，写入分片与 pinyin_build")
    ap.add_argument("--default-assert", choices=("assert", "keep"), default="assert",
                    help="defaultAssert 型规则命中时：assert=升为已确定(旧行为)；"
                         "keep=保持存疑并附建议音(符合 D5-b 禁伪精确)")
    args = ap.parse_args()

    from pypinyin import pinyin, Style

    build_id = args.build_id or time.strftime("b%Y%m%d_%H%M%S") + "_L05rule_v1"
    engine = args.engine or "L0.5-rule-v1"
    by_surface, rule_rows, rule_hash = load_rules(args.rule_file or None)

    # 繁简归一（耦合契约三：字形联立标注）—— 语料多为繁体，规则库为简体，
    # 逐字 1:1 转换后匹配，保证 offset 不错位；输出读音仍按原字。
    try:
        from opencc import OpenCC
        _cc = OpenCC("t2s")
    except Exception:
        _cc = None
    _t2s = {}

    def t2s(ch):
        c = _t2s.get(ch)
        if c is None:
            if _cc is None:
                c = ch
            else:
                try:
                    r = _cc.convert(ch)
                    c = r if len(r) == 1 else ch
                except Exception:
                    c = ch
            _t2s[ch] = c
        return c

    con = sqlite3.connect(str(DB))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=OFF")
    cur = con.cursor()

    # 规则库入表
    cur.execute("DELETE FROM pinyin_rule")
    cur.executemany(
        "INSERT OR REPLACE INTO pinyin_rule(rule_key,surface,reading,reading_type,pattern,"
        "priority,authority,source_ref,note) VALUES (?,?,?,?,?,?,?,?,?)", rule_rows)
    con.commit()

    rc = load_reading_count(con)

    # 语料
    sql = ("SELECT id, work_id, COALESCE(clean_text, text) FROM chapters "
           "WHERE COALESCE(clean_text,text) IS NOT NULL ORDER BY id")
    if args.limit:
        sql += f" LIMIT {args.limit} OFFSET {args.offset}"
    chapters = cur.execute(sql).fetchall()
    corpus_hash = hashlib.sha256()
    for cid, wid, txt in chapters:
        corpus_hash.update(f"{cid}:{len(txt or '')}\n".encode("utf-8"))

    shard_dir = SHARD_ROOT / build_id
    db_rows = []
    st = Counter()
    rule_hit = Counter()
    uncertain_char = Counter()
    t0 = time.time()
    n_char_total = 0

    # 单字基线音表：优先取带声调音、关闭词组模式 —— pypinyin 词典里文言高频字
    # （子/也/之/乎）首音常被现代口语排成轻声（子→zi），会破坏字级粒度契约（D4-b）。
    TONE_RE = re.compile(r"[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜńňǹḿ]")
    base_map = {}
    for s, r in con.execute(
            "SELECT surface, reading FROM pinyin_lexicon ORDER BY surface, rank"):
        if s in base_map or not r:
            continue
        if TONE_RE.search(r):
            base_map[s] = r
    for s, r in con.execute(
            "SELECT surface, reading FROM pinyin_lexicon ORDER BY surface, rank"):
        if s not in base_map and r:
            base_map[s] = r
    missing = 0
    for _cid, _wid, _txt in chapters:
        for ch in set(CJK_RE.findall(_txt or "")):
            if ch in base_map:
                continue
            rr = pinyin(ch, style=Style.TONE, heteronym=True,
                        errors=lambda x: [[""]])
            flat = rr[0] if rr else []
            cand = [x for x in flat if x and TONE_RE.search(x)]
            base_map[ch] = cand[0] if cand else (flat[0] if flat else "")
            missing += 1
    print(f"  单字音表：{len(base_map)} 字（词典外补录 {missing}）", flush=True)

    for idx, (cid, wid, text) in enumerate(chapters, 1):
        raw = text if text is not None else ""
        offsets, readings, states, metas, confs = [], [], [], {}, []
        simp = [t2s(ch) for ch in raw]
        for i, ch in enumerate(raw):
            if not CJK_RE.match(ch):
                continue
            base = base_map.get(ch, "")
            sc = simp[i]
            rd, state_code, conf, rtype, auth, rid = base, "a", 0.99, "normal", "pypinyin-default", None
            n_read = max(rc.get(ch, 1), rc.get(sc, 1))
            if n_read > 1:
                state_code, conf = "a", 0.80
                if sc in HIGH_RISK:
                    # 高危字先置存疑，待规则层确有命中再升为 asserted/variant
                    state_code, conf = "u", 0.45
            # 规则层（以简体字形匹配）
            cands = by_surface.get(sc)
            if cands:
                lo, hi = max(0, i - WINDOW), min(len(raw), i + WINDOW + 1)
                win = "".join(simp[lo:hi])
                center = i - lo
                best = None
                for rc_ in cands:
                    ms = list(rc_["_re"].finditer(win))
                    if not ms:
                        continue
                    if rc_.get("position_check") == "center":
                        # 锚定目标字位：遍历窗口内全部匹配，任一覆盖 center 方采纳
                        if not any(m.start() <= center < m.end() for m in ms):
                            continue
                    elif not any(sc in m.group(0) for m in ms):
                        continue
                    if best is None or rc_.get("priority", 50) > best.get("priority", 50):
                        best = rc_
                if best is not None:
                    rid = best["_rid"]
                    rd = best["reading"]
                    rtype = best["reading_type"]
                    auth = best["authority"]
                    rule_hit[best["rule_key"]] += 1
                    if rtype == "defaultAssert" and args.default_assert == "keep":
                        # 语料主导音非音韵学证据：保持存疑，仅附建议音供 L4 队列采纳
                        state_code, conf = "u", 0.60
                        metas[len(offsets)] = [rtype, rid, auth, [rd, base]]
                    elif best["rule_key"] in VARIANT_KEYS:
                        state_code, conf = "v", 0.70
                        metas[len(offsets)] = [rtype, rid, auth, [rd, base]]
                    else:
                        state_code, conf = "a", 0.88
                        metas[len(offsets)] = [rtype, rid, auth, None]
            if state_code == "u":
                uncertain_char[ch] += 1
            offsets.append(i)
            confs.append(conf)
            readings.append(rd or "")
            states.append(state_code)
            st[state_code] += 1
            n_char_total += 1

        # 分片（紧凑结构：只存汉字位，前端按 offset 对齐）
        if not args.shard_limit or idx <= args.shard_limit:
            d = shard_dir / str(wid)
            d.mkdir(parents=True, exist_ok=True)
            shard = {
                "chapter_id": cid, "work_id": wid, "build_id": build_id,
                "engine": engine, "len": len(raw),
                "pos": offsets, "py": readings, "st": "".join(states),
                "meta": metas,
            }
            (d / f"{cid}.json").write_text(
                json.dumps(shard, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8")

        # 落库：只存 "需人审/需举证" 的子集 —— uncertain / variant / 规则命中
        # 全量读音在分片 JSON，DB 保持为审核队列（L4 工作台）而非镜像
        if not args.no_db:
            for k, off in enumerate(offsets):
                m = metas.get(k)
                if states[k] == "a" and m is None:
                    continue
                db_rows.append((
                    cid, off, raw[off], readings[k],
                    json.dumps(m[3], ensure_ascii=False) if m and m[3] else None,
                    "asserted" if states[k] == "a" else ("variant" if states[k] == "v" else "uncertain"),
                    confs[k],
                    m[0] if m else "normal",
                    "modern",
                    m[2] if m else ("pypinyin-default" if states[k] != "u" else "none"),
                    m[1] if m else None,
                    build_id,
                ))
            if len(db_rows) >= 20000:
                cur.executemany(
                    "INSERT OR REPLACE INTO chapter_pinyin(chapter_id,char_offset,surface,reading,"
                    "reading_alt,state,confidence,reading_type,layer,authority,rule_id,build_id) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", db_rows)
                con.commit()
                db_rows = []

        if idx % 500 == 0:
            el = time.time() - t0
            print(f"  [{idx}/{len(chapters)}] {n_char_total} 字 {el:.0f}s "
                  f"({n_char_total/max(el,1):.0f} 字/秒)", flush=True)

    if db_rows:
        cur.executemany(
            "INSERT OR REPLACE INTO chapter_pinyin(chapter_id,char_offset,surface,reading,"
            "reading_alt,state,confidence,reading_type,layer,authority,rule_id,build_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", db_rows)
        con.commit()

    total = sum(st.values()) or 1
    cfg = {"engine": engine, "window": WINDOW, "limit": args.limit,
           "db_write": not args.no_db, "shard_write": args.shard_limit or "all"}
    stats = {
        "build_id": build_id, "chapters": len(chapters), "han_chars": n_char_total,
        "state_counts": dict(st),
        "state_ratio": {k: round(v / total, 5) for k, v in st.items()},
        "rule_hits_total": sum(rule_hit.values()),
        "rule_hits_top": dict(rule_hit.most_common(30)),
        "uncertain_top": dict(uncertain_char.most_common(30)),
        "rule_hash": rule_hash, "corpus_hash": corpus_hash.hexdigest(),
        "config": cfg, "elapsed_s": round(time.time() - t0, 1),
        "chars_per_s": round(n_char_total / max(time.time() - t0, 1), 1),
    }
    cur.execute(
        "INSERT OR REPLACE INTO pinyin_build(build_id,built_at,engine,model_hash,lexicon_hash,"
        "rule_hash,corpus_hash,config_json,stats_json,notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (build_id, time.strftime("%Y-%m-%d %H:%M:%S"), engine, None,
         "see lexicon_stats.json", rule_hash, corpus_hash.hexdigest(),
         json.dumps(cfg, ensure_ascii=False), json.dumps(stats, ensure_ascii=False),
         "L0 基线 + L0.5 规则层；多音字默读音标 pypinyin-default，待 L1 受限分类接管"))
    con.commit()
    con.close()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    tag = f"{args.offset:05d}_{args.limit or 'all'}"
    rp = REPORT_DIR / f"pinyin_stats_{build_id}_{tag}.json"
    rp.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: stats[k] for k in
                      ("build_id", "chapters", "han_chars", "state_counts",
                       "state_ratio", "rule_hits_total", "chars_per_s")},
                     ensure_ascii=False, indent=2))
    print(f"[OK] 报告：{rp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
