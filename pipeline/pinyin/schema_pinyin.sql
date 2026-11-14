-- =====================================================================
-- 维点图书馆 · 古籍注音 FLCA-6 数据模型（V3.0 定版）
-- 目标库：D:\DimensionsCosmos\data\guji.db
-- 生成：2026-11-11 ｜ 依据：V2.0 §7.1，V3.0 契约修订见 §5
-- 执行：python pipeline\pinyin\apply_schema.py
-- =====================================================================
-- 【V3.0 相对 V2.0 的两处工程修订】
--   修订1：chapter_pinyin 主键去掉 build_id（V2.0 为 4 列复合主键）。
--          理由：全库 2156 万行，build_id 入主键会使每次重建索引体积翻倍且无法就地覆盖；
--          改为 build_id 普通列 + 重建前按 build_id 删除，可复现性由 pinyin_build 表 + 分片哈希保证。
--   修订2：新增 pinyin_rule 表（L0.5 规则层）。D2-b 专家后置后，规则层承担破读/通假的第一道
--          判音职责，规则必须入库可审计、可版本化，不能硬编码在脚本里。
-- =====================================================================

-- 1) 音项字典：每个字/词的合法读音集合 P(c)，L1 约束解码的唯一合法音来源
CREATE TABLE IF NOT EXISTS pinyin_lexicon (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  surface      TEXT NOT NULL,              -- 字或词
  reading      TEXT NOT NULL,              -- 拼音（带调，ü 用 v 前置转换在读取时处理）
  reading_type TEXT NOT NULL DEFAULT 'normal',  -- normal|poDu|tongJia|yeYin|guJinZi|properNoun
  authority    TEXT NOT NULL,              -- shenYinBiao|cidian|zhuben|expert|model
  source_ref   TEXT,                       -- 具体出处（数据集名/条目/URL）
  rank         INTEGER DEFAULT 99,         -- 常用度排序（1=默认高频音）
  UNIQUE(surface, reading, reading_type)
);
CREATE INDEX IF NOT EXISTS idx_lex_surface ON pinyin_lexicon(surface);

-- 2) 正文注音（按字符偏移，与 chapters.text 解耦；正文零污染）
CREATE TABLE IF NOT EXISTS chapter_pinyin (
  chapter_id   INTEGER NOT NULL,
  char_offset  INTEGER NOT NULL,           -- 在 chapter.text 中的字符偏移（0-based）
  surface      TEXT NOT NULL,              -- 该位置字形（校勘后）
  reading      TEXT,                       -- 主读音（NULL = uncertain）
  reading_alt  TEXT,                       -- JSON 数组：并列读音（variant 时）
  state        TEXT NOT NULL,              -- asserted|variant|uncertain
  confidence   REAL,                       -- L0.5/L1 置信度
  reading_type TEXT NOT NULL DEFAULT 'normal',
  layer        TEXT NOT NULL DEFAULT 'modern',  -- modern|historical
  authority    TEXT,                       -- 本音裁定来源
  rule_id      INTEGER,                    -- 命中的 pinyin_rule.id（NULL=L0 默认音）
  build_id     TEXT NOT NULL,
  PRIMARY KEY (chapter_id, char_offset, layer)
);
CREATE INDEX IF NOT EXISTS idx_cp_build ON chapter_pinyin(build_id);
CREATE INDEX IF NOT EXISTS idx_cp_state ON chapter_pinyin(build_id, state);

-- 3) 证据链（学术贡献载体 A2；L2 层写入）
CREATE TABLE IF NOT EXISTS pinyin_evidence (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  chapter_id        INTEGER NOT NULL,
  char_offset       INTEGER NOT NULL,
  candidate_reading TEXT NOT NULL,
  evidence_source   TEXT NOT NULL,         -- 注本/韵书/语料/专家
  evidence_ref      TEXT NOT NULL,         -- 可定位引用（卷次/条目/URL）
  evidence_quote    TEXT,                  -- 原文片段
  support_strength  INTEGER,               -- 1..5（5=直接注音）
  verdict           TEXT,                  -- support|refute|neutral
  created_by        TEXT NOT NULL,         -- pipeline|expert
  build_id          TEXT,
  UNIQUE(chapter_id, char_offset, candidate_reading, evidence_source, evidence_ref)
);
CREATE INDEX IF NOT EXISTS idx_ev_locus ON pinyin_evidence(chapter_id, char_offset);

-- 4) 中古音层（L3，D1-b/D6-b）
CREATE TABLE IF NOT EXISTS char_historical_phon (
  surface        TEXT NOT NULL,
  period         TEXT NOT NULL,            -- middleChinese|oldChinese|poeticRhyme
  fanqie         TEXT,                     -- 反切
  initial        TEXT, final TEXT, tone TEXT,
  she            TEXT, deng TEXT, kaIHe TEXT,   -- 摄/等/开合
  rhyme_group    TEXT,                     -- 平水韵韵部
  reconstruction TEXT,                     -- 拟音（含来源前缀，如 BS:*Cə-mˤraŋ）
  tone_ping_ze   TEXT,                     -- 平|仄（派生）
  source         TEXT NOT NULL,
  PRIMARY KEY (surface, period, fanqie)
);

-- 5) 规则库（L0.5；D2-b 专家后置阶段的判音主力，可审计可版本化）
CREATE TABLE IF NOT EXISTS pinyin_rule (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  rule_key     TEXT NOT NULL UNIQUE,       -- 稳定标识，如 poDu.wang.verb_tianxia
  surface      TEXT NOT NULL,              -- 目标字
  reading      TEXT NOT NULL,              -- 目标读音
  reading_type TEXT NOT NULL,              -- poDu|tongJia|yeYin|guJinZi|properNoun
  pattern      TEXT NOT NULL,              -- 正则（作用在含目标字的句窗上）
  priority     INTEGER DEFAULT 50,         -- 越大越优先，冲突时取高
  authority    TEXT NOT NULL,              -- zhuben|expert|model
  source_ref   TEXT NOT NULL,              -- 依据出处（注本/辞书条目）
  note         TEXT,
  enabled      INTEGER DEFAULT 1,
  created_at   TEXT DEFAULT (datetime('now','localtime'))
);

-- 6) 构建元数据（D7-b 可复现锚点）
CREATE TABLE IF NOT EXISTS pinyin_build (
  build_id     TEXT PRIMARY KEY,
  built_at     TEXT,
  engine       TEXT,                       -- 如 L0.5-rule-v1
  model_hash   TEXT,
  lexicon_hash TEXT,
  rule_hash    TEXT,
  corpus_hash  TEXT,
  config_json  TEXT,
  stats_json   TEXT,                       -- 覆盖率/三态分布/命中分布
  notes        TEXT
);

-- 7) 金标语料台账（A1 载体；D2-b 后置 → 先由 AI 预标 + 双模型交叉，专家后置复核）
CREATE TABLE IF NOT EXISTS gold_sentence (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  gid          TEXT NOT NULL UNIQUE,       -- ccp-000001
  work_id      INTEGER,
  chapter_id   INTEGER,
  source_title TEXT,
  dynasty      TEXT,
  genre        TEXT,
  text         TEXT NOT NULL,
  tokens_json  TEXT,
  focus_json   TEXT,                       -- 焦点字/候选音/证据/标注人
  label_status TEXT DEFAULT 'ai_pre',      -- ai_pre|ai_dual|expert_final|disputed
  annotators   INTEGER DEFAULT 0,
  agreement    TEXT,                       -- unanimous|majority|split
  build_id     TEXT,
  created_at   TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_gold_status ON gold_sentence(label_status);
