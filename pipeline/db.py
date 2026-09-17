"""SQLite 数据底座。零成本、单文件、可直接提交进 git 随 Actions 更新。"""
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS taxonomy (
  name   TEXT PRIMARY KEY,
  parent TEXT,
  qid    TEXT
);

CREATE TABLE IF NOT EXISTS works (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  seed_title   TEXT NOT NULL UNIQUE,   -- 种子表标准书名
  ws_title     TEXT,                   -- 维基文库实际页面名（重定向后）
  bu           TEXT,                   -- 经部/史部/子部/集部
  author       TEXT,
  dynasty      TEXT,
  wikidata_qid TEXT,
  status       TEXT NOT NULL DEFAULT 'pending',  -- pending / ok / missing
  fetched_at   TEXT
);

CREATE TABLE IF NOT EXISTS chapters (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  work_id INTEGER NOT NULL REFERENCES works(id),
  title   TEXT NOT NULL,               -- 章节页面名
  text    TEXT,
  chars   INTEGER DEFAULT 0,
  UNIQUE (work_id, title)
);

CREATE INDEX IF NOT EXISTS idx_chapters_work ON chapters(work_id);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    return conn
