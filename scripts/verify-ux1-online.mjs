// UX-1 线上复测：pages.dev 上的书库三相筛选（部类 × 朝代 × 排序）与 URL 分享
// 用法：node scripts/verify-ux1-online.mjs
// 依赖：本机 Edge + puppeteer-core（可选本机依赖，不入 package.json，避免 CI 拉取 Chromium）
// 口径：结果数一律以线上 /data/index.json 的独立统计为基准；线上取不到数据则整轮判失败，
//      不拿本地数据"代答"线上结果。
import { spawn } from 'node:child_process';
import path from 'node:path';

let puppeteer;
try {
  puppeteer = (await import('puppeteer-core')).default;
} catch {
  console.error('缺少 puppeteer-core：请在本机执行  npm i -D puppeteer-core  后重跑。');
  process.exit(2);
}

const SITE = process.env.SITE || 'https://dimensionscosmos.pages.dev';
const EDGE = process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const CDP = 9370;
const spawnEdge = spawn(EDGE, ['--headless=new', `--remote-debugging-port=${CDP}`, `--user-data-dir=${path.join(process.env.TEMP, 'edge-ux1on-' + Date.now())}`, '--no-first-run', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

let ws = null;
for (let i = 0; i < 80; i++) { try { const r = await fetch(`http://127.0.0.1:${CDP}/json/version`); if (r.ok) { ws = (await r.json()).webSocketDebuggerUrl; break; } } catch {} await wait(300); }
if (!ws) { console.error('CDP 未就绪：Edge 未启动'); process.exit(1); }

const browser = await puppeteer.connect({ browserWSEndpoint: ws, defaultViewport: { width: 1280, height: 900 } });
const page = await browser.newPage();
const errs = [];
page.on('pageerror', (e) => errs.push(String(e).slice(0, 140)));

const out = [];
const ck = (name, ok, detail) => out.push({ name, ok: !!ok, detail });

const go = async (search = '', w = 1280, h = 900) => {
  await page.setViewport({ width: w, height: h });
  await page.goto(`${SITE}/books/${search}`, { waitUntil: 'networkidle2', timeout: 60000 });
  await wait(400);
};

const snap = () => page.evaluate(() => {
  const grid = document.querySelector('.book-grid');
  const visible = Array.from(grid ? grid.querySelectorAll('.book-card:not([hidden])') : []);
  return {
    rows: document.querySelectorAll('.filters').length,
    dynChips: Array.from(document.querySelectorAll('.filter-chip[data-dyn]')).filter((a) => a.dataset.dyn).length,
    sortChips: document.querySelectorAll('.filter-chip[data-sort]').length,
    shown: visible.length,
    chars: visible.map((c) => +(c.dataset.chars || 0)),
    chapters: visible.map((c) => +(c.dataset.chapters || 0)),
    hrefs: visible.slice(0, 3).map((c) => c.querySelector('a').getAttribute('href')),
    count: (document.querySelector('.result-count') || {}).textContent?.trim() || '',
    chipHeights: Array.from(document.querySelectorAll('.filter-chip')).map((c) => Math.round(c.getBoundingClientRect().height)),
  };
});

// 1. 线上默认态
await go('');
const s0 = await snap();
ck('线上：三行筛选存在', s0.rows === 3, `rows=${s0.rows}`);
ck('线上：朝代 chip > 10 个', s0.dynChips > 10, `n=${s0.dynChips}`);
ck('线上：排序 chip = 3', s0.sortChips === 3, `n=${s0.sortChips}`);
ck('线上：默认渲染全部可读书目（>100）', s0.shown > 100, `shown=${s0.shown}`);

// 2. 线上数据侧基准
const stat = await page.evaluate(async (site) => {
  const r = await fetch(`${site}/data/index.json`);
  const d = await r.json();
  const works = d.works.filter((w) => w.ok && w.readable);
  const byDyn = {};
  for (const w of works) if (w.dynasty) byDyn[w.dynasty] = (byDyn[w.dynasty] || 0) + 1;
  const top = Object.entries(byDyn).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'zh'))[0];
  const byKey = (k) => works.filter((w) => w.bu && w.dynasty && w[k] > 0);
  return {
    total: works.length,
    topDyn: top[0],
    topDynCount: top[1],
    maxChars: Math.max(...works.map((w) => w.total_chars || 0)),
    maxChapters: Math.max(...works.map((w) => w.chapter_count || 0)),
    hasBoth: byKey('total_chars').length > 0,
  };
}, SITE);
ck('线上数据可独立取到', stat.total > 100, `total=${stat.total}`);

// 3. 朝代带参直开
await go(`?dyn=${encodeURIComponent(stat.topDyn)}`);
const s1 = await snap();
ck(`线上：?dyn=${stat.topDyn} 结果数=数据统计`, s1.shown === stat.topDynCount, `dom=${s1.shown} data=${stat.topDynCount}`);
ck('线上：计数含朝代名', s1.count.includes(stat.topDyn), s1.count);

// 4. 排序带参直开
await go('?sort=chars');
const s2 = await snap();
ck('线上：?sort=chars 生效且降序', s2.chars.length > 0 && s2.chars.every((v, i, a) => i === 0 || a[i - 1] >= v), `top=${s2.chars[0]}`);
ck('线上：字数排序首项=数据最大字数', s2.chars[0] === stat.maxChars, `top=${s2.chars[0]} data=${stat.maxChars}`);

await go('?sort=chapters');
const s3 = await snap();
ck('线上：?sort=chapters 生效且降序', s3.chapters.every((v, i, a) => i === 0 || a[i - 1] >= v), `top=${s3.chapters[0]}`);
ck('线上：章数排序首项=数据最大章数', s3.chapters[0] === stat.maxChapters, `top=${s3.chapters[0]} data=${stat.maxChapters}`);

// 5. 叠加态
await go(`?dyn=${encodeURIComponent(stat.topDyn)}&sort=chapters`);
const s4 = await snap();
ck('线上：朝代 × 排序叠加不炸', s4.shown === stat.topDynCount && s4.chapters.every((v, i, a) => i === 0 || a[i - 1] >= v), `shown=${s4.shown}`);

// 6. 移动端触控
await go('', 375, 800);
const s5 = await snap();
ck('线上 375px：全部 chip 触控 44px', s5.chipHeights.length > 10 && s5.chipHeights.every((h) => h === 44), `n=${s5.chipHeights.length} min=${Math.min(...s5.chipHeights)}`);
const docOver = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
ck('线上 375px：无横向溢出', docOver <= 0, `overflow=${docOver}`);

// 7. 三语页
for (const loc of ['en', 'es']) {
  await page.setViewport({ width: 1280, height: 900 });
  await page.goto(`${SITE}/${loc}/books/`, { waitUntil: 'networkidle2', timeout: 60000 });
  await wait(350);
  const sl = await snap();
  ck(`线上 /${loc}/books/ 三行筛选齐备`, sl.rows === 3 && sl.shown === stat.total, `rows=${sl.rows} shown=${sl.shown}`);
}

ck('线上无页面 JS error', errs.length === 0, errs.join(' ; ').slice(0, 200));

const pass = out.filter((o) => o.ok).length;
for (const o of out) console.log(`${o.ok ? 'PASS' : 'FAIL'}  ${o.name}${o.detail ? '  [' + o.detail + ']' : ''}`);
console.log(`\nUX-1 线上复测：${pass}/${out.length} 通过`);

await browser.disconnect();
spawnEdge.kill();
process.exit(pass === out.length ? 0 : 1);
