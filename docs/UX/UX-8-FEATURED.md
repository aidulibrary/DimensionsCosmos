# UX-8 首屏引导与精选 — 交付说明与验收记录

> **REVERTED（2026-11-05）** — 本方向已由项目负责人否决并整体回滚，提交链 `6ef92323` / `85afb7cc` 的功能代码、文案、类型、校验脚本与构建脚本入口已全部移除，首页回到内容优先原貌。
> 本文仅作历史证据留存：所记验收数据在回滚那一刻仍然成立，但不构成任何现行方案依据。**不得据此恢复实现**，任何重启须先过 `docs/UX/UX-PRINCIPLES-2026-11-05.md` 的四条准入闸门。

- 版本：v1（2026-11-04）
- 归属域：前端（`src/components` / `src/lib` / `src/i18n` / `scripts` / `docs/UX`），**未触碰 `data/**`、`pipeline/**`、`public/data/index.json`**
- 优先级：P0 · 0.5 人日 · 纯前端 · 不阻塞供数
- 状态：四层验收全绿（静态构建 / 本地 DOM 断言 48 项 / 线上复测 / UX-1·UX-4·UX-6 回归），已推送

---

## 1. 本轮做了什么

首页在 hero 之下、书库之上新增「首屏引导与精选」区，按四身份分栏，把平台从"112 部书的大目录"改写为"按读者身份可进入的入口"。

| 层 | 文件 | 作用 |
|---|---|---|
| 数据读取与校验 | `src/lib/featured.ts`（新增） | 读 `public/data/featured.json`；缺失/破损/条目不足时回退 `SEED_FEATURED`；`audiences` 四值枚举白名单过滤；`reason` 按 `reviewed` 语言白名单放行 |
| 渲染组件 | `src/components/FeaturedGuide.astro`（新增） | 服务端全量渲染四栏（**不依赖 JS**），tablist + ARIA + 键盘左右/Home/End，`<noscript>` 时四栏全部展开 |
| 文案 | `src/i18n/pages/home.ts`（改） | 新增 `featured` 文案块，zh / zh-TW / en / es 四语齐备 |
| 挂载 | `src/components/HomeView.astro`（改） | hero 之后插入 `<FeaturedGuide>`，传入 `index.works` 与 `taxonomy` |
| 验收 | `scripts/verify-ux8.mjs` / `verify-ux8-online.mjs`（新增） | 本地双构建分支验收 48 项 + 线上复测 |

设计取向：**服务端直出 + 渐进增强**。首屏引导对 SEO 与"无 JS 环境可读"是硬要求，因此四栏内容全部在 HTML 里，JS 只负责切 tab；禁用 JS 时四栏退化为纵向堆叠，不出现空白区。

---

## 2. 两条降级分支（本轮硬性要求，均已成测）

### 分支 ①：`guides` 为空的书

精选 6 部中 `13-史记`、`17-资治通鉴` 属"有元数据、无导读"状态（线上 `index.json`：论语 7 篇 / 老子 2 篇 / 颜氏家训 3 篇 / 世说新语 1 篇，合计 13 篇，这两部为 0）。

处理：
- 主 CTA 指向 `/books/{slug}/read`（直达阅读页），而非详情页——避免把用户送进一个没有导读的空详情页；
- 徽标显示"导读筹备中"类状态文案（i18n 提供，四语齐备），**不显示"0 种解读"**这种自曝空值；
- 卡片与有导读的书同尺寸、同视觉权重，不做降级灰化，不制造二等公民感；
- 断言：`data-has-guide="0"`、CTA 命中 `/read`、徽标非空。

### 分支 ②：`featured.json` 缺失或条目少于 6 部

- **文件缺失 / 解析失败**：回退 `SEED_FEATURED`（6 部骨架），保证首屏不空；
- **条目少于 6 部**：按实际条目数渲染，**不补占位卡、不追问数据侧**（成测：注入 5 部 fixture，页面渲染 5 部，`33-世说新语` 未被 SEED 追加）；
- 断言：去重 slug 数 == fixture 条目数；不出现 SEED 独有条目。

### 文案缺省纪律

- `reason` 缺省时整段不渲染（不留空 `<p>`、不输出 `—` / `暂无` / `TBD`）；
- 断言黑名单 `— / —— / 暂无 / 待补 / 待定 / TBD / TODO / null / undefined / N/A` 全文零命中；
- 未供数状态下 `reasonCount === 0`（A 阶段）与供数后 `32-颜氏家训`（无 reason）卡片 `reason === ''` 双向验证。

### 未过审语言不硬译

`reason` 带 `reviewed: ['zh']` 时，英文页 `reasonCount === 0`，且断言"英文页不泄露中文推荐语"。即使 `reason.en` 有值也**不放行**——底稿未经人工过审即上线，属内容事故，宁可空。

---

## 3. 四身份分栏

`audiences` 枚举固定四值，禁止同义词：`student` / `general` / `family` / `research`（学子 / 大众 / 家庭 / 研究）。

- 每部书可属多栏，按 `order` 稳定排序；
- 默认落在 `general`（最大公约数受众），仅该面板可见；
- 栏标签带条目数，无条目的栏不渲染（不出现空栏）；
- SEED 分支实测分布：student 4 / general 5 / family 3 / research 4，共 16 张卡片。

---

## 4. 验收记录（可复跑）

| 层 | 命令 | 结果 |
|---|---|---|
| 静态构建 | `npx astro build` | 成功，1372 页，无告警级错误 |
| 本地 DOM 断言 | `npm run test:ux8` | **48 / 48** |
| 线上复测 | `npm run test:ux8:online` | 见 §6 |
| UX-6 回归 | `npm run test:ux6` | **52 / 52** |
| UX-1 回归 | `npm run test:ux1` | **31 / 31** |
| UX-4 回归 | `npm run test:ux4` | **23 / 23** |

`verify-ux8.mjs` 的构造要点（区别于既有 UX-1/4/6 脚本）：

1. **双构建分支**：脚本自行触发两次 `astro build`——A 阶段临时移走 `featured.json` 走 SEED 分支，B 阶段写入 5 部 fixture 走"条目不足"分支，测完恢复原状并重建干净产物。两条降级分支都是**真构建 + 真 DOM**，不是 mock。
2. **期望值独立计算**：四栏期望由 `index.json` 的 `audiences` 独立算出，分类路径期望由 `siku-map.json` + `taxonomy` 父子校验复算，一律不读页面自报内容。
3. **SEED 同源校验**：脚本内的 SEED 期望会与 `src/lib/featured.ts` 的 `SEED_FEATURED` 正则比对，防止两处清单漂移后"脚本和页面一起错"（这类假绿最难查）。
4. **Windows 文件占用坑**：两次构建之间必须先关掉 Edge 与静态服务，否则 astro 清空 `dist` 会 EPERM，第二次构建静默失败 → 断言跑在旧产物上，表现为"fixture 明明写了却全是 SEED 数据"。已在脚本里显式 `shutdown()` 并把 build 失败抛出（不吞异常）。

---

## 5. 已知边界（不做，非债务）

1. **`featured.json` 供数未到位**：数据侧口径已锁定（独立文件、`slug` / `order` / `audiences[]` / `reason{zh,zh-TW,en,es}`），前端脚手架已就位，供数文件落地即生效，前端零改动。
2. **`bu_sub` 权威值仍读 `siku-map.json`**：优先级已实现为 `book.bu_sub` → 映射表，数据侧并入后可直接删映射文件，无需改前端代码。
3. **`zh-TW` / `en` / `es` 推荐语**：等数据侧出底稿 → 人工过审 → 才进 `reviewed`，本轮不做机器硬译。
4. **不做个性化持久化**：身份选择不写 localStorage/cookie，每次默认 `general`。理由：首屏引导的价值是"让人看懂平台有什么"，不是"记住我是谁"；引入持久化会带出"用户身份标签"的隐私面与跨端一致问题，收益不抵成本。留待有真实账号体系后再议。

---

## 6. 线上复测口径

- 期望值一律取线上 `/data/index.json`（及 `/data/featured.json`，404 则按 SEED 分支期望），**不回退本地数据**；
- URL 统一带尾斜杠，规避 308 与旧 HTML 缓存；
- 若线上仍是旧版（无 `[data-featured]`），首轮断言直接失败，不静默放行；
- 附带 UX-6 / UX-1 关键项回归（史记详情页繁正名 + 分类路径部级可点、史部结果数），防新版覆盖旧交付。

---

## 7. 首屏引导与三步条（UX-8b，本轮补齐）

backlog 里 UX-8 的原表述含"三步引导（选书 → 选大师 → 读章）"，此前落地的是精选四栏，缺首屏引导。本轮补齐，且不引入任何交互状态。

### 7.1 hero 双 CTA

| 位置 | 文案来源 | 目标 | 语义 |
| --- | --- | --- | --- |
| 主 CTA | `homeStart.heroPrimary` | `/books` | 不知道读什么也能立刻进书库 |
| 次 CTA | `homeStart.heroSecondary` | `/methods` | 先看"怎么读"，降低古籍心理门槛 |
| 分流提示 | `homeStart.heroHint` | `#start` 锚点 | 拿不定主意的人往下走三步条 |

触控高度 48px（主）/ 44px（次），1280 与 375 双视口均不溢出。

### 7.2 三步条（`src/components/StartSteps.astro`）

- **纯静态、零 JS**：三步都是真链接（`/books`、`/methods`、`/books/{slug}/read`），禁用 JS/键盘直连/无痕首屏都能用；
- **第三步目标书由数据推导**：取精选顺序里第一个 `guides` 非空的书（当前为 `1-论语`）。若全部为空则降级到 `/books`——即"guides 为空的书不进第三步"，与详情页空态分支同源；
- **文案四语**：独立文件 `src/i18n/pages/homeStart.ts`，与 `home.ts` 分离，避免双机并行时同文件冲突；
- **375 单列**：三步纵向堆叠、左缘对齐，按钮不挤成一团（断言按 y 递增判定，不按 x——同 x 也可能是行内并排）。

### 7.3 本轮验收（沿用同一口径）

| 层 | 结果 |
| --- | --- |
| 本地 DOM 断言 `npm run test:ux8` | **67/67**（A 精选 + A2 首屏引导 + B 两条降级分支） |
| 线上复测 `npm run test:ux8:online` | **38/38**（含首屏引导 12 项 + UX-6/UX-1 回归） |
| UX-6 回归 | 52/52 |
| UX-1 回归 | 31/31 |
| UX-4 回归 | 23/23 |

期望值独立计算：第三步目标书由 `index.json` 的 `guides` 独立算出，与页面自报无关；四语页断言 CTA 文案不得为空、`en`/`es` 不得残留中文（防漏译回退到 zh）。

### 7.4 仍不做的

- 首屏引导**不记忆**用户选择（同第 5 节第 4 条）；
- 三步条**不做**动画、不做进度感知——它不是 onboarding 流程，只是导航；
- 精选区的推荐语仍受 `reviewed` 闸门约束，未过审语言一律不渲染。
