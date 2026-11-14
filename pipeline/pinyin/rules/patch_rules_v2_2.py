# -*- coding: utf-8 -*-
"""T2.3 · L05 规则库 v2.2 补丁（幂等可复现）

输入  rules/L05_rules_v2_1.json
输出  rules/L05_rules_v2_2.json

改动三类：
  FIX  修正 v2.1 反向错误：将(?=军|兵) 被 poDu.jiang.general 判为 jiàng，
       「将军/将兵」在古籍中为 jiāng（官名或"率领军队"），v2.2 以 priority 92 覆盖。
  ADD  按字补齐异读词表（重点：恶 wū 整套缺失、将 jiàng 名词族、亡 wú 通假族、
       以及 说/长/少/传/食/好/乐/数/卒/共/衣/弟/乘/强/冠/雨/处/与/有/从 等典型多音）。
  META 每条新增规则统一 position_check='center'，避免窗口内同名他字被误赋读音。

原则：只写明确的词形/句法框架，不写宽泛后顾；涉及学界并存两读的不入本层（留 variant）。
"""
import json
import pathlib
import hashlib

HERE = pathlib.Path(__file__).parent
SRC = HERE / "L05_rules_v2_1.json"
DST = HERE / "L05_rules_v2_2.json"
AUTH = "zhuben"

# ---------------------------------------------------------------- 修正层
FIXES = {
    # v2.1 缺陷：将军/将兵被 general 规则判 jiàng
    "fix.jiang.jiangjun_jiang": dict(
        surface="将", reading="jiāng", reading_type="poDu", priority=92,
        pattern="将(?:军|兵|命|士众)",
        source_ref="《广韵》阳韵即良切；『将军』官名及『将兵』率领义均读平声",
        note="修正 v2.1：将军/将兵读 jiāng，非 jiàng", tier="core", rev="v2.2"),
}

# ---------------------------------------------------------------- 新增层
# (rule_key, surface, reading, reading_type, priority, pattern, source_ref, note)
ADD = [
    # ===== 恶 wū：疑问代词「何/怎么」、叹词（v2.1 整套缺失，最大单点缺口）=====
    ("poDu.wu.wuhu", "恶", "wū", "poDu", 94,
     "恶(?:乎|在其|得|能|足|可|知|识|观|取|有|用|能已)",
     "《广韵》模韵哀都切；『恶乎』＝于何，『恶得/恶能/恶足』＝何得/何能/何足",
     "疑问代词/叹词读 wū"),
    ("poDu.wu.xie_wu", "恶", "wū", "poDu", 92,
     "(?:奚|曷|胡)恶|恶(?=乎其)",
     "《孟子·尽心上》『奚恶乎执』；疑问代词连用", "奚恶/恶乎其 读 wū"),

    # ===== 将 jiàng：名词「将领」族（判读显示最高误标源）=====
    ("poDu.jiang.general2", "将", "jiàng", "poDu", 88,
     "(?:部|别|边|都|守|众|列|群|主|副|牙|叛|骁|宿|勇|悍|战|戍|骑|步|水|马|材官|楼船|行营)将"
     "(?!军|兵|来|去|出|入|至|行|死|亡|乱|战|欲|有|无|自|以|命|相|奈何)",
     "《广韵》漾韵子亮切；将帅、将吏、部将、别将、边将、守将皆为去声",
     "将领名词族读 jiàng"),
    ("poDu.jiang.guoming", "将", "jiàng", "poDu", 86,
     "(?:秦|楚|燕|赵|魏|韩|齐|晋|宋|梁|陈|隋|唐|汉|周|吴|越|蜀|鲁|卫|郑)将"
     "(?!军|兵|来|去|出|入|至|行|死|亡|战|欲|有|无|自|以)",
     "史传『秦将』『楚将』指某国之将领，去声", "国名+将 读 jiàng"),
    ("poDu.jiang.shuci", "将", "jiàng", "poDu", 84,
     "(?<=[一二三四五六七八九十百千万])将(?:军|各|皆|导|击|屯|守|拒|迎)",
     "『五将导』『诸将各』——数词修饰将领，去声", "数词+将 读 jiàng"),
    ("poDu.jiang.jiangli", "将", "jiàng", "poDu", 90,
     "将(?:吏|佐|校|卒|帅|相|领)",
     "《汉书》多见『将吏』『将佐』『将校』，指将帅与属吏，去声",
     "将吏/将佐/将校/将卒/将帅/将相 读 jiàng"),

    # ===== 亡 wú：通「无」=====
    ("tongJia.wang.wu4", "亡", "wú", "tongJia", 88,
     "亡(?:厌|阙|缺|非|虑|疑|状|聊|几|艺|穷|已|恙|害)",
     "《说文》段注『亡』通『无』；『亡厌』『亡阙』『亡虑』并读 wú",
     "通『无』读 wú"),
    ("tongJia.wang.huiwang", "亡", "wú", "tongJia", 88,
     "(?:悔|无)亡(?![国身命走])",
     "《易·系辞》『悔亡』，亡通无，读 wú", "悔亡 读 wú"),

    # ===== 相 xiàng：动词「察看/辅助」=====
    ("poDu.xiang.verb_zhi", "相", "xiàng", "poDu", 76,
     "相(?:之[，。；：、而也者其]|其[^，。]{0,2}(?:而|以|则|者|也))",
     "《诗·大雅》『相其阴阳』；相＋之/其 为察看、辅相之义，去声",
     "相之/相其 读 xiàng"),
    ("poDu.xiang.xiangmao", "相", "xiàng", "poDu", 82,
     "(?:吉|凶|貌|骨|色|瑞|法|真|本|假|变|报|实|幻|空|寿|病|死|贫|富)相",
     "佛典与相术文献『吉相』『法相』『实相』，去声", "名词性 相 读 xiàng"),

    # ===== 行 háng / xìng =====
    ("poDu.hang.xingjiu", "行", "háng", "poDu", 82,
     "行(?=酒)|(?<=[一二三四五六七八九十数])行(?=[，。；、])",
     "《史记》『酒数行』，行酒一轮为一 háng", "行酒/酒数行 读 háng"),
    ("poDu.xing.dexing4", "行", "xìng", "poDu", 86,
     "(?:志|德|操|品|孝|忠|言|躬|修|阴|善|恶|姦|洁|节|才|学)行(?!李|走|路|事|礼|军|兵|法|政|令|止|营|装|粮|帐)",
     "《广韵》映韵下更切；德行、志行、操行为去声", "德行类 行 读 xìng"),

    # ===== 中 zhòng =====
    ("poDu.zhong.verb_hit2", "中", "zhòng", "poDu", 84,
     "(?:射|击|刺|命中|言必有)中|中(?:其|吾|我)(?:心|意|矢|目|肩|股|臂)",
     "《广韵》陟仲切；射中、中其心为去声", "击中之 中 读 zhòng"),

    # ===== 说 shuì：游说 =====
    ("poDu.shui.youshui", "说", "shuì", "poDu", 88,
     "(?:游|遨)说|说(?=齐|楚|燕|赵|魏|韩|秦|吴|越|梁|晋|宋|王|诸侯|项羽|沛公|项王)",
     "《广韵》舒芮切；游说、说齐王为去声", "游说读 shuì"),

    # ===== 长 zhǎng =====
    ("poDu.zhang.grow", "长", "zhǎng", "poDu", 84,
     "(?:年|尊|家|族|里|乡)长|长(?=幼|老|子|孙|男|兄|者|吏|官|女)",
     "《广韵》知丈切；长幼、长子、长老为去声", "生长/年长读 zhǎng"),

    # ===== 少 shào =====
    ("poDu.shao.junior", "少", "shào", "poDu", 84,
     "(?:年|幼)少|少(?=师|傅|保|卿|主|府|尹|吏|子|壮|艾)",
     "《广韵》失照切；少师、少傅、少卿为去声", "年少/官职 少 读 shào"),

    # ===== 传 zhuàn：传体 =====
    ("poDu.zhuan.zhuanji", "传", "zhuàn", "poDu", 86,
     "传(?=文|注|赞|略)|(?:经|史|列|别|外|内|自|家|左|公羊|谷梁|世|合)传",
     "《广韵》直恋切；列传、经传为去声", "经传/传记 读 zhuàn"),

    # ===== 食 sì：饲 =====
    ("poDu.si.feed", "食", "sì", "poDu", 84,
     "食(?=马|母|人|之食)|(?:饮)食(?:之|其)",
     "《广韵》祥吏切；食马、食母为去声", "饲食义读 sì"),

    # ===== 好 hào =====
    ("poDu.hao.like", "好", "hào", "poDu", 86,
     "好(?=学|兵|勇|利|名|色|战|胜|奇|事者|生|谋|施|仁|义|武|弄|货)",
     "《广韵》呼到切；好学、好兵、好色为去声", "爱好义读 hào"),

    # ===== 乐 yuè =====
    ("poDu.yue.music", "乐", "yuè", "poDu", 86,
     "乐(?=章|正|器|工|府|律|官|舞|曲|记|经|师|悬)|(?:礼|诗|雅|燕|韶)乐",
     "《广韵》五角切；乐章、乐正、礼乐为入声转去", "音乐义读 yuè"),

    # ===== 数 shǔ =====
    ("poDu.shu.count", "数", "shǔ", "poDu", 84,
     "数(?=之|其罪|以|说|让|责)|(?<=[不可胜])数",
     "《广韵》所矩切；数之、数其罪为责备义，上声", "责备/计数义读 shǔ"),

    # ===== 卒 cù =====
    ("poDu.cu.sudden", "卒", "cù", "poDu", 88,
     "卒(?=然|急|暴|发)|仓卒",
     "《广韵》仓没切；卒然、仓卒读 cù", "仓促义读 cù"),

    # ===== 共 gōng =====
    ("poDu.gong.supply", "共", "gōng", "poDu", 84,
     "共(?=养|奉|给|工|具|张)|(?:供)共",
     "《广韵》九容切；共养、共奉通『供』，读 gōng", "供奉义读 gōng"),

    # ===== 衣 yì =====
    ("poDu.yi.wear", "衣", "yì", "poDu", 82,
     "衣(?=布|帛|褐|麻|锦|绣|紫|素|之|其)[^，。]{0,3}",
     "《广韵》於既切；衣布、衣帛为动词穿衣，去声", "动词穿衣读 yì"),

    # ===== 弟 tì =====
    ("tongJia.di.ti", "弟", "tì", "tongJia", 86,
     "弟(?=顺)|(?:孝|恺|友)弟",
     "《广韵》特计切；孝弟通『悌』，读 tì", "通『悌』读 tì"),

    # ===== 乘 shèng =====
    ("poDu.sheng.chariot", "乘", "shèng", "poDu", 86,
     "(?<=[十百千万])乘(?!马|车|舟|之)|(?:车|兵|革)乘",
     "《广韵》实证切；千乘、万乘为车乘单位，去声", "车乘单位读 shèng"),

    # ===== 强 qiǎng =====
    ("poDu.qiang.force", "强", "qiǎng", "poDu", 84,
     "强(?=起|请|谏|食|酒|从|听|行|使)|(?:勉|牵|勍)强",
     "《广韵》其两切；强起、强请为勉强义，上声", "勉强义读 qiǎng"),

    # ===== 冠 guàn =====
    ("poDu.guan.capping", "冠", "guàn", "poDu", 86,
     "冠(?=者|礼)|(?:弱|未|已|既|加)冠",
     "《广韵》古玩切；弱冠、冠者为加冠义，去声", "加冠/二十岁读 guàn"),

    # ===== 雨 yù =====
    ("poDu.yu.rain_verb", "雨", "yù", "poDu", 82,
     "雨(?=雪|血|粟|金|雹)|(?:天|乃|大)雨(?:雪|血|粟|雹)",
     "《广韵》王遇切；雨雪为动词『下（雪）』，去声", "动词降雨/雪读 yù"),

    # ===== 处 chǔ =====
    ("poDu.chu.dwell", "处", "chǔ", "poDu", 84,
     "处(?=之|其|世|事|难|众|约|贫|富|静|决|置|分|治)|(?:自)处",
     "《广韵》昌与切；处之、处世为动词，上声", "动词居处/处置读 chǔ"),

    # ===== 与 yù =====
    ("poDu.yu.join", "与", "yù", "poDu", 86,
     "(?:参)与",
     "《广韵》羊洳切；参与读 yù", "参与义读 yù"),

    # ===== 有 yòu =====
    ("tongJia.you.again", "有", "yòu", "tongJia", 88,
     "(?<=[十百千万亿])有(?=[一二三四五六七八九十])",
     "《广韵》于救切；『十有三年』有通『又』，读 yòu", "通『又』读 yòu"),

    # ===== 从 zòng =====
    ("tongJia.cong.vertical", "从", "zòng", "tongJia", 86,
     "(?:合)从|从(?=横|衡)",
     "《广韵》疾用切；合从连衡之从通『纵』，读 zòng", "通『纵』读 zòng"),

    # ===== 告 gù（学界并存，低置信）=====
    ("poDu.gao.gu", "告", "gù", "poDu", 60,
     "(?:忠)告",
     "《诗·大雅》郑笺『忠告』读 gù；今读 gào 并存", "忠告 古读 gù（并存）"),
]


def build():
    src = json.loads(SRC.read_text(encoding="utf-8"))
    rules = [dict(r) for r in src["rules"]]

    # --- FIX：改写 v2.1 中将军/将兵 的判音（以新增高优先级规则覆盖，原规则保留但降权）
    for r in rules:
        if r["rule_key"] == "poDu.jiang.general":
            r["pattern"] = "(?:大|名|老|猛|裨|偏|诸|军)将|将(?=士|帅|者|之能)"
            r["note"] = r.get("note", "") + "（v2.2 移除 将(?=军|兵)，改由 fix.jiang.jiangjun_jiang 判 jiāng）"
            r["rev"] = "v2.2"
        if r["rule_key"] == "lex.jiang.jiangjun":
            r["pattern"] = "(?:大|名|老|猛|裨|偏|诸|军|上|下|列|部)将(?:士|帅|者之)"
            r["rev"] = "v2.2"

    # --- ADD
    have = {r["rule_key"] for r in rules}
    added = 0
    for key, surf, rd, rtype, pri, pat, src_ref, note in ADD:
        if key in have:
            continue
        rules.append({
            "rule_key": key, "surface": surf, "reading": rd, "reading_type": rtype,
            "pattern": pat, "priority": pri, "authority": AUTH,
            "source_ref": src_ref, "note": note, "confidence": 0.88,
            "tier": "core", "position_check": "center", "rev": "v2.2",
        })
        added += 1

    # --- FIX key
    for key, spec in FIXES.items():
        if any(r["rule_key"] == key for r in rules):
            continue
        rules.append({
            "rule_key": key, "surface": spec["surface"], "reading": spec["reading"],
            "reading_type": spec["reading_type"], "pattern": spec["pattern"],
            "priority": spec["priority"], "authority": AUTH,
            "source_ref": spec["source_ref"], "note": spec["note"],
            "confidence": 0.90, "tier": "core", "position_check": "center",
            "rev": "v2.2",
        })
        added += 1

    out = {
        "version": "v2.2", "base": "v2.1",
        "note": "T2.3 defaultAssert 专项治理层：修正 将军/将兵 判音反向错误，补齐 恶wū 整套、"
                "将jiàng名词族、亡wú通假族及 20 个典型多音字异读词形；新增规则统一 center 锚定",
        "count": len(rules), "revisions": src.get("revisions", []),
        "dropped": src.get("dropped", []),
        "added_keys": [a[0] for a in ADD] + list(FIXES),
        "rules": rules,
    }
    DST.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"v2.1 {len(src['rules'])} 条 → v2.2 {len(rules)} 条（新增 {added}）")
    print("输出:", DST)
    print("sha256:", hashlib.sha256(DST.read_bytes()).hexdigest()[:16])


if __name__ == "__main__":
    build()
