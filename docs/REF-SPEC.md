---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 0c5caf7145ca8876d640e5da87215fbf_deba284ed54711f1b4e4525400cd780f
    ReservedCode1: qib+v6oA108s/5mIrQq/6qBejAbZSyOT+xJ3J7DYxktCfrYiuVgY0qer2zWL1huGaIGEx2BmZ8uPtwMA2FCsFgUR73nmbUnRjEO65nk/WD2w22t4o7Bp8bPOnGTlZIze1Kw/5Odr950aKAHlYQwB6vibeY6JA2czcvb37jcBF5A8BnkA1XALA+fk8hg=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 0c5caf7145ca8876d640e5da87215fbf_deba284ed54711f1b4e4525400cd780f
    ReservedCode2: qib+v6oA108s/5mIrQq/6qBejAbZSyOT+xJ3J7DYxktCfrYiuVgY0qer2zWL1huGaIGEx2BmZ8uPtwMA2FCsFgUR73nmbUnRjEO65nk/WD2w22t4o7Bp8bPOnGTlZIze1Kw/5Odr950aKAHlYQwB6vibeY6JA2czcvb37jcBF5A8BnkA1XALA+fk8hg=
---

# REF-SPEC v1 · 维点图书馆稳定引用规范

> 状态：已落地（2026-11-01）｜数据库：`chapters.ref` 已全量回填 5531 条，唯一索引 `idx_chapters_ref` 就位
> 脚本：`scripts/migrate_ref.py`（迁移/校验/导出）、`scripts/rollback_ref.py`（回滚）

---

## 1. 为什么需要这一层

当前章内锚点为 `#ch-{id}:b{block}:k{item}`，其中 `id` 是 `chapters.id` **自增主键**。
一旦重导数据（换底本、补卷、清理孤儿章），主键即漂移，所有外链、批注、导读引证、复习卡全部错位。

REF-SPEC 的目标：给出一个**由内容结构推导、与主键无关、可被外部系统长期解析**的标识。

---

## 2. 语法

```
dc:<work-key>/c<chapNo>                      章节级（入库，chapters.ref）
dc:<work-key>/c<chapNo>/b<block>             块级（不入库，运行时派生）
dc:<work-key>/c<chapNo>/b<block>/k<item>     句元级（预留，不入库）
```

| 片段 | 取值 | 说明 |
|---|---|---|
| `dc` | 固定 | DimensionsCosmos 命名空间前缀 |
| `work-key` | `Q\d+` 或 `x[0-9a-f]{8}` | 优先用 Wikidata QID；无 QID 时用 `x` + `sha1(seed_title)[:8]` |
| `chapNo` | 3 位零填充整数（≥1000 自然扩展为 4 位） | 该书内按 `ORDER BY ord ASC, id ASC` 的 **1-based 序号**，前置附文（负 ord）优先编号 |
| `block` | 3 位零填充整数 | `chapters.blocks` 数组下标（0-based 存储，引用时按 1-based 输出，见 §4） |
| `item` | 3 位零填充整数 | 块内句元下标，预留 |

**示例**

| 书 | 章节 | ref |
|---|---|---|
| 论语 | 論語/序說 | `dc:Q276015/c001` |
| 论语 | 論語/學而第一 | `dc:Q276015/c002` |
| 论语 | 學而第一 第 3 块 | `dc:Q276015/c002/b003` |
| 说文解字 | 第 530 章 | `dc:Q1072348/c530` |

当前 50 部书全部有 ref；49 部走 QID，1 部因缺 QID 走 `x<sha1>` 兜底。

---

## 3. 稳定性保证

| 变更场景 | ref 是否变化 | 说明 |
|---|---|---|
| 重导入同一底本 | **不变** | 仅依赖 work-key + 书内相对序号 |
| 章节正文修订 | **不变** | 与文本内容无关 |
| 表重建 / 主键重排 | **不变** | 与 `chapters.id` 解耦 |
| 书中**插入**一卷（中间位置） | 后续章节序号整体 +1 | **已知代价**：唯一可变情形 |
| 书中**追加**末卷 | **不变** | 末尾追加不影响既有序号 |
| 删除某章 | 其后续章节 -1 | 同上 |

> 设计取舍：为换取"人类可读 + 无需 registry"，接受"中间插入导致重编号"的代价。
> 若未来需要绝对不变，可加 `ref_pin` 表冻结历史映射，作为 v2 演进，不影响现有语法。

---

## 4. 派生与解析

块级引用不入库，运行时按章 ref + 块下标拼接：

```js
// 存储层 blocks[i] 为 0-based；对外 URN 采用 1-based，避免 b000 与"无块"歧义
const blockRef = (chapterRef, i) => `${chapterRef}/b${String(i + 1).padStart(3, "0")}`;
```

解析（Python 已实现于 `migrate_ref.py: parse_ref`，前端需等价实现）：

```js
function parseRef(urn) {
  if (typeof urn !== "string" || !urn.startsWith("dc:")) return null;
  const segs = urn.slice(3).split("/");
  const wk = segs.shift();
  if (!wk) return null;
  const out = { workKey: wk, chapNo: null, block: null, item: null };
  for (const s of segs) {
    const m = /^([cbk])(\d+)$/.exec(s);
    if (!m) return null;
    if (m[1] === "c") out.chapNo = +m[2];
    if (m[1] === "b") out.block = +m[2];
    if (m[1] === "k") out.item = +m[2];
  }
  return out;
}
```

**禁止按字符串排序 chapNo**（`c1000` 会排在 `c999` 前），一律解析为整数比较。

---

## 5. 迁移与回滚

```bash
# 预览（只读，不写库）
python scripts/migrate_ref.py

# 执行（自动整库备份 → 加列 → 回填 → 唯一索引 → 复核）
python scripts/migrate_ref.py --apply

# 独立复核 / 导出 chapter_id → ref 映射
python scripts/migrate_ref.py --verify
python scripts/migrate_ref.py --export ref_map.json

# 回滚（逻辑回滚优先；ref 为纯派生字段，删除零数据损失）
python scripts/rollback_ref.py
python scripts/rollback_ref.py --restore "<备份路径>"
```

`--apply` 具备幂等性：列已存在则跳过 ADD COLUMN，仅重算回填与索引。

---

## 6. 已验证结果（2026-11-01）

| 校验项 | 结果 |
|---|---|
| 回填条数 | 5531 / 5531 |
| ref 空值 | 0 |
| ref 去重数 | 5531（唯一索引 `idx_chapters_ref` 生效） |
| 与算法重算不一致 | 0 |
| `chapters` 主键与既有列 | 与迁移前备份**逐行完全一致**（id/title/ord/chars/文本长度全等） |
| 回滚演练 | 副本上 `DROP COLUMN` 成功，行数 5531 不变，其余 4 个索引完好 |

---

## 7. 前端接入现状（P0-1 第二阶段，2026-11-01 完成）

| # | 接入点 | 状态 | 实现 |
|---|---|---|---|
| 1 | 导出 `ref` | ✅ | `gen-data.mjs` 写 `book-*.json` / `ch/{id}.json`；另出 `public/data/ref-index.json`（workKey → slug + 合法章号表，21 KB） |
| 2 | 阅读页锚点 URN 化 | ✅ | `read.astro` 目录 href 改 `#dc:...`；`parseHash()` 同时接受新 URN 与旧 `#ch-` 锚，旧外链不失效 |
| 3 | 外部 URL 精确命中 | ✅ | 章级短链 `/<workKey>/c<chapNo>/`（构建期生成 5531 页，含 `b`/`k` 段透传）；任意粒度 `/r?urn=dc:...`（客户端查索引校验后跳转，非法 URN 给明确文案） |
| 4 | 导读引证字段 | ✅ | `ai_guides.citations`（JSON 数组）；`scripts/migrate_citations.py` 三级确定性回填（T1 引文逐字 → 块级 / T2 篇名提及 / T3 术语命中），入库前校验 URN 必须能解析；导读页新增「引证 · 原文锚点」区块 |

**引证覆盖现实**：现有 12 篇导读均为改写型散文，只有「论语 × 朱熹读书法」一篇可确定性提取到锚点（4 条），其余 11 篇为
空数组——脚本宁可不填也不猜。真正的引证密度要等 P0-5 按「每段必带引文」的提示词重生成导读后才有意义，
届时同一字段直接承接，前端无需再改。

**粒度约定**：`/<workKey>/c<chapNo>/` 只做**章级**跳转（构建期静态页，5531 个）；块级 `b`、句元级 `k` 走
`/r?urn=dc:<workKey>/c<chapNo>/b<block>/k<item>`，由 `/r` 客户端解析后带 hash 跳转，避免为每块生成静态页。
块/句序号在 URN 中**1-based**（`b001` = 首块），阅读页内部 `data-bi` 为 0-based，`hashFor()` 与 `parseHash()` 成对 ±1 转换。

**自测**：`npm run test:ref` 覆盖跳转 / 块级 / hash 形式 / 章号越界 / 未知书 / 格式错误 / 缺参数 7 个用例，全部通过。

---

## 8. 回滚

- `ref` 层：`python scripts/rollback_ref.py`（纯派生字段，删除零数据损失）。
- `citations` 层：`python scripts/migrate_citations.py --apply` 会打印整库备份路径，覆盖回来即可（SQLite <3.35 不支持 DROP COLUMN）。
- 短链页与 `/r`：均为构建产物，删除 `scripts/postbuild-ref-routes.mjs` 的 postbuild 挂钩即整体下线，源码页面 `src/pages/r.astro` 可保留不影响构建。

*（内容由AI生成，仅供参考）*
