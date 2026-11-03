# 双机分工与协作协议（2026-11-03）

> 参与方：**本机**（Windows 10，8GB，无外网 HTTPS/DNS，仅 SSH 可用）与 **marvis 主机**（外网可用）
> 仓库：`DimensionsCosmos`（github.com:aidulibrary/DimensionsCosmos，分支 main）
> 基线：`ece7e895`（batch7 收尾后 head）+ 本批前端改动
> 数据基线：112 部 / 10075 章 / 2639.7 万字；标准 v1.2.3；构建 1360 页

---

## 1. 分工原则（三条硬规则）

1. **能力边界优先**：凡需访问外网（wikidata / wikisource / ctext / pages.dev / GitHub API / CI 日志 / 外部模型 API）的任务，一律归 marvis；凡须在本地跑 SQLite 管道、`npm run build`、Edge 实测的任务，一律归本机。
2. **文件所有权隔离**：两台机不同时改同一个文件。改动前必须 `git pull --rebase`；push 前再 rebase 一次；同一文件若被对方占用，改用"任务转移"，不并行编辑。
3. **验收口径唯一**：线上以 `https://dimensions-cosmos.pages.dev/data/index.json` 的 `total` + `generatedAt` 为准；本地以 `npm run build` 退出码 + `dist/` 产物断言为准。任何"看起来好了"不算验收。

---

## 2. 文件所有权矩阵（防止并行冲突）

| 路径 | 本机 | marvis | 说明 |
|---|---|---|---|
| `src/**`（pages / layouts / components / i18n / styles） | 所有者 | 只读 | 前端改动全部由本机落，marvis 提需求不直接改 |
| `scripts/**`（gen / postbuild / check-i18n） | 所有者 | 只读 | 构建期脚本属前端链 |
| `pipeline/**` | 只读 | 所有者 | 数据管道须外网与模型 API，归 marvis |
| `data/guji.db`、`data/sources/**` | 只读 | 所有者 | 写库一律在 marvis，写前快照 |
| `public/data/*.json` | 构建产物 | 构建产物 | 由 `npm run gen` 重生成，不手改，不参与冲突讨论 |
| `docs/CORPUS-*`、`docs/HANDOFF-*` | 只读 | 所有者 | 数据类文档归 marvis |
| `docs/UX-*`、`docs/WORKSPLIT-*`、`docs/BRAND.md` | 所有者 | 只读 | 体验与品牌文档归本机 |
| `.github/workflows/**` | 只读 | 所有者 | CI 归 marvis |
| `D:\DimensionsCosmos\LAN_SHARE`（本机局域网共享） | 所有者 | 只读（只读账户） | 交付包分发通道，见 §5 |

> 例外：若某任务写错了所有者列，以"谁有能力验证"为最终判据，并在本文档末尾变更记录登记。

---

## 3. 本机任务（当前在手 + 本轮新增）

### 已完成（本批）

| 编号 | 内容 | 验收 |
|---|---|---|
| L-0 | 交付包经 SMB 共享 `\\192.168.43.174\DimensionsCosmos`（只读账户 weiyuzhou）移交，3.19GB / 11 文件 | marvis 已接收并同步 |
| L-1 | 书库页检索重构：服务端 `?q=` 整页刷新 → 客户端即时过滤（关键词 + 部类可叠加，条件同步进 URL） | Edge 实测：输入"庄"→1 部（庄子）；"论"+子部→3 部且全部子部；`?q=庄子` 直达 1 部 |
| L-2 | 导航新增"首页"标签 + 当前页高亮（`aria-current`），四语言文案补齐 | `/` 高亮首页、`/books` 与书籍详情页高亮书库 |
| L-3 | 多语言由 4 个导航胶囊合并为单个 `<details>` 下拉，带当前语言标识与选中态 | 下拉列出 4 语言，Esc 与点击外部均收起 |
| L-4 | 语言回落修复：目标语言无本页译文时跳该语言首页，避免"点了没反应" | en 切换 `/books` → `/en/`，`html lang=en` |
| L-5 | 移动端导航两行布局（品牌行 + 可横滚链接行），不再隐藏非 CTA 链接 | 375px：4 项导航可见，横向溢出 0，导航两行共 109px |
| L-6 | 无障碍基线：skip-link（首 Tab 可见，top=12）、`main#main`、`aria-live` 结果计数 | Tab 一次聚焦"跳到主内容" |
| L-7 | 检索无结果闭环：空态文案 + 搜不到的词记入 `localStorage.dc_search_miss`（供后续聚合） | 输入 `zzzznotexist` → 空态显示且词已记录 |

### 待做（本机承接，见 `docs/UX-BACKLOG-2026-11-03.md` 任务卡）

- UX-1 书库筛选维度扩展（朝代 / 可读状态 / 排序）
- UX-2 详情页阅读体验（字号、行距、纸色、目录侧栏、阅读进度）
- UX-3 检索索引化（拼音 / 异体字 / 作者朝代域检索），支撑 300 部以上
- UX-6 首屏新手引导与空态体系
- UX-7 无障碍与键盘全量审计（对照 WCAG 2.1 AA）
- UX-8 性能：书库卡片分片渲染（>300 部时）

---

## 4. marvis 任务（继承 + 新增）

### 4.1 继承（`docs/HANDOFF-2026-11-02-batch7.md` 任务 0–6，未完成部分继续）

| 编号 | 任务 | 状态口径 |
|---|---|---|
| M-0 | 线上验收 batch7 + 本批前端改动 | 见 4.2 |
| M-1 | 补 63 部 `wikidata_qid`（查不到留空并登记，严禁推测） | 归零或全部有结论 |
| M-2 | D3 学术史核验（122 部 provisional → verified，每批 20–30 部出清单） | `pipeline/score_corpus.py --report` 0 错误 |
| M-3 | AI 导读补写（先 162 号朱子语类选本，再主线 🟡 部次） | `guidesCount` 上升、构建拦截数下降 |
| M-4 | 旧库 92 条 `incomplete` 章整改（71 条 chars=0 优先） | 换底本或按 §P9 显式声明，不留静默空 |
| M-5 | 补章与 batch8（幼学琼林、海国图志、朱子语类选本二） | 按 v1.2.3 §2.7 选本子批口径 |
| M-6 | 四条 C 档主线（方志 / 药学 / 农书 / 蒙学） | 补 N3/N5 依据重判，或走 §3.7 例外仲裁留档 |

### 4.2 新增（与本批前端改动配套，均需外网）

| 编号 | 任务 | 验收 |
|---|---|---|
| M-UX1 | 部署后线上验收本批前端：`/books` 存在"首页"链接与 `lang-menu`、检索脚本、移动端两行导航 | `curl -s .../books \| grep -c 'lang-menu'` > 0；首页 `grep -c 'aria-current="page"'` = 1 |
| M-UX2 | 页面级多语言落地（`/en/books`、`/en/tasks`、`/en/methods`、`/en/pricing` 路由与文案），并把 i18n 覆盖率检查扩到"页面级" | `check-i18n-coverage` 覆盖页面级键；四语言 sitemap 条目齐 |
| M-UX3 | `dc_search_miss` 聚合：CF Worker / 轻量端点收埋点，输出"高频搜不到书名"周报 | 端点可用，报告落 `docs/`，TOP20 转入补书候选 |
| M-UX4 | 精选与"最近更新"数据供给：给首页提供 `featured` 与 `recently` 字段（人工精选 + git 时间序） | `index.json` 增字段，前端 L 侧接图 |

> M-UX3 若判断成本过高，降级为"本机导出 localStorage 手工汇总"，由本机执行，需在本文档变更记录登记。

---

## 5. 协作协议（每日节奏）

1. **开工前**：两台机各自 `git pull --rebase origin main`，确认 `git status` 干净或仅有本方所有权内改动。
2. **交付前**：`npm run build` 必须通过（1360 页基线，页数变动须解释）；数据侧须过 S1–S6 自检。
3. **推送**：`git push` 前再 `git pull --rebase`；冲突只允许由文件所有者解决，另一方不得强推。
4. **大文件**：数据包、模型产物、`dist/` 不进 git，走本机 SMB 共享（只读账户）或 marvis 侧对象存储。
5. **日报**：每台机在 `docs/PROGRESS.md` 追加一行（日期 / 编号 / 状态 / 阻塞），避免重复劳动。
6. **冲突升级**：同一文件双方都需改 → 停手，按"是否需要外网"判归属，另一方转出需求说明；仍无法判定则由业主裁定。

---

## 6. 关键风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 本机 HTTPS/DNS 不可达 | 线上验收、外部元数据全依赖 marvis，形成单点 | 验收清单化（§4.2 M-UX1），本机只读 curl 结果不阻塞开发 |
| 两机并行改同一页面 | 冲突、回退 | 文件所有权矩阵；`src/**` 只归本机 |
| `public/data/*.json` 由构建重生成 | 假冲突 | 明确为产物，冲突时以"重跑 gen"解决 |
| 8GB 内存 + 1360 页构建 | 构建慢/失败 | 单机串行构建，不同时跑管道；必要时 `--no-minify` 定位 |
| 检索埋点只在本机 localStorage | 数据分散 | M-UX3 聚合端点，或导出汇总 |

---

## 变更记录

- 2026-11-03：初版。本机完成 L-1 至 L-7 前端改动并 Edge 实测；新增 M-UX1 至 M-UX4。
