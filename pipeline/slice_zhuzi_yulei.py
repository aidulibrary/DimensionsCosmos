#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《朱子语类》底本卷级裁剪器（选本子批专用）。

背景：殆知阁底本《朱子语类》全书 193.3 万字，单部即超交付标准 §2.6
「单批正文 150 万字」上限，按 §2.4/§2.6 另立「选本/分卷」子批。
本脚本按卷号白名单裁剪底本，输出可复算的选本底本，供 run_import.py 导入。

用法：
  python slice_zhuzi_yulei.py                       # 只列各卷字数
  python slice_zhuzi_yulei.py --vols 1-13 --write    # 输出选本底本
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SRC = Path(r"D:\DimensionsCosmos\data\sources\daizhige\朱子语类.md")
OUT = Path(r"D:\DimensionsCosmos\data\sources\daizhige\_slices\朱子语类_选本卷一至卷十三.md")

CN = "一二三四五六七八九十百"
D = {x: i for i, x in enumerate("一二三四五六七八九", 1)}
RE_VOL = re.compile(rf"^(?:朱子语类)?卷第([{CN}]+)$")


def ten(b: str) -> int:
    if "十" in b:
        x, y = b.split("十", 1)
        return (D.get(x, 1) if x else 1) * 10 + (D.get(y, 0) if y else 0)
    return D.get(b, 0)


def cn2i(c: str) -> int:
    if "百" in c:
        a, b = c.split("百", 1)
        return (D.get(a, 1) if a else 1) * 100 + (ten(b) if b else 0)
    return ten(c)


def parse_vols(spec: str) -> set[int]:
    got: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            got.update(range(int(a), int(b) + 1))
        else:
            got.add(int(part))
    return got


def scan() -> list[dict]:
    lines = SRC.read_text(encoding="utf-8", errors="replace").split("\n")
    hits = []
    for i, l in enumerate(lines):
        t = l.replace("\u3000", "").strip()
        m = RE_VOL.match(t)
        if m:
            hits.append((i, cn2i(m.group(1))))
    vols = []
    for k, (i, no) in enumerate(hits):
        end = hits[k + 1][0] if k + 1 < len(hits) else len(lines)
        seg = [x.replace("\u3000", "").strip() for x in lines[i + 1:end]]
        seg = [x for x in seg if x]
        sub = seg[0] if seg else ""
        body = seg[1:] if seg else []
        vols.append({"no": no, "head": f"卷第{'一二三四五六七八九十'[0] if False else no}",
                     "sub": sub, "body": body,
                     "chars": len("".join(seg))})
    return vols


def cn_num(n: int) -> str:
    """阿拉伯数字 → 中文卷序（1-140，依底本「卷第一百二十」式写法）。"""
    d = "一二三四五六七八九"
    if n <= 10:
        return "十" if n == 10 else d[n - 1]
    if n < 20:
        return "十" + d[n - 11] if n > 10 else "十"
    if n < 100:
        a, b = divmod(n, 10)
        return d[a - 1] + "十" + (d[b - 1] if b else "")
    if n == 100:
        return "一百"
    rest = n - 100
    if rest < 10:
        return "一百零" + d[rest - 1]
    if rest == 10:
        return "一百一十"
    a, b = divmod(rest, 10)
    return "一百一十" + (d[b - 1] if b else "") if a == 1 else "一百" + d[a - 1] + "十" + (d[b - 1] if b else "")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--vols", default="")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    vols = scan()
    if not a.vols:
        for v in vols:
            print(f"  卷{v['no']:>3}  {v['sub'][:22]:<24} {v['chars']:>7}")
        print(f"[total] {len(vols)} 卷 {sum(v['chars'] for v in vols)} 字")
        return 0

    want = parse_vols(a.vols)
    pick = [v for v in vols if v["no"] in want]
    missing = sorted(want - {v["no"] for v in pick})
    if missing:
        print(f"[error] 卷号未命中：{missing}")
        return 2
    total = sum(v["chars"] for v in pick)
    print(f"[select] {len(pick)} 卷 {total} 字（全书 {sum(v['chars'] for v in vols)} 字）")
    if not a.write:
        return 0

    out = []
    for v in pick:
        out.append(f"卷{cn_num(v['no'])} {v['sub']}")
        out.append("")
        out.extend(v["body"])
        out.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out).strip() + "\n", encoding="utf-8")
    print(f"[write] {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
