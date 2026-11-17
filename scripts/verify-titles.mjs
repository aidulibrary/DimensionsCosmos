// 375x812 移动仿真：验证史记回填章名在阅读页目录/面包屑的显示与溢出
// 用法：BASE=http://127.0.0.1:4321 node scripts/verify-titles.mjs <outDir>
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const BASE = process.env.BASE || 'http://127.0.0.1:4321';
const OUT = process.argv[2] || path.join(os.tmpdir(), 'titles-verify');
const URL_READ = BASE + '/books/13-%E5%8F%B2%E8%AE%B0/read';
const URL_BOOK = BASE + '/books/13-%E5%8F%B2%E8%AE%B0/';
fs.mkdirSync(OUT, { recursive: true });

const profile = path.join(os.tmpdir(), 'edge-titles-prof-' + Date.now());
spawn(EDGE, ['--headless=new', '--remote-debugging-port=9341', '--user-data-dir=' + profile,
  '--no-first-run', '--no-default-browser-check', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });

const sleep = (ms) => new Promise(r => setTimeout(r, ms));
let msgId = 0; const pending = new Map();

async function wsUrl() {
  for (let i = 0; i < 40; i++) {
    try { const j = await (await fetch('http://127.0.0.1:9341/json/version')).json(); if (j.webSocketDebuggerUrl) return j.webSocketDebuggerUrl; } catch { }
    await sleep(300);
  }
  throw new Error('CDP 未就绪');
}

function rpc(ws, method, params = {}, sessionId) {
  const id = ++msgId;
  return new Promise((res, rej) => { pending.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) })); });
}

(async () => {
  const ws = new WebSocket(await wsUrl());
  const results = [];
  await new Promise(r => ws.addEventListener('open', r));
  ws.addEventListener('message', (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result); }
  });
  const { targetId } = await rpc(ws, 'Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await rpc(ws, 'Target.attachToTarget', { targetId, flatten: true });
  await rpc(ws, 'Page.enable', {}, sessionId);
  await rpc(ws, 'Runtime.enable', {}, sessionId);
  await rpc(ws, 'Emulation.setDeviceMetricsOverride', { width: 375, height: 812, deviceScaleFactor: 2, mobile: true }, sessionId);

  const ev = async (expr) => {
    const r = await rpc(ws, 'Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }, sessionId);
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || 'eval');
    return r.result?.value;
  };
  const shot = async (name) => {
    const r = await rpc(ws, 'Page.captureScreenshot', { format: 'png' }, sessionId);
    fs.writeFileSync(path.join(OUT, name), Buffer.from(r.data, 'base64'));
  };
  const go = async (url) => {
    await rpc(ws, 'Page.navigate', { url }, sessionId);
    await sleep(2500);
  };

  await go(URL_READ);
  const read = await ev(`(() => {
    const docW = document.documentElement.scrollWidth, winW = window.innerWidth;
    const links = [...document.querySelectorAll('.toc-link')];
    const sample = links.slice(0, 3).map(a => ({ t: a.textContent.trim(), w: a.scrollWidth, c: a.clientWidth, over: a.scrollWidth > a.clientWidth + 1 }));
    const longest = links.map(a => a.textContent.trim()).sort((a,b)=>b.length-a.length)[0] || '';
    const overflows = [...document.querySelectorAll('body *')].filter(e => {
      const r = e.getBoundingClientRect(); return r.width > 0 && r.right > winW + 1 && getComputedStyle(e).position !== 'fixed';
    }).slice(0, 5).map(e => ({ tag: e.tagName, cls: e.className.toString().slice(0, 30), par: e.parentElement?.className?.toString().slice(0, 30) || '', right: Math.round(e.getBoundingClientRect().right) }));
    return { docW, winW, tocCount: links.length, sample, longest, longestLen: longest.length,
             crumb: (document.querySelector('.breadcrumb')?.textContent || '').trim().slice(0, 80),
             active: (document.querySelector('.toc-link.active')?.textContent || '').trim(), overflows };
  })()`);
  await shot('read-13-toc.png');
  results.push({ page: 'read', ...read });

  await go(URL_BOOK);
  const book = await ev(`(() => ({ docW: document.documentElement.scrollWidth, winW: window.innerWidth,
    crumb: (document.querySelector('.breadcrumb')?.textContent || '').trim().slice(0,80),
    h1: (document.querySelector('h1')?.textContent || '').trim() }))()`);
  await shot('book-13.png');
  results.push({ page: 'book', ...book });

  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(results, null, 2), 'utf-8');
  console.log(JSON.stringify(results, null, 2));
  process.exit(0);
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
