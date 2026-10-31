/**
 * 构建后 SEO 收尾：生成 robots.txt 与 sitemap.xml。
 *
 * 背景：站点为静态输出（astro build → dist），未引入 @astrojs/sitemap 依赖，
 * 因此在 build 结束后扫描 dist 内的 index.html 自建 sitemap，避免为单一需求
 * 增加依赖体积（本项目在低配机器上构建）。
 *
 * 用法：npm run build 之后自动执行（见 package.json 的 postbuild）。
 */
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..");
const DIST = path.join(ROOT, "dist");
const SITE = "https://dimensionscosmos.pages.dev";

// 不进入搜索引擎索引的内部目录
const EXCLUDE_PREFIX = ["/data/", "/collation/"];

if (!fs.existsSync(DIST)) {
  console.error("[seo] 未找到 dist 目录，请先执行 astro build");
  process.exit(0);
}

/** 递归收集所有 index.html → 对应路由 */
function collect(dir, acc = []) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) {
      if (ent.name === "_astro" || ent.name === "data" || ent.name === "icons") continue;
      collect(p, acc);
    } else if (ent.name === "index.html") {
      let rel = "/" + path.relative(DIST, dir).split(path.sep).join("/");
      rel = rel === "/." ? "/" : rel.replace(/\/\.$/, "") + "/";
      rel = rel.replace(/\/+/g, "/");
      const loc = rel === "/" ? "/" : rel;
      if (EXCLUDE_PREFIX.some((x) => loc.startsWith(x))) continue;
      acc.push({ loc, mtime: fs.statSync(p).mtime });
    }
  }
  return acc;
}

const routes = collect(DIST).sort((a, b) => a.loc.localeCompare(b.loc));

// 首页与一级栏目优先
const priority = (loc) => {
  if (loc === "/") return "1.0";
  if (loc.split("/").filter(Boolean).length <= 1) return "0.8";
  return "0.6";
};

const urls = routes
  .map(
    (r) => `  <url>
    <loc>${SITE}${r.loc}</loc>
    <lastmod>${r.mtime.toISOString().slice(0, 10)}</lastmod>
    <changefreq>${r.loc === "/" ? "daily" : "weekly"}</changefreq>
    <priority>${priority(r.loc)}</priority>
  </url>`,
  )
  .join("\n");

const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;
fs.writeFileSync(path.join(DIST, "sitemap.xml"), sitemap, "utf-8");

const robots = `User-agent: *
Allow: /
Disallow: /data/
Disallow: /collation/

Sitemap: ${SITE}/sitemap.xml
`;
fs.writeFileSync(path.join(DIST, "robots.txt"), robots, "utf-8");

console.log(`[seo] robots.txt + sitemap.xml 已生成（${routes.length} 个 URL）`);
