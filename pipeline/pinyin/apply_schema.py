# -*- coding: utf-8 -*-
"""
import sqlite3
import pathlib
import sys

DB = pathlib.Path(r"D:\DimensionsCosmos\data\guji.db")
DDL = pathlib.Path(__file__).with_name("schema_pinyin.sql")


def main() -> int:
    if not DB.exists():
        print(f"[FATAL] 目标库不存在：{DB}")
        return 2
    sql = DDL.read_text(encoding="utf-8")
    con = sqlite3.connect(str(DB))
    try:
        con.executescript(sql)
        con.commit()
        cur = con.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'pinyin%' "
            "OR name IN ('chapter_pinyin','char_historical_phon','gold_sentence') ORDER BY name"
        )
        tables = [r[0] for r in cur.fetchall()]
        print("[OK] 已建/已存在表：", ", ".join(tables))
        for t in tables:
            n = cur.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
            print(f"       {t:<22} rows={n}")
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
