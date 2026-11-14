# -*- coding: utf-8 -*-
"""T2.3 · L05 规则库 v2.3 补丁：存量规则精度审计修订层（幂等可复现）

v2.2 只做"加规则"，实测 defaultAssert 组精度仍不足。v2.3 转向**存量规则审计**，
修复 4 条系统性错标规则（单规则命中量大、错误率过半），并补齐抽检暴露的窄词形。

审计结论（v2.6 全库实测命中量）：
  rule#11  poDu.jian.xian      4351 位  `(?:不|复|始|乃|而)见` 判 xiàn ——「不见」实为 jiàn，污染率 >85%
  rule#18  tongJia.di.ti      2076 位  `弟(?=子)` 判 tì ——「弟子」实为 dì，污染率 >80%
  rule#3   poDu.wang.tianxia  2482 位  `王(?=者)` 判 wàng ——「王者」实为 wáng，污染率 >40%
  rule#15  poDu.shi.si        2617 位  `食(?=之|人|以)` 判 sì ——「日有食之」「食人」实为 shí，污染率 >30%

输入 rules/L05_rules_v2_2.json → 输出 rules/L05_rules_v2_3.json
"""
import json
import pathlib
import hashlib

HERE = pathlib.Path(__file__).parent
SRC = HERE / "L05_rules_v2_2.json"
DST = HERE / "L05_rules_v2_3.json"
AUTH = "zhuben"

# rule_key -> (new_pattern, audit_note)
SHRINK = {
    "poDu.jian.xian": (
        "图穷匕见|见(?=龙|其睫)|(?<=[昼夜])见",
        "审计收窄：删除 (不|复|始|乃|而)见（实为 jiàn）；保留图穷匕见/见龙/昼见夜见（出现义 xiàn）",
    ),
    "tongJia.di.ti": (
        "(?:孝|悌|恺)弟|弟(?=顺)",
        "审计收窄：删除 弟(?=子)（弟子读 dì）；保留孝弟/弟顺（通悌 tì）",
    ),
    "poDu.wang.verb_tianxia": (
        "王(?=天下|诸侯)|(?:不王)",
        "审计收窄：删除 王(?=者)（王者为名词 wáng）；保留王天下（动词 wàng）",
    ),
    "poDu.shi.si": (
        "食(?=母|畜)|(?<=[而爲为])食之",
        "审计收窄：删除 食(?=人|马|以)（食人多指吃人 shí）；仅留 食母/食畜 及 而食之（使动）",
    ),
    "poDu.wei.weiwo": (
        "为(?=我|吾|尔|汝|己|已)",
        "审计收窄：删除 为(?=之)（为之多作 wéi）；为之交由 poDu.wei.dongci 判 wéi",
    ),
    "poDu.wu.hate": (
        "(?:所|不|好)恶|恶(?=之|其|湿|居|旨)",
        "审计收窄：删除 恶(?=衣)（恶衣恶食为 è）；其余保留",
    ),
    "poDu.hao.like": (
        "好(?=学|兵|勇|利|名|色|战|胜|奇|事者|谋|施|仁|义|武|弄|货)",
        "审计收窄：删除 好(?=生)（好生看管读 hǎo）",
    ),
}

# 抽检暴露的补充窄词形（key, surface, reading, rtype, pri, pattern, src, note）
ADD = [
    ("poDu.shi.rishi", "食", "shí", "poDu", 96,
     "日食|(?<=[日])食(?=之)|(?<=[有])食(?=之)",
     "《春秋》『日有食之』即日食，读 shí；史书天文志高频句式",
     "日食读 shí（修正 poDu.shi.si 污染）"),
    ("poDu.zhuan.bookend", "传", "zhuàn", "poDu", 90,
     "传(?=[》」』])|传(?=[一二三四五六七八九十]+章)",
     "《隋书·经籍志》著录体例『《某某传》』，传体读去声", "书名末 传 读 zhuàn"),
    ("poDu.shao.junior2", "少", "shào", "poDu", 88,
     "少(?=帝|阳|阴|监|袭|庶|牢)",
     "少帝、少阳、少监、少庶子皆为 shào", "少帝/少阳/少监 读 shào"),
    ("poDu.yue.music2", "乐", "yuè", "poDu", 88,
     "乐(?=议|架|悬|县)|(?<=[架宫廷殿])乐",
     "《宋史·乐志》『宫架之乐』『乐议』，音乐义读 yuè", "宫架之乐/乐议 读 yuè"),
    ("poDu.xiang.buddha", "相", "xiàng", "poDu", 88,
     "(?<=[人我眾众壽寿者])相(?=[、，。；」』])",
     "《金刚经》『我相、人相、众生相、寿者相』，四相读 xiàng", "佛典四相读 xiàng"),
    ("poDu.wang.wuxing", "王", "wàng", "poDu", 90,
     "(?<=[火水木金土])王",
     "《素问》五行『夏则火王』，王通旺，读 wàng", "五行相王读 wàng"),
    ("poDu.jiang.shuci2", "将", "jiàng", "poDu", 86,
     "(?<=[一二三四五六七八九十百千萬万])将(?!军|兵|[來来去出入至行死亡戰战欲有無无自以命相])",
     "『二将大叫』『五将导』——数词直接修饰将领，去声", "数词+将 读 jiàng"),
    ("poDu.zhang.zhi", "长", "zhǎng", "poDu", 82,
     "(?<=[之])长(?=[，。；、」』])|(?<=[为為])长(?=[，。；、」』])",
     "『众列之长』『令史为长』——长＝长官，去声", "之长/为长 读 zhǎng"),
    ("poDu.shi.sishi", "食", "sì", "poDu", 84,
     "食(?=士|卒)",
     "《左传》『杀羊食士』，食士＝飨士，读 sì", "食士/食卒 读 sì"),
    ("poDu.jian.xian2", "见", "xiàn", "poDu", 92,
     "(?:昼|晝|夜|日|月)见(?=[，。；、])",
     "《汉书·天文志》『太白昼见』，见＝现，读 xiàn", "昼见/夜见 读 xiàn"),
]


def build():
    src = json.loads(SRC.read_text(encoding="utf-8"))
    rules = [dict(r) for r in src["rules"]]
    by_key = {r["rule_key"]: r for r in rules}

    changed = []
    for key, (pat, note) in SHRINK.items():
        r = by_key.get(key)
        if not r:
            print("  [WARN] 未找到", key)
            continue
        if r["pattern"] == pat:
            continue
        r["pattern"] = pat
        r["note"] = (r.get("note", "") + " | " + note).strip(" |")
        r["rev"] = "v2.3"
        changed.append(key)

    added = 0
    for key, surf, rd, rt, pri, pat, sref, note in ADD:
        if key in by_key:
            continue
        rules.append({
            "rule_key": key, "surface": surf, "reading": rd, "reading_type": rt,
            "pattern": pat, "priority": pri, "authority": AUTH, "source_ref": sref,
            "note": note, "confidence": 0.90, "tier": "core",
            "position_check": "center", "rev": "v2.3",
        })
        added += 1

    out = {
        "version": "v2.3", "base": "v2.2",
        "note": "T2.3 存量规则精度审计层：修复 4 条系统性错标规则（见xiàn/弟tì/王wàng/食sì），"
                "收窄 3 条过度泛化规则，补齐 10 条抽检暴露的窄词形",
        "count": len(rules),
        "audit_fixed": changed, "added_keys": [a[0] for a in ADD],
        "revisions": src.get("revisions", []), "dropped": src.get("dropped", []),
        "rules": rules,
    }
    DST.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"v2.2 {len(src['rules'])} 条 → v2.3 {len(rules)} 条")
    print("审计修订:", changed)
    print("新增:", added, "| sha256:", hashlib.sha256(DST.read_bytes()).hexdigest()[:16])


if __name__ == "__main__":
    build()
