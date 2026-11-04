// UX-6 可复算验收：① 题名以繁体正名为准（附通称）② 四部分类升级为分类路径
// 用法：node scripts/verify-ux6.mjs  （需先 npm run build 产出 dist/）
// 依赖：本机 Edge + puppeteer-core（可选本机依赖，不入 package.json，避免 CI 拉取 Chromium）
// 口径：正名/分类路径的期望值一律从 public/data/index.json + public/data/siku-map.json 独立计算，
//      不看页面自报内容，杜绝「渲染与数据一起错」的假修复；覆盖 112 部抽检 + 全量静态另由
//      temp 脚本比对（不入库）。
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
const PORT = 8798, CDP = 9369;
const MIME = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp' };

if (!fs.existsSync(path.join(DIST, 'books', 'index.html'))) {
  console.error('dist/books/index.html 不存在，请先 npm run build');
  process.exit(2);
}

const index = JSON.parse(fs.readFileSync('public/data/index.json', 'utf-8'));
const siku = JSON.parse(fs.readFileSync('public/data/siku-map.json', 'utf-8'));
const works = index.works ?? [];
const bySlug = new Map(works.map((w) => [w.slug, w]));

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

const edge = spawn(EDGE, ['--headless=new', `--remote-debugging-port=${CDP}`, `--user-data-dir=${path.join(process.env.TEMP, 'edge-ux6v-' + Date.now())}`, '--no-first-run', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });
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
const BASE = `http://127.0.0.1:${PORT}`;
const go = async (p, w = 1280, h = 900) => {
  await page.setViewport({ width: w, height: h });
  await page.goto(BASE + p, { waitUntil: 'networkidle2' });
  await wait(150);
};
const snapDetail = () => page.evaluate(() => {
  const t = (s) => (document.querySelector(s) || {}).textContent?.replace(/\s+/g, ' ').trim() ?? null;
  const h1 = document.querySelector('.book-header h1');
  const bu = document.querySelector('.tax-bu');
  const de = document.documentElement;
  return {
    h1: h1?.textContent?.trim() ?? null,
    h1Lang: h1?.getAttribute('lang') ?? null,
    alias: t('.title-alias'),
    tax: t('.tax-line'),
    sub: t('.tax-sub'),
    buHref: bu?.getAttribute('href') ?? null,
    overflowX: de.scrollWidth - de.clientWidth,
    docTitle: document.title,
  };
});

// ---- 抽检样本：有二级类（史记/论语）、无二级（三国演义/天演论）、长题名（心经） ----
const samples = ['13-史记', '1-论语', '120-三国演义', '108-天演论', '147-般若波罗蜜多心经'];

for (const slug of samples) {
  const w = bySlug.get(slug);
  if (!w) { ck(`样本存在 ${slug}`, false, 'index.json 无此书'); continue; }
  const wsTitle = (w.ws_title || '').trim();
  const expTitle = wsTitle && wsTitle !== w.seed_title ? wsTitle : w.seed_title;
  const expSub = siku.map?.[slug] ?? null;

  await go(`/books/${encodeURIComponent(slug)}/`, 1280, 900);
  const s = await snapDetail();

  ck(`${slug} h1=正名`, s.h1 === expTitle, `${s.h1} vs ${expTitle}`);
  ck(`${slug} 正名字形标注`, expTitle === w.seed_title ? s.h1Lang === null : s.h1Lang === 'zh-Hant', s.h1Lang);
  ck(`${slug} 通称行`, expTitle === w.seed_title ? s.alias === null : s.alias === `通称 ${w.seed_title}`, s.alias);
  ck(`${slug} 分类路径`, expSub ? (s.tax || '').includes(w.bu) && s.sub === expSub : (s.tax || '').includes(w.bu) && s.sub === null, `${s.tax} | sub=${s.sub}`);
  ck(`${slug} 部级可点回分面`, s.buHref === `/books?bu=${encodeURIComponent(w.bu)}`, s.buHref);
  ck(`${slug} 页面标题含正名`, (s.docTitle || '').startsWith(expTitle), s.docTitle);
  ck(`${slug} 1280 无横向溢出`, s.overflowX <= 1, s.overflowX);

  // 375 端：题名换正名后笔画更宽，重点看是否溢出
  await go(`/books/${encodeURIComponent(slug)}/`, 375, 780);
  const m = await snapDetail();
  ck(`${slug} 375 无横向溢出`, m.overflowX <= 1, m.overflowX);
  ck(`${slug} 375 分类路径未截断`, (m.tax || '').includes(w.bu), m.tax);
}

// ---- 分类路径可点：点部级 -> 落到书库并对上筛选态 ----
await go('/books/13-%E5%8F%B2%E8%AE%B0/', 1280, 900);
if (await page.$('.tax-bu')) {
  await Promise.all([page.waitForNavigation({ waitUntil: 'networkidle2' }), page.click('.tax-bu')]);
  await wait(250);
  const after = await page.evaluate(() => ({
    url: location.pathname + location.search,
    active: (document.querySelector('.filter-chip[data-bu].active') || {}).dataset?.bu ?? null,
    shown: document.querySelectorAll('.book-card:not([hidden])').length,
    buOfCards: Array.from(document.querySelectorAll('.book-card:not([hidden])')).map((c) => c.dataset.bu),
  }));
  const expShi = works.filter((w) => w.bu === '史部').length;
  ck('点击史部跳转书库分面', after.url.includes('bu=') && after.active === '史部', after.url + ' active=' + after.active);
  ck('书库史部结果数与数据基准一致', after.shown === expShi && after.buOfCards.every((b) => b === '史部'), `${after.shown} vs ${expShi}`);
} else {
  ck('点击史部跳转书库分面', false, '未找到 .tax-bu');
}

// ---- 书库回归：部类分面整体仍可用（四部各一次） ----
for (const bu of ['经部', '史部', '子部', '集部']) {
  const exp = works.filter((w) => w.bu === bu).length;
  await go(`/books?bu=${encodeURIComponent(bu)}`, 1280, 900);
  const n = await page.evaluate(() => document.querySelectorAll('.book-card:not([hidden])').length);
  ck(`书库 ${bu} 结果数`, n === exp, `${n} vs ${exp}`);
}

ck('无 JS 运行错误', pageErrs.length === 0, pageErrs.join(' | ').slice(0, 200));

console.log('');
for (const r of out) console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.name}  ${r.ok ? '' : '<< ' + r.detail}`);
const pass = out.filter((r) => r.ok).length;
console.log(`\nUX-6 浏览器验收：${pass}/${out.length}`);

await browser.close();
edge.kill();
srv.close();
process.exit(pass === out.length ? 0 : 1);
