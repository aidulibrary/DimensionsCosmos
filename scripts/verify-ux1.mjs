// UX-1 可复算验收：书库筛选维度扩展（部类 × 朝代 × 排序）+ URL 可分享
// 用法：node scripts/verify-ux1.mjs  （需先 npx astro build 产出 dist/）
// 依赖：本机 Edge + puppeteer-core（可选本机依赖，不入 package.json，避免 CI 拉取 Chromium）
// 口径：所有“结果数”断言都以 /data/index.json 的独立统计为基准，不看页面自报的数字，
//      杜绝“筛选逻辑与计数一起错”的假修复。
import { spawn } from 'node:child_process';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

let puppeteer;
try {
  puppeteer = (await import('puppeteer-core')).default;
} catch {
  console.error('缺少 puppeteer-core：请在本机执行  npm i -D puppeteer-core  后重跑（不影响 CI 构建）。');
  process.exit(2);
}

const DIST = path.resolve('dist');
const EDGE = process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const PORT = 8797, CDP = 9368;
const MIME = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp' };

if (!fs.existsSync(path.join(DIST, 'books', 'index.html'))) {
  console.error('dist/books/index.html 不存在，请先 npx astro build');
  process.exit(2);
}

const srv = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  let f = path.join(DIST, u);
  try { if (fs.statSync(f).isDirectory()) f = path.join(f, 'index.html'); } catch { f = path.join(DIST, u + '/index.html'); }
  fs.readFile(f, (e, b) => {
    if (e) { res.writeHead(404); res.end('404'); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' });
    res.end(b);
  });
}).listen(PORT);

const edge = spawn(EDGE, ['--headless=new', `--remote-debugging-port=${CDP}`, `--user-data-dir=${path.join(process.env.TEMP, 'edge-ux1v-' + Date.now())}`, '--no-first-run', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

let ws = null;
for (let i = 0; i < 60; i++) { try { const r = await fetch(`http://127.0.0.1:${CDP}/json/version`); if (r.ok) { ws = (await r.json()).webSocketDebuggerUrl; break; } } catch {} await wait(300); }
if (!ws) { console.error('CDP 未就绪：Edge 未启动'); process.exit(1); }

const browser = await puppeteer.connect({ browserWSEndpoint: ws, defaultViewport: { width: 1280, height: 900 } });
const page = await browser.newPage();
const pageErrs = [];
page.on('pageerror', (e) => pageErrs.push(String(e).slice(0, 140)));

const out = [];
const ck = (name, ok, detail) => out.push({ name, ok: !!ok, detail });
const BASE = `http://127.0.0.1:${PORT}/books/`;
const go = async (search = '', w = 1280, h = 900) => {
  await page.setViewport({ width: w, height: h });
  await page.goto(BASE + search, { waitUntil: 'networkidle2' });
  await wait(200);
};

const snap = () => page.evaluate(() => {
  const grid = document.querySelector('.book-grid');
  const rows = Array.from(document.querySelectorAll('.filters'));
  const visible = Array.from(grid.querySelectorAll('.book-card:not([hidden])'));
  return {
    rows: rows.length,
    buChips: document.querySelectorAll('.filter-chip[data-bu]').length,
    dynChips: Array.from(document.querySelectorAll('.filter-chip[data-dyn]')).map((a) => ({ k: a.dataset.dyn, t: a.textContent.trim() })),
    sortChips: Array.from(document.querySelectorAll('.filter-chip[data-sort]')).map((a) => a.dataset.sort),
    shown: visible.length,
    hrefs: visible.map((c) => c.querySelector('a').getAttribute('href')),
    chapters: visible.map((c) => +(c.dataset.chapters || 0)),
    chars: visible.map((c) => +(c.dataset.chars || 0)),
    active: {
      bu: (document.querySelector('.filter-chip[data-bu].active') || {}).dataset?.bu ?? null,
      dyn: (document.querySelector('.filter-chip[data-dyn].active') || {}).dataset?.dyn ?? null,
      sort: (document.querySelector('.filter-chip[data-sort].active') || {}).dataset?.sort ?? null,
    },
    count: (document.querySelector('.result-count') || {}).textContent?.trim() || '',
    search: location.search,
    emptyShown: !document.querySelector('.empty')?.hasAttribute('hidden'),
    chipHeights: Array.from(document.querySelectorAll('.filter-chip')).map((c) => Math.round(c.getBoundingClientRect().height)),
    dynHrefOk: Array.from(document.querySelectorAll('.filter-chip[data-dyn]')).filter((a) => a.dataset.dyn).every((a) => a.getAttribute('href').includes('dyn=')),
  };
});

// 先落到书库页，再取数据侧独立统计（与页面渲染同源规则：ok && readable）
await go('');
const data = await page.evaluate(async (port) => {
  const r = await fetch(`http://127.0.0.1:${port}/data/index.json`);
  const d = await r.json();
  return d.works.filter((w) => w.ok && w.readable).map((w) => ({ bu: w.bu, dyn: w.dynasty, chapters: w.chapter_count || 0, chars: w.total_chars || 0 }));
}, PORT);
const TOTAL = data.length;
const byDyn = new Map();
for (const w of data) if (w.dyn) byDyn.set(w.dyn, (byDyn.get(w.dyn) ?? 0) + 1);
const topDyn = [...byDyn.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'zh'))[0][0];
const restDyn = [...byDyn.keys()].filter((d) => (byDyn.get(d) ?? 0) < 3);
const nDyn = (dyn) => data.filter((w) => w.dyn === dyn).length;
const nBu = (bu) => data.filter((w) => w.bu === bu).length;
const nBoth = (bu, dyn) => data.filter((w) => w.bu === bu && w.dyn === dyn).length;
const dynTop3 = [...byDyn.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'zh')).slice(0, 3).map(([d]) => d);
const nonEmptyBu = [...new Set(data.map((w) => w.bu))];
const testBu = nonEmptyBu.map((b) => ({ b, d: dynTop3.find((d) => nBoth(b, d) > 0) })).find((x) => x.d);

// ---- 1. 结构：三行筛选齐备 ----
await go('');
const s0 = await snap();
ck('三行筛选齐备（部类/朝代/排序）', s0.rows === 3, `rows=${s0.rows}`);
ck('朝代 chip 数 = 频次≥3 的朝代数 + 全部', s0.dynChips.filter((c) => !c.k).length === 1, `chips=${s0.dynChips.length}, top=${dynTop3.length}`);
ck('排序 chip = 3（书目序/章数/字数）', s0.sortChips.length === 3, s0.sortChips.join('|'));
ck('默认可见数 = 数据可读总数', s0.shown === TOTAL, `dom=${s0.shown} data=${TOTAL}`);
ck('默认高亮落在“全部”', s0.active.bu === '' && s0.active.dyn === '' && s0.active.sort === '', JSON.stringify(s0.active));
ck('默认 URL 无筛选参数', s0.search === '', s0.search || '(空)');
ck('无 JS 降级：朝代 chip href 带 ?dyn=', s0.dynHrefOk === true, `dynHrefOk=${s0.dynHrefOk}`);

// ---- 2. 单维度朝代筛选 ----
await page.click(`.filter-chip[data-dyn="${topDyn}"]`);
await wait(220);
const s1 = await snap();
ck(`朝代筛选 ${topDyn}：结果数=数据统计`, s1.shown === nDyn(topDyn), `dom=${s1.shown} data=${nDyn(topDyn)}`);
ck('朝代筛选写回 URL', s1.search.includes(`dyn=${encodeURIComponent(topDyn)}`), s1.search);
ck('朝代高亮唯一', s1.active.dyn === topDyn, String(s1.active.dyn));
ck('计数文案含朝代名', s1.count.includes(s1.dynChips.find((c) => c.k === topDyn).t), s1.count);

// ---- 3. 部类 × 朝代 叠加 ----
await page.click(`.filter-chip[data-bu="${testBu.b}"]`);
await wait(220);
const s2 = await snap();
ck(`部类(${testBu.b}) × 朝代(${testBu.d}) 交集数正确`, s2.shown === nBoth(testBu.b, testBu.d), `dom=${s2.shown} data=${nBoth(testBu.b, testBu.d)}`);
ck('两个维度同时写回 URL', s2.search.includes(`bu=${encodeURIComponent(testBu.b)}`) && s2.search.includes(`dyn=${encodeURIComponent(testBu.d)}`), s2.search);

// ---- 4. 带参直开可分享 ----
await go(`?bu=${encodeURIComponent(testBu.b)}&dyn=${encodeURIComponent(testBu.d)}`);
const s3 = await snap();
ck('带参直开：结果数一致', s3.shown === nBoth(testBu.b, testBu.d), `dom=${s3.shown}`);
ck('带参直开：双维高亮还原', s3.active.bu === testBu.b && s3.active.dyn === testBu.d, JSON.stringify(s3.active));

// ---- 5. 排序：章数降序 ----
await go('');
await page.click('.filter-chip[data-sort="chapters"]');
await wait(220);
const s4 = await snap();
const monoCh = s4.chapters.every((v, i, a) => i === 0 || a[i - 1] >= v);
ck('排序·章数：可见卡片严格降序', monoCh && s4.chapters[0] > 0, `head=${s4.chapters.slice(0, 4).join(',')}`);
ck('排序·章数：URL=sort=chapters', s4.search.includes('sort=chapters'), s4.search);
const expectChapTop = Math.max(...data.map((w) => w.chapters));
ck('排序·章数：首项为数据侧最大章数', s4.chapters[0] === expectChapTop, `top=${s4.chapters[0]} data=${expectChapTop}`);

// ---- 6. 排序：字数降序 ----
await page.click('.filter-chip[data-sort="chars"]');
await wait(220);
const s5 = await snap();
const monoChr = s5.chars.every((v, i, a) => i === 0 || a[i - 1] >= v);
const expectCharTop = Math.max(...data.map((w) => w.chars));
ck('排序·字数：可见卡片严格降序', monoChr, `head=${s5.chars.slice(0, 4).join(',')}`);
ck('排序·字数：首项为数据侧最大字数', s5.chars[0] === expectCharTop, `top=${s5.chars[0]} data=${expectCharTop}`);

// ---- 7. 排序带参直开 + 切回书目序还原 ----
await go('?sort=chapters');
const s6 = await snap();
ck('带参直开 sort=chapters 生效', s6.active.sort === 'chapters' && s6.chapters.every((v, i, a) => i === 0 || a[i - 1] >= v), `active=${s6.active.sort}`);
await page.click('.filter-chip[data-sort=""]');
await wait(220);
const s7 = await snap();
ck('切回书目序：顺序还原为构建序', JSON.stringify(s7.hrefs) === JSON.stringify(s0.hrefs), `first=${s7.hrefs[0]} vs ${s0.hrefs[0]}`);
ck('切回书目序：URL 清空 sort', !s7.search.includes('sort='), s7.search || '(空)');

// ---- 8. 排序 + 筛选叠加 ----
await go('');
await page.click(`.filter-chip[data-dyn="${topDyn}"]`);
await page.click('.filter-chip[data-sort="chars"]');
await wait(240);
const s8 = await snap();
ck('朝代 × 字数排序可叠加', s8.shown === nDyn(topDyn) && s8.chars.every((v, i, a) => i === 0 || a[i - 1] >= v), `shown=${s8.shown} top=${s8.chars[0]}`);

// ---- 9. 空态与关键词叠加 ----
await go('?q=zzzznotexist');
const s9 = await snap();
ck('无关关键词：空态显示且计数 0', s9.emptyShown === true && s9.shown === 0, `empty=${s9.emptyShown} shown=${s9.shown}`);

// ---- 10. 移动端：三行 chip 仍 44px 触控 ----
await go('', 375, 800);
const s10 = await snap();
ck('375px：全部 chip 触控高 44px', s10.chipHeights.length > 10 && s10.chipHeights.every((h) => h === 44), `n=${s10.chipHeights.length} min=${Math.min(...s10.chipHeights)}`);
const overflow = await page.evaluate(() => {
  const de = document.documentElement;
  const rows = Array.from(document.querySelectorAll('.filters'));
  return {
    doc: de.scrollWidth - de.clientWidth,
    rows: rows.map((r) => ({ scrollable: r.classList.contains('is-scrollable'), max: r.scrollWidth - r.clientWidth })),
  };
});
ck('375px：无横向溢出', overflow.doc <= 0, `docOverflow=${overflow.doc}`);
ck('375px：可滚动行都挂了 is-scrollable', overflow.rows.every((r) => (r.max > 2) === r.scrollable), JSON.stringify(overflow.rows));

// ---- 11. 其它语言页同步 ----
await go('', 1280, 900);
await page.goto(`http://127.0.0.1:${PORT}/en/books/`, { waitUntil: 'networkidle2' });
await wait(200);
const en = await snap();
ck('en 语言页同样具备三行筛选', en.rows === 3 && en.shown === TOTAL, `rows=${en.rows} shown=${en.shown}`);
await page.goto(`http://127.0.0.1:${PORT}/es/books/`, { waitUntil: 'networkidle2' });
await wait(200);
const es = await snap();
ck('es 语言页同样具备三行筛选', es.rows === 3 && es.shown === TOTAL, `rows=${es.rows} shown=${es.shown}`);

ck('全程无页面 JS error', pageErrs.length === 0, pageErrs.join(' ; ').slice(0, 200));

const pass = out.filter((o) => o.ok).length;
for (const o of out) console.log(`${o.ok ? 'PASS' : 'FAIL'}  ${o.name}${o.detail ? '  [' + o.detail + ']' : ''}`);
console.log(`\nUX-1 验收：${pass}/${out.length} 通过`);

await browser.disconnect();
edge.kill();
srv.close();
process.exit(pass === out.length ? 0 : 1);
