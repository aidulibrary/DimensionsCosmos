/**
 * 构建后生成"稳定引用短链"静态页（REF-SPEC v1 · P0-1 第二阶段）
 *
 * 为每一章输出 <dist>/<workKey>/c<chapNo>/index.html：
 *   /Q276015/c002  →  /books/1-论语/read/#dc:Q276015/c002
 *
 * 为什么放在构建后而不是 Astro 页面：
 *   5531 章若走 getStaticPaths 要过一遍组件编译（构建时间与内存双增），
 *   而短链页内容固定、无组件依赖，直接写 HTML 更快更省，也不进 sitemap。
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

if (!fs.existsSync(DIST)) {
  console.error("[ref-routes] 未找到 dist 目录，请先执行 astro build");
  process.exit(0);
}
if (!fs.existsSync(DATA)) {
  console.warn("[ref-routes] 未找到 public/data，跳过");
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

let books = 0;
let pages = 0;
const refs = new Set();

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
    if (refs.has(urn)) continue;
    refs.add(urn);
    const dir = path.join(DIST, workKey, `c${chapNoRaw}`);
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(
      path.join(dir, "index.html"),
      page({
        urn,
        slug: book.slug,
        book: book.seed_title || book.ws_title || book.slug,
        chapter: String(ch.title || "").split("/").pop() || urn,
      }),
    );
    pages++;
  }
}

console.log(
  `[ref-routes] 已生成 ${pages} 个稳定引用短链页（覆盖 ${books} 部书，去重 ${refs.size} 条 URN）`,
);
