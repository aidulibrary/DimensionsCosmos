// 构建脚本：从 SQLite 读取，生成 Astro 能用的 JSON 数据源。
// 运行时：npm run build 的前置步骤（package.json 的 prebuild / predev）。
// 依赖：Node 22+ 原生 node:sqlite，零外部包。
//
// P0 变更：
//   1) 增导出章节 ord / ord_group / quality / quality_note
//   2) 正文改为按章拆分（public/data/ch/{chapterId}.json），book-*.json 只留目录
//      → 单书 JSON 从数 MB 降到数十 KB，阅读页按需加载
//   3) 章节排序统一按 ord（附文为负值，NULL 排最后）
import { DatabaseSync } from "node:sqlite";
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const DB_PATH = path.join(ROOT, "data", "guji.db");
const OUT_DIR = path.join(ROOT, "public", "data");
const CH_DIR = path.join(OUT_DIR, "ch");

if (!fs.existsSync(DB_PATH)) {
  console.warn(
    "[gen] data/guji.db 不存在，跳过（GitHub Actions 构建时会先 clone）",
  );
  process.exit(0);
}

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.mkdirSync(CH_DIR, { recursive: true });

const db = new DatabaseSync(DB_PATH, { readonly: true });

// 0) 表结构兜底（老库可能没有 P0 新列）
const cols = (t) =>
  db.prepare(`PRAGMA table_info(${t})`).all().map((c) => c.name);
const chCols = cols("chapters");
const has = (c) => chCols.includes(c);
const col = {
  ord: has("ord") ? "c.ord" : "NULL AS ord",
  ordGroup: has("ord_group") ? "c.ord_group" : "NULL AS ord_group",
  quality: has("quality") ? "c.quality" : "'ok' AS quality",
  note: has("quality_note") ? "c.quality_note" : "NULL AS quality_note",
  clean: has("clean_text") ? "c.clean_text" : "c.text AS clean_text",
  blocks: has("blocks") ? "c.blocks" : "NULL AS blocks",
  // REF-SPEC v1 稳定引用（dc:<work-key>/c<chapNo>）；老库无该列时降级为 null
  ref: has("ref") ? "c.ref" : "NULL AS ref",
};
const wCols = cols("works");
const wQuality = wCols.includes("quality") ? "w.quality" : "'ok' AS quality";

// 1) 书库总表
const works = db
  .prepare(
    `
  SELECT w.id, w.seed_title, w.ws_title, w.bu, w.author, w.dynasty,
         w.status, w.wikidata_qid, w.fetched_at,
         ${wQuality},
         (SELECT COUNT(*) FROM chapters c WHERE c.work_id = w.id) AS chapter_count,
         (SELECT COALESCE(SUM(c.chars),0) FROM chapters c WHERE c.work_id = w.id) AS total_chars
  FROM works w
  ORDER BY w.bu, w.id
`,
  )
  .all();

const safeSlug = (t) =>
  String(t || "untitled")
    .replace(/[/\?#]/g, "-")
    .replace(/\s+/g, "-");
// 版本档案（EGV 裁决）：无 A1 锚定时 grade=reference，但 version_text 仍可能给出可读底本说明
const profiles = {};
try {
  for (const p of db
    .prepare(
      `SELECT work_id, version_text, structure_note, reading_tip, grade, score
       FROM work_profiles`,
    )
    .all()) {
    if (!p.version_text && !p.structure_note && !p.reading_tip) continue;
    profiles[p.work_id] = {
      text: p.version_text || null,
      structure: p.structure_note || null,
      readingTip: p.reading_tip || null,
      grade: p.grade || null,
      score: p.score ?? null,
    };
  }
} catch (_) {
  /* 表可能不存在 */
}

const worksWithSlug = works.map((w) => ({
  ...w,
  slug: `${w.id}-${safeSlug(w.seed_title)}`,
  ok: w.status === "ok",
  readable: w.status === "ok" && (w.quality ?? "ok") !== "unavailable",
  version: profiles[w.id] || null,
}));

// 2) 分类聚合
const byBu = {};
for (const w of worksWithSlug) {
  byBu[w.bu] ??= [];
  byBu[w.bu].push(w);
}

// 3) AI 解读
// 质量闸门：由 `python pipeline/qa_guides.py --gate data/guide-qa-gate.json` 产出。
// 未过闸（旧版 3 段短篇、论述不足、引文不在块内等）的导读不进前端数据，
// 页面自动落到「筹备中/未上架」态（/read/[slug]/[method] 的路由与数据互相独立）。
// 闸门文件缺失时 fail-open（全量放行 + 告警），避免一次漏跑把整站导读清空。
const GATE_PATH = path.join(ROOT, "data", "guide-qa-gate.json");
let guideGate = null;
try {
  const gate = JSON.parse(fs.readFileSync(GATE_PATH, "utf-8"));
  guideGate = new Map(
    (gate.items ?? []).map((it) => [`${it.work_id}:${it.method_id}`, !!it.pass]),
  );
  console.log(
    `[guides] 质量闸门生效：放行 ${gate.passed}/${gate.total}（${gate.at ?? "未标注时间"}）`,
  );
} catch (_) {
  console.warn(
    "[guides] 未找到 data/guide-qa-gate.json，AI 导读不做质量过滤（全部发布）。" +
      "建议先跑 pipeline/qa_guides.py --gate 再构建。",
  );
}

const worksGuides = {};
let guidesBlocked = 0;
try {
  // citations（REF-SPEC v1 URN 列表）为 P0-5 引证式导读字段，老库可能没有该列
  const hasCites = db
    .prepare("PRAGMA table_info(ai_guides)")
    .all()
    .some((c) => c.name === "citations");
  const guides = db
    .prepare(
      `SELECT work_id, method_id, result, generated_at, model_used${
        hasCites ? ", citations" : ""
      }
       FROM ai_guides ORDER BY work_id, method_id`,
    )
    .all();
  for (const g of guides) {
    if (guideGate && guideGate.get(`${g.work_id}:${g.method_id}`) === false) {
      guidesBlocked += 1;
      continue;
    }
    worksGuides[g.work_id] ??= [];
    let parsed = {};
    try {
      parsed = JSON.parse(g.result || "{}");
    } catch (_) {
      /* ignore */
    }
    let cites = [];
    if (hasCites && g.citations) {
      try {
        const v = JSON.parse(g.citations);
        if (Array.isArray(v)) cites = v.filter((x) => typeof x === "string");
      } catch (_) {
        /* 脏值静默丢弃，不阻断构建 */
      }
    }
    // 引证式导论的正文段落（P0-5）：每段自带 cites（REF-SPEC v1 URN），
    // 老数据没有 paragraphs，留空数组，前端整块不渲染。
    const paras = Array.isArray(parsed.paragraphs)
      ? parsed.paragraphs
          .filter((p) => p && typeof p.text === "string" && p.text.trim())
          .map((p) => ({
            text: String(p.text).trim(),
            cites: Array.isArray(p.cites)
              ? p.cites.filter((u) => typeof u === "string" && /^dc:[^/]+\/c\d+/.test(u))
              : [],
          }))
      : [];
    worksGuides[g.work_id].push({
      method_id: g.method_id,
      generated_at: g.generated_at,
      model_used: g.model_used,
      content: parsed.content || parsed,
      paragraphs: paras,
      citations: cites,
    });
  }
} catch (_) {
  /* 表可能不存在 */
}

// 4) 章节：目录写进 book-*.json，正文按章落 ch/{id}.json
const ORDER = has("ord")
  ? `ORDER BY (c.ord IS NULL), c.ord, c.id`
  : `ORDER BY c.id`;
const chapterStmt = db.prepare(
  `SELECT c.id, c.title, c.chars, ${col.ord}, ${col.ordGroup},
          ${col.quality}, ${col.note}, ${col.clean}, ${col.blocks}, ${col.ref}
   FROM chapters c WHERE c.work_id = ? ${ORDER}`,
);

const workChapters = {};
const missing = [];
// 同一本书内若已存在「卷号×1e9」刻度条目，则把 1e6 以下的正序条目归一到同一刻度，
// 避免混刻度导致章节顺序错乱（如《史記》卷033「魯周公世家」被篇序号 33 顶到全书最前）。
const ORD_UNIT = 1e9;
function normalizeOrdScale(rows) {
  if (!rows.length) return;
  if (!rows.some((c) => Number(c.ord) >= 1e6)) return;
  for (const c of rows) {
    const o = Number(c.ord);
    if (o > 0 && o < 1e6) c.ord = o * ORD_UNIT;
  }
  rows.sort((a, b) => {
    const an = a.ord == null;
    const bn = b.ord == null;
    if (an !== bn) return an ? 1 : -1;
    if (a.ord !== b.ord) return (a.ord ?? 0) - (b.ord ?? 0);
    return a.id - b.id;
  });
}
for (const w of worksWithSlug) {
  if (!w.ok) continue;
  const rows = chapterStmt.all(w.id);
  normalizeOrdScale(rows);
  workChapters[w.id] = rows.map((c) => {
    let blocks = null;
    if (c.blocks) {
      try {
        blocks = JSON.parse(c.blocks);
      } catch (_) {
        blocks = null;
      }
    }
    if (!blocks) {
      const txt = c.clean_text || "";
      blocks = txt
        .split(/\n{2,}/)
        .map((s) => s.trim())
        .filter(Boolean)
        .map((s) => ({ t: "p", x: s }));
    }
    const payload = {
      id: c.id,
      workId: w.id,
      workTitle: w.seed_title,
      title: c.title,
      ord: c.ord,
      ordGroup: c.ord_group,
      chars: c.chars,
      quality: c.quality || "ok",
      qualityNote: c.quality_note || null,
      blocks,
      ref: c.ref || null,
    };
    fs.writeFileSync(
      path.join(CH_DIR, `${c.id}.json`),
      JSON.stringify(payload),
    );
    if (!c.ord && c.quality !== "ok") missing.push(c.id);
    return {
      id: c.id,
      title: c.title,
      chars: c.chars,
      ord: c.ord,
      ordGroup: c.ord_group,
      quality: c.quality || "ok",
      qualityNote: c.quality_note || null,
      excerpt: (c.clean_text || "").replace(/\s+/g, " ").slice(0, 120),
      ref: c.ref || null,
    };
  });
}

// 5) 写出
const indexJson = {
  generatedAt: new Date().toISOString(),
  total: worksWithSlug.length,
  ok: worksWithSlug.filter((w) => w.ok).length,
  readable: worksWithSlug.filter((w) => w.readable).length,
  taxonomy: db.prepare("SELECT name, parent FROM taxonomy ORDER BY name").all(),
  byBu,
  works: worksWithSlug.map((w) => ({ ...w, guides: worksGuides[w.id] || [] })),
  guidesCount: Object.values(worksGuides).reduce((s, g) => s + g.length, 0),
};
// 5.0) 写出前的数据健康守卫：防误删 + 防空产物上线
//   背景：CI 侧抓取源失效曾导出 0 部 0 章，脚本先把 9874 个章节文件清空再 exit 1，
//         造成「数据被删 + 部署被阻断」双重损失。改为：异常时一律不动 public/data，
//         保留已提交的上一版数据继续构建——页面降级，但站点不断。
const totalCh = Object.values(workChapters).reduce((s, a) => s + a.length, 0);
const existingCh = fs
  .readdirSync(CH_DIR)
  .filter((f) => f.endsWith(".json")).length;
const shrinkRatio = existingCh > 0 ? totalCh / existingCh : 1;
const emptyExport = indexJson.ok === 0 || totalCh === 0;
const forceWrite = process.env.GEN_PRUNE_FORCE === "1";
const shrunk = !forceWrite && existingCh >= 200 && shrinkRatio < 0.5;

if (emptyExport || shrunk) {
  console.error(
    emptyExport
      ? `[gen] 导出为空：可读 ${indexJson.ok} 部 · ${totalCh} 章 —— 疑似数据库/抓取异常`
      : `[gen] 章节数骤降：本次 ${totalCh} 章 vs 现有 ${existingCh} 章（保留率 ${(
          shrinkRatio * 100
        ).toFixed(1)}%）`,
  );
  console.error(
    "[gen] 已跳过本轮写盘：public/data 保持上一版原样，构建继续（不阻断部署），站点使用已提交的数据。",
  );
  console.error(
    "[gen] 排查方向：抓取是否 0 部入库 / DB 是否为空或字段异常；确属正常删减时，设 GEN_PRUNE_FORCE=1 强制写出。",
  );
  db.close();
  process.exit(0);
}

fs.writeFileSync(
  path.join(OUT_DIR, "index.json"),
  JSON.stringify(indexJson, null, 2),
);
if (guidesBlocked > 0) {
  console.warn(
    `[guides] 质量闸门拦下 ${guidesBlocked} 篇（未过 QA，前端显示为筹备中）`,
  );
}
console.log(
  `[guides] 已发布 ${indexJson.guidesCount} 篇导读 / 拦截 ${guidesBlocked} 篇`,
);

for (const w of worksWithSlug) {
  const bookData = {
    ...w,
    chapters: workChapters[w.id] || [],
    guides: worksGuides[w.id] || [],
  };
  fs.writeFileSync(
    path.join(OUT_DIR, `book-${w.id}.json`),
    JSON.stringify(bookData),
  );
}

// 5.1) 稳定引用索引（REF-SPEC v1）：workKey → {slug, 书名, 合法 chapNo 列表}
//      供 /r 解析路由与短链页在纯静态环境下做 URN → 阅读页跳转，无需服务端
const refIndex = {};
for (const w of worksWithSlug) {
  for (const c of workChapters[w.id] || []) {
    const m = /^dc:([^/]+)\/c(\d+)$/.exec(c.ref || "");
    if (!m) continue;
    const wk = m[1];
    refIndex[wk] ??= { s: w.slug, n: w.seed_title, c: [] };
    refIndex[wk].c.push(Number(m[2]));
  }
}
for (const v of Object.values(refIndex)) v.c.sort((a, b) => a - b);
fs.writeFileSync(
  path.join(OUT_DIR, "ref-index.json"),
  JSON.stringify(refIndex),
);

// 6) 清理旧版残留（老 book-*.json 里内嵌全文的时代已过）

// 6.1) 删除库中已不存在的章节文件：避免陈旧正文被一并部署上线
const keep = new Set();
for (const arr of Object.values(workChapters)) {
  for (const c of arr) keep.add(`${c.id}.json`);
}
let removed = 0;
for (const f of fs.readdirSync(CH_DIR)) {
  if (!f.endsWith(".json")) continue;
  if (!keep.has(f)) {
    fs.unlinkSync(path.join(CH_DIR, f));
    removed++;
  }
}
if (removed) console.log(`[gen] 已清理 ${removed} 个陈旧章节文件`);

db.close();

// 7) 零数据门禁已上移至 5.0（写出前拦截，且改成"保数据不阻断"而非硬失败）

const totalRef = Object.values(workChapters)
  .flat()
  .filter((c) => !!c.ref).length;

console.log(
  `[gen] ${worksWithSlug.length} 部书 · 有正文 ${indexJson.ok} · 可阅读 ${indexJson.readable} · ` +
    `${totalCh} 章 → ${CH_DIR}`,
);
console.log(
  `[gen] 稳定引用 ref 覆盖 ${totalRef}/${totalCh} 章` +
    (totalRef === 0
      ? " —— 库中 chapters.ref 全空（未执行 migrate_ref.py），阅读页将退回旧锚 #ch-<id>"
      : ""),
);
