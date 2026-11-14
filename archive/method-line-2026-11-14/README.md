---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 0c5caf7145ca8876d640e5da87215fbf_57aba413e04211f1b140525400de85a5
    ReservedCode1: 9MpQly2oASxYl2DXH/L6G+vhT80F0S7h7gBaH1z/1Pynr6OnxuOVJ4CLEM8L6IWKFRHZP3lZF7Xtkd5yNh2bUs19TGsXpkMnMDW97hcjJwESCDSXX968R36iuMdgBs830K0AaM0QgnV4oWenPvomdV7ZxYCuqlLq2e5BY7rHhYc3qhJjvCIVd2IsFPI=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 0c5caf7145ca8876d640e5da87215fbf_57aba413e04211f1b140525400de85a5
    ReservedCode2: 9MpQly2oASxYl2DXH/L6G+vhT80F0S7h7gBaH1z/1Pynr6OnxuOVJ4CLEM8L6IWKFRHZP3lZF7Xtkd5yNh2bUs19TGsXpkMnMDW97hcjJwESCDSXX968R36iuMdgBs830K0AaM0QgnV4oWenPvomdV7ZxYCuqlLq2e5BY7rHhYc3qhJjvCIVd2IsFPI=
---

# 方法线归档（冻结）· 2026-11-14

> 状态：**FROZEN / 已从前台移出**
> 依据：《维点图书馆_认知纠正令与读书方法暂停令_2026-11-14》第五节「乙档 · 前台移出」，业主 2026-11-14 拍板采纳。
> 唯一可用定位表述：**浇灌自由生长的文明**。

## 一、为什么在这里

业主裁定：现有「读书方法」产物不成立 —— `method_doctrines` 表 0 行（方法本体从未建成）、
`method_plugins.py` 自认方法与内容无关、13 篇导读全部出自 `qwen2.5:3b` / `qwen3:4b` 小模型且输出退化成千篇一律的注疏、
方法脚本存在人名与生卒错误。据此「用大师的方法读一切书」被明确否定，方法线即刻冻结并从前台移出。

## 二、归档内容

| 类别 | 文件 | 说明 |
|---|---|---|
| 前端路由 | `src/pages/methods.astro`、`src/pages/[locale]/methods.astro`、`src/pages/pricing.astro`、`src/pages/[locale]/pricing.astro`、`src/pages/read/[slug]/[method].astro` | 原路径已删除，线上 404 状态与本归档一致 |
| 前端组件 | `src/components/MethodsView.astro`、`MethodSelector.astro`、`GuideView.astro`、`PaywallGate.astro`、`PricingView.astro` | 不再被任何页面引用 |
| 文案 | `src/i18n/pages/methods.ts`、`pricing.ts` | 方法线与定价页词条 |
| 生成管线 | `pipeline/gen_guides_cited.py`、`batch_guides.py`、`qa_guides.py`、`run_ai.py`、`method_plugins.py`、`refpack.py` | 9 个方法 id：zhuxi / sushi / qianzhongshu / wangyangming / adler / feynman / socratic / arendt / ibn_khaldun |
| 数据留档 | `guides_13_frozen.json` | `ai_guides` 表 13 行的只读导出（work=1/23/32/33），含冻结原因与 G1–G5 恢复门槛 |

## 三、数据库侧状态

- `data/guji.db` 未做任何删除；`ai_guides` 表 13 行原样留库，标记 frozen，前端不再读取。
- `method_doctrines` 维持 0 行，不填充。
- 前端下发数据（`public/data/index.json`、`book-*.json`）中的 `guides` 已清空，
  并在 `scripts/gen-data.mjs` 设 `GUIDES_FROZEN = true`，使后续构建不再下发导读。

## 四、恢复准入条件（G1–G5，全部满足方可解冻）

| 编号 | 条件 | 验收 |
|---|---|---|
| G1 | 方法本体建成：每方法 10 字段全非空且各带一手文献出处（原典+版本+页码） | 业主逐条判读，抽查可回溯 |
| G2 | 区分度盲测：去标签后业主判别方法归属，正确率 ≥ 85% | 盲测记录留档 |
| G3 | 反模板检测：替换书名后语义仍成立即判模板段，整篇作废 | 可脚本化门控 |
| G4 | 与作品深度耦合：引证须回指该作品具体章句坐标 | `citations` 非空且可回溯 |
| G5 | 计划层落地：含阶段-书目-进度-检验四要素 | 业主实做一轮 |

技术前置：3–4B 本地小模型不具备通过 G2–G4 的能力，恢复前须先解决模型能力这一前置项。

## 五、如何恢复（可逆路径）

1. 代码：把本目录 `src/` 与 `pipeline/` 下的文件按原相对路径移回项目根；
2. 数据：将 `guides_13_frozen.json` 回填 `ai_guides`，并把 `scripts/gen-data.mjs` 的 `GUIDES_FROZEN` 置回 `false`；
3. 导航与文案：恢复页面路由与 i18n 词条（当前版本已改为「原文优先」口径，需按新定位重写，不得复用被否定表述）；
4. 解冻前提：G1–G5 全部通过并留档，缺一继续冻结。

## 六、明令不动（勿误伤）

- `data/guji.db` 全库与注音主线 T-A；
- `work_cards` / `work_dojo_card` 道场线；
- 任何已有产出文件 —— 冻结不等于删除。
*（内容由AI生成，仅供参考）*
