// URN 端到端：/r?urn= → 实际落点章节名与锚点（375x812）
import { spawn } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs';

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const B = process.env.BASE || 'https://dimensionscosmos.pages.dev';
const URN = process.env.URN || 'dc:Q272530/c005';
const OUT = process.argv[2] || path.join(os.tmpdir(), 'urn-check');
fs.mkdirSync(OUT, { recursive: true });

spawn(EDGE, ['--headless=new', '--remote-debugging-port=9355', '--user-data-dir=' + path.join(os.tmpdir(), 'edge-urn-' + Date.now()),
  '--no-first-run', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
let id = 0; const pend = new Map();
const rpc = (ws, m, p = {}, s) => { const i = ++id; return new Promise((res, rej) => { pend.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method: m, params: p, ...(s ? { sessionId: s } : {}) })); }); };

(async () => {
  let wsUrl;
  for (let i = 0; i < 40; i++) { try { const j = await (await fetch('http://127.0.0.1:9355/json/version')).json(); if (j.webSocketDebuggerUrl) { wsUrl = j.webSocketDebuggerUrl; break; } } catch { } await sleep(300); }
  const ws = new WebSocket(wsUrl);
  await new Promise(r => ws.addEventListener('open', r));
  ws.addEventListener('message', (e) => { const m = JSON.parse(e.data); if (m.id && pend.has(m.id)) { const p = pend.get(m.id); pend.delete(m.id); m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result); } });
  const { targetId } = await rpc(ws, 'Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await rpc(ws, 'Target.attachToTarget', { targetId, flatten: true });
  await rpc(ws, 'Page.enable', {}, sessionId); await rpc(ws, 'Runtime.enable', {}, sessionId);
  await rpc(ws, 'Emulation.setDeviceMetricsOverride', { width: 375, height: 812, deviceScaleFactor: 2, mobile: true }, sessionId);
  const ev = async (x) => (await rpc(ws, 'Runtime.evaluate', { expression: x, returnByValue: true, awaitPromise: true }, sessionId)).result?.value;

  await rpc(ws, 'Page.navigate', { url: B + '/r?urn=' + encodeURIComponent(URN) }, sessionId);
  await sleep(5000);
  const r = await ev(`(() => ({
    url: location.href.slice(0, 160),
    title: document.title,
    h: (document.querySelector('h1,h2')?.textContent || '').trim().slice(0, 60),
    active: (document.querySelector('.toc-link.active')?.textContent || '').trim(),
    bodyHead: document.body.innerText.replace(/\\s+/g,' ').slice(0, 160)
  }))()`);
  const shot = await rpc(ws, 'Page.captureScreenshot', { format: 'png' }, sessionId);
  fs.writeFileSync(path.join(OUT, 'urn-landing.png'), Buffer.from(shot.data, 'base64'));
  console.log(JSON.stringify({ urn: URN, ...r }, null, 2));
  process.exit(0);
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
