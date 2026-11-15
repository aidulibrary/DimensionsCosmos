# -*- coding: utf-8 -*-
"""T2.4 · L05 规则库 v2.6 补丁：存疑校准层（依据人工抽样复核结论，幂等可复现）

来源：2026-11-15 注音存疑抽样复核（40 条抽样，5 条判为应改，主理人已确认同意）。
复核发现的真实缺口只有三类，均可由词形/句法位置确定性判定，不引入语义猜测：

1. 中 → zhòng：帝王名「中壬」「中𤳹」（《史记·殷本纪》「立外丙之弟中壬」「中𤳹作诰」），
   旧规则 df.zhong.zhong_default 负向表不含「壬」，被默认标 zhōng。
2. 与/與 → yú：句末疑问语气词（通「欤」）。旧规则 poDu.yu.yuqi / yuqi2 / lex.yu.yuqi3 均要求
   「与」前一字为 也/乎/矣/焉/欤，覆盖不到「师愈与？」「是谁之过与？」这类前字非虚词的句末用例；
   改为直接以「句末标点（？）」与「虚词后置」两个位置特征判定，召回由窄模板扩至全库 813 位。
3. 女 → rǔ：第二人称（通「汝」）。旧 tongJia.nv.ru/ru2/ru3 仅覆盖「女弗」「女何为」等 6 个固定后字；
   新增「人称代词/句读 + 女 + 否定疑问词」双条件模式（不含「亦」，实测「女亦」多指代前文女子），避开「男女无别」「妇女不育」「吾女何得」
   等名词用法（已用 2000 章抽样验证）。

输入 rules/L05_rules_v2_5.json → 输出 rules/L05_rules_v2_6.json（冻结版候选）
"""
import json
import pathlib
import hashlib

HERE = pathlib.Path(__file__).parent
SRC = HERE / "L05_rules_v2_5.json"
DST = HERE / "L05_rules_v2_6.json"
AUTH = "zhuben"
REV = "v2.6"

ADD = [
    # 中 zhòng：帝王名 中壬 / 中𤳹
    ("poDu.zhong.zhongren", "中", "zhòng", "poDu", 90,
     "中(?=[壬𤳹])",
     "《史记·殷本纪》「立外丙之弟中壬，是为帝中壬」「中𤳹作诰」，人名读去声",
     "中壬/中𤳹 读 zhòng（人名）"),
    # 与 yú：句末疑问语气词（通欤）
    ("poDu.yu.yuqi_end", "与", "yú", "poDu", 88,
     "[与與](?=[？?])|(?<=[乎哉也矣])[与與]",
     "《论语》「然则师愈与？」《汉书》「是谁之过与？」，句末与通欤，读 yú",
     "句末『与』通『欤』读 yú"),
]

# 修订：女 → rǔ 扩容（合并 ru/ru2/ru3 的窄后字表，新增双条件模式）
NV_PAT = ("女(?=与|也不|弗如|为周南|器|闻之|知之乎)"
          "|(?<=[予與与爾尔乃])女(?=[安弗其何必皆曹等])"
          "|(?<=[，。：；！？」』、\\s])女(?=[安弗何必皆曹等])")
NV_KEYS = ["tongJia.nv.ru", "tongJia.nv.ru2", "tongJia.nv.ru3"]


def build():
    src = json.loads(SRC.read_text(encoding="utf-8"))
    rules = [dict(r) for r in src["rules"]]
    by_key = {r["rule_key"]: r for r in rules}

    changed = []
    for key in NV_KEYS:
        r = by_key.get(key)
        if r and r["pattern"] != NV_PAT:
            r["pattern"] = NV_PAT
            r["priority"] = 88
            r["note"] = ("v2.6 增补：人称代词/句读 + 女 + 否定疑问词 双条件模式，"
                         "覆盖第二人称『汝』；已排除名词用法（男女/妇女/吾女）")
            r["rev"] = REV
            changed.append(key)

    added = 0
    for key, surf, rd, rt, pri, pat, sref, note in ADD:
        if key in by_key:
            continue
        rules.append({
            "rule_key": key, "surface": surf, "reading": rd, "reading_type": rt,
            "pattern": pat, "priority": pri, "authority": AUTH, "source_ref": sref,
            "note": note, "confidence": 0.90, "tier": "core",
            "position_check": "center", "rev": REV,
        })
        added += 1

    out = {
        "version": "v2.6", "base": "v2.5", "frozen": True,
        "note": "T2.4 存疑校准层：按 2026-11-15 人工抽样复核结论（40 抽 5 判应改）补三条确定性规则——"
                "中壬/中𤳹读 zhòng、句末与通欤读 yú、女作第二人称读 rǔ。语义级同形歧义仍不入本层。",
        "count": len(rules),
        "audit_fixed": src.get("audit_fixed", []) + changed,
        "added_keys": [a[0] for a in ADD],
        "revisions": src.get("revisions", []) + [{
            "rev": REV, "reason": "存疑抽样复核 5 条应改项落地",
            "changed": changed, "added": [a[0] for a in ADD],
        }],
        "dropped": src.get("dropped", []),
        "rules": rules,
    }
    DST.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"v2.5 {len(src['rules'])} → v2.6 {len(rules)} 条（新增 {added}，修订 {len(changed)}）")
    print("sha256:", hashlib.sha256(DST.read_bytes()).hexdigest()[:16])


if __name__ == "__main__":
    build()
