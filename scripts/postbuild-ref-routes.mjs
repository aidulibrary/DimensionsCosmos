/**
 * 构建后处理"稳定引用短链"（REF-SPEC v1 · P0-1 第二阶段）
 *
 * 目标：/Q276015/c002 → /books/1-论语/read/#dc:Q276015/c002
 *
 * 三种模式（REF_ROUTE_MODE）：
 *   dynamic（默认）：不生成静态页，只输出 <dist>/data/ref-index/works.json（workKey → slug），
 *                    由 functions/_middleware.js 在边缘 302 重定向。
 *                    用途：Cloudflare Pages 单次部署上限 20000 文件，9874 个短链页会撑爆配额。
 *   static         ：旧行为，为每章写 <dist>/<workKey>/c<chapNo>/index.html（仅本地/回滚使用）。
 *   off            ：什么都不做。
 *
 * 数据源：public/data/book-*.json 内每章的 ref 字段（gen-data 已导出）。
 * 用法：npm run build 之后自动执行（见 package.json 的 postbuild）。
 */
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..");
const DATA = path.join(ROOT, "public", "data");
const DIST = path.join(ROOT, "dist");
const SITE = "https://dimensionscosmos.pages.dev";

const MODE = (process.env.REF_ROUTE_MODE || "dynamic").toLowerCase();

if (!fs.existsSync(DIST)) {
  console.error("[ref-routes] 未找到 dist 目录，请先执行 astro build");
  process.exit(0);
}
if (!fs.existsSync(DATA)) {
  console.warn("[ref-routes] 未找到 public/data，跳过");
  process.exit(0);
}
if (MODE === "off") {
  console.log("[ref-routes] REF_ROUTE_MODE=off，跳过短链输出");
  process.exit(0);
}

const esc = (s) =>
  String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

const page = ({ urn, slug, book, chapter }) => `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>${esc(chapter)} · ${esc(book)} · 维点图书馆</title>
<link rel="canonical" href="${esc(`${SITE}/books/${slug}/read/#${urn}`)}">
<meta http-equiv="refresh" content="0;url=${esc(`/books/${slug}/read/#${urn}`)}">
<style>html,body{margin:0;height:100%;background:#fbf7ef;color:#2c2620;font-family:"Songti SC","Source Han Serif SC",Georgia,serif}body{display:grid;place-items:center;padding:32px;line-height:1.9}main{max-width:640px;border:1px solid #e6dccb;border-radius:14px;background:#fffdf8;padding:28px}h1{font-size:18px;letter-spacing:3px;margin:0 0 12px}p{margin:0 0 10px;font-size:15px}.u{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;background:#f6efe2;border-radius:8px;padding:8px 10px;word-break:break-all}.m{color:#8a7a63;font-size:13px}a{color:#9c6b30}</style>
</head>
<body>
<main>
<h1>正在定位原文</h1>
<p>${esc(book)} · ${esc(chapter)}</p>
<p class="u">${esc(urn)}</p>
<p class="m">若浏览器未自动跳转，请点此：<a href="${esc(`/books/${slug}/read/#${urn}`)}">打开阅读页</a></p>
</main>
<script>
(function () {
  var urn = ${JSON.stringify(urn)};
  var target = "/books/" + ${JSON.stringify(slug)} + "/read/#" + urn;
  var a = document.querySelector("a");
  if (a) a.href = target;
  location.replace(target);
})();
</script>
</body>
</html>
`;

/** 扫描 book-*.json，收集 workKey → slug 映射与可生成短链的章节 */
function collect() {
  const workMap = new Map(); // workKey → slug
  const entries = []; // { urn, workKey, chapNo, slug, book, chapter }
  const seenRef = new Set();
  let books = 0;

  for (const f of fs.readdirSync(DATA)) {
    const m = /^book-(\d+)\.json$/.exec(f);
    if (!m) continue;
    let book;
    try {
      book = JSON.parse(fs.readFileSync(path.join(DATA, f), "utf8"));
    } catch {
      continue;
    }
    if (!book?.slug) continue;
    books++;
    for (const ch of book.chapters || []) {
      const rm = /^dc:([^/]+)\/c(\d+)$/.exec(ch.ref || "");
      if (!rm) continue;
      const [, workKey, chapNoRaw] = rm;
      // 只有 3 位以上零填充的章号才配短链，避免 c1 与 c001 两套写法
      if (chapNoRaw.length < 3) continue;
      const urn = ch.ref;
      if (seenRef.has(urn)) continue;
      seenRef.add(urn);
      const prev = workMap.get(workKey);
      if (prev && prev !== book.slug) {
        console.warn(`[ref-routes] workKey ${workKey} 指向多部书（${prev} / ${book.slug}），保留前者`);
      } else {
        workMap.set(workKey, book.slug);
      }
      entries.push({
        urn,
        workKey,
        chapNo: chapNoRaw,
        slug: prev || book.slug,
        book: book.seed_title || book.ws_title || book.slug,
        chapter: String(ch.title || "").split("/").pop() || urn,
      });
    }
  }
  return { books, workMap, entries, urnCount: seenRef.size };
}

const { books, workMap, entries, urnCount } = collect();

if (MODE === "static") {
  let pages = 0;
  for (const e of entries) {
    const dir = path.join(DIST, e.workKey, `c${e.chapNo}`);
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(
      path.join(dir, "index.html"),
      page({ urn: e.urn, slug: e.slug, book: e.book, chapter: e.chapter }),
    );
    pages++;
  }
  console.log(
    `[ref-routes] static：已生成 ${pages} 个稳定引用短链页（覆盖 ${books} 部书，去重 ${urnCount} 条 URN）`,
  );
  process.exit(0);
}

// dynamic：只落一份 workKey → slug 索引，交给边缘函数 302
const outDir = path.join(DIST, "data", "ref-index");
fs.mkdirSync(outDir, { recursive: true });
const index = {};
for (const [wk, slug] of [...workMap.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
  index[wk] = slug;
}
const outFile = path.join(outDir, "works.json");
fs.writeFileSync(outFile, JSON.stringify(index), "utf-8");

console.log(
  `[ref-routes] dynamic：已输出 ${Object.keys(index).length} 条 workKey 索引（${(
    fs.statSync(outFile).size / 1024
  ).toFixed(1)} KB），覆盖 ${urnCount} 条 URN / ${books} 部书；静态短链页已停用（节省 ${urnCount} 个部署文件）`,
);
