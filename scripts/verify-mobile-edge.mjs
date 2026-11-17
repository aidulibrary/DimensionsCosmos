// 移动端（375x812 移动仿真）硬证据验证：布局溢出 / 注音开关 / PWA安装与SW / 截图
// 使用本机 Edge headless + CDP（无需安装浏览器扩展或模拟器）
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const OUT = process.argv[2] || path.join(os.tmpdir(), 'mobile-verify');
const BASE = process.env.BASE || 'https://dimensionscosmos.pages.dev';
const TARGETS = [
  { name: 'home', url: BASE + '/', py: false },
  { name: 'books', url: BASE + '/books/', py: false },
  { name: 'read-13-siji', url: BASE + '/books/13-%E5%8F%B2%E8%AE%B0/read', py: true },
];
fs.mkdirSync(OUT, { recursive: true });

const profile = path.join(os.tmpdir(), 'edge-cdp-prof-' + Date.now());
const child = spawn(EDGE, [
  '--headless=new', '--remote-debugging-port=9333', '--user-data-dir=' + profile,
  '--no-first-run', '--no-default-browser-check', '--disable-gpu', '--hide-scrollbars=false',
  '--window-size=375,812', 'about:blank',
], { stdio: 'ignore' });

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function getWs() {
  for (let i = 0; i < 40; i++) {
    try {
      const r = await fetch('http://127.0.0.1:9333/json/version');
      const j = await r.json();
      if (j.webSocketDebuggerUrl) return j.webSocketDebuggerUrl;
    } catch { }
    await sleep(300);
  }
  throw new Error('CDP 未就绪');
}

const results = [];
let msgId = 0;
const pending = new Map();

function send(ws, method, params = {}, sessionId) {
  const id = ++msgId;
  return new Promise((res, rej) => {
    pending.set(id, { res, rej });
    ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
  });
}

async function evaluate(ws, sessionId, expr, awaitPromise = true) {
  const r = await send(ws, 'Runtime.evaluate', {
    expression: expr, returnByValue: true, awaitPromise,
  }, sessionId);
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || 'eval error');
  return r.result?.value;
}

(async () => {
  const url = await getWs();
  const ws = new WebSocket(url);
  await new Promise(r => ws.addEventListener('open', r, { once: true }));
  ws.addEventListener('message', (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id); pending.delete(m.id);
      m.error ? p.rej(new Error(m.error.message)) : p.res(m.result);
    }
  });

  for (const t of TARGETS) {
    const { targetId } = await send(ws, 'Target.createTarget', { url: 'about:blank' });
    const { sessionId } = await send(ws, 'Target.attachToTarget', { targetId, flatten: true });
    await send(ws, 'Page.enable', {}, sessionId);
    await send(ws, 'Runtime.enable', {}, sessionId);
    await send(ws, 'Emulation.setDeviceMetricsOverride', {
      width: 375, height: 812, deviceScaleFactor: 2, mobile: true,
    }, sessionId);
    await send(ws, 'Emulation.setUserAgentOverride', {
      userAgent: 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
    }, sessionId);
    await send(ws, 'Page.navigate', { url: t.url }, sessionId);
    await sleep(4500);

    const base = await evaluate(ws, sessionId, `(() => {
      const de = document.documentElement;
      const over = [];
      document.querySelectorAll('body *').forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && (r.right > innerWidth + 2 || r.left < -2)) {
          over.push((el.tagName + '.' + (el.className || '')).slice(0, 60) + '@' + Math.round(r.right));
        }
      });
      return {
        title: document.title,
        innerWidth, scrollWidth: de.scrollWidth, clientWidth: de.clientWidth,
        overflow: de.scrollWidth > de.clientWidth + 1,
        offenders: over.slice(0, 8),
        manifest: document.querySelector('link[rel=manifest]')?.getAttribute('href') || null,
        themeColor: document.querySelector('meta[name=theme-color]')?.content || null,
        footerLegal: Array.from(document.querySelectorAll('a[href]'))
          .map(a => a.getAttribute('href'))
          .filter(h => /\\/(terms|privacy|refund)\\/?$/.test(h)),
      };
    })()`);

    // PWA / SW 状态
    const pwa = await evaluate(ws, sessionId, `(async () => {
      if (!('serviceWorker' in navigator)) return { sw: 'unsupported' };
      const regs = await navigator.serviceWorker.getRegistrations();
      return { sw: 'supported', count: regs.length,
        scopes: regs.map(r => r.scope),
        active: regs.map(r => !!(r.active && r.active.state === 'activated')) };
    })()`);

    let py = null;
    if (t.py) {
      py = { before: await evaluate(ws, sessionId, `document.getElementById('pyToggle')?.getAttribute('aria-pressed')`) };
      await evaluate(ws, sessionId, `document.getElementById('pyToggle').click()`);
      await sleep(3500);
      py.after = await evaluate(ws, sessionId, `document.getElementById('pyToggle')?.getAttribute('aria-pressed')`);
      py.rubyCount = await evaluate(ws, sessionId, `document.querySelectorAll('ruby, .py, rt').length`);
      py.pinyinChars = await evaluate(ws, sessionId, `(document.body.innerText.match(/[a-zA-Züǖǘǚǜāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]/g)||[]).length`);
      await evaluate(ws, sessionId, `document.getElementById('pyToggle').click()`);
    }

    const shot = await send(ws, 'Page.captureScreenshot', { format: 'png', captureBeyondViewport: false }, sessionId);
    const file = path.join(OUT, 'mobile-' + t.name + '.png');
    fs.writeFileSync(file, Buffer.from(shot.data, 'base64'));

    results.push({ name: t.name, url: t.url, ...base, pwa, py, screenshot: file });
    await send(ws, 'Target.closeTarget', { targetId });
  }

  child.kill();
  fs.writeFileSync(path.join(OUT, 'report.json'), JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results, null, 2));
  process.exit(0);
})().catch(e => { console.error('FAIL', e.message); try { child.kill(); } catch { } process.exit(1); });
