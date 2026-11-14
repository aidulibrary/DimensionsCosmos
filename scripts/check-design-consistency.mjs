#!/usr/bin/env node
/**
 * 站点设计一致性检查（常态化门禁）
 *
 * 背景：新增页面（注音标注台、注音预览页等）若脱离全站设计令牌，会出现"另一套系统"的割裂感。
 * 本脚本把「新页面必须与整站一致」变成可执行检查，纳入日常自检。
 *
 * 检查项：
 *  1) must_layout  —— 页面须经 BaseLayout（含薄壳页 import 的 View 组件链）
 *  2) hex_color    —— 样式内禁止裸十六进制色值（#fff/#000 等极简别名除外），一律 var(--token)
 *  3) rgba_color   —— 禁止裸 rgba()，半透明层用 color-mix(in srgb, var(--token) N%, transparent)
 *  4) font_stack   —— 字体栈须为衬线/楷体/等宽等语义栈（古籍正文），禁止随意新造无衬线栈
 *  5) nav_height   —— 依赖顶栏高度须用 var(--nav-h)，禁止硬编码 top: 40~120px
 *
 * 遗留豁免：BASELINE 内的历史页面违规仅提示、不判定失败；新增页面一律强制。
 *
 * 用法：
 *   node scripts/check-design-consistency.mjs           # 默认：新增页面强制，遗留仅提示
 *   node scripts/check-design-consistency.mjs --strict  # 全部强制
 *   node scripts/check-design-consistency.mjs --json
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = process.cwd();
const PAGES_DIR = path.join(ROOT, 'src', 'pages');
const EXEMPT_LAYOUT = new Set(['404.astro', '500.astro']);
const ALLOW_HEX = new Set(['#fff', '#ffffff', '#000', '#000000', '#0001']);

// 历史遗留页面：字号/配色在令牌体系建立前写定，暂不返工；新页面不得加入本清单
const BASELINE = new Set([
  'src/pages/books/[slug]/read.astro',
  'src/pages/books/[slug].astro',
  'src/pages/brand.astro',
  'src/pages/privacy.astro',
  'src/pages/r.astro',
  'src/pages/read/[slug]/[method].astro',
  'src/pages/tasks/index.astro',
  'src/pages/terms.astro',
  'src/pages/collation/tj-review/index.astro',
]);

const strict = process.argv.includes('--strict');
const asJson = process.argv.includes('--json');
const FONT_OK = /(serif|Kaiti|Songti|STSong|SimSun|monospace|var\(--(serif|sans|mono))|inherit/i;

function walk(dir, out = []) {
  for (const name of fs.readdirSync(dir)) {
    const fp = path.join(dir, name);
    const st = fs.statSync(fp);
    if (st.isDirectory()) walk(fp, out);
    else if (name.endsWith('.astro')) out.push(fp);
  }
  return out;
}

/** 页面或其一级 import 的组件链上是否出现 BaseLayout */
function hasBaseLayout(fp, depth = 0) {
  const src = fs.readFileSync(fp, 'utf8');
  if (/BaseLayout/.test(src)) return true;
  if (depth >= 2) return false;
  const fm = src.match(/^---([\s\S]*?)---/);
  if (!fm) return false;
  for (const m of fm[1].matchAll(/import\s+\w+\s+from\s+['"]([^'"]+\.astro)['"]/g)) {
    const rel = m[1];
    if (!rel.startsWith('.')) continue;
    const target = path.resolve(path.dirname(fp), rel);
    if (fs.existsSync(target) && hasBaseLayout(target, depth + 1)) return true;
  }
  return false;
}

const files = walk(PAGES_DIR);
const rows = [];
for (const fp of files) {
  const rel = path.relative(ROOT, fp).replaceAll('\\', '/');
  const src = fs.readFileSync(fp, 'utf8');
  const styleBlocks = [...src.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map((m) => m[1]).join('\n');
  const inlineAttrs = [...src.matchAll(/style="([^"]*)"/g)].map((m) => m[1]).join('\n');
  const cssText = `${styleBlocks}\n${inlineAttrs}`;

  const issues = [];
  if (!EXEMPT_LAYOUT.has(path.basename(fp)) && !hasBaseLayout(fp)) {
    issues.push({ type: 'must_layout', detail: '未经 BaseLayout 渲染（导航/页脚/主题变量会缺失）' });
  }
  const hexes = [...cssText.matchAll(/#[0-9a-fA-F]{3,8}\b/g)].map((m) => m[0].toLowerCase()).filter((h) => !ALLOW_HEX.has(h));
  if (hexes.length) issues.push({ type: 'hex_color', detail: [...new Set(hexes)].slice(0, 8).join(' ') });
  const rgbas = [...cssText.matchAll(/rgba?\([^)]*\)/g)].map((m) => m[0]);
  if (rgbas.length) issues.push({ type: 'rgba_color', detail: [...new Set(rgbas)].slice(0, 6).join(' ') });
  const fonts = [...cssText.matchAll(/font-family\s*:\s*([^;]+);/g)].map((m) => m[1].trim()).filter((f) => !FONT_OK.test(f));
  if (fonts.length) issues.push({ type: 'font_stack', detail: [...new Set(fonts)].join(' | ') });
  const navPx = [...cssText.matchAll(/top\s*:\s*(\d+)px/g)].map((m) => Number(m[1])).filter((v) => v >= 40 && v <= 120);
  if (navPx.length) issues.push({ type: 'nav_height', detail: `top: ${navPx.join(',')}px（请用 var(--nav-h)）` });

  if (issues.length) rows.push({ file: rel, baseline: BASELINE.has(rel), issues });
}

const failed = rows.filter((r) => strict || !r.baseline);
const report = { scanned: files.length, violations: rows.length, failing: failed.length, rows };

if (asJson) {
  console.log(JSON.stringify(report, null, 2));
} else {
  console.log(`[design] 扫描 ${files.length} 个页面；违规 ${rows.length}（其中强制阻断 ${failed.length}）`);
  for (const r of rows) {
    console.log(`  ${r.baseline && !strict ? '·' : '✗'} ${r.file}${r.baseline ? '（遗留豁免）' : ''}`);
    for (const i of r.issues) console.log(`      - ${i.type}: ${i.detail}`);
  }
  if (!failed.length) console.log('  ✓ 新增页面设计一致性通过');
}
process.exit(failed.length ? 1 : 0);
