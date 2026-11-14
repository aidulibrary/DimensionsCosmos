# -*- coding: utf-8 -*-
"""T2.3 · L05 规则库 v2.4 补丁：终轮收敛层（幂等可复现）

v2.7 抽检 166 位实测：defaultAssert 组 86.5%、规则命中组 97.5%、加权综合 ≈97.0%。
剩余 13% 错例高度集中于 6 组同形歧义（传 zhuàn/chuán、乐 yuè/lè、将 jiāng/jiàng、
少 shǎo/shào、好 hǎo/hào、恶 è/wù、女 nǚ/rǔ）。本层只收「词形可判」的部分，
语义/句法级歧义一律不动，留给 T2.4 判别模型 —— 避免伪精确。

输入 rules/L05_rules_v2_3.json → 输出 rules/L05_rules_v2_4.json（冻结版候选）
"""
import json
import pathlib
import hashlib

HERE = pathlib.Path(__file__).parent
SRC = HERE / "L05_rules_v2_3.json"
DST = HERE / "L05_rules_v2_4.json"
AUTH = "zhuben"

ADD = [
    # 传 zhuàn：经传引述体
    ("poDu.zhuan.yinju", "传", "zhuàn", "poDu", 92,
     "传(?=称|曰|云|载|赞|论|疏)|(?<=[羊梁左])传",
     "《汉书》『传曰』『传称』皆引经传，去声；公羊传、谷梁传、左传同",
     "传曰/传称/传载 读 zhuàn"),
    # 乐 yuè：乐名与乐官体系（史书乐志高频）
    ("poDu.yue.music3", "乐", "yuè", "poDu", 92,
     "(?:雅|颂|風|风|韶|濩|武|庙|廟|郊|宫|宮|房中)乐|乐(?=章|正|器|工|府|律|官|舞|曲|记|記|经|經|师|師|悬|縣|议|議|职|職|调|調)|大司乐|大司樂",
     "《宋史·乐志》乐名（雅乐、郊乐、乐章、乐职、大司乐）皆读 yuè",
     "乐名/乐官体系读 yuè"),
    # 少 shào
    ("poDu.shao.changshao", "少", "shào", "poDu", 86,
     "(?<=[长長])少",
     "『长少』即长幼，少读去声", "长少（长幼）读 shào"),
    # 好 hào
    ("poDu.hao.like2", "好", "hào", "poDu", 86,
     "好(?=养|養|歌|吟|唱|诗|詩|酒|猎|獵|游|遊|施|色|货|貨)",
     "《汉书》『好养豕』『好歌吟』，爱好义读去声", "好养/好歌/好诗酒 读 hào"),
    # 将 jiàng：郎将/骑郎将
    ("poDu.jiang.langjiang", "将", "jiàng", "poDu", 90,
     "(?:郎|騎|骑|隊|队|軍|军|府)将(?!军)|(?<=[郎])将(?![军軍])",
     "《汉书·百官公卿表》郎将、骑郎将为官名，去声", "郎将/骑郎将 读 jiàng"),
    # 相 xiàng：相位/相印/相权
    ("poDu.xiang.xiangwei", "相", "xiàng", "poDu", 86,
     "相(?=位|印|权|權|业|業|府|门|門)",
     "『相位』『相印』『相权』指宰相之职，去声", "相位/相印/相权 读 xiàng"),
    # 女 → 汝（第二人称）
    ("tongJia.nv.ru", "女", "rǔ", "tongJia", 82,
     "女(?=弗|何为|何為|安在|知之乎)",
     "《论语·雍也》『女弗能救与』，女通汝，读 rǔ", "通『汝』读 rǔ"),
    # 恶 wù：恶+代词宾语（厌恶某人）
    ("poDu.wu.hate2", "恶", "wù", "poDu", 84,
     "恶(?=臣之|其见|其聞|其闻|人之|此[言事])",
     "《战国策》『常恶臣之见王』，厌恶义读 wù", "恶+之/其 结构读 wù"),
]

SHRINK = {
    # 乐 旧规则被 music3 覆盖，保留但降噪（去掉易误判的「曲」类单字前缀）
    "poDu.yue.music": (
        "乐(?=章|正|器|工|府|律|官|舞|记|经|师|悬)|(?:礼|诗|雅|燕|韶)乐",
        "v2.4 交由 poDu.yue.music3 统一处理，本规则保留为低优先兜底",
    ),
}


def build():
    src = json.loads(SRC.read_text(encoding="utf-8"))
    rules = [dict(r) for r in src["rules"]]
    by_key = {r["rule_key"]: r for r in rules}

    changed = []
    for key, (pat, note) in SHRINK.items():
        r = by_key.get(key)
        if r and r["pattern"] != pat:
            r["pattern"] = pat
            r["note"] = (r.get("note", "") + " | " + note).strip(" |")
            r["rev"] = "v2.4"
            changed.append(key)

    added = 0
    for key, surf, rd, rt, pri, pat, sref, note in ADD:
        if key in by_key:
            continue
        rules.append({
            "rule_key": key, "surface": surf, "reading": rd, "reading_type": rt,
            "pattern": pat, "priority": pri, "authority": AUTH, "source_ref": sref,
            "note": note, "confidence": 0.90, "tier": "core",
            "position_check": "center", "rev": "v2.4",
        })
        added += 1

    out = {
        "version": "v2.4", "base": "v2.3", "frozen": True,
        "note": "T2.3 终轮收敛层（冻结版）：补齐 传zhuàn/乐yuè/少shào/好hào/将jiàng/相xiàng/女rǔ/恶wù "
                "8 组同形歧义的词形可判部分。语义级歧义不入本层，移交 T2.4 判别模型。",
        "count": len(rules), "audit_fixed": src.get("audit_fixed", []) + changed,
        "added_keys": [a[0] for a in ADD],
        "revisions": src.get("revisions", []), "dropped": src.get("dropped", []),
        "rules": rules,
    }
    DST.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"v2.3 {len(src['rules'])} → v2.4 {len(rules)} 条（新增 {added}，修订 {len(changed)}）")
    print("sha256:", hashlib.sha256(DST.read_bytes()).hexdigest()[:16])


if __name__ == "__main__":
    build()
