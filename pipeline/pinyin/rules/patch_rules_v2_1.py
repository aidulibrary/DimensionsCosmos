# -*- coding: utf-8 -*-
"""L05_rules_v2 -> v2.1 修订层

抽检（asserted 45 / variant 20 / defaultAssert 40）暴露的核心缺陷：
  1) tongJia「知->zhì」以「知(?=也|之)」匹配，几乎吃掉全部文言「知之/知也」→ variant 误标率约 65%
  2) poDu「王->wàng」含「王(?=之)」，「王之+名词」结构被误判为动词王天下
  3) poDu「为->wèi」介词规则含「为(?=之|国|民|人|天下)」，「为天下父」「为御史大夫」类判断句被误判
  4) 另有一批「单字+单字前瞻」的 tongJia 规则（说/要/归/陈/共/生）在有歧义语境直接给错音

本层只做"收窄"，不新增规则，全部改动留痕可审计（D7-b 可复现）。
"""
import json, pathlib

HERE = pathlib.Path(__file__).parent
SRC = HERE / "L05_rules_v2.json"
DST = HERE / "L05_rules_v2_1.json"

# rule_key -> 新 pattern；None 表示删除该规则
PATCH = {
    # --- tongJia 知 -> 智：改为白名单搭配 ---
    "tongJia.zhi.zhi":
        r"(?:真知|良知|才知|明智|知虑|知能|知谋|知巧|知慧)",
    "tongJia.zhi.zhizhe":
        r"知(?=者乐|者不惑|者动|者静)|(?:真|良|才|明)知",
    # --- tongJia 说 -> 悦：剔除「而说」类游说语境 ---
    "tongJia.shuo.yue":  r"(?:不亦|中心|可|学而)说(?:乎|之|焉)",
    "tongJia.shuo.yue2": r"(?:不亦|中心|可|学而)说(?:乎|之|焉|也|矣)",
    "tongJia.shuo.yue3": r"(?:不亦|中心|可|学而)说(?:乎|之|焉|也|矣)",
    # --- 其余「单字+单字前瞻」收窄 ---
    "tongJia.yao.invite":  r"要(?=君|我君)|要(?:之)有",
    "tongJia.gui.gift":    r"归(?=孔子)",
    "tongJia.zhen.array":  r"(?:陈陈相因)|陈(?=固)",
    "tongJia.sheng.nature": r"生(?:之谓性)",
    "tongJia.gong.supply": None,          # 与 gongyang/gongfeng 重复，且含「共之」
    # --- poDu 王 -> wàng：去掉「王之/王此/王其」 ---
    "poDu.wang.verb_tianxia": r"王(?=天下|诸侯|者)|(?:不王)",
    # --- poDu 为 -> wèi：介词义只认代词宾语与「何为」 ---
    "poDu.wei.jieci": r"为(?=我|吾|尔|汝|己|已)|(?:何|曷|奚|胡)为",
    "poDu.wei.weiwo": r"为(?=我|吾|尔|汝|己|已|之)",
    # --- 补「牙将/副将/主将」等常见将职 ---
    "lex.jiang.wujiang":
        r"(?:中郎|虎贲中郎|五官中郎|羽林中郎|射声|越骑|屯骑|步兵|长水|胡骑|材官|楼船)将"
        r"|(?:大|名|老|猛|裨|偏|诸|军|上|下|列|部|主|副|行营|牙)将(?:军|士|帅|兵|校|佐|吏)",
    # --- 知 -> zhì(智)：去掉「小知恪」「其知人」类误吃 ---
    "poDu.zhi.wise": r"(?:大|小)知(?=而|不|者|也)|其知(?:虑|能|谋|也)",
    # --- 乐 -> yào：地名「平乐水」被「乐(?=水)」误吃 ---
    "poDu.le.yao":   r"(?:知者|仁者|智者)乐(?:山|水)?|乐(?:山|水)(?:而|者|也)",
    "poDu.le.yaoshan": r"(?:知者|仁者|智者)乐(?:山|水)?|乐(?:山|水)(?:而|者|也)",
    "poDu.le.yao2":  r"(?:知者|仁者|智者)乐(?:山|水)?|乐(?:山|水)(?:而|者|也)",
}

raw = json.loads(SRC.read_text(encoding="utf-8"))
rules, dropped, changed = [], [], []
for r in raw["rules"]:
    k = r["rule_key"]
    if k in PATCH:
        if PATCH[k] is None:
            dropped.append(k)
            continue
        if r["pattern"] != PATCH[k]:
            changed.append({"rule_key": k, "old": r["pattern"], "new": PATCH[k]})
            r["pattern"] = PATCH[k]
        r["rev"] = "v2.1"
    rules.append(r)

out = {
    "version": "v2.1",
    "base": raw.get("version", "v2"),
    "note": "收窄误标缺陷（抽检驱动的修订层，仅改 pattern / 删重）",
    "count": len(rules),
    "revisions": changed,
    "dropped": dropped,
    "rules": rules,
}
DST.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("规则数:", len(rules), "修订:", len(changed), "删除:", len(dropped))
for c in changed:
    print(" *", c["rule_key"], "\n   old:", c["old"], "\n   new:", c["new"])
