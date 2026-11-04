// UX-4 可复算验收：触控目标 44px / chip 间距 / 筛选行横滚与渐隐 / 卡片密度断点
// 用法：node scripts/verify-ux4.mjs  （需先 npm run build 产出 dist/）
// 依赖：本机 Edge + puppeteer-core（devDependency，缺失时 npm i -D puppeteer-core）
import { spawn } from 'node:child_process';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import puppeteer from 'puppeteer-core';

const DIST = path.resolve('dist');
const EDGE = process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const PORT = 8795, CDP = 9366;
const MIME = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp' };

if (!fs.existsSync(path.join(DIST, 'books', 'index.html'))) {
  console.error('dist/books/index.html 不存在，请先 npm run build');
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

const edge = spawn(EDGE, ['--headless=new', `--remote-debugging-port=${CDP}`, `--user-data-dir=${path.join(process.env.TEMP, 'edge-ux4v-' + Date.now())}`, '--no-first-run', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

let ws = null;
for (let i = 0; i < 60; i++) { try { const r = await fetch(`http://127.0.0.1:${CDP}/json/version`); if (r.ok) { ws = (await r.json()).webSocketDebuggerUrl; break; } } catch {} await wait(300); }
if (!ws) { console.error('CDP 未就绪：Edge 未启动'); process.exit(1); }

const browser = await puppeteer.connect({ browserWSEndpoint: ws, defaultViewport: { width: 375, height: 800 } });
const page = await browser.newPage();
const pageErrs = [];
page.on('pageerror', (e) => pageErrs.push(String(e).slice(0, 120)));
const cdp = await page.target().createCDPSession();

const out = [];
const ck = (name, ok, detail) => out.push({ name, ok: !!ok, detail });

const URL_BOOKS = `http://127.0.0.1:${PORT}/books/`;
const goto = async (w, h = 800) => { await page.setViewport({ width: w, height: h }); await page.goto(URL_BOOKS, { waitUntil: 'networkidle2' }); await wait(250); };

const probe = () => page.evaluate(() => {
  const f = document.querySelector('.filters');
  const grid = document.querySelector('.book-grid');
  const cs = getComputedStyle(f);
  const chips = Array.from(document.querySelectorAll('.filter-chip'));
  const cards = Array.from(grid.querySelectorAll('.book-card:not([hidden]) .card-link'));
  const ys = cards.slice(0, 12).map((c) => Math.round(c.getBoundingClientRect().top + window.scrollY));
  const firstRowY = Math.min(...ys);
  return {
    fClass: f.className,
    mask: (cs.maskImage || cs.webkitMaskImage || 'none'),
    fadeR: cs.getPropertyValue('--fade-r').trim(),
    fadeL: cs.getPropertyValue('--fade-l').trim(),
    scrollW: f.scrollWidth, clientW: f.clientWidth, scrollLeft: f.scrollLeft,
    chipH: chips.map((c) => +c.getBoundingClientRect().height.toFixed(1)),
    chipGap: parseFloat(cs.columnGap) || 0,
    cols: ys.filter((y) => y === firstRowY).length,
    cardW: cards[0] ? +cards[0].getBoundingClientRect().width.toFixed(1) : 0,
    gridGap: parseFloat(getComputedStyle(grid).rowGap) || 0,
    docOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  };
});

// ---- 375：移动端主场景 ----
await goto(375);
let r = await probe();
ck('375 无横向溢出', r.docOverflow === 0, `overflow=${r.docOverflow}`);
ck('375 chip 触控高 44px', r.chipH.every((h) => Math.abs(h - 44) < 0.5), r.chipH.join('/'));
ck('375 chip 间距 10px', r.chipGap === 10, `${r.chipGap}px`);
ck('375 筛选行可横滚', r.scrollW > r.clientW + 2, `scrollW=${r.scrollW} clientW=${r.clientW}`);
ck('375 初始右侧渐隐 fade-r', /fade-r/.test(r.fClass) && r.fadeR === '22px' && r.mask !== 'none', `class=${r.fClass} fadeR=${r.fadeR}`);
ck('375 单列 + 网格间距 12', r.cols === 1 && r.gridGap === 12, `cols=${r.cols} gap=${r.gridGap}`);

await page.evaluate(() => { const f = document.querySelector('.filters'); f.scrollLeft = f.scrollWidth; });
await wait(300);
r = await probe();
ck('375 滚到底左侧渐隐 fade-l', /fade-l/.test(r.fClass) && !/fade-r/.test(r.fClass) && r.fadeL === '22px', `class=${r.fClass} fadeL=${r.fadeL}`);

// ---- 481–600：非溢出区间不得残留 mask（防"假渐隐"）----
for (const w of [500, 540, 560, 580]) {
  await goto(w);
  r = await probe();
  ck(`${w} 无假渐隐（mask=none）`, r.mask === 'none' && !/fade-r/.test(r.fClass), `mask=${r.mask.slice(0, 24)} class=${r.fClass}`);
  ck(`${w} 单列且 gap 12`, r.cols === 1 && r.gridGap === 12, `cols=${r.cols} cardW=${r.cardW} gap=${r.gridGap}`);
}

// ---- 600 / 768：密度与触控口径 ----
await goto(600);
r = await probe();
ck('600 单列', r.cols === 1, `cols=${r.cols} cardW=${r.cardW}`);

await goto(768);
r = await probe();
ck('768 双列（卡宽 ≥ 280）', r.cols === 2 && r.cardW >= 280, `cols=${r.cols} cardW=${r.cardW}`);
ck('768 无渐隐（wrap 布局）', r.mask === 'none', `mask=${r.mask.slice(0, 24)}`);

// 触屏设备（pointer: coarse）在宽视口也应保持 44px
await cdp.send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
await page.setViewport({ width: 768, height: 800, hasTouch: true, isMobile: false });
await page.goto(URL_BOOKS, { waitUntil: 'networkidle2' });
await wait(250);
const coarse = await page.evaluate(() => matchMedia('(pointer: coarse)').matches);
r = await probe();
ck('768 pointer:coarse 媒体命中', coarse === true, `matches=${coarse}`);
ck('768 pointer:coarse chip 44px', r.chipH.every((h) => Math.abs(h - 44) < 0.5), r.chipH.join('/'));
await cdp.send('Emulation.setTouchEmulationEnabled', { enabled: false, maxTouchPoints: 1 });

// ---- 过滤功能回归 ----
await goto(375);
await page.type('[data-books-q]', '庄');
await wait(500);
const filtered = await page.evaluate(() => ({
  count: document.querySelectorAll('.book-grid .book-card:not([hidden])').length,
  label: (document.querySelector('.result-count') || {}).textContent.trim(),
}));
ck('过滤「庄」命中 1 部', filtered.count === 1, `count=${filtered.count} label=${filtered.label}`);
await page.click('[data-books-clear]').catch(() => {});
await wait(500);
const cleared = await page.evaluate(() => document.querySelectorAll('.book-grid .book-card:not([hidden])').length);
ck('清空恢复全集 112 部', cleared === 112, `count=${cleared}`);
ck('无 JS 运行时错误', pageErrs.length === 0, pageErrs.join(' | ') || 'none');

// ---- 汇总 ----
const pass = out.filter((o) => o.ok).length;
for (const o of out) console.log(`${o.ok ? 'PASS' : 'FAIL'}  ${o.name}  ${o.detail ? '— ' + o.detail : ''}`);
console.log(`\nUX-4 验收：${pass}/${out.length} 通过`);

await browser.close(); edge.kill(); srv.close();
process.exit(pass === out.length ? 0 : 1);

