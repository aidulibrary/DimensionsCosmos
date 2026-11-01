#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rollback_ref.py — P0-1「稳定引用层」回滚脚本

两种回滚方式
-----------
1) 逻辑回滚（默认，推荐）：删除唯一索引 + 删除 chapters.ref 列。
   ref 是纯派生字段（由 work QID/书名 + 书内 ord 序号推导），
   删除后原始数据零损失，重新执行 migrate_ref.py --apply 即可完全复原。

2) 文件级恢复（--restore <bak>）：用备份整库覆盖 data/guji.db。
   覆盖前会把当前库另存一份，避免二次损失。

用法
----
    python scripts/rollback_ref.py
    python scripts/rollback_ref.py --restore "C:\\...\\temp\\backups\\guji.db.20261101-xxxxxx.bak"
"""
import argparse
import os
import shutil
import sqlite3
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "guji.db")
COL = "ref"
IDX = "idx_chapters_ref"


def cols_of(con, table="chapters"):
    return [r[1] for r in con.execute(f"PRAGMA table_info({table})")]


def logical_rollback(db):
    con = sqlite3.connect(db)
    try:
        cur = con.cursor()
        cols = cols_of(con)
        if COL not in cols:
            print("chapters.ref 不存在，无需回滚。")
            return
        rows = cur.execute("SELECT COUNT(*) FROM chapters WHERE ref IS NOT NULL").fetchone()[0]
        try:
            cur.execute("BEGIN IMMEDIATE")
            cur.execute(f"DROP INDEX IF EXISTS {IDX}")
            # SQLite >= 3.35 支持 DROP COLUMN
            cur.execute(f"ALTER TABLE chapters DROP COLUMN {COL}")
            con.commit()
        except Exception as e:
            con.rollback()
            sys.exit(f"[FATAL] 回滚失败，事务已撤销：{e}\n"
                     f"可用文件级恢复：python scripts/rollback_ref.py --restore <bak>")
        print(f"[OK] 已删除索引 {IDX} 与列 chapters.{COL}（受影响行 {rows}）")
        print("     自增主键 id 与其它列未被触碰。")
    finally:
        con.close()


def file_restore(db, bak):
    if not os.path.exists(bak):
        sys.exit(f"备份不存在：{bak}")
    os.makedirs(os.path.dirname(db), exist_ok=True)
    safety = db + ".before-restore." + time.strftime("%Y%m%d-%H%M%S")
    if os.path.exists(db):
        shutil.copy2(db, safety)
        print(f"[1/2] 当前库已另存 -> {safety}")
    shutil.copy2(bak, db)
    # 清理残留 WAL/SHM，避免旧日志覆盖恢复结果
    for ext in ("-wal", "-shm", "-journal"):
        p = db + ext
        if os.path.exists(p):
            os.remove(p)
            print(f"    已清理 {os.path.basename(p)}")
    print(f"[2/2] 已从备份恢复 -> {db}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--restore", metavar="BAK")
    ap.add_argument("--db", default=DB)
    a = ap.parse_args()
    if a.restore:
        file_restore(a.db, a.restore)
    else:
        logical_rollback(a.db)


if __name__ == "__main__":
    main()
