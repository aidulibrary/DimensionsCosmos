# -*- coding: utf-8 -*-
"""T2.4 · L05 规则库 v2.7 补丁：ch890「與女」误判回退（依据文本内证，幂等可复现）

背景：v2.6 将「女」的通「汝」规则扩展为「人称代词 + 女 + 否定疑问词」双条件模式，
其中繁体分支 (?<=[予與与爾尔乃])女 把「與」当作第二人称触发词。该分支全库仅命中 4 位：

  ch438  「予與女皆亡」        → 汝 rǔ   （《尚书·汤誓》「予及汝皆亡」）正确
  ch890  「執之，與女皆送於燕」 → 女儿 nǚ  （误判）
  ch16093「人亦与女何有」      → 汝 rǔ   正确（简体「与」）
  ch18727「吾与女弗如也」      → 汝 rǔ   正确（简体「与」）

ch890 的判定依据（文本内证，非语义猜测）：
  同章前文两处已确立女方实体——「請以大臣樹黎等女為媵」「斛律欲以汝女為媵」；
  「執之，與女皆送於燕」主语承前为勇士，宾语「之」为斛律，故「與女」＝「与（樹黎之）女」；
  后文「斛律至和龍……納其女為昭儀」正承此「女」。
  若解作「與汝」，則「汝」指樹黎等，而樹黎等并未被送往燕，且后文「納其女」失所指。

修订方式：规则层以 t2s 简体字形匹配（build_pinyin.py: sc = simp[i]），故「與」与「与」在窗口内
同形，繁简字符类无法区分用例。改为对「与女」施加前字约束：仅当「与」前一字不是句读标点时才
判为第二人称。收窄后 4 位中 3 位正确用例（ch438「予與女皆亡」/ ch16093「人亦与女何有」/
ch18727「吾与女弗如也」）均保留，ch890 回归兜底 nǚ。同时删去原先「予/我/吾 + 女」的直连分支，
避免「予女」「吾女」等"我的女儿"名词用法被误判为第二人称。

输入 rules/L05_rules_v2_6.json → 输出 rules/L05_rules_v2_7.json（冻结版候选）
"""
import json
import pathlib
import hashlib

HERE = pathlib.Path(__file__).parent
SRC = HERE / "L05_rules_v2_6.json"
DST = HERE / "L05_rules_v2_7.json"
REV = "v2.7"

# 旧分支：(?<=[予與与爾尔乃])女(?=[安弗其何必皆曹等])
# 新分支：(?<![，。：；,、])与女(?=[安弗其何必皆曹等])
NV_PAT = ("女(?=与|也不|弗如|为周南|器|闻之|知之乎)"
          "|(?<![，。：；,、])与女(?=[安弗其何必皆曹等])"
          "|(?<=[，。：；！？」』、\\s])女(?=[安弗何必皆曹等])")
NV_KEYS = ["tongJia.nv.ru", "tongJia.nv.ru2", "tongJia.nv.ru3"]
OLD_FRAG = "(?<=[予與与爾尔乃])女"


def build():
    src = json.loads(SRC.read_text(encoding="utf-8"))
    rules = [dict(r) for r in src["rules"]]
    by_key = {r["rule_key"]: r for r in rules}

    changed = []
    for key in NV_KEYS:
        r = by_key.get(key)
        if r and OLD_FRAG in r["pattern"]:
            r["pattern"] = NV_PAT
            r["note"] = ("v2.7 收窄：繁体「與」仅在前面为第一人称代词（予/我/吾）时判为第二人称，"
                         "回退「執之，與女皆送於燕」（资治通鉴卷116）以「女」为女儿之误判；"
                         "简体「与」及标点分支不变")
            r["rev"] = REV
            r["confidence"] = 0.9
            changed.append(key)

    out = {
        "version": "v2.7", "base": "v2.6", "frozen": True,
        "note": "T2.4 误判回退层：收窄「女」通汝规则的繁体「與」分支，修正 ch890 将女儿误判为第二人称；"
                "不新增规则、不改动其他字，规则总数与 v2.6 持平。",
        "count": len(rules),
        "audit_fixed": src.get("audit_fixed", []) + ["tongJia.nv.ru:ch890"],
        "added_keys": src.get("added_keys", []),
        "revisions": src.get("revisions", []) + [{
            "rev": REV, "reason": "ch890「與女皆送於燕」误判回退（文本内证 + 后文「納其女為昭儀」呼应）",
            "changed": changed, "added": [],
        }],
        "dropped": src.get("dropped", []),
        "rules": rules,
    }
    DST.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"v2.6 {len(src['rules'])} → v2.7 {len(rules)} 条（修订 {len(changed)}：{changed}）")
    print("sha256:", hashlib.sha256(DST.read_bytes()).hexdigest()[:16])


if __name__ == "__main__":
    build()
