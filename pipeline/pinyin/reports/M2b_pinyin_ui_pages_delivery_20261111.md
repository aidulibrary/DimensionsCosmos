---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 0c5caf7145ca8876d640e5da87215fbf_c364a21fddcd11f1bff2525400cd780f
    ReservedCode1: JOPWOfAJU0Ia3/nMZICN/K87xkaImFtyT2Pe/j+XGfveExHPhP7p7ufVxB5n9FK6IEiyz40Nns+0Pzz9WdA4Rp7Uhw2hk6UaPD9F0dYjLBAXsZundYlfKMZsOiU0FnpCKkawKuvLEeRpJdqCse3iPwRPosV1ZaJV/1H3TkYrmprB/b/WjUMZSZ8zVUM=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 0c5caf7145ca8876d640e5da87215fbf_c364a21fddcd11f1bff2525400cd780f
    ReservedCode2: JOPWOfAJU0Ia3/nMZICN/K87xkaImFtyT2Pe/j+XGfveExHPhP7p7ufVxB5n9FK6IEiyz40Nns+0Pzz9WdA4Rp7Uhw2hk6UaPD9F0dYjLBAXsZundYlfKMZsOiU0FnpCKkawKuvLEeRpJdqCse3iPwRPosV1ZaJV/1H3TkYrmprB/b/WjUMZSZ8zVUM=
---

# M2 波 2 · 注音标注台与预览页交付报告（站点化改造）

- **交付日期**：2026-11-11
- **范围**：标注台站点化 + 注音预览页 + 任务中心常态化入口 + 设计一致性门禁
- **状态**：三页均已构建通过，可本地预览；P0 标注待人工执行；T2.4 计划已立项待启动

---

## 一、结论速览

| 项 | 结果 |
|---|---|
| 标注台 `/collation/pinyin-review/` | 重挂 BaseLayout + 令牌化，dist 38.9 KB，构建通过 |
| 注音预览页 `/collation/pinyin-preview/` | 新建，dist 32.4 KB，G3 门禁条已对齐全库口径 |
| 任务中心 `/tasks/` | 新增「在办产线」区，2 张产线卡（标注台 / 预览页） |
| 设计一致性门禁 | `scripts/check-design-consistency.mjs` 已挂 `prebuild` / `predev` |
| 全站构建 | 1,374 页，RC=0，postbuild 通过 |
| 一致性检查 | 扫描 23 页，违规 8 页（全部为历史遗留），**强制阻断 0** |
| P0 数据校验 | 1,200 条全部通过（见第五节） |

---

## 二、为什么首版不一致（问题清单）

| # | 首版问题 | 根因 | 已改 |
|---|---|---|---|
| 1 | 独立配色（米白/金/蓝写死） | 单文件离线工具，无站点上下文 | 全部换 `var(--*)` 令牌，`rgba()` 计数归零 |
| 2 | 无导航、无页脚、无主题切换 | 未挂 BaseLayout | 挂载 `../../../layouts/BaseLayout.astro` |
| 3 | 分层名显示 `B4_defaultAssert` | 构建脚本键名大小写不匹配 | `bucket_cn()` 容错映射 → 「默认读音组」 |
| 4 | 徽章样式按分层写死 `.b-B1…` | 类名与分层码绑定 | 改通用 `.badge-b1~b4` + `BCLS` 映射 |
| 5 | 键盘流语义含糊（prev 会丢标记） | 回退与回看混为一谈 | prev = 回看不撤销；review 定位末条已标 |
| 6 | 与站点字号/间距节奏不同 | 自定 font-family | 字体栈限语义栈（楷体/衬线），继承站点节奏 |

---

## 三、三页现状

### 3.1 标注台 `src/pages/collation/pinyin-review/index.astro`
- 数据：`public/collation/pinyin-review/data.json`（1,200 条，四桶各 300）
- 交互：`Enter` 正确 / 输入拼音 `Enter` 记错并改 / `S` 存疑 / `Backspace` 回看
- 三态固定：确定（`--cinnabar`）· 异读（`--gold`）· 存疑（`--warn-*`），禁第四套色
- 进度存 localStorage，导出 JSONL 直接作 T2.4 训练集
- 分层徽章：词形多音 / 破读 / 通假 / 默认读音组

### 3.2 注音预览页 `src/pages/collation/pinyin-preview/index.astro`
- 数据：`public/data/pinyin/manifest.json` + 每章分片 JSON
- 内容：史记 / 后汉书 / 资治通鉴 共 9 章，`<ruby>/<rt>` 三态渲染
- 门禁条（与 T2.3 冻结报告口径一致，全库 21,558,218 字位）：
  - 存疑率：样本 5.01% ／ 全库 4.3305%，目标 规则期 ≤5%
  - 异读：全库 0.0074%，目标 ≤0.01%
  - 字位覆盖率：81.14%，目标 ≥80%
  - 单章分片体积：最大 ≤60 KB（构建时实测）
- 定位声明：预览验证页，**非线上阅读页**；线上 read 页仍按「默认关、按需拉例外分片」接入（P3）

### 3.3 任务中心入口 `src/pages/tasks/index.astro`
新增「在办产线」区，标准卡形态（`.pipe-grid`），每卡含：状态徽章 + 数量 + 说明 + 进度条 + 入口文案。

| 卡 | 徽章 | 指标 | 入口 |
|---|---|---|---|
| 注音金标标注台 | 待标注 | 1,200 位 | `/collation/pinyin-review/` |
| 注音版预览 | 预览中 | 9 章 / 3 部书 | `/collation/pinyin-preview/` |

样式全部使用 `--white/--line/--cinnabar/--gold/--shadow-md`，未引入新色。

---

## 四、目标与标准对齐（三档口径）

| 门禁项 | 阶段一 规则期（r2v9，已达成） | 阶段二 模型期（T2.4 目标） | 前端验收（预览页/线上） |
|---|---|---|---|
| variant 误标率 | ≤0.01% ✅ 0.0074% | ≤0.01% | 异读组高亮可辨 |
| defaultAssert 精度 | ≥85% ✅ 85.3% | **≥96%** | 不参与前端判定，仅数据侧 |
| 规则组精度 | ≥97% ✅ 97.5% | 保持 ≥97% | — |
| uncertain | ≤5% ✅ 4.3305% | **≤1.5%** | 存疑位不显示 ruby，回退内置字典 |
| 字位覆盖率 | — | — | ≥80%（实测 81.14%） |
| 单章分片体积 | — | — | ≤60 KB |
| 金标准确率 | ≥95% | ≥96% | — |

结论：**预览页当前按阶段一口径展示并通过**；阶段二数值待 T2.4 回填，届时门禁条自动换口径（`ALL` 常量与 `gates` 数组单点修改即可）。

---

## 五、P0 数据校验（1,200 条全量）

| 校验项 | 方法 | 结果 |
|---|---|---|
| 上下文切分等价 | `ctx[:ti] + 目标字 + ctx[ti+1:] == ctx` | 0 异常 |
| 队列推进 | 模拟全量标记，`firstUnmarked` 推进 | 1,200 条不重不漏，末态 None |
| 四桶均衡 | 按 bucket 计数 | 各 300 |
| 目标字合法性 | 目标字属 CJK 统一汉字区 | 0 异常 |
| 机器读音合法性 | 拼音字符集（含声调）正则 | 0 异常 |
| 分片可达性 | 预览页 9 章分片文件存在性 | 全部存在 |
| 链接可达 | 标注台 slug 链接 | 84 个全部可达 |

---

## 六、一致性门禁（新增）

| 产物 | 说明 |
|---|---|
| `scripts/check-design-consistency.mjs` | 五项检查：必须挂 BaseLayout、禁裸 hex、禁裸 rgba、字体须语义栈、顶栏用 `var(--nav-h)` |
| `docs/DESIGN-CONSISTENCY-2026-11-11.md` | 规范正文（令牌清单、参照页面、入口原则、豁免清单） |
| `package.json` | 新增 `check:design` / `check:design:strict`，并挂入 `prebuild` / `predev` |

规则要点：**历史遗留页只减不增**；新页面违规即阻断构建，不允许多人情豁免。

---

## 七、预览方式

```bash
# 已在本机起静态服务（后台，端口 4321）
http://127.0.0.1:4321/tasks/                       # 任务中心 · 在办产线入口
http://127.0.0.1:4321/collation/pinyin-review/     # 标注台（P0 1,200 位）
http://127.0.0.1:4321/collation/pinyin-preview/    # 注音版预览（9 章）
```

线上：`https://dimensionscosmos.pages.dev/tasks/`（待部署后生效）

---

## 八、下一步与选项对比

### 推荐：先生直接开标 P0（2–3 小时），回传即启动 T2.4

标注台已站点化并通过浏览器可达，数据校验全绿，无需再改工具。

| 方案 | 做法 | 优势 | 代价 |
|---|---|---|---|
| **A（推荐）** | 即刻标注 P0 1,200 位，回传后启动 T2.4 | 唯一能解锁 defaultAssert 85%→96% 的路径；P0 只需 2–3 h | 需先生投入 2–3 小时人工 |
| B | 先返工 8 个遗留页配色，再标注 | 全站一致性彻底 | 阻断 T2.4 启动，收益低（遗留页非新增） |
| C | 先做线上 read 页接入（P3） | 用户更早看到注音效果 | 门禁未过，会把 4.33% 存疑与 85.3% 错标直接暴露给读者 |
| D | 先扩 P1 标注量（3,000 位）再训模型 | 样本更厚 | 推迟 3–5 天，且主动学习比盲标更省人力 |

**取舍理由**：门禁分期已明确——阶段一已达、阶段二卡在 defaultAssert。任何绕过 P0 标注的动作都无法推进主指标，故 A 为最短路径。B/C/D 均可在 A 完成后并行或顺延。

### T2.4 时间表（P0 回传为 D+0）

D+0 入库 → D+1 特征+LR 基线 → D+2 LightGBM + 5 折 CV → D+3 全库推理 + 主动学习取样 → D+4 三态回写与门禁核算 → D+5 报告。

详见 `reports/T2.4_defaultAssert_model_plan_20261111.md`。
*（内容由AI生成，仅供参考）*
