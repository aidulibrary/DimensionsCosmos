"""P0-5 引证式导读生成器：每段必带引文，入库前封闭校验。

与 pipeline/run_ai.py 的区别
----------------------------
run_ai.py 把整部书正文塞进提示词，请模型「解读」——输出是一篇散文，
模型在文末随手写几个引用，事后 migrate_citations.py 只能确定性回填，
宁可空着（12 篇里 11 篇 citations 为空）。
本脚本反过来：

1. 先由 refpack.py 抽一份**封闭候选池**（每块带块级 URN）；
2. 提示词只允许从池内引证，要求正文以 paragraphs 段落数组输出，
   每段必须带 ≥1 个池内 URN；
3. 生成后逐段校验（池内性、引文与所引块的字面支撑度、段落数、字段完备性）；
4. 校验不过 → 把错误清单回灌给模型修一次（repair）；仍不过 → **不入库**，
   落一份 rejected 记录便于人工复核。宁可不生成，也不产出无据导读。

用法：
    python pipeline/gen_guides_cited.py --book 论语 --method zhuxi --dry-run
    python pipeline/gen_guides_cited.py --book 论语 --method zhuxi --force
    python pipeline/gen_guides_cited.py --book 论语 --method zhuxi,feynman --force
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

from ai_client import chat, get_last_model  # noqa: E402
from db import connect  # noqa: E402
from method_plugins import METHODS  # noqa: E402
from refpack import build_refpack, normalize, render_refpack  # noqa: E402

AUTO_PARAGRAPHS = 3
MIN_PARAGRAPHS = 3
MIN_QUOTE_LEN = 4
SUPPORT_THRESHOLD = 0.6
FUZZY_FIX = 0.5  # 引文与被引块字面相似度达此值即用原文片段替换
BACKUP_DIR = ROOT / "temp" / "backups"

QUOTE_RE = re.compile(r"「([^「」]{2,200})」|『([^『』]{2,200})』|“([^“”]{2,200})”|\"([^\"]{2,200})\"")


def extract_quotes(text: str):
    out = []
    for m in QUOTE_RE.finditer(text or ""):
        q = next((g for g in m.groups() if g), "")
        if len(normalize(q)) >= MIN_QUOTE_LEN:
            out.append(q)
    return out


def lcs_len(a: str, b: str) -> int:
    """最长公共子串长度（DP，文本块都很短，够用）。"""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for ca in a:
        cur = [0] * (len(b) + 1)
        for j, cb in enumerate(b, 1):
            if ca == cb:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


try:  # 繁简归一，用于识别「模型把原文转成简体复述一遍」
    from opencc import OpenCC
    _T2S = OpenCC("t2s")
except Exception:  # pragma: no cover
    _T2S = None


def _simp(text: str) -> str:
    return _T2S.convert(text or "") if _T2S else (text or "")


PLACEHOLDERS = ("原文引文", "此处引文", "此處引文", "引文在此", "……」", "⋯⋯")
INNER_MARKS = str.maketrans({c: None for c in "「」『』“”\"'"})
_PLACEHOLDER_RE = re.compile(r"「(?:\.{2,}|…+|原文引文|此处引文|原文|引文)」")
_SENT_MARKS = ("。", "！", "？", "；")
_SOFT_MARKS = ("，", "、", "：")


def _strip_placeholders(text: str) -> str:
    return _PLACEHOLDER_RE.sub("", text or "")


def _excerpt(text: str, limit: int = 40) -> str:
    """取原文的**连续**片段：尽量落在句末，其次落在逗顿处，绝不跳字拼接。"""
    t = (text or "").strip()
    if len(t) <= limit:
        return t
    head = t[:limit]
    for marks in (_SENT_MARKS, _SOFT_MARKS):
        idx = max(head.rfind(m) for m in marks)
        if idx >= limit * 0.4:
            return head[: idx + 1]
    return head


def _clean_piece(q: str) -> str:
    """去掉原文自带的引号，避免与段首的外层「」嵌套。"""
    return re.sub(r"[「」『』“”]", "", q or "").strip()


def extract_json(raw: str):
    """从模型输出里抠出 JSON 对象：容忍代码围栏、前后噪声、尾逗号。"""
    if not raw:
        return {}
    t = raw.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    i, j = t.find("{"), t.rfind("}")
    if i >= 0 and j > i:
        t = t[i: j + 1]
    t = re.sub(r",\s*([}\]])", r"\1", t)
    for candidate in (t, t.replace("“", '"').replace("”", '"')):
        try:
            # strict=False：模型常在字符串里塞真实换行，容忍掉这类控制字符
            return json.loads(candidate, strict=False)
        except Exception:
            continue
    return {}


def align_and_fix(parsed, refpack):
    """model 模式的后处理：清占位符、剔除池外引证、把近似引文换回原文片段。"""
    fixes = []
    by_urn = {c["urn"]: c for c in refpack["candidates"]}
    paras = parsed.get("paragraphs") if isinstance(parsed, dict) else None
    if not isinstance(paras, list):
        return parsed, fixes

    out = []
    for i, p in enumerate(paras, 1):
        if not isinstance(p, dict):
            out.append(p)
            continue
        text = _strip_placeholders(str(p.get("text") or ""))
        cites = [u for u in (p.get("cites") or []) if isinstance(u, str) and u in by_urn]
        if len(cites) != len(p.get("cites") or []):
            fixes.append(f"第 {i} 段剔除池外引证 {len(p.get('cites') or []) - len(cites)} 个")

        quotes = extract_quotes(text)
        backed = []
        for q in quotes:
            nq = normalize(q)
            hit = None
            for u in cites:
                blk = normalize(by_urn[u]["text"])
                if nq and nq in blk:
                    hit = (u, 1.0)
                    break
                ratio = lcs_len(nq, blk) / max(len(nq), 1)
                if ratio >= FUZZY_FIX and (hit is None or ratio > hit[1]):
                    hit = (u, ratio)
            if hit:
                u, ratio = hit
                backed.append(u)
                if ratio < 1.0:
                    piece = _excerpt(by_urn[u]["text"], max(8, len(q)))
                    text = text.replace(f"「{q}」", f"「{_clean_piece(piece)}」")
                    fixes.append(f"第 {i} 段引文「{q[:12]}」非逐字，已替换为原文片段")
            else:
                text = text.replace(f"「{q}」", _clean_piece(q))
                fixes.append(f"第 {i} 段引文「{q[:12]}」无原文支撑，已去引号")
        if backed:
            cites = [u for u in dict.fromkeys(backed)]
        out.append({"text": text, "cites": cites})
    parsed["paragraphs"] = out
    return parsed, fixes


def build_repair_prompt(prompt: str, parsed, errors) -> str:
    errs = "\n".join(f"- {e}" for e in errors[:8])
    return f"""{prompt}

---
你上一次的输出不合格，问题如下：
{errs}

上一次输出（供参考，不要照抄）：
{json.dumps(parsed, ensure_ascii=False)[:3000]}

请**完整重写**，严格按上面要求的 JSON 结构输出，只输出 JSON。"""


def pick_spread(refpack, n):
    """从候选池里按章节均匀取 n 块，保证各段落在不同章节、形成全书脉络。"""
    cands = refpack["candidates"]
    if len(cands) <= n:
        return cands
    step = len(cands) / n
    picked, seen_chap = [], set()
    for k in range(n):
        idx = int(k * step)
        # 同章已取过就往后挪，避免两段挤在同一篇
        for off in range(len(cands)):
            c = cands[(idx + off) % len(cands)]
            if c["chap"] not in seen_chap:
                picked.append(c)
                seen_chap.add(c["chap"])
                break
    return picked


def build_prompt_auto(method, book_meta, blocks) -> str:
    """auto 模式提示词：先把 3 块材料按顺序钉死，模型只写「只谈第 k 块」的论述。"""
    schema = json.dumps(method.get("output_schema", {}), ensure_ascii=False)
    mats = []
    for k, b in enumerate(blocks, 1):
        mats.append(f"【材料{k}】{b['urn']}（{b.get('chap_title') or ''}）\n{b['text']}")
    slots = "、".join(f"材料{k}" for k in range(1, len(blocks) + 1))
    return f"""{method['system_prompt']}

---
你正在为《{book_meta['title']}》（{book_meta.get('author') or '佚名'}，{book_meta.get('dynasty') or ''}）写一篇**引证式导读**。
导读由 {len(blocks)} 段组成，每段**只谈**下面指定的那一块原文（{slots}，一段对一块，顺序不可调换）：

{chr(10).join(mats)}

【硬性规则】
1. 第 k 段的论述**只能谈材料 k 那一块**：它说了什么、为什么这样说、在全书脉络里的位置、对今天读者的意义。
   **不得谈别的材料，不得把材料 k 的内容安到别的段上。**
2. **禁止出现任何编号**：「第X则」「第X章」「第X段」「材料1」「材料2」之类一律不许写；
   也不要复述原文。读者只看到原文和你的论述，不知道你在跟哪份材料对话。
3. **每一段的 text 里不得出现任何引号（「」『』“”"），也不得逐字复制原文句子**——
   原文由程序自动补在该段开头，你只写论述，不要代它引原文。
4. 每段 150-220 字，一段成文，不分点列条，句子长短要有变化，不要套同一句式。
5. 只依据给定材料说话；不得引入材料之外的典故、书目与原文。
6. 不要输出解释性文字，不要 markdown 代码围栏。

【输出格式】只输出一个 JSON 对象，paragraphs 必须是 {len(blocks)} 段、与材料一一对应：

{{
  "method": "{method['name_zh']}",
  "book": "{book_meta['title']}",
  "generated_at": "{datetime.now(timezone.utc).isoformat()}",
  "paragraphs": [{{"text": "只谈材料1的论述"}}, {{"text": "只谈材料2的论述"}}],
  "content": {schema}
}}

content 里的每个字段都要有内容；确实无法判断的写「原文未提供足够信息」，不要留空。"""


def build_prompt(method, book_meta, refpack, quote_mode="auto") -> str:
    schema = json.dumps(method.get("output_schema", {}), ensure_ascii=False)
    head = f"""{method['system_prompt']}

---
你正在为《{book_meta['title']}》（{book_meta.get('author') or '佚名'}，{book_meta.get('dynasty') or ''}）做一篇**引证式导读**。
下面是你**唯一允许引用**的原文片段，每段前面方括号里是它的引用编号（URN）：

【可引证原文】
{render_refpack(refpack)}
"""
    if quote_mode == "auto":
        rules = f"""
【硬性规则】
1. 正文写成 paragraphs 段落数组，至少 {MIN_PARAGRAPHS} 段，**建议 4 段**。
2. 每段必须带 cite 字段，值是上面池子里的**一个** URN，不得编造、不得改写章节号或块号。
3. 各段的 cite 不得重复，尽量覆盖不同章节，形成对全书脉络的推进。
4. text 只写你自己的论述：这一块说了什么、它在全书中的位置、义理指向、以及读者可切己之处，
   每段 150-220 字，句子长短要有变化，不要套模板、不要分点列条。
5. **text 里绝对不要复制原文句子，也不要出现任何引号（「」『』“”"）**——
   原文由程序自动补在该段开头，你只需写论述，不要代替它引原文。
6. 池子之外的内容一律不写；不得引入池外典故、书目与原文。
7. 不要输出任何解释性文字或 markdown 代码围栏。
"""
        body = f"""
【输出格式】只输出一个 JSON 对象：

{{
  "method": "{method['name_zh']}",
  "book": "{book_meta['title']}",
  "generated_at": "{datetime.now(timezone.utc).isoformat()}",
  "paragraphs": [
    {{"cite": "池中某个 URN", "text": "针对这一块的论述，不要引原文、不要加引号"}}
  ],
  "content": {schema}
}}

content 里的每个字段都要有内容；确实无法判断的写「原文未提供足够信息」，不要留空。"""
        return head + rules + body

    return head + f"""
【硬性规则】
1. 正文写成 paragraphs 段落数组，**每一段都必须至少引用上面池子里的 1 个 URN**，不得留空。
2. cites 只能填上面出现过的 URN，不得编造、不得改写章节号或块号；一段可引多个。
3. 段落里凡是加了「」的引文，必须**逐字**来自你所引的 URN 对应的那段原文，不得改字、不得拼接、不得用你的记忆代替原文。
4. 凡属你的阐释、评价，一律放在引文之外，不要伪装成原文。
5. 至少 {MIN_PARAGRAPHS} 段，段落之间要有推进（从字面到义理到切己），不要重复同一意涵。
6. 池子里没有的内容，宁可不说；**不得引入池外典故与原文**。
7. **禁止任何占位符**：不得出现「原文引文」「此处引文」「……」之类的占位文字，
   每处「」里都必须是你在池子里挑出的真实原文的**连续片段**（可从原句头部截取，不可跳字拼接）。
8. 段落正文以你自己的论述为主，引文只占其中一小部分；不要在段首堆两个省略号，
   不要套用固定句式模板，各段句式要有变化。

【输出格式】只输出一个 JSON 对象，不要任何解释、不要 markdown 代码围栏：

{{
  "method": "{method['name_zh']}",
  "book": "{book_meta['title']}",
  "generated_at": "{datetime.now(timezone.utc).isoformat()}",
  "paragraphs": [
    {{"text": "你的论述，中间以「池中原文的连续片段」支撑", "cites": ["池中某个 URN"]}}
  ],
  "content": {schema}
}}

content 里的每个字段都要有内容；确实无法判断的写「原文未提供足够信息」，不要留空。"""


def _bag_ratio(a: str, b: str):
    """字袋重合率：对简体/繁体写法差异不敏感，用来识别「原文被复述一遍」。"""
    ca, cb = set(a), set(b)
    shared = ca & cb
    return len(shared), len(shared) / max(len(ca), 1)


_MAT_REF_RE = re.compile(r"材料\s*[0-9一二三四五六七八九十]+\s*(?:中|里|裏|的)?")


def _strip_material_refs(text: str) -> str:
    """模型常把提示词里的「材料1中，」抄进正文，这里清掉。"""
    t = _MAT_REF_RE.sub("", text or "")
    t = re.sub(r"材料[0-9一二三四五六七八九十]*\s*(?:还|也|则|便)[，,]?", "", t)
    t = re.sub(r"^[，,、；;：:\s]+", "", t)
    t = re.sub(r"^(?:则|便|也|又|而)(?=[\u4e00-\u9fa5])", "", t)
    # 「材料2论述中，」这类残留：把「论述中，」也去掉
    t = re.sub(r"^(?:论述|描述|阐述|分析|解读|记载|说明)中[，,]", "", t)
    # 正文中段偶发的「材料还/材料也」一并清掉
    t = re.sub(r"材料(?=还|也|则|便)", "", t)
    # 删掉「材料1中，」后可能只剩无主语的谓语，补回一个主语
    t = re.sub(r"^(论述了|描述了|提出了|阐述了|表明了|强调了|探讨了|揭示了|勾勒了|指出|认为)",
               r"原文\1", t)
    t = re.sub(r"[，,]{2,}", "，", t)
    return t.strip()


def _dedup_lead(body: str, block_norm: str) -> str:
    """模型常把原文（多半转成简体）复述一遍，紧贴在引文之后；这里删掉这段复述句。"""
    sents = [x for x in re.split(r"(?<=[。！？；])", body or "") if x.strip()]
    dropped = 0
    while sents and dropped < 3:
        head = sents[0].strip()
        nh = normalize(_simp(head))
        shared, ratio = _bag_ratio(nh, block_norm)
        lcs = lcs_len(nh, block_norm) / max(len(nh), 1)
        if lcs >= 0.6 or (shared >= 5 and ratio >= 0.45):
            sents.pop(0)
            dropped += 1
            continue
        break
    kept = "".join(sents).strip()
    # 若删完只剩残句，说明这段论述本身就在复述原文（诘问法常见），保留原样更好
    if len(kept) < 40:
        return (body or "").strip()
    return kept


def assemble_auto(parsed, blocks):
    """auto 模式：材料的 URN 由程序按顺序钉死，模型只负责写论述；
    原文引文由程序从对应块里截取补在段首，因此「每段必带逐字原文」由构造保证。
    """
    fixes = []
    if not isinstance(parsed, dict):
        return parsed, fixes
    paras = parsed.get("paragraphs")
    if not isinstance(paras, list):
        return parsed, fixes

    out = []
    for i, b in enumerate(blocks):
        raw = paras[i] if i < len(paras) else {}
        text = raw.get("text") if isinstance(raw, dict) else ""
        text = _strip_placeholders(str(text or "")).translate(INNER_MARKS)
        text = re.sub(r"\s+", " ", text).strip()
        text = _strip_material_refs(text)
        deduped = _dedup_lead(text, normalize(_simp(b["text"])))
        if deduped != text:
            fixes.append(f"第 {i + 1} 段删去紧跟引文的原文复述句")
        text = deduped
        if not text:
            fixes.append(f"第 {i + 1} 段论述为空，已丢弃该材料（不产出无解读的残段）")
            continue
        piece = _clean_piece(_excerpt(b["text"], 40))
        out.append({"text": f"「{piece}」{text}".strip(), "cites": [b["urn"]]})
    if len(paras) > len(blocks):
        fixes.append(f"模型多给了 {len(paras) - len(blocks)} 段，已丢弃（材料只有 {len(blocks)} 块）")
    parsed["paragraphs"] = out
    return parsed, fixes


def validate(parsed, refpack, method):
    """封闭校验。返回 (errors, warnings, paragraphs_clean)。"""
    errors, warnings = [], []
    if not isinstance(parsed, dict):
        return ["输出不是 JSON 对象"], [], []

    by_urn = {c["urn"]: c for c in refpack["candidates"]}
    paras = parsed.get("paragraphs")
    if not isinstance(paras, list) or not paras:
        errors.append("缺少 paragraphs 数组")
        paras = []
    min_paras = refpack.get("min_paras") or MIN_PARAGRAPHS
    if len(paras) < min_paras:
        errors.append(f"段落数 {len(paras)} 少于下限 {min_paras}")

    clean, seen_text = [], set()
    for i, p in enumerate(paras, 1):
        if not isinstance(p, dict):
            errors.append(f"第 {i} 段不是对象")
            continue
        text = (p.get("text") or "").strip()
        cites = p.get("cites")
        if not text:
            errors.append(f"第 {i} 段正文为空")
            continue
        if not isinstance(cites, list) or not cites:
            errors.append(f"第 {i} 段未带任何引证（每段必带引文）")
            continue
        good = []
        for u in cites:
            if not isinstance(u, str) or u not in by_urn:
                errors.append(f"第 {i} 段引证 {u!r} 不在候选池内（禁止池外引证）")
                continue
            good.append(u)
        if not good:
            continue
        key = normalize(text)[:60]
        if key in seen_text:
            warnings.append(f"第 {i} 段与前文高度重复")
        seen_text.add(key)

        quotes = extract_quotes(text)
        if not quotes:
            errors.append(f"第 {i} 段没有任何「」引文（每段必带原文）")
        for q in quotes:
            nq = normalize(q)
            best = 0.0
            for u in good:
                blk = normalize(by_urn[u]["text"])
                if nq and nq in blk:
                    best = 1.0
                    break
                best = max(best, lcs_len(nq, blk) / max(len(nq), 1))
            if best < SUPPORT_THRESHOLD:
                errors.append(f"第 {i} 段引文「{q[:18]}」与所引块字面匹配度 {best:.0%}（非原文）")
        if any(ph in text for ph in PLACEHOLDERS):
            errors.append(f"第 {i} 段含占位符（未填真实原文）")

        clean.append({"text": text, "cites": good})

    for i, p in enumerate(clean, 1):
        body = p["text"].split("」", 1)[-1].strip() if "」" in p["text"] else p["text"]
        if len(body) < 40:
            errors.append(f"第 {i} 段论述过短（{len(body)} 字，仅剩引文）")

    uniq = {u for p in clean for u in p["cites"]}
    if len(clean) >= 2 and len(uniq) < 2:
        warnings.append(f"全篇仅引到 {len(uniq)} 处原文，覆盖不足")
    short = [i for i, p in enumerate(clean, 1) if len(p["text"]) < 60]
    if short:
        warnings.append(f"论述偏短的段落：{', '.join(map(str, short))}")

    content = parsed.get("content")
    if not isinstance(content, dict) or not content:
        errors.append("缺少 content 解读字段")
    else:
        emptied = [k for k, v in content.items() if v in (None, "", [], {})]
        if emptied and len(emptied) == len(content):
            errors.append("content 全部字段为空")
        elif emptied:
            warnings.append(f"content 字段为空：{', '.join(emptied[:5])}")

    if len(clean) != len(paras):
        errors.append(f"有效段落 {len(clean)}/{len(paras)}，存在不可用段落")
    return errors, warnings, clean


def collect_citations(paragraphs):
    out, seen = [], set()
    for p in paragraphs:
        for u in p.get("cites", []):
            if u not in seen:
                seen.add(u)
                out.append(u)
    return out


def backup_existing(conn, work_id, method_id):
    row = conn.execute(
        "SELECT result, generated_at, model_used, citations FROM ai_guides WHERE work_id=? AND method_id=?",
        (work_id, method_id),
    ).fetchone()
    if not row:
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / f"guide_{work_id}_{method_id}_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(
        {"work_id": work_id, "method_id": method_id, "result": row[0],
         "generated_at": row[1], "model_used": row[2], "citations": row[3]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def generate_one(conn, work, method_id, *, max_blocks, max_tokens, dry_run, force, quote_mode="auto"):
    method = METHODS[method_id]
    refpack = build_refpack(conn, work["id"], method_id, max_blocks=max_blocks)
    if len(refpack["candidates"]) < 2:
        return {"ok": False, "error": f"候选块不足（{len(refpack['candidates'])}）"}
    blocks = pick_spread(refpack, AUTO_PARAGRAPHS) if quote_mode == "auto" else []
    if blocks:
        # auto 模式下每块对应一段，允许模型放弃 1 块，但不允许只剩 1 段
        refpack["min_paras"] = max(2, len(blocks) - 1)
    prompt = (
        build_prompt_auto(method, work, blocks) if quote_mode == "auto"
        else build_prompt(method, work, refpack, quote_mode)
    )

    if dry_run:
        out = ROOT / "temp" / f"prompt_{work['id']}_{method_id}.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(prompt, encoding="utf-8")
        return {"ok": True, "dry_run": True, "prompt": str(out), "stats": refpack["stats"]}

    if not force:
        exists = conn.execute(
            "SELECT 1 FROM ai_guides WHERE work_id=? AND method_id=?", (work["id"], method_id)
        ).fetchone()
        if exists:
            return {"ok": False, "error": "已有导读（加 --force 才覆盖）"}

    t0 = time.time()
    raw = chat(prompt, max_tokens=max_tokens)
    model_used = get_last_model() or "unknown"
    parsed = extract_json(raw)
    parsed, fixes = (
        assemble_auto(parsed, blocks) if quote_mode == "auto" else align_and_fix(parsed, refpack)
    )
    errors, warnings, paras = validate(parsed, refpack, method)

    repaired = False
    if errors:
        raw2 = chat(build_repair_prompt(prompt, parsed, errors), max_tokens=max_tokens)
        parsed2 = extract_json(raw2)
        parsed2, fixes2 = (
            assemble_auto(parsed2, blocks) if quote_mode == "auto"
            else align_and_fix(parsed2, refpack)
        )
        e2, w2, p2 = validate(parsed2, refpack, method)
        repaired = True
        if len(e2) < len(errors):
            parsed, errors, warnings, paras = parsed2, e2, w2, p2
            fixes = fixes + fixes2
            model_used = get_last_model() or model_used
    if errors:
        rej = ROOT / "temp" / f"rejected_{work['id']}_{method_id}.json"
        rej.parent.mkdir(parents=True, exist_ok=True)
        rej.write_text(json.dumps(
            {"errors": errors, "warnings": warnings, "raw": raw[:8000]},
            ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": False, "error": "; ".join(errors[:3]), "rejected": str(rej)}

    parsed["paragraphs"] = paras
    parsed["citation_check"] = {
        "paragraphs": len(paras),
        "citations": len(collect_citations(paras)),
        "warnings": warnings,
        "fixes": fixes,
        "repaired": repaired,
        "pool_blocks": refpack["stats"]["blocks"],
        "pool_chars": refpack["stats"]["chars"],
        "quote_mode": quote_mode,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    cites = collect_citations(paras)

    backup = backup_existing(conn, work["id"], method_id)
    conn.execute(
        "INSERT OR REPLACE INTO ai_guides (work_id, method_id, result, generated_at, model_used, citations) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (work["id"], method_id, json.dumps(parsed, ensure_ascii=False),
         datetime.now(timezone.utc).isoformat(), model_used, json.dumps(cites, ensure_ascii=False)),
    )
    conn.commit()
    return {
        "ok": True, "model": model_used, "paragraphs": len(paras), "citations": cites,
        "warnings": warnings, "seconds": round(time.time() - t0, 1),
        "backup": str(backup) if backup else None,
    }


def main():
    ap = argparse.ArgumentParser(description="引证式导读生成器")
    ap.add_argument("--book", type=str, default=None)
    ap.add_argument("--work-id", type=int, default=None)
    ap.add_argument("--method", type=str, required=True)
    ap.add_argument("--max-blocks", type=int, default=30)
    ap.add_argument("--max-tokens", type=int, default=2000)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--quote-mode", choices=["auto", "model"], default="auto",
                    help="auto=程序按块补原文引文（默认）；model=要求模型自己逐字引原文")
    args = ap.parse_args()

    method_ids = [m.strip() for m in args.method.split(",")]
    bad = [m for m in method_ids if m not in METHODS]
    if bad:
        print(f"未知方法: {bad}. 可用: {', '.join(METHODS)}")
        sys.exit(1)

    conn = connect(ROOT / "data" / "guji.db")
    if args.work_id:
        rows = conn.execute("SELECT id, seed_title, author, dynasty FROM works WHERE id=?", (args.work_id,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, seed_title, author, dynasty FROM works WHERE status='ok' AND seed_title LIKE ?",
            (f"%{args.book or ''}%",),
        ).fetchall()
    works = [{"id": r[0], "title": r[1], "author": r[2], "dynasty": r[3]} for r in rows]
    if not works:
        print("未找到作品")
        sys.exit(1)

    done = 0
    for w in works:
        for mid in method_ids:
            print(f"[{w['title']} × {METHODS[mid]['name_zh']}] ", end="", flush=True)
            res = generate_one(conn, w, mid, max_blocks=args.max_blocks,
                               max_tokens=args.max_tokens, dry_run=args.dry_run,
                               force=args.force, quote_mode=args.quote_mode)
            if res.get("ok") and res.get("dry_run"):
                print(f"dry-run → {res['prompt']} {res['stats']}")
            elif res.get("ok"):
                print(f"✅ {res['paragraphs']} 段 / {len(res['citations'])} 引证 / {res['model']} / {res['seconds']}s")
                for warn in res["warnings"][:3]:
                    print(f"    ⚠ {warn}")
            else:
                print(f"❌ {res.get('error')}")
            done += 1
            if args.limit and done >= args.limit:
                conn.close()
                return
            time.sleep(1.0)
    conn.close()


if __name__ == "__main__":
    main()
