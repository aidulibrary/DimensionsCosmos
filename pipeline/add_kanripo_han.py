#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为《汉书》补充 Kanripo KR2a0007 前漢書（武英殿本，含顏師古注）可读注本证据。

用法：python add_kanripo_han.py [--dry-run]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

EV = Path(r"D:\DimensionsCosmos\data\evidence")
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

BT_HAN = ("白文本百二十卷（纪12、表8、志10、传70），无注，卷次与《武英殿二十四史》本"
          "（ctext ctp:han-shu）一致；表部卷十三至二十为表格内容，已归档文本有省略")

ENTRY = {
    "grade": "B", "weight": 0.85, "source_name": "Kanripo漢籍リポジトリ",
    "url": "https://www.kanripo.org/ed/KR2a0007/WYG/100",
    "fields": {"base_text": BT_HAN},
    "quote": "KR2a0007 前漢書-漢-班固（WYG 武英殿本，含顏師古注全文可读，起髙祖終孝平，百篇；可作注本对读）",
}

TIP_HAN = ("本库正文为白文本（约90万字），无颜师古注，适合通读、检索与统计；深度研读（尤其律历、地理、礼乐诸志）"
           "建议对读中华书局点校本（ISBN 9787101079869）或 Kanripo KR2a0007 前漢書（武英殿本，含顏師古注）。"
           "注意：表部卷十五下、卷十九下底本以“表略”省略，表内容需另查印本或 ctext《武英殿二十四史》本。")


def main() -> int:
    dry = "--dry-run" in sys.argv
    p = EV / "work_14.json"
    payload = json.loads(p.read_text(encoding="utf-8"))
    old_urls = {e["url"] for e in payload["entries"]}
    if ENTRY["url"] not in old_urls:
        payload["entries"].append({**ENTRY, "grabbed_at": NOW})
        payload["entries"].sort(key=lambda x: -x["weight"])
    print(f"[evid] work=14 《{payload['title']}》 累计 {len(payload['entries'])} 条")
    if not dry:
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[evid] 已写盘")

    # reading_tip 增补 Kanripo 注本对读路径
    import sqlite3
    db = sqlite3.connect(r"D:\DimensionsCosmos\data\guji.db")
    db.execute("UPDATE work_profiles SET reading_tip=? WHERE work_id=14", (TIP_HAN,))
    db.commit()
    print("[profile] work=14 reading_tip 已更新")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
