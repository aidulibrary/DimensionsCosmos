#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为《尚书》《汉书》补充开源/已归档古籍库的可读版本证据（含底本说明）。

用法：python add_open_text_evidence.py [--dry-run]
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

BT_SHANG = ("白文本五十八篇（虞书5、夏书4、商书17、周书32，含东晋所出伪古文二十五篇），"
            "底本属《武英殿十三经注疏》本系统，参校《尚書正義》（四部叢刊本，漢籍リポジトリ KR1b0003）"
            "与《尚書注疏》（武英殿本，KR1b0004）")
BT_HAN = ("白文本百二十卷（纪12、表8、志10、传70），无注，卷次与《武英殿二十四史》本"
          "（ctext ctp:han-shu）一致；表部卷十三至二十为表格内容，已归档文本有省略")

NEW = {
    6: [
        {"grade": "B", "weight": 0.85, "source_name": "中国哲学书电子化计划",
         "url": "https://ctext.org/searchbooks.pl?searchu=ctp:work:shang-shu",
         "fields": {"base_text": BT_SHANG},
         "quote": "《尚書》版本表：春秋 尚書 武英殿十三經注疏本 ctp:shang-shu（代表性文献）；西漢 孔安國 傳 尚書 四部叢刊初編本 ctp:wb111907"},
        {"grade": "B", "weight": 0.85, "source_name": "Kanripo漢籍リポジトリ",
         "url": "https://www.kanripo.org/text/KR1b0003/001",
         "fields": {"base_text": BT_SHANG},
         "quote": "KR1b0003 尚書正義-唐-孔穎達（四部叢刊本，全文可读，可作白文本注疏对读）"},
        {"grade": "B", "weight": 0.80, "source_name": "殆知阁",
         "url": "https://github.com/daizhige-org/daizhigev20",
         "fields": {"base_text": BT_SHANG},
         "quote": "殆知阁古籍库 v20（data 分支，约 2.1GB）：已归档 尚书.md 58 篇；另存 尚书正义.md（KR1b0003）、尚书注疏.md（KR1b0004/WYG）"},
        {"grade": "C", "weight": 0.60, "source_name": "维基文库",
         "url": "https://zh.wikisource.org/wiki/%E5%B0%9A%E6%9B%B8",
         "fields": {"base_text": BT_SHANG},
         "quote": "维基文库《尚書》全文（自由许可，可交叉校对用字）"},
    ],
    14: [
        {"grade": "B", "weight": 0.85, "source_name": "中国哲学书电子化计划",
         "url": "https://ctext.org/han-shu",
         "fields": {"base_text": BT_HAN},
         "quote": "Book of Han 漢書：Author 班固 Dynasty Eastern Han，Base text《武英殿二十四史》本，Alternative titles 漢書顏師古注"},
        {"grade": "B", "weight": 0.80, "source_name": "殆知阁",
         "url": "https://github.com/daizhige-org/daizhigev20",
         "fields": {"base_text": BT_HAN},
         "quote": "殆知阁古籍库 v20（data 分支）：已归档 汉书.md，120 卷，白文约 90 万字"},
        {"grade": "C", "weight": 0.60, "source_name": "维基文库",
         "url": "https://zh.wikisource.org/wiki/%E6%BC%A2%E6%9B%B8",
         "fields": {"base_text": BT_HAN},
         "quote": "维基文库《漢書》全文（自由许可，可交叉校对用字）"},
    ],
}

PROFILE = {
    6: {
        "structure_note": "五十八篇：虞书5（尧典、舜典、大禹谟、皋陶谟、益稷）、夏书4（禹贡、甘誓、五子之歌、胤征）、"
                          "商书17（汤誓至微子）、周书32（泰誓至秦誓）；其中大禹谟以下二十五篇为东晋所出伪古文。",
        "reading_tip": "本库正文为白文本，无注。伪古文二十五篇（大禹谟、五子之歌、胤征、仲虺之诰、汤诰、伊训、"
                       "太甲三篇、咸有一德、说命三篇、泰誓三篇、武成、旅獒、微子之命、蔡仲之命、周官、"
                       "君陈、毕命、君牙、冏命）研读时须辨真伪，可对读《尚書正義》（KR1b0003）或"
                       "中华书局整理本；今文二十八篇为可靠先秦文献。",
    },
    14: {
        "structure_note": "百二十卷：帝纪12卷、表8卷（卷十三至二十）、志10卷（卷二十一至三十）、列传70卷（卷三十一至一百）。",
        "reading_tip": "本库正文为白文本，无颜师古注，适合通读与检索。表部卷十三至二十为表格，殆知阁文本多有省略"
                       "（如卷十九下仅存“表略”），需查 ctext《武英殿二十四史》本或中华书局点校本；"
                       "研读制度、地理、律历诸志可参中华书局点校本（ISBN 9787101079869）。",
    },
}


def main() -> int:
    dry = "--dry-run" in sys.argv
    for wid, entries in NEW.items():
        p = EV / f"work_{wid}.json"
        payload = json.loads(p.read_text(encoding="utf-8"))
        old_urls = {e["url"] for e in payload["entries"]}
        added = 0
        for e in entries:
            if e["url"] in old_urls:
                continue
            payload["entries"].append({**e, "grabbed_at": NOW})
            added += 1
        payload["entries"].sort(key=lambda x: -x["weight"])
        print(f"[evid] work={wid} 《{payload['title']}》 新增 {added} 条，累计 {len(payload['entries'])} 条")
        if not dry:
            p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if dry:
        print("[dry-run] 未写盘")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
