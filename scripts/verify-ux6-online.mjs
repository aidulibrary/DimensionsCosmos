// UX-6 线上复测：详情页题名繁体正名 + 四部分类路径（pages.dev）
// 用法：node scripts/verify-ux6-online.mjs
// 依赖：本机 Edge + puppeteer-core（可选本机依赖，不入 package.json，避免 CI 拉取 Chromium）
// 口径：正名/分类路径的期望值一律取自线上 /data/index.json 与 /data/siku-map.json，
//      线上取不到就整轮判失败，不拿本地数据代答线上结果；URL 统一带尾斜杠，规避 308 与旧 HTML 缓存。
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
const CDP = 9371;
const edge = spawn(EDGE, ['--headless=new', `--remote-debugging-port=${CDP}`, `--user-data-dir=${path.join(process.env.TEMP, 'edge-ux6on-' + Date.now())}`, '--no-first-run', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

let ws = null;
for (let i = 0; i < 80; i++) { try { const r = await fetch(`http://127.0.0.1:${CDP}/json/version`); if (r.ok) { ws = (await r.json()).webSocketDebuggerUrl; break; } } catch {} await wait(300); }
if (!ws) { console.error('CDP 未就绪：Edge 未启动'); process.exit(1); }

const out = [];
const ck = (name, ok, detail) => out.push({ name, ok: !!ok, detail });

// 线上数据基准
const bust = `?v=${Date.now()}`;
let index, siku;
try {
  index = await (await fetch(`${SITE}/data/index.json${bust}`)).json();
  siku = await (await fetch(`${SITE}/data/siku-map.json${bust}`)).json();
} catch (e) {
  console.error('线上数据取不到，无法建立基准：' + e);
  process.exit(1);
}
const works = index.works ?? [];
const bySlug = new Map(works.map((w) => [w.slug, w]));
ck('线上 /data/siku-map.json 可访问', !!siku.map, `keys=${Object.keys(siku.map || {}).length}`);

const browser = await puppeteer.connect({ browserWSEndpoint: ws, defaultViewport: { width: 1280, height: 900 } });
const page = await browser.newPage();
const errs = [];
page.on('pageerror', (e) => errs.push(String(e).slice(0, 140)));

const go = async (p, w = 1280, h = 900) => {
  await page.setViewport({ width: w, height: h });
  await page.goto(`${SITE}${p}`, { waitUntil: 'networkidle2', timeout: 60000 });
  await wait(350);
};
const snap = () => page.evaluate(() => {
  const t = (s) => (document.querySelector(s) || {}).textContent?.replace(/\s+/g, ' ').trim() ?? null;
  const h1 = document.querySelector('.book-header h1');
  const de = document.documentElement;
  return {
    h1: h1?.textContent?.trim() ?? null,
    h1Lang: h1?.getAttribute('lang') ?? null,
    alias: t('.title-alias'),
    tax: t('.tax-line'),
    sub: t('.tax-sub'),
    buHref: (document.querySelector('.tax-bu') || {}).getAttribute?.('href') ?? null,
    overflowX: de.scrollWidth - de.clientWidth,
    docTitle: document.title,
  };
});

const samples = ['13-史记', '1-论语', '120-三国演义', '108-天演论', '147-般若波罗蜜多心经'];
for (const slug of samples) {
  const w = bySlug.get(slug);
  if (!w) { ck(`线上样本存在 ${slug}`, false, 'index.json 无此书'); continue; }
  const wsTitle = (w.ws_title || '').trim();
  const expTitle = wsTitle && wsTitle !== w.seed_title ? wsTitle : w.seed_title;
  const expSub = (siku.map || {})[slug] ?? null;

  await go(`/books/${encodeURIComponent(slug)}/`);
  const s = await snap();
  ck(`线上 ${slug} h1=正名`, s.h1 === expTitle, `${s.h1} vs ${expTitle}`);
  ck(`线上 ${slug} 通称行`, expTitle === w.seed_title ? s.alias === null : s.alias === `通称 ${w.seed_title}`, s.alias);
  ck(`线上 ${slug} 分类路径`, (s.tax || '').includes(w.bu) && s.sub === expSub, `${s.tax} | sub=${s.sub}`);
  ck(`线上 ${slug} 部级可点`, s.buHref === `/books?bu=${encodeURIComponent(w.bu)}`, s.buHref);
  ck(`线上 ${slug} 页面标题含正名`, (s.docTitle || '').startsWith(expTitle), s.docTitle);
  ck(`线上 ${slug} 1280 无横向溢出`, s.overflowX <= 1, s.overflowX);

  await go(`/books/${encodeURIComponent(slug)}/`, 375, 780);
  const m = await snap();
  ck(`线上 ${slug} 375 无横向溢出`, m.overflowX <= 1, m.overflowX);
}

// 部级跳转 + 书库四部结果数
await go('/books/13-%E5%8F%B2%E8%AE%B0/');
if (await page.$('.tax-bu')) {
  await Promise.all([page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 60000 }), page.click('.tax-bu')]);
  await wait(500);
  const a = await page.evaluate(() => ({
    url: location.pathname + location.search,
    active: (document.querySelector('.filter-chip[data-bu].active') || {}).dataset?.bu ?? null,
    shown: document.querySelectorAll('.book-card:not([hidden])').length,
  }));
  const exp = works.filter((w) => w.bu === '史部').length;
  ck('线上 点击史部跳转分面', a.url.includes('bu=') && a.active === '史部' && a.shown === exp, `${a.url} active=${a.active} shown=${a.shown}/${exp}`);
} else {
  ck('线上 点击史部跳转分面', false, '未找到 .tax-bu');
}

for (const bu of ['经部', '史部', '子部', '集部']) {
  const exp = works.filter((w) => w.bu === bu).length;
  await go(`/books/?bu=${encodeURIComponent(bu)}`);
  const n = await page.evaluate(() => document.querySelectorAll('.book-card:not([hidden])').length);
  ck(`线上 书库 ${bu} 结果数`, n === exp, `${n} vs ${exp}`);
}

ck('线上 无 JS 运行错误', errs.length === 0, errs.join(' | ').slice(0, 200));

console.log('');
for (const r of out) console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.name}  ${r.ok ? '' : '<< ' + r.detail}`);
const pass = out.filter((r) => r.ok).length;
console.log(`\nUX-6 线上验收：${pass}/${out.length}`);

await browser.close();
edge.kill();
process.exit(pass === out.length ? 0 : 1);
