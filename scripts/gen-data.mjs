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
const worksGuides = {};
try {
  const guides = db
    .prepare(
      `SELECT work_id, method_id, result, generated_at, model_used
       FROM ai_guides ORDER BY work_id, method_id`,
    )
    .all();
  for (const g of guides) {
    worksGuides[g.work_id] ??= [];
    let parsed = {};
    try {
      parsed = JSON.parse(g.result || "{}");
    } catch (_) {
      /* ignore */
    }
    worksGuides[g.work_id].push({
      method_id: g.method_id,
      generated_at: g.generated_at,
      model_used: g.model_used,
      content: parsed.content || parsed,
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
          ${col.quality}, ${col.note}, ${col.clean}, ${col.blocks}
   FROM chapters c WHERE c.work_id = ? ${ORDER}`,
);

const workChapters = {};
const missing = [];
for (const w of worksWithSlug) {
  if (!w.ok) continue;
  const rows = chapterStmt.all(w.id);
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
fs.writeFileSync(
  path.join(OUT_DIR, "index.json"),
  JSON.stringify(indexJson, null, 2),
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

// 6) 清理旧版残留（老 book-*.json 里内嵌全文的时代已过）
const totalCh = Object.values(workChapters).reduce((s, a) => s + a.length, 0);

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

// 7) 零数据门禁：导出结果为空说明库/字段异常，必须硬失败，禁止空产物上线
if (!indexJson.ok || totalCh === 0) {
  console.error(
    `[gen] 导出结果异常：可读 ${indexJson.ok} 部 · ${totalCh} 章 —— 疑似数据库或字段异常，终止构建`,
  );
  process.exit(1);
}

console.log(
  `[gen] ${worksWithSlug.length} 部书 · 有正文 ${indexJson.ok} · 可阅读 ${indexJson.readable} · ` +
    `${totalCh} 章 → ${CH_DIR}`,
);
