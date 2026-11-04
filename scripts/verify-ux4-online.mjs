// 线上复测：dimensionscosmos.pages.dev/books/ 的 UX-4 口径（无本地 server）
import { spawn } from 'node:child_process';
import path from 'node:path';
import puppeteer from 'puppeteer-core';

const EDGE = process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const PORT = 8795, CDP = 9366;
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

const out = [];
const ck = (name, ok, detail) => out.push({ name, ok: !!ok, detail });

const URL_BOOKS = 'https://dimensionscosmos.pages.dev/books/';
const goto = async (w, h = 800) => { await page.setViewport({ width: w, height: h }); await page.goto(URL_BOOKS, { waitUntil: 'networkidle2', timeout: 60000 }); await wait(350); };

let r;
await page.emulateTimezone('Asia/Shanghai').catch(()=>{});
await goto(375);
r = await probe();
ck('线上 375 无横向溢出', r.docOverflow === 0, `overflow=${r.docOverflow}`);
ck('线上 375 chip 44px', r.chipH.every((h) => Math.abs(h - 44) < 0.5), r.chipH.join('/'));
ck('线上 375 chip 间距 10px', r.chipGap === 10, `${r.chipGap}px`);
ck('线上 375 可横滚', r.scrollW > r.clientW + 2, `scrollW=${r.scrollW} clientW=${r.clientW}`);
ck('线上 375 初始右侧渐隐', /fade-r/.test(r.fClass) && r.fadeR === '22px' && r.mask !== 'none', `class=${r.fClass}`);
ck('线上 375 单列 gap12', r.cols === 1 && r.gridGap === 12, `cols=${r.cols} gap=${r.gridGap}`);
await page.evaluate(() => { const f = document.querySelector('.filters'); f.scrollLeft = f.scrollWidth; });
await wait(350);
r = await probe();
ck('线上 375 滚到底左侧渐隐', /fade-l/.test(r.fClass) && !/fade-r/.test(r.fClass), `class=${r.fClass}`);

for (const w of [540, 580]) {
  await goto(w);
  r = await probe();
  ck(`线上 ${w} 无假渐隐`, r.mask === 'none' && !/fade-r/.test(r.fClass), `mask=${r.mask.slice(0, 20)}`);
  ck(`线上 ${w} 单列`, r.cols === 1, `cols=${r.cols} cardW=${r.cardW}`);
}

await goto(600); r = await probe();
ck('线上 600 单列', r.cols === 1, `cols=${r.cols} cardW=${r.cardW}`);
await goto(768); r = await probe();
ck('线上 768 双列', r.cols === 2 && r.cardW >= 280, `cols=${r.cols} cardW=${r.cardW}`);

await cdp.send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
await page.setViewport({ width: 768, height: 800, hasTouch: true });
await page.goto(URL_BOOKS, { waitUntil: 'networkidle2', timeout: 60000 });
await wait(350);
r = await probe();
ck('线上 768 coarse chip 44px', r.chipH.every((h) => Math.abs(h - 44) < 0.5), r.chipH.join('/'));
await cdp.send('Emulation.setTouchEmulationEnabled', { enabled: false, maxTouchPoints: 1 });

ck('线上无 JS 运行时错误', pageErrs.length === 0, pageErrs.join(' | ') || 'none');

const pass = out.filter((o) => o.ok).length;
for (const o of out) console.log(`${o.ok ? 'PASS' : 'FAIL'}  ${o.name}  ${o.detail ? '— ' + o.detail : ''}`);
console.log(`\n线上复测：${pass}/${out.length} 通过`);
await browser.close(); edge.kill();
process.exit(pass === out.length ? 0 : 1);
