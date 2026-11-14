---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 0c5caf7145ca8876d640e5da87215fbf_c015e490ddcd11f1a0ca525400de85a5
    ReservedCode1: SNQFrzxxoK02P0M1VX2sEM4shuMN2ZjCXxVmtaUFrSZKKokhXevagYMEB1Vunq60BV2dJuDtu80YDHOoAXNX1L7mIlmcG5/hA4ZHrP1ZbG/QIeJ9eDM/X+Y6uAbPlNUYdiBuzo6YWH2CnAZP9+jqsaJY+jzjSW8yK60Dqwj3IAdKEXoper1dqnTvSXI=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 0c5caf7145ca8876d640e5da87215fbf_c015e490ddcd11f1a0ca525400de85a5
    ReservedCode2: SNQFrzxxoK02P0M1VX2sEM4shuMN2ZjCXxVmtaUFrSZKKokhXevagYMEB1Vunq60BV2dJuDtu80YDHOoAXNX1L7mIlmcG5/hA4ZHrP1ZbG/QIeJ9eDM/X+Y6uAbPlNUYdiBuzo6YWH2CnAZP9+jqsaJY+jzjSW8yK60Dqwj3IAdKEXoper1dqnTvSXI=
---

# 站点设计一致性规范（常态化约束）

- **生效日期**：2026-11-11
- **适用范围**：维点图书馆站点（Astro，`dimensionscosmos.pages.dev`）此后所有新建 / 改造的常态化页面
- **强制方式**：可执行门禁 `npm run check:design`，已挂入 `prebuild` / `predev`，构建前自动拦截

---

## 一、为何立此规范

注音标注台（gold_P0_标注台.html）首版为单文件离线版，自成一套配色与排版，进入站点后与全站视觉割裂。结论：**离线工具的视觉不能直接搬进站点，必须重挂站点外壳与令牌。**

自此确立：页面外观 = 站点令牌体系 + 结构组件，不允许页面自造色值与字体栈。

---

## 二、五条硬约束

| # | 约束 | 判定 | 正确做法 |
|---|---|---|---|
| 1 | 必须经 `BaseLayout` 渲染 | 页面或其一级 View 组件链上出现 `BaseLayout` | 薄壳页 `import XxxView` + View 内挂 `BaseLayout` 亦可 |
| 2 | 样式不得出现裸十六进制色 | `#abc` / `#aabbcc` 等（`#fff` `#000` 例外） | 用 `var(--ink)` `var(--cinnabar)` `var(--gold)` `var(--line)` … |
| 3 | 不得出现裸 `rgba()` | `rgba(…)` / `rgb(…)` | 半透明层用 `color-mix(in srgb, var(--gold) 12%, transparent)` |
| 4 | 字体栈须为语义栈 | 含 `serif` / `Kaiti` / `Songti` / `monospace` / `var(--serif)` | 正文继承 `global.css`；古籍正文可显式用楷体栈（内容性需求，允许） |
| 5 | 顶栏偏移须用令牌 | `top: 40~120px` 硬编码 | `top: var(--nav-h)` |

---

## 三、令牌清单（真实值，`src/styles/global.css`）

### 3.1 底色与墨色
| 令牌 | 白天 | 夜间 | 用途 |
|---|---|---|---|
| `--paper` | `#f7f2e8` | `#12171a` | 页面底色 |
| `--paper-deep` | `#efe7d6` | `#0d1215` | 次级底 |
| `--white` | `#FEFCF7` | `#182027` | 卡片面 |
| `--ink` | `#2b2926` | `#e7e3d9` | 主文字 |
| `--ink-soft` | `#6b655c` | `#9ba4ab` | 次文字 |
| `--line` | `#ddd2bd` | `#2a343b` | 描边 |
| `--line-strong` | `#cbbda1` | `#38454d` | 强调描边 |

### 3.2 强调色
| 令牌 | 白天 | 夜间 | 用途 |
|---|---|---|---|
| `--cinnabar`（= brand-sky） | `#003048` | `#2b6d8c` | 主强调、链接、按钮 |
| `--gold` | `#b8934a` | `#c9a765` | 次级强调、进度、金标 |
| `--brand-red` / `--point` | `#e41824` | `#cf2b34` | 仅做"点"，不可大面积 |
| `--accent-ink` | `#33566a` | `#82bdd8` | 浅底上的蓝字 |
| `--on-accent` | `#f7f2e8` | `#f2f5f6` | 品牌底上的文字 |
| `--brand-sky-tint` | `#e8eef1` | `#1b2830` | 浅蓝底块 |

### 3.3 语义面
`--ok-bg` / `--ok-line`、`--danger-bg` / `--danger-line`、`--note-*`、`--warn-*`、`--success`、`--shadow-sm|md|lg`、`--radius` / `--radius-lg`。

> 三态标注的色语义约定（沿用全站）：确定 = `--cinnabar`／异读 = `--gold`／存疑 = `--warn-bg` + `--warn-ink`。禁止另造第四套色。

---

## 四、参照实现（可作为新页面的模板）

| 页面 | 路径 | 可抄的结构 |
|---|---|---|
| 注音标注台 | `src/pages/collation/pinyin-review/index.astro` | 吸顶工具条 + 分段筛选 + 卡内主对象 + 键盘快捷键条 + 三态徽章 |
| 注音预览页 | `src/pages/collation/pinyin-preview/index.astro` | 书目/章节选择器 + ruby 正文 + 门禁指标条 + 分片统计 |
| 任务中心 | `src/pages/tasks/index.astro` | 在办产线卡（`.pipe-grid`）——常态化入口的标准形态 |

---

## 五、门禁用法

```bash
npm run check:design          # 新增页面强制；历史遗留仅提示（退出码 0/1）
npm run check:design:strict   # 全部页面强制（用于专项返工）
node scripts/check-design-consistency.mjs --json   # 机器可读
```

- **遗留豁免清单**（`BASELINE`，脚本内）只减不增：`books/[slug]/read.astro`、`books/[slug].astro`、`brand.astro`、`privacy.astro`、`r.astro`、`read/[slug]/[method].astro`、`tasks/index.astro`、`terms.astro`、`collation/tj-review/index.astro`。
- 新页面**不得**加入 `BASELINE`，违规即阻断构建。
- 当前基线：扫描 23 页，违规 8 页，**强制阻断 0**。

---

## 六、入口放置原则

常态化作业面（标注台、复核台、数据看板）统一从 **任务中心 `/tasks/` 的在办产线区**进入，不散落到导航一级。理由：

1. 任务中心是"作业面"的既有语义中心，用户心智一致；
2. 产线卡自带状态徽章 + 进度 + 门禁，进站即可判断该做什么；
3. 避免导航随产线增加而膨胀。

新增产线只需在 `.pipe-grid` 内追加一张卡，附 `badge`（待标注/进行中/已收口）、`p-metric`（数量）、`p-bar`（进度）、`p-go`（入口文案）。
*（内容由AI生成，仅供参考）*
