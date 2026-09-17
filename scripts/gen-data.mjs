// 构建脚本：从 SQLite 读取，生成 Astro 能用的 JSON 数据源。
// 运行时：npm run build 的前置步骤，或在 Astro frontmatter 里 import 调用。
// 依赖：Node 22+ 原生 node:sqlite，零外部包。
import { DatabaseSync } from "node:sqlite";
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const DB_PATH = path.join(ROOT, "data", "guji.db");
const OUT_DIR = path.join(ROOT, "public", "data");

if (!fs.existsSync(DB_PATH)) {
  console.warn(
    "[gen] data/guji.db 不存在，跳过（GitHub Actions 构建时会先 clone）",
  );
  process.exit(0);
}

fs.mkdirSync(OUT_DIR, { recursive: true });

const db = new DatabaseSync(DB_PATH, { readonly: true });

// 1) 书库总表（首页书库用）
const works = db
  .prepare(
    `
  SELECT w.id, w.seed_title, w.ws_title, w.bu, w.author, w.dynasty,
         w.status, w.wikidata_qid, w.fetched_at,
         (SELECT COUNT(*) FROM chapters c WHERE c.work_id = w.id) AS chapter_count
  FROM works w
  ORDER BY w.bu, w.id
`,
  )
  .all();

// slug: "{id}-{safe_title}" — 保留中文字符，只替换 URL 不安全字符
const safeSlug = (t) =>
  String(t || "untitled")
    .replace(/[\/\?#]/g, "-")
    .replace(/\s+/g, "-");
const worksWithSlug = works.map((w) => ({
  ...w,
  slug: `${w.id}-${safeSlug(w.seed_title)}`,
  ok: w.status === "ok",
}));

// 2) 分类聚合（首页三层导读/书库筛选用）
const byBu = {};
for (const w of worksWithSlug) {
  byBu[w.bu] ??= [];
  byBu[w.bu].push(w);
}

// 3) AI 解读（ai_guides 表，join method_id → result JSON）
const worksGuides = {};
try {
  const guides = db
    .prepare(
      `
    SELECT work_id, method_id, result, generated_at, model_used
    FROM ai_guides ORDER BY work_id, method_id
  `,
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
  // ai_guides 表可能尚不存在（首次构建时），忽略
}

// 4) 详情页所需：每本书 + 章节
const workChapters = {};
for (const w of worksWithSlug) {
  if (!w.ok) continue;
  const chapters = db
    .prepare(
      `
    SELECT id, title, text, chars FROM chapters
    WHERE work_id = ? ORDER BY id
  `,
    )
    .all(w.id);
  workChapters[w.id] = chapters.map((c) => ({
    id: c.id,
    title: c.title,
    text: c.text || "",
    excerpt: (c.text || "").slice(0, 200),
    chars: c.chars,
  }));
}

// 5) 写出 JSON
const indexJson = {
  generatedAt: new Date().toISOString(),
  total: worksWithSlug.length,
  ok: worksWithSlug.filter((w) => w.ok).length,
  taxonomy: db.prepare("SELECT name, parent FROM taxonomy ORDER BY name").all(),
  byBu,
  works: worksWithSlug,
  guidesCount: Object.values(worksGuides).reduce((sum, g) => sum + g.length, 0),
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

db.close();
console.log(
  `[gen] ${worksWithSlug.length} 部书 · ${worksWithSlug.filter((w) => w.ok).length} 部有正文 → ${OUT_DIR}`,
);
