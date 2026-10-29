-- P1 知识层建表（幂等，可重复执行）
-- 设计约束：零算力优先、人工可核定、字段留 confidence 便于"可信/推测"分级展示

-- 1) 书籍档案：版本 / 成书 / 作者 / 背景 / 结构 / 阅读建议
CREATE TABLE IF NOT EXISTS work_profiles (
  work_id       INTEGER PRIMARY KEY REFERENCES works(id),
  version_text  TEXT,            -- 底本与版本，如「中华书局 2016 杨伯峻《论语译注》本」
  version_source TEXT,           -- 版本依据（ISBN / 网址 / 文库页）
  compiled_year TEXT,            -- 成书年代（区间亦可）
  author_note   TEXT,            -- 作者小传（100-200 字）
  background    TEXT,            -- 成书背景与思想脉络
  structure_note TEXT,           -- 全书结构说明
  reading_tip   TEXT,            -- 读法建议（先读哪几篇）
  confidence    TEXT DEFAULT 'draft',  -- draft/verified
  updated_at    TEXT
);

-- 2) 注释：字层（说文）/ 词层（人工）/ 句层（AI，需标注来源）
CREATE TABLE IF NOT EXISTS glosses (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  work_id    INTEGER NOT NULL REFERENCES works(id),
  chapter_id INTEGER REFERENCES chapters(id),
  layer      TEXT NOT NULL CHECK (layer IN ('char','word','sentence')),
  term       TEXT NOT NULL,
  gloss      TEXT NOT NULL,
  source     TEXT,               -- shuowen / manual / ai:qwen2.5-1.5b ...
  confidence TEXT DEFAULT 'draft',
  verified   INTEGER DEFAULT 0,
  created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_glosses_lookup ON glosses(work_id, chapter_id, term);
CREATE INDEX IF NOT EXISTS idx_glosses_term ON glosses(term);

-- 3) 章旨：一句话主旨 / 白话 / 要点 / 主题
CREATE TABLE IF NOT EXISTS chapter_notes (
  chapter_id INTEGER PRIMARY KEY REFERENCES chapters(id),
  summary    TEXT,               -- 一句话章旨
  vernacular TEXT,               -- 白话译文
  key_points TEXT,               -- JSON 数组
  themes     TEXT,               -- JSON 数组
  source     TEXT,
  confidence TEXT DEFAULT 'draft',
  updated_at TEXT
);

-- 4) 方法学：每法一篇七段式
CREATE TABLE IF NOT EXISTS method_doctrines (
  method_id    TEXT PRIMARY KEY,
  name         TEXT NOT NULL,
  one_line     TEXT,
  definition   TEXT,
  origin       TEXT,             -- 出处（人物/典籍/年代）
  principle    TEXT,             -- 原理
  logic        TEXT,             -- 底层逻辑
  steps        TEXT,             -- JSON 数组：可执行步骤
  applicable   TEXT,             -- 适用文本类型
  misuse       TEXT,             -- 常见误用
  updated_at   TEXT
);

-- 5) 策展图谱
CREATE TABLE IF NOT EXISTS graph_nodes (
  id     TEXT PRIMARY KEY,       -- 如 person:zhu-xi / work:13 / concept:li
  kind   TEXT NOT NULL,          -- person / work / concept / school / event
  label  TEXT NOT NULL,
  work_id INTEGER REFERENCES works(id),
  meta   TEXT
);
CREATE TABLE IF NOT EXISTS graph_edges (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  src      TEXT NOT NULL REFERENCES graph_nodes(id),
  dst      TEXT NOT NULL REFERENCES graph_nodes(id),
  relation TEXT NOT NULL,        -- 師承/註/引/同源/評/...
  note     TEXT,
  verified INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_edges_src ON graph_edges(src);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON graph_edges(dst);
