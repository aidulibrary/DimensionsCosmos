# -*- coding: utf-8 -*-
"""构建站点内「注音金标标注台」与「注音版预览页」所需数据

产出：
  1) public/collation/pinyin-review/data.json   标注台任务数据（含精确上下文窗口 + target 偏移）
  2) public/data/pinyin/{chapter_id}.json       预览页章节分片（原文 + pos/py/st/meta）
  3) public/data/pinyin/manifest.json           预览页索引（书目、章节、三态统计、构建元信息）

用法：
  python build_site_pages.py
  python build_site_pages.py --build-id b20261111_L05rule_r2v9 --preview-works 13,15,17
"""
import argparse
import io
import json
import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(r"D:\DimensionsCosmos")
DB = ROOT / "data" / "guji.db"
SHARD_ROOT = ROOT / "data" / "pinyin"
P0_PATH = ROOT / "pipeline" / "pinyin" / "gold_batch2_P0_1200.jsonl"
WORKORDER = ROOT / "pipeline" / "pinyin" / "gold_batch2_workorder_r2v9.jsonl"
OUT_REVIEW = ROOT / "public" / "collation" / "pinyin-review" / "data.json"
OUT_PREVIEW = ROOT / "public" / "data" / "pinyin"

CTX_L = 16  # 目标字左侧窗口字数
CTX_R = 20  # 目标字右侧窗口字数

STATE_CN = {"asserted": "确定", "variant": "异读", "uncertain": "存疑"}
BUCKET_CN = {
    "b1_lexical": "语词汇",
    "b2_podu": "破读",
    "b3_tongjia": "通假",
    "b4_defaultassert": "默认读音组",
    "b5_rare": "生僻",
}


def bucket_cn(key: str) -> str:
    """分层名中文化（对大小写不敏感，未知键回退原值）。"""
    if not key:
        return ""
    return BUCKET_CN.get(key.lower(), key)


def load_chapters():
    con = sqlite3.connect(str(DB))
    rows = con.execute(
        "SELECT id, work_id, COALESCE(title,''), COALESCE(clean_text,text) FROM chapters"
    ).fetchall()
    con.close()
    return {r[0]: {"work_id": r[1], "title": r[2], "text": r[3] or ""} for r in rows}


def load_work_names():
    raw = (ROOT / "public" / "data" / "index.json").read_text(encoding="utf-8")
    idx = json.loads(raw)
    return {
        int(w["id"]): {
            "slug": w.get("slug", ""),
            "title": w.get("seed_title") or w.get("title") or w.get("slug", ""),
        }
        for w in idx.get("works", [])
        if w.get("id") is not None
    }


def window(text, offset):
    """返回 (窗口文本, 窗口内 target 索引, 是否有左截断, 是否有右截断)"""
    lo = max(0, offset - CTX_L)
    hi = min(len(text), offset + 1 + CTX_R)
    return text[lo:hi], offset - lo, lo > 0, hi < len(text)


def build_review(chapters, works):
    items = []
    skipped = 0
    with io.open(P0_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            ch = chapters.get(int(r["chapter_id"]))
            if not ch:
                skipped += 1
                continue
            text = ch["text"]
            off = int(r["offset"])
            if off >= len(text):
                skipped += 1
                continue
            # 以原文为准校验字面（工单生成时已对齐，这里只做护栏）
            surface = r.get("surface") or text[off]
            ctx, ti, tl, tr = window(text, off)
            w = works.get(ch["work_id"], {})
            items.append(
                {
                    "id": len(items) + 1,
                    "bucket": r.get("bucket", ""),
                    "bucketCn": bucket_cn(r.get("bucket", "")),
                    "chId": int(r["chapter_id"]),
                    "off": off,
                    "surface": surface,
                    "machine": r.get("machine_reading", ""),
                    "ruleId": r.get("rule_id"),
                    "state": r.get("state", "asserted"),
                    "ctx": ctx,
                    "ti": ti,
                    "tl": tl,
                    "tr": tr,
                    "work": w.get("title", ""),
                    "slug": w.get("slug", ""),
                    "chap": ch["title"],
                }
            )

    # 分层统计
    dist = {}
    for it in items:
        dist[it["bucket"]] = dist.get(it["bucket"], 0) + 1
    strata = [
        {"key": k, "cn": bucket_cn(k), "n": v}
        for k, v in sorted(dist.items(), key=lambda kv: -kv[1])
    ]

    payload = {
        "meta": {
            "batch": "P0",
            "title": "注音金标标注台 · P0",
            "buildId": "b20261111_L05rule_r2v9",
            "engine": "L0.5-rule-v2.5",
            "total": len(items),
            "skipped": skipped,
            "source": "gold_batch2_P0_1200.jsonl",
            "ctxL": CTX_L,
            "ctxR": CTX_R,
        },
        "strata": strata,
        "items": items,
    }
    OUT_REVIEW.parent.mkdir(parents=True, exist_ok=True)
    OUT_REVIEW.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[review] {OUT_REVIEW}  items={len(items)} skipped={skipped} size={OUT_REVIEW.stat().st_size/1024:.1f}KB")
    return payload


def build_preview(chapters, works, build_id, preview_works, per_book=4, max_chars=4000):
    OUT_PREVIEW.mkdir(parents=True, exist_ok=True)
    books, total = [], {"a": 0, "v": 0, "u": 0}
    written = set()
    for wid in preview_works:
        wdir = SHARD_ROOT / build_id / str(wid)
        if not wdir.is_dir():
            print(f"[preview] 跳过 work {wid}：分片目录缺失")
            continue
        w = works.get(wid, {})
        chs = []
        for shard_file in sorted(wdir.glob("*.json"), key=lambda p: int(p.stem)):
            if len(chs) >= per_book:
                break
            cid = int(shard_file.stem)
            ch = chapters.get(cid)
            if not ch:
                continue
            if len(ch["text"]) > max_chars:  # 预览样本：过长章节跳过，控制站点体积
                continue
            shard = json.loads(shard_file.read_text(encoding="utf-8"))
            st = shard.get("st", "")
            cnt = {
                "a": st.count("a"),
                "v": st.count("v"),
                "u": st.count("u"),
            }
            for k in cnt:
                total[k] += cnt[k]
            meta = {int(k): v for k, v in (shard.get("meta") or {}).items()}
            out = {
                "chId": cid,
                "workId": wid,
                "title": ch["title"],
                "work": w.get("title", ""),
                "slug": w.get("slug", ""),
                "buildId": shard.get("build_id", build_id),
                "engine": shard.get("engine", ""),
                "len": shard.get("len", len(ch["text"])),
                "text": ch["text"],
                "pos": shard.get("pos", []),
                "py": shard.get("py", []),
                "st": st,
                "meta": meta,
            }
            (OUT_PREVIEW / f"{cid}.json").write_text(
                json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
            )
            written.add(f"{cid}.json")
            chs.append(
                {
                    "chId": cid,
                    "title": ch["title"],
                    "chars": len(ch["text"]),
                    "annotated": len(shard.get("pos", [])),
                    "coverage": round(len(shard.get("pos", [])) / max(1, len(ch["text"])), 4),
                    "a": cnt["a"],
                    "v": cnt["v"],
                    "u": cnt["u"],
                }
            )
        if chs:
            n = sum(c["annotated"] for c in chs)
            books.append(
                {
                    "workId": wid,
                    "title": w.get("title", ""),
                    "slug": w.get("slug", ""),
                    "chapters": chs,
                    "annotated": n,
                    "chars": sum(c["chars"] for c in chs),
                    "rateU": round(sum(c["u"] for c in chs) / max(1, n), 4),
                    "rateV": round(sum(c["v"] for c in chs) / max(1, n), 4),
                }
            )

    ann = total["a"] + total["v"] + total["u"]
    manifest = {
        "buildId": build_id,
        "engine": "L0.5-rule-v2.5",
        "generatedFrom": str(SHARD_ROOT / build_id),
        "books": books,
        "totals": {
            "chapters": sum(len(b["chapters"]) for b in books),
            "annotated": ann,
            "chars": sum(b["chars"] for b in books),
            "a": total["a"],
            "v": total["v"],
            "u": total["u"],
            "rateU": round(total["u"] / max(1, ann), 4),
            "rateV": round(total["v"] / max(1, ann), 4),
            "coverage": round(ann / max(1, sum(b["chars"] for b in books)), 4),
        },
    }
    (OUT_PREVIEW / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    # 清理过期分片：移入缓存目录（不物理删除，可回溯）
    trash = ROOT / "data" / "pinyin" / "_site_preview_stale"
    moved = 0
    for f in OUT_PREVIEW.glob("*.json"):
        if f.name == "manifest.json" or f.name in written:
            continue
        trash.mkdir(parents=True, exist_ok=True)
        target = trash / f.name
        if target.exists():
            target.unlink()
        f.replace(target)
        moved += 1
    if moved:
        print(f"[preview] 过期分片 {moved} 个已移至 {trash}")
    t = manifest["totals"]
    print(
        f"[preview] books={len(books)} chapters={t['chapters']} annotated={t['annotated']} "
        f"u={t['rateU']:.2%} v={t['rateV']:.2%} coverage={t['coverage']:.2%}"
    )
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-id", default="b20261111_L05rule_r2v9")
    ap.add_argument("--preview-works", default="13,15,17")
    a = ap.parse_args()
    chapters = load_chapters()
    works = load_work_names()
    build_review(chapters, works)
    build_preview(chapters, works, a.build_id, [int(x) for x in a.preview_works.split(",") if x.strip()])
    return 0


if __name__ == "__main__":
    sys.exit(main())
