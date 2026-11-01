# 引证式导读生成器（P0-5）

> 脚本：`pipeline/gen_guides_cited.py`（生成+校验+入库）、`pipeline/refpack.py`（候选原文池）
> 产物：`ai_guides.result.paragraphs[]` + `ai_guides.citations[]` → 构建时经 `scripts/gen-data.mjs` 落到 `public/data/book-{id}.json`
> 前端：`GuideView.astro` 渲染「精读正文」段落与段末「本段引证」锚点

---

## 1. 为什么重写旧生成器

`pipeline/run_ai.py` 的做法是「整书正文塞进提示词 → 让模型写散文 → 事后从输出里抽引文」。
旧 12 篇导读都是这样产出的，问题有三：引文多为转述而非原文、段落与原文对不上号、
抽出来的 `citations` 只有 4 条（仅在《论语》）。P0-1 把 `chapters.ref` 与 `ai_guides.citations`
这一层引用地基铺好之后，导读需要改由「**封闭候选池 + 每段必带逐字原文**」来产出。

## 2. 两段式结构

```
build_refpack()  → 从 chapters.blocks 抽 p/v/q 类块（b{idx+1:03d}）→ 封闭候选池
pick_spread()    → 按章轮转取 n 块（默认 3），保证各段落在不同章节、形成全书脉络
build_prompt_*() → 材料按顺序钉死进提示词
模型输出          → paragraphs（+ content 解读四层）
assemble_auto()  → 由程序把原文引文补在段首、URN 按顺序绑定
validate()       → 封闭校验（池内性 / 逐字支撑 / 段数 / 占位符 / content 完整性）
入库             → 备份旧导读 → INSERT OR REPLACE，同时写 citations 数组
```

**关键点：不要求模型抄原文。** 3B 级本地模型抄不了繁体原文，所以 `--quote-mode auto`（默认）
把「引哪一块」交给程序、把「怎么讲」交给模型；引文由 `_excerpt()` 从该块**连续**截取，
因此「每段必带逐字原文」是**构造保证**，不是模型自觉。

## 3. 校验规则（入库前硬门槛）

| 检查 | 不通过时的处理 |
|---|---|
| `paragraphs` 存在且 ≥3 段（auto 模式下按实际取块数，允许模型放弃 1 块，下限 `max(2, 块数-1)`） | 报错 |
| **每篇 ≥ 5 段、正文合计 ≥ 1000 字（v1.1 深度标准）** | 报错（`body_chars` 记入 `citation_check`，`tmp` 下留底） |
| 每段 `cites` 非空且全部在候选池内 | 报错（禁止池外引证） |
| 每段含「」引文，且与所引块字面匹配 ≥ `SUPPORT_THRESHOLD`(0.6) | 报错（非原文） |
| 每段引文之后的论述 ≥ 40 字（只剩引文即判失败） | 报错 |
| 无「原文引文」「……」类占位符 | 报错（未填真实原文） |
| `content` 四个解读字段非全空 | 报错 |
| 全篇引证覆盖 < 2 处、段落 < 60 字 | 记 warning |

### 3.1 确定性清洗（入库后仍会跑一遍）

| 函数 | 处理的问题 |
|---|---|
| `_strip_material_refs()` | 模型把提示词里的「材料1中，」「材料3则」抄进正文 → 删编号、补回主语（"原文描述了…"） |
| `_dedup_lead()` | 引文后紧跟一段原文复述（多为简体）→ 按字袋重合率 + LCS 判定并删除；若删完不足 40 字则保留原样（诘问法常见） |
| `extract_json(strict=False)` | 模型在 JSON 字符串里塞真实换行 → 容忍控制字符，避免整篇被误判为"非 JSON" |

清洗脚本：`temp/clean_all_guides_<时间戳>.py`（幂等，可反复跑；跑完需重跑 `gen-data` + 构建）。

### 3.2 auto 模式的两条防御性设计

- 模型只写论述、不碰原文；某块论述为空时**丢弃该块**，不产出"只有引文"的残段。
- 若模型始终写不出第 3 段（实测《老子》×伊本·赫勒敦），按 `min_paras` 下探到 2 段入库，而不是整篇拒绝。

报错会触发一次 repair 重写；仍不过则落 `temp/rejected_{work}_{method}.json`，**不入库**。
旧导读在覆盖前写入 `temp/backups/guide_{work}_{method}_{时间}.json`。

## 4. 用法

```bash
# 看提示词与候选池覆盖（不调模型）
.venv/Scripts/python.exe pipeline/gen_guides_cited.py --work-id 1 --method zhuxi --dry-run

# 真实生成（覆盖旧导读）
.venv/Scripts/python.exe pipeline/gen_guides_cited.py --book 论语 --method zhuxi --force --max-tokens 900

# 多方法一次跑
.venv/Scripts/python.exe pipeline/gen_guides_cited.py --work-id 1 --method adler,feynman,sushi --force
```

`--quote-mode model` 保留旧的「模型自己逐字引原文」路径：仅对能稳定抄写原文的大模型有意义，
输出会经 `align_and_fix()` 清洗——近似引文换回原文片段、无支撑引文去引号、剔除陪跑引证。

## 5. 已落地结果（2026-11-01）

全部 12 篇导读已按 auto 模式重生成，逐段落首均为底本繁体原文连续片段，段末标注「篇名 · 第 N 块」并可点回阅读页 `#dc:<work>/c<章>/b<块>` 锚点：

| 书 | 方法 | 段数 / 引证 | 备注 |
|---|---|---|---|
| 论语 | 朱熹读书法、阿德勒、费曼、钱锺书、苏轼、王阳明 | 各 3 / 3 | 块位 c002/c012/c022 |
| 老子 | 阿伦特、伊本·赫勒敦 | 3/3、2/3 | 赫勒敦法模型只写得出 2 段 |
| 颜氏家训 | 阿伦特、伊本·赫勒敦、苏格拉底诘问 | 各 3 / 3 | |
| 世说新语 | 伊本·赫勒敦 | 3 / 3 | |

- 校验：`temp/qa_guides.py` 全量体检 12/12 通过（引文齐全、论述达标、无提示词残留、`citations` 字段一致）。
- 构建：`node --experimental-sqlite scripts/gen-data.mjs` → `npx astro build`（613 页，EXIT=0）。
- 本机 Ollama `qwen2.5:3b` 单篇 160-530 秒（3 段 1500 tokens；提到 2 段约 160 秒）。

## 6. 已知限制与下一步

### 6.1 v1.1 分段生成（S1 pilot，2026-11-01）

整篇一次生成时，`qwen2.5:3b` 只肯写 2 段 / 每段 30 字，故 v1.1 改为**逐段生成**（`--segmented`，默认开启）：

| 环节 | 做法 |
|---|---|
| `write_segment()` | 每次只喂 1 个候选块（420 字材料），要求 200-280 字、三层推进；字数不足或出现翻译腔时**带原因重写一次** |
| 引文绑定 | 段首「」原文由程序按块截取（`QUOTE_LEN=60`），URN 与段落一一对应，模型不接触引号 |
| `write_content()` | 四字段单独一次调用，产出后过 `_sanitize_content()` 规范化 `keywords`（脏值/破损结构/缺字段一律清洗或丢弃） |
| 新增清洗 | `_DICT_REF_RE` 清「此段话/这段原文/本段」等指代；`INNER_MARKS` 增加 `‘’` 等单引号；`_TRANS_HINTS` 命中即判"疑为白话翻译"并重写 |

实测（《论语》×朱熹读书法，`qwen2.5:3b`）：**5 段 / 1968 字 / 5 引证 / 943 秒**，硬门槛全过。

### 6.2 尚未解决的模型层问题（v1.1 阻塞项）

字数与段数达标后，3B 模型仍有三类硬伤，**仅靠提示词已到天花板**：

1. **仍以白话翻译为主**：如第 5 段把「里仁爲美」讲成"选择居住在仁义的人中"（应为"择仁厚之俗而居"），第 3 段把「名不正则言不顺…」整段译述一遍。
2. **事实/主体误判**：有子之言归到孔子；「陳司敗問昭公」被写成"齐昭公"；子游、子夏之辩全算作"孔子在这里提出"。
3. **content.keywords 结构性破损**：出现 `{'term': '仁爱之心}` 这类残片，v1.1 直接清空并在 warning 里报"content 字段为空"。

→ 若要 36 篇都达到"义理层"标准，需换模型（`qwen3:4b` 或云端 API），或改由注疏要点驱动而非单块原文驱动。

### 6.3 换模型的实测结论（2026-11-01，本机）

`qwen3:4b`（Ollama 0.34.2，capabilities 含 thinking）在本机**不可用**：

| 现象 | 数据 |
|---|---|
| `"think": false` 不生效 | 返回的 `message.content` 直接是思维链（"首先，用户要求…"），`/no_think` 前缀同样无效，需靠 `===正文===` 标记剥离 |
| 吞吐 | 约 2.9 tok/s；单段（200-280 字 + 思考）≥ 10 分钟，`num_predict=1800` 时单次调用超 600 秒 |
| 推算整篇 | 5 段 + content ≈ 60 分钟/篇；34 篇 ≈ 34 小时 |
| 硬件根因 | 8 GB 内存 + Intel HD 630 集显，模型 3.5 GB、23% 落在 CPU（内存不足部分换出） |

→ 本机 3B 档（`qwen2.5:3b`，约 950 秒/篇）已是这台机器可承受的上限；

1. **模型层**：3B 模型的论述偏通稿化（"对今天的读者而言…"句式重复），诘问法段落易变成对原文的连环发问。
   义理深度需换更大模型（`OLLAMA_MODEL=qwen3:4b` 或云端 API）。
2. **块的选择**：`pick_spread()` 取的是各章首块，长章内部的名段（如《论语》里仁、述而）覆盖不到；
   下一步按块长度/信息量加权取样。
3. **段数**：v1.1 默认 5 段（`AUTO_PARAGRAPHS=5`，合计 ≥1000 字）；走 `--segmented` 逐段生成时个别段可能被模型压线到 200 字下限。
4. **简繁**：模型输出为简体、原文为繁体，正文混排是有意的（导读是今人语，引文保留底本字形）。
5. **构建注意**：`scripts/gen-data.mjs` 依赖 `node:sqlite`，Node 22 需带 `--experimental-sqlite` 运行，
   直接 `node scripts/gen-data.mjs` 会报 `ERR_UNKNOWN_BUILTIN_MODULE`。

## 7. 批量与跨机分派（v1.1）

目标口径：**36 篇 = 4 部书（论语/老子/颜氏家训/世说新语）× 9 法**，`multimodal` 不计入正篇。当前 12/36，缺 24 篇。

生成与发布已拆成两段，本机只做打包与验收（算力活交给强机器）：

```bash
python pipeline/batch_guides.py --plan                              # 覆盖矩阵（秒级，不调模型）
python pipeline/batch_guides.py --export-pack output/guidepack.db   # 2.6 MB 异机数据集
python pipeline/batch_guides.py --run --max-seconds 28800           # 异机：补齐缺失，可中断续跑
python pipeline/batch_guides.py --export output/guides.json         # 异机：回传导读
python pipeline/batch_guides.py --import output/guides.json         # 本机：幂等合并（先备份）
```

`guidepack.db` 含 4 部书 147 章 + 已有 12 篇导读 + 方法义理，`--dry-run` 已验证 8 组方法均可正常构建 prompt（候选池 12–30 块）。往返自测：清空副库导入后 12 篇字段摘要哈希与主库一致。完整操作手册见 `docs/GUIDE-BATCH.md`。
