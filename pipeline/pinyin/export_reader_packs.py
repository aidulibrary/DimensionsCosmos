# -*- coding: utf-8 -*-
"""
维点图书馆 · 阅读页注音分片导出器（format = py1）

输入：data/pinyin/<build_id>/**/*.json        构建产物（含 pos/py/st/meta）
输出：public/data/py/index.json               全局索引（章号 → 包序号 + 全局音节表）
      public/data/py/p<NNN>.json              每包 N 章的紧凑注音数据

设计取舍：
  1) 不逐章出一个文件 —— Cloudflare Pages 单站点文件数上限 20000，
     现有 dist 已 10481 文件，再叠 10075 个分片会直接部署失败，故按包（默认 50 章）打包。
  2) 丢弃 meta —— 阅读页只需要「字位 / 读音 / 三态」，meta（规则号、建议音）只有标注台用，
     实测占分片体积 21.7%，本就不该进前端。
  3) py 改用全局音节表索引 —— 拼音字符串占 40%，索引化后降到约 16%。
  4) pos / st 保持原样（绝对偏移 + 每字 1 字符的状态串），换取前端解析零歧义。

前端契约（勿轻改）：
  chapter = index.ch[chId] = { len, pack }
  pack.ch[chId] = { pos:[...], py:[...], st:"aaau..." }
    - pos[i] 是相对本章 clean_text 的汉字字符偏移（0-based）
    - py[i]  是 index.syl[py[i]] 的下标
    - st   是逐汉字的 'a' | 'u' | 'v' 状态串，与 pos 等长

运行：
  python pipeline\pinyin\export_reader_packs.py --build-id b20261115_v27_full --pack-size 50
"""
import argparse
import difflib
import json
import pathlib
import re
import sqlite3
import time

ROOT = pathlib.Path(r"D:\DimensionsCosmos")
SHARD_ROOT = ROOT / "data" / "pinyin"
OUT_DIR = ROOT / "public" / "data" / "py"
CH_DIR = ROOT / "public" / "data" / "ch"
DB_PATH = ROOT / "data" / "guji.db"
ALIGN_CACHE = SHARD_ROOT / "_reader_align.json"

# 与阅读页 read.astro 的 clean() / HAN_RE 必须逐条一致，否则对齐会整体错位
HAN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_TAG1 = re.compile(r"\[\d+\]")
_TAG2 = re.compile(r"\[(註|注|编辑|編輯|来源|來源)\]")


def clean_block(s: str) -> str:
    s = _TAG1.sub("", s)
    s = _TAG2.sub("", s)
    return s.replace("\u200b", "").strip()


def build_align() -> dict:
    """块文本汉字序列 vs clean_text 汉字序列的对齐结论（v2）。

    为什么要这张表：注音分片按 clean_text 生成，而阅读页只渲染 blocks；两者
    在 10075 章里有 383 章不完全等长（卷首「註疏」标签、章末校勘记、[註] 标记
    等未进 blocks）。若前端盲按「第 k 个汉字」取音，序列一旦错位，整章读音
    会全部张冠李戴。

    fl 取值（v2 扩充了 fl=1 与 fl=3，使原本放弃的 20 章也能注音）：
      2 = 两条序列逐字完全一致（9692 章）          → 直接等长取音
      1 = 块文本是注音序列的**连续切片**（含 off>0 的卷首前缀，383 章）
                                                    → 从 off 起等长取音
      3 = 中间有插入/删除但逐字映射率 ≥99%（少数章） → 用 mp 逐字取音
      0 = 映射不可靠 → 不注音，宁缺不错
    """
    if ALIGN_CACHE.exists():
        try:
            d = json.loads(ALIGN_CACHE.read_text(encoding="utf-8"))
            if isinstance(d, dict) and d.get("__v") == 2:
                return d
        except Exception:
            pass
    con = sqlite3.connect(DB_PATH)
    al: dict = {"__v": 2}
    for cid, ct in con.execute("SELECT id, clean_text FROM chapters"):
        han_c = "".join(HAN_RE.findall(ct or ""))
        p = CH_DIR / f"{cid}.json"
        if not p.exists():
            al[str(cid)] = {"n": 0, "fl": 0, "off": 0}
            continue
        ch = json.loads(p.read_text(encoding="utf-8"))
        hb: list = []
        for b in ch.get("blocks") or []:
            t = clean_block(str(b.get("x") or ""))
            if t:
                hb.extend(HAN_RE.findall(t))
        sb, n = "".join(hb), len(hb)
        if sb == han_c:
            al[str(cid)] = {"n": n, "fl": 2, "off": 0}
            continue
        off = han_c.find(sb) if sb else -1
        if off >= 0:
            al[str(cid)] = {"n": n, "fl": 1, "off": off}
            continue
        mp: list = [None] * n
        ok = 0
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
                None, sb, han_c, autojunk=False).get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1):
                    mp[i1 + k] = j1 + k
                ok += i2 - i1
        if n and ok / n >= 0.99:
            last = 0
            for k in range(n):
                if mp[k] is None:
                    mp[k] = last
                last = mp[k]
            al[str(cid)] = {"n": n, "fl": 3, "off": 0, "mp": mp}
        else:
            al[str(cid)] = {"n": n, "fl": 0, "off": 0}
    con.close()
    ALIGN_CACHE.write_text(json.dumps(al, separators=(",", ":")), encoding="utf-8")
    return al




def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-id", default="b20261115_v27_full")
    ap.add_argument("--pack-size", type=int, default=10, help="单包最多章数")
    ap.add_argument("--pack-kb", type=int, default=350, help="单包目标体积上限 KB（超长章节按章打包，不拆分）")
    ap.add_argument("--engine", default="")
    args = ap.parse_args()

    src = SHARD_ROOT / args.build_id
    files = sorted(src.rglob("*.json"))
    if not files:
        print(f"[FAIL] 未找到分片：{src}")
        return 1
    print(f"  源分片 {len(files)} 章：{src}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("p*.json"):
        old.unlink()
    old_index = OUT_DIR / "index.json"
    if old_index.exists():
        old_index.unlink()

    syl_list = []
    syl_idx = {}
    chapters_index = {}
    st_agg = {"a": 0, "u": 0, "v": 0}

    t_align = time.time()
    ALIGN = build_align()
    _v = [v for k, v in ALIGN.items() if k != "__v" and isinstance(v, dict)]
    n_exact = sum(1 for v in _v if v.get("fl") == 2)
    n_pre = sum(1 for v in _v if v.get("fl") == 1)
    n_map = sum(1 for v in _v if v.get("fl") == 3)
    n_bad = sum(1 for v in _v if v.get("fl") == 0)
    print(
        f"  对齐表 {len(_v)} 章（完全一致 {n_exact} / 切片 {n_pre} / 映射 {n_map} / 不可注音 {n_bad}）"
        f"  {time.time() - t_align:.1f}s",
        flush=True,
    )
    pack_size = max(1, args.pack_size)
    n_pack = 0
    written_bytes = 0
    buf = {}
    buf_bytes = 0
    pack_kb_limit = max(50, args.pack_kb) * 1024
    t0 = time.time()

    def flush():
        nonlocal buf, n_pack, written_bytes, buf_bytes
        if not buf:
            return
        path = OUT_DIR / f"p{n_pack:03d}.json"
        payload = json.dumps({"v": args.build_id, "ch": buf},
                             ensure_ascii=False, separators=(",", ":"))
        path.write_text(payload, encoding="utf-8")
        written_bytes += len(payload.encode("utf-8"))
        n_pack += 1
        buf = {}
        buf_bytes = 0

    total_in = 0
    for i, f in enumerate(sorted(files, key=lambda x: int(x.stem)), 1):
        total_in += f.stat().st_size
        d = json.loads(f.read_text(encoding="utf-8"))
        cid = str(d["chapter_id"])
        pos = d["pos"]
        pys = d["py"]
        st = d["st"]
        idxs = []
        for r in pys:
            j = syl_idx.get(r)
            if j is None:
                j = len(syl_list)
                syl_idx[r] = j
                syl_list.append(r)
            idxs.append(j)
        for ch in st:
            st_agg[ch] = st_agg.get(ch, 0) + 1
        a = ALIGN.get(cid) or {"n": 0, "fl": 0, "off": 0}
        entry = {"pos": pos, "py": idxs, "st": st}
        if a.get("mp"):
            entry["mp"] = a["mp"]
        entry_txt = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
        if len(buf) >= pack_size or (buf and buf_bytes + len(entry_txt) > pack_kb_limit):
            flush()
        buf[cid] = entry
        buf_bytes += len(entry_txt) + len(cid) + 8
        chapters_index[cid] = {
            "len": int(d.get("len") or 0),
            "pack": n_pack,
            "n": int(a["n"]),
            "fl": int(a["fl"]),
            "off": int(a.get("off") or 0),
        }
        if i % 1000 == 0:
            print(f"  已处理 {i}/{len(files)} 章 …", flush=True)
    flush()

    total_h = sum(st_agg.values())
    index = {
        "v": args.build_id,
        "engine": args.engine or "L0.5-rule-v2.7",
        "format": "py1",
        "packSize": pack_size,
        "packs": n_pack,
        "syl": syl_list,
        "stats": {
            "chapters": len(chapters_index),
            "hanChars": total_h,
            "a": st_agg.get("a", 0),
            "u": st_agg.get("u", 0),
            "v": st_agg.get("v", 0),
        },
        "ch": chapters_index,
    }
    idx_txt = json.dumps(index, ensure_ascii=False, separators=(",", ":"))
    (OUT_DIR / "index.json").write_text(idx_txt, encoding="utf-8")

    print(f"\n[OK] 导出完成 {time.time()-t0:.0f}s")
    print(f"  包数 {n_pack}（每包 {pack_size} 章）  索引 {len(idx_txt)/1024:.0f} KB")
    print(f"  注音数据 {written_bytes/1024/1024:.1f} MB  原体积 {total_in/1024/1024:.1f} MB "
          f"（压缩率 {written_bytes/total_in*100:.0f}%）")
    print(f"  全局音节表 {len(syl_list)} 项")
    print(f"  三态：a={st_agg.get('a',0)} u={st_agg.get('u',0)} v={st_agg.get('v',0)}"
          f"  u 率 {st_agg.get('u',0)/total_h*100:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
