# 古籍扩容执行记录 · batch7（2026-11-02，选本子批）

> 依据：《维点图书馆 · 新增古籍筛选及入选顺序标准 v1.2.3》（`docs/CORPUS-ACQUISITION-STANDARD-v1.2.md`）
> 性质：**选本/分卷子批**（v1.2.3 新增条款首次落地），不是常规整本入册批。
> 一句话结论：朱子语类 193.3 万字全本无法整本入册，按新条款取「理学纲领」十三卷成选本入册（work_id 162），全库达 **112 部 / 10075 章**，子部「理学语录」主线由 🟡 转 ✅。

---

## 一、立项依据：为什么必须走选本而不是整本

| 约束 | 实际 | 结论 |
|---|---|---|
| §2.6 单批正文 ≤ 150 万字 | 朱子语类全本 140 卷 **193.3 万字**（`slice` 实测 1933495 字） | 单部即超一批容量，整本入册违反 P10「有界扩张」 |
| §P3 / §P4 可读完 | 语录体 140 卷，含论语、孟子、易、诗、礼、释老、本朝及历代、作文、杂类 | 全本对读者不成立，须选篇 |
| §2.5 T2 断线优先 | 子部「理学语录」为唯一 🟡 待选篇主线 | 选卷须服务断线，而非平铺 |

即：**超容不是放弃理由，也不是压缩进单批的理由**。v1.2.3 §2.7「选本/分卷子批口径」为此立规：脚本裁剪可复算、标题带「选本」、`version_text` 声明非全本、余卷留账、不受短制条款豁免。

## 二、选卷口径与裁剪

**选卷**（理学纲领十三卷，按主线取轴）：

| 卷 | 内容 | 处置 |
|---|---|---|
| 1–2 | 理气（太极、天地、鬼神附） | 收 |
| 3 | 鬼神 | 收 |
| 4–6 | 性理（性、人物之性、气质之性） | 收 |
| 7–13 | 学（小学、总论为学、论知行、读书法上下等） | 收 |
| 14–140 | 论语、孟子、易、诗、礼、春秋、朱子自述、吕陆陈诸家、释老、本朝及历代、杂类、作文 | **未收，留账** |

**裁剪脚本**：`pipeline/slice_zhuzi_yulei.py`（卷号白名单 + 中文卷序换算，输出确定性文本，无时间戳）

- 复算入口：`python pipeline/slice_zhuzi_yulei.py --vols 1-13 --write`
- 复算实测：输出 410260 bytes，SHA256 重跑一致（`3863d2b3f82cf91d…`），**可复算成立**
- 计字口径差：切片合计 135778 字（含 13 行卷题），入册 `total_chars` = **135717 字**（切章后仅正文），差 61 字为卷题行，非丢字

**切章配置**（`pipeline/daizhige_corpus_config.py` 的 `batch=7` 段）：

```python
"朱子语类选本": dict(batch=7, file="_slices/朱子语类_选本卷一至卷十三.md",
               bu="子", mode="re", re=r"^卷[一二三四五六七八九十]+ \S+$",
               prefix="朱子语类选本", sep="·", max_title=24, min_chars=300, note=…)
```

- `re` 以「卷X + 空格 + 篇题」定界，实测 13 卷全命中、0 空章；
- `sep="·"` 生成 `朱子语类选本·理气上` 式章题，与既有库命名一致。

## 三、执行结果

| 步骤 | 命令 | 结果 |
|---|---|---|
| 写库 | `python pipeline/run_import.py --batch 7 --apply` | work_id=162，**13 章 / 135717 字**，`quality=ok`，0 空章 0 重复章 |
| 元数据 | `python pipeline/backfill_works_meta.py --apply` | 162：`bu=子部` / `author=朱熹` / `dynasty=南宋` / `ws_title=朱子語類選本`（OpenCC s2twp）；**待更新 62 部一次写清**，写后 `author 空缺=0`、`dynasty 空缺=0`、`bu 未归一=0` |
| 引用层 | `python scripts/migrate_ref.py --apply` | dry-run 显示 ref 空 13 条、与算法不一致 13 条（均为新章）→ apply 后 `ref_null=0`、`ref_distinct=10075`、`mismatch=0`；**旧 10062 条 ref 未变动**，P7「既有结论不失效」成立 |
| 站点构建 | `npm run build` | 1360 页，`postbuild` 输出 **112 条 workKey / 10075 条 URN**，sitemap **238 个 URL** |
| 索引 | `public/data/index.json` | `total=112 ok=112 readable=112 works=112`，`generatedAt=2026-11-02T06:40:48Z` |

**六项交付标准逐项核验（S1–S6）**：

| # | 标准 | 162 号实测 | 判定 |
|---|---|---|---|
| S1 | 入库完整 | 13 章 / 135717 字，`status=ok`，0 空章 | ✅ |
| S2 | 稳定引用 | `dc:xf69aaae4/c001`–`c013` 全唯一，全库 `ref` 覆盖 10075/10075 | ✅ |
| S3 | 元数据 | author/dynasty/bu/ws_title 齐全（`wikidata_qid` 空，见缺口） | ✅（qid 单列债务） |
| S4 | 版本说明 | `version_text` 写明「取卷 1–13 … 余 127 卷未收，属选本，非全本」；`version_source` 含殆知阁 CC BY-SA 4.0 | ✅ |
| S5 | 站点可读 | `dist/read/162-朱子语类选本/`（10 种导读方法入口页：zhuxi/feynman/socratic/adler/qianzhongshu/sushi/wangyangming/arendt/ibn_khaldun/multimodal）+ `dist/books/162-朱子语类选本/` + `book-162.json`（13 章）+ `ch/19080–19092.json` | ✅ |
| S6 | 可发现性 | workKey 动态路由覆盖 + sitemap 收录（238 URL） | ✅ |

全库：**112 部 / 10075 章 / 章字合计 2639.7 万字**（`works.total_chars` 合计 2609.2 万字）；四部 经 20 / 史 21 / 子 44 / 集 27；`incomplete` 仍 92 条（全在旧库，batch4–7 新书 0 条）。

## 四、标准与编号

- 标准升 **v1.2.3**：§2.7 新增「选本/分卷子批口径」五条；§3.2 编号推进 batch7=162、下一批 163 起；§4 基线更新至 112 部 / 10075 章，子部「理学语录」🟡→✅；§4 增「联网能力」一行。
- 本批不新增切章模式（`re` 为既有模式），未触及 §2.6「新模式 ≤3」约束。

## 五、缺口账本（batch7 收尾后）

### 本机已偿

| 缺口 | 状态 |
|---|---|
| 朱子语类容量卡点（超 150 万字一批） | ✅ 以选本入册，余卷留账 |
| batch6 未落库的元数据（62 部 bu 归一 / author / dynasty / ws_title） | ✅ 一次 apply 写清，三项空缺均为 0 |
| 162 号 ref / 页面 / sitemap / 索引 | ✅ 全齐 |

### 本机不可偿（须移交，见第六节）

| 缺口 | 规模 | 不可就地偿的原因 |
|---|---|---|
| `wikidata_qid` 空 | **63 部**（含 162） | 本机外网 SSL 不可达：`urllib` 与 `web_fetch` 对 Wikidata / Wikisource / ctext 均超时；qid 禁造，不得凭记忆填 |
| D3 学术史核验（全部 `provisional`） | 122 部 | 同上，须外网权威来源 |
| AI 导读过闸 | 112 部仅 1 篇；本批 `guides=[]`，构建日志「质量闸门拦下 11 篇」 | 导读生成依赖模型质量与配比，非本批交付范围；162 号待补 |
| `compiled_year` 未满 | 多部 | 依赖 D3 核验结果 |
| `incomplete` 章 92 条（71 条 `chars=0`） | 全在旧库（论语、诗经、公羊传、谷梁传、东京梦华录、廿二史札记、日知录、聊斋志异、管子、春秋繁露等） | 底本缺栏与注疏体噪音交织，须逐部换底本或补章，超出单批范围 |
| 幼学琼林（136）仅卷一二、海国图志（135）单章 | 2 部 | 源文件远大于已入内容，须补章批次 |
| 朱子语类余 127 卷 | 1 部 | 可续立「选本二」（卷 14–40 论语/孟子等），各占独立 work_id |
| 方志 / 药学总集 / 农书总集 / 蒙学千字文系 | 4 条主线 | 卡点均为 §2.4「C 档不升」（华阳国志 2.77、本草纲目 2.36、农政全书 2.23、千字文 2.25），须先补 D3 核验或走 §3.7 仲裁 |

## 六、移交清单（给另一台设备的 marvis）

> 前置：在具备外网（可访问 wikidata.org / zh.wikisource.org / ctext.org）的设备上、同一仓库 `D:\DimensionsCosmos`、同一 `data/guji.db` 上执行。所有操作幂等、写前快照。

1. **补 63 部 `wikidata_qid`**
   - 脚本：`pipeline/wikidata.py`（既有）。先 `--dry-run` 只读比对，确认无冲突再 `--apply`。
   - 约束：查不到就留空并登记，**禁止推测填写**；`wikidata_qid` 有唯一性要求，写前查重。
   - 验收：`SELECT count(*) FROM works WHERE wikidata_qid IS NULL OR wikidata_qid=''` 由 63 降为 0（或全部登记为「确无条目」）。
2. **D3 学术史核验（122 部 provisional → verified）**
   - 逐部按 `data/corpus_scores.csv` 的 `d3_evidence` 列补权威依据（专著/论文/权威书目），核验后重跑 `pipeline/score_corpus.py --report`，确认 0 错误、档位变动留档。
   - 122 部建议分批（每批 20–30 部），每批落一份核验清单。
3. **AI 导读补写与过闸**
   - 入口：`pipeline/batch_guides.py`、`pipeline/gen_guides_cited.py`；质量闸门见构建日志（当前 11 篇被拦）。
   - 优先补 162 号（`guides=[]`），再按主线补 🟡 部次。
4. **旧库 92 条 `incomplete` 章整改**
   - 71 条 `chars=0` 优先：按 `version_text` 换底本或按 §P9 声明阙栏；注疏体噪音部（诗经等）须重选白文本底本。
5. **幼学琼林 / 海国图志 补章**，及 **朱子语类「选本二」**（卷 14–40）：各立新 batch（batch8 起，work_id 163 起），复用本批脚本与条款。
6. **四条 C 档主线**：先补 D3 或走 §3.7 仲裁，未过闸不得放行（§2.4 硬约束）。
7. **收尾**：`npm run build` → 校验 `dist/data/index.json` 的 `total`/`generatedAt` → `git add -A && git commit && git push` → CI success → 线上 `data/index.json` 复验（线上以 `index.json` 为唯一验收口径）。
8. **线上验收（本机未完成，必须由外网设备补做）**
   - 本机 `git push` 走 SSH 正常（`e3825a63..4fdf01b2` 已推，本地与 `origin/main` 0/0 同步），但 HTTPS/DNS 全部不可达：`urllib` → `getaddrinfo failed`、`curl.exe` 无输出、`web_fetch` 浏览器启动失败，故 pages.dev 拉取与 GitHub Actions 轮询均无法在本机完成。
   - 补做方式：`curl -s https://dimensions-cosmos.pages.dev/data/index.json` 校验 `total=112`、`generatedAt` 晚于 `2026-11-02T06:40:48Z`；抽查 `/read/162-朱子语类选本/`、`/books/162-朱子语类选本/`、`/data/ch/19080.json`、短链 302 与 sitemap（应含 238 URL）；GitHub Actions 确认该 commit 的 CI success。

## 七、复算与回滚

- 复算：`python pipeline/score_corpus.py --report`；`python pipeline/run_import.py --batch 7`（dry-run，不入库）；`python pipeline/slice_zhuzi_yulei.py --vols 1-13`（只列字数，不写盘）
- 回滚：库快照 `..\temp\backups\guji.db.20261102-143844.bak`；引用层 `python scripts/rollback_ref.py`
- 本批改动文件：`pipeline/daizhige_corpus_config.py`（batch7 段）、`pipeline/backfill_works_meta.py`（META 增 162）、`pipeline/slice_zhuzi_yulei.py`（新增）、`public/data/*`（构建产物）
