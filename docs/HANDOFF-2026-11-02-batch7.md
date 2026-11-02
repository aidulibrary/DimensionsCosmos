# 移交任务书（2026-11-02，batch7 收尾后）

> 给：另一台设备的 Marvis（须具备外网：wikidata.org / zh.wikisource.org / ctext.org / *.pages.dev / api.github.com）
> 仓库：`DimensionsCosmos`（github.com:aidulibrary/DimensionsCosmos，分支 main，当前 head `0dfa0d13`）
> 数据库：`data/guji.db`（112 部 / 10075 章）；标准：`docs/CORPUS-ACQUISITION-STANDARD-v1.2.md` **v1.2.3**
> 本机（交出方）已完成：batch7 选本入库、元数据 62 部补齐、引用层 10075/10075、站点构建、push（本地与 origin 0/0）。
> 本机无法完成的原因：HTTPS/DNS 全不可达（`urllib` getaddrinfo failed、`curl` 无输出、`web_fetch` 浏览器启动失败），仅 SSH 可用。

---

## 任务 0（先做）：线上验收 batch7

```bash
curl -s https://dimensions-cosmos.pages.dev/data/index.json   # 期望 total=112，generatedAt > 2026-11-02T06:40:48Z
curl -sI https://dimensions-cosmos.pages.dev/read/162-朱子语类选本/            # 200
curl -sI https://dimensions-cosmos.pages.dev/books/162-朱子语类选本/           # 200
curl -s  https://dimensions-cosmos.pages.dev/data/ch/19080.json                # 首章 JSON 可读
curl -s  https://dimensions-cosmos.pages.dev/sitemap.xml | grep -c "<loc>"     # 应为 238
```
另需在 GitHub Actions 确认 commit `4fdf01b2` / `0dfa0d13` 的 CI success。若失败，看 `ingest.yml` / build 日志，修好重推。

## 任务 1：补 63 部 `wikidata_qid`

- 脚本：`pipeline/wikidata.py`（先 `--dry-run` 只读比对，再 `--apply`，写前快照 `data/guji.db` 到仓库外 `.backups/`）
- 约束：**查不到就留空并登记「确无条目」，严禁推测或凭记忆填**；qid 有唯一性，写前查重。
- 验收：`SELECT count(*) FROM works WHERE wikidata_qid IS NULL OR wikidata_qid=''` → 0（或全部有登记结论）

## 任务 2：D3 学术史核验（122 部 provisional → verified）

- 数据：`data/corpus_scores.csv` 的 `d3` 与 `d3_evidence` 列
- 每批 20–30 部，补权威依据（专著 / 论文 / 权威书目），每批落一份核验清单到 `docs/`
- 核验后重跑 `pipeline/score_corpus.py --report`，确认 0 错误；档位如变动须在结论文档写明理由

## 任务 3：AI 导读补写

- 入口：`pipeline/batch_guides.py`、`pipeline/gen_guides_cited.py`；质量闸门在构建时执行（当前日志「拦下 11 篇」）
- 优先补 **162 号 朱子语类选本**（`guides=[]`），再按主线补 🟡 部次
- 验收：`npm run build` 后 `dist/data/index.json` 的 `guidesCount` 上升，且被拦数下降

## 任务 4：旧库 92 条 `incomplete` 章整改

- 71 条 `chars=0` 优先处理（论语、诗经、汉书、公羊传、谷梁传、东京梦华录、廿二史札记、日知录、聊斋志异、管子、春秋繁露等）
- 处置只有两条合法路径：① 换可读白文本底本重切；② 底本确阙则按 §P9 在 `version_text` 显式声明（不得静默留空）
- 诗经等注疏体噪音部须重选白文本，不得直接沿用注疏底本

## 任务 5：补章与续批

- 幼学琼林（id 136）现仅卷一二、海国图志（id 135）现单章 → 从 `data/sources/daizhige` 底本补章
- 朱子语类「选本二」（卷 14–40，论语 / 孟子等）→ 复用 `pipeline/slice_zhuzi_yulei.py --vols 14-40 --write`，新 batch（batch8 起，work_id 163 起）
- 全部按 v1.2.3 §2.7「选本/分卷子批口径」执行：脚本裁剪可复算、`seed_title` 带「选本」、`version_text` 声明非全本、余卷留账

## 任务 6：四条 C 档主线（不得跳闸）

方志（华阳国志 2.77）、药学总集（本草纲目 2.36）、农书总集（农政全书 2.23）、蒙学千字文系（千字文 2.25 等 4 种）。

- 卡点：§2.4「C 档不升」硬约束
- 合法出路只有两条：① 补 D3 核验 / 复核 D5 依据后按分档规则重判；② 走 §3.7 例外仲裁并留档（须业主裁定）
- 未过闸前**禁止**直接入库

## 通用纪律

1. 每一步写库前 `data/guji.db` 快照到仓库外 `.backups/`；引用层改动后跑 `scripts/migrate_ref.py --apply`，并核对旧 ref 零变动（P7）
2. 命令入口只用 `pipeline/run_import.py`（`import_daizhige_corpus.py` 是底层库，不是 CLI）
3. 收尾六项交付标准 S1–S6 逐项自检（见标准 §2.8）；`npm run build` 通过后再 push
4. 线上验收唯一口径：`data/index.json` 的 `total` 与 `generatedAt`
5. 每批落 `docs/CORPUS-EXPANSION-2026-11-batchN.md`，并同步标准 §3.2 编号、§4 基线、附录 C 变更记录
