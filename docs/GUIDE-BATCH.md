---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 0c5caf7145ca8876d640e5da87215fbf_a5366de9d5de11f19101525400de85a5
    ReservedCode1: 25RslQe2A+4GlSVf8RbqQC9eu81k0uiD+aBbEfzfZukXU6VwKrJBcoQHbSbXyz3lrQnXFtnJeIJOWfTna4EoM7hvCi36NT/EzUc7zsS5nEdHh1YI5IH968a2NBXPunAtGNkb0hjqaN6hXsPQSqG3QdjWmBeKSRfE73bSkdbOWo+zOG0GS6omTebyBkQ=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 0c5caf7145ca8876d640e5da87215fbf_a5366de9d5de11f19101525400de85a5
    ReservedCode2: 25RslQe2A+4GlSVf8RbqQC9eu81k0uiD+aBbEfzfZukXU6VwKrJBcoQHbSbXyz3lrQnXFtnJeIJOWfTna4EoM7hvCi36NT/EzUc7zsS5nEdHh1YI5IH968a2NBXPunAtGNkb0hjqaN6hXsPQSqG3QdjWmBeKSRfE73bSkdbOWo+zOG0GS6omTebyBkQ=
---

# 36 篇引证式导读：批量生成与跨机搬运手册

> 配套：`docs/GUIDE-CITED.md`（导读的内容标准与校验规则）、`pipeline/gen_guides_cited.py`（单篇生成器）、`pipeline/batch_guides.py`（批量调度 + 打包 + 回传）。

## 1. 目标口径

36 篇 = **4 部书 × 9 种方法**（`multimodal` 不计入正篇）：

| 书 | works.id | 已覆盖 | 缺 |
|---|---|---|---|
| 论语 | 1 | `zhuxi` `sushi` `qianzhongshu` `wangyangming` `adler` `feynman` | `socratic` `arendt` `ibn_khaldun` |
| 老子 | 23 | `arendt` `ibn_khaldun` | 其余 7 |
| 颜氏家训 | 32 | `socratic` `arendt` `ibn_khaldun` | 其余 6 |
| 世说新语 | 33 | `ibn_khaldun` | 其余 8 |

进度随时用一条命令自检（不调模型，秒级）：

```bash
python pipeline/batch_guides.py --plan
```

单篇验收口径（v1.1）：**≥5 段、正文 ≥1000 字、每段 1 处池内逐字引证、论述段落 ≥120 字、无占位符、content 四字段非空**。

## 2. 为什么搬到别的机器跑

本机（8 GB 内存 / Intel HD 630 集显）实测：`qwen2.5:3b` 约 950 秒/篇，`qwen3:4b` 约 60 分钟/篇（3.5 GB 模型有 23 % 溢到 CPU，且 `think:false` 在本机 Ollama 上不生效，需靠标记剥离思维链），24 篇要 9–34 小时。**生成是算力活，搬到强机器上做，本机只负责发布与验收。**

## 3. 搬到另一台机器（三步）

```bash
# ① 代码
git clone <repo> DimensionsCosmos && cd DimensionsCosmos
pip install -r requirements.txt

# ② 数据：只要本机打的小包（2.6 MB，含 4 部书 147 章 + 已有 12 篇导读）
#    本机执行：python pipeline/batch_guides.py --export-pack output/guidepack.db
#    把 output/guidepack.db 拷到异机 DimensionsCosmos/data/guji.db

# ③ 模型：装 Ollama 并拉一个够用的模型
ollama pull qwen3:4b        # 或 qwen2.5:7b / 14b，取决于显存
```

`data/guji.db` 不入版本库（本机 113 MB，全库 50 部书），异机只需要这份 2.6 MB 的小包——四部书、方法义理、底本档案全在里面，`--dry-run` 已验证 8 组方法都能正常构建 prompt。

## 4. 异机生成

```bash
# 先看清单
python pipeline/batch_guides.py --plan

# 全量补齐 24 篇（已有项自动跳过＝断点续跑）
python pipeline/batch_guides.py --run

# 分夜跑：给 8 小时预算，到点优雅退出，第二天重跑同一条命令即续
python pipeline/batch_guides.py --run --max-seconds 28800

# 只补某一部书 / 某一种方法
python pipeline/batch_guides.py --run --only-book 老子
python pipeline/batch_guides.py --run --only-method socratic

# 重写已有篇目（默认不动已有的）
python pipeline/batch_guides.py --run --force --only-book 论语
```

指定模型：与单篇生成器共用环境变量。

```bash
export OLLAMA_MODEL=qwen3:4b        # Windows: set OLLAMA_MODEL=qwen3:4b
export OLLAMA_HOST=http://10.0.0.5:11434   # 模型在另一台机器上时
```

运行痕迹：

- `temp/batch_progress_<时间戳>.jsonl` — 逐篇追加（段数/字数/引证/耗时/告警），中断也不丢
- `temp/batch_report_<时间戳>.json` — 本轮汇总与失败清单
- `temp/rejected_<work>_<method>.json` — 校验没过被拒的原始输出，便于定位

## 5. 回传与合并（关键一步）

生成只写异机的 `guji.db`，**不要回传整个数据库**，只回传导读 JSON：

```bash
# 异机：导出（约 44 KB/12 篇，24 篇约 90 KB）
python pipeline/batch_guides.py --export output/guides.json

# 本机：先试跑校验，再正式合并
python pipeline/batch_guides.py --import output/guides.json --dry-run
python pipeline/batch_guides.py --import output/guides.json
```

合并规则：

- 按**书名**（`works.seed_title`）映射工作区 id，不依赖自增 id，异机与本机的 id 不必一致
- 幂等：同一份 JSON 重复导入不会产生重复行
- 覆盖前把旧导读备份到 `temp/backups/import_<时间戳>/<书名>_<方法>.json`，可回滚
- 未知方法、本地无此书 → 跳过并列出，不写入

往返自测已通过：主库导出 → 清空副库 → 导入 → 12 篇逐字段摘要哈希一致（`digest=bbb14b81…`）。

## 6. 本机发布（异机回传之后）

```bash
python pipeline/batch_guides.py --plan          # 应显示 36/36
npm run build                                    # 前端构建（退出码 0）
git add data docs pipeline && git commit -m "feat: 补齐 36 篇引证式导读"
git push                                         # Cloudflare 自动构建
```

线上验证：`/work/<qid>` 页导读段数与引证数、`/r/dc:<qid>/c<n>/b<m>` 短链 200。

## 7. 已知坑

| 现象 | 原因 / 处置 |
|---|---|
| `qwen3:4b` 返回的是「首先，用户要求…」思维链 | 该机器 Ollama 的 `think:false` 未生效；在 prompt 里加 `===正文===` 分隔标记再剥离，或升级 Ollama |
| 段落数不足 / 论述过短 | 3B 模型整篇生成会偷工；v1.1 走 `--segmented`（逐段单独生成，程序绑引文），默认开启 |
| 引证对不上原文 | 只用 `quote_mode=auto`：引文由程序从候选池按块绑定，不交给模型手抄 |
| 单篇超时 | 先把 `--max-tokens` 降到 2400，或换 7B 以上模型；3B 单段约 150 秒属正常 |
| 导入后页面没变化 | 前端读的是 `data/guji.db` 的 `ai_guides`；确认导入了主库而非 guidepack，再重新 `npm run build` |
*（内容由AI生成，仅供参考）*
