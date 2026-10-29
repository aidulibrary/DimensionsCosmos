# -*- coding: utf-8 -*-
"""《中庸》导入：以朱熹《中庸章句集注》的 33 章标记为切分锚点，
把殆知阁白文本《中庸》(5143 字、无分章) 精确切成 33 章后写库。

锚点定位法：
  1) 从集注正文按「上第X章。」切出 33 个章块，块首常混有朱熹按语/注文；
  2) 把白文本拼成连续字符串 S，用 16 字去标点窗口在 S 中顺序查找章块中首个可命中片段，
     命中点即该章在白文中的起点（注文因不在白文中而被自然跳过）；
  3) 失败章在前后已定位锚点区间内用 14→8 字窗口重试；异体字（著/着、於/于）统一后再比；
  4) 边界吸附到最近的白文段落起点，消除注文引述原文造成的数十字偏移。
"""
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from import_daizhige_generic import build_rows, grade_work  # noqa: E402
from normalize_text import clean_text  # noqa: E402

DB = r"D:\DimensionsCosmos\data\guji.db"
SRC = Path(r"D:\DimensionsCosmos\data\sources\daizhige")
WORK_ID = 4
PUNC = set("，。；：！？“”‘’、（）《》〈〉…—～·「」『』(),.;:!?\"'")
VAR = {"著": "着", "於": "于", "餘": "余", "彊": "强", "傚": "效", "説": "说", "爲": "为"}
NOTE = ("《中庸》白文本，据《正统道藏》所收本；分章依朱熹《中庸章句》三十三章，"
        "章界由章句集注经文起句锚定")


def norm(s: str, want_map: bool = False):
    out, idx = [], []
    for i, ch in enumerate(s):
        if ch in PUNC:
            continue
        out.append(VAR.get(ch, ch))
        idx.append(i)
    return ("".join(out), idx) if want_map else "".join(out)


def load():
    body = (SRC / "中庸章句集注.md").read_text(encoding="utf-8", errors="ignore").split("---", 2)[2]
    marks = list(re.finditer(r"上第([一二三四五六七八九十]+)章。", body))
    start, prev, blocks = body.find("天命之谓性"), body.find("天命之谓性"), []
    assert start > 0, "集注正文起始句未找到"
    for m in marks:
        blocks.append(re.sub(r"[\s　]+", "", body[prev:m.start()]))
        prev = m.end()
    raw = (SRC / "中庸.md").read_text(encoding="utf-8", errors="ignore").split("---", 2)[2]
    paras = [re.sub(r"[\s　]+", "", p) for p in raw.splitlines() if p.strip()][1:]
    return blocks, paras


def locate(blocks, paras):
    S = "".join(paras)
    nS, idxmap = norm(S, True)
    last, pos = 0, []
    for b in blocks:
        nb, found = norm(b), None
        for st in range(0, max(0, min(len(nb), 600) - 16 + 1)):
            win = nb[st:st + 16]
            if len(win) < 16:
                break
            k = nS.find(win, last)
            if k != -1:
                found, last = idxmap[k], k + 1
                break
        pos.append(found)
    for i, p in enumerate(pos):  # 短章兜底：在前后锚点区间内用短窗口重试
        if p is not None:
            continue
        lo = pos[i - 1] if i and pos[i - 1] is not None else 0
        hi = next((pos[j] for j in range(i + 1, len(pos)) if pos[j] is not None), len(S))
        nb = norm(blocks[i])
        for W in (14, 12, 10, 8):
            ok = None
            for st in range(0, max(0, len(nb) - W + 1)):
                win = nb[st:st + W]
                if len(win) < W:
                    break
                k = nS.find(win)
                while k != -1:
                    o = idxmap[k]
                    if lo < o < hi:
                        ok = o
                        break
                    k = nS.find(win, k + 1)
                if ok:
                    break
            if ok:
                pos[i] = ok
                break
    if any(p is None for p in pos):
        raise SystemExit(f"定位失败章：{[i+1 for i,p in enumerate(pos) if p is None]}")
    # 边界吸附到段落起点（仅前移不超过 40 字，修注文引述造成的偏移）
    pstart, acc = [], 0
    for p in paras:
        pstart.append(acc)
        acc += len(p)
    for i in range(1, len(pos)):
        cands = [p for p in pstart if pos[i - 1] < p <= pos[i]]
        if cands and 0 < pos[i] - max(cands) <= 40:
            pos[i] = max(cands)
    bounds = pos + [len(S)]
    return [S[bounds[i]:bounds[i + 1]] for i in range(len(blocks))]


def main() -> int:
    apply = "--apply" in sys.argv
    blocks, paras = load()
    segs = locate(blocks, paras)
    chapters = [{"title": f"中庸/第{n}章", "text": s} for n, s in enumerate(segs, 1)]
    rows = build_rows(chapters, min_chars=10, min_avg=60)
    total = sum(r["chars"] for r in rows)
    wq, wnote = grade_work(rows, min_avg=60, min_total=3000)
    print(f"[parse] 中庸 章数={len(rows)} 总字数={total} work_quality={wq} {wnote}")
    tiny = [(r["title"], r["chars"]) for r in rows if r["chars"] < 20]
    if tiny:
        print("   [warn] 短章:", tiny)
    if not apply:
        print("[dry-run] 加 --apply 写库")
        return 0
    con = sqlite3.connect(DB)
    con.execute("delete from chapters where work_id=?", (WORK_ID,))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for ordn, r in enumerate(rows, 1):
        con.execute("""insert into chapters
            (work_id,title,text,chars,clean_text,blocks,quality,quality_note,ord,ord_source,noise_ratio,ord_group)
            values(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (WORK_ID, r["title"], r["text"], r["chars"], r["clean"],
                     json.dumps(r["blocks"], ensure_ascii=False), r["quality"], r["note"],
                     ordn, "zhangju-anchor", 0.0, ""))
    con.execute("""update works set status='ok', quality=?, total_chars=?, chapter_count=?,
                   fetched_at=?, last_error=NULL where id=?""",
                (wq, total, len(rows), now, WORK_ID))
    con.commit()
    print(f"[apply] work={WORK_ID} 中庸 写入 {len(rows)} 章 {total} 字，quality={wq}")
    print(f"[底本] {NOTE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
