/**
 * UX-8 交付质量审计（非回归门禁，产出量化证据）
 *
 * 目的：回答"这套首屏交付是否达到国际一线成熟应用的工程与体验标准"，
 * 用可实测指标代替主观判断。审计不参与 CI 门禁（不作为 pass/fail 卡点），
 * 只输出指标 + 阈值对照，供人工判读。
 *
 * 采集维度：
 *   1) Core Web Vitals：LCP / CLS / TTFB / FCP（真实浏览器实测，非估算）
 *   2) 资源与体积：请求数、传输字节、渲染阻塞资源、字体加载
 *   3) 无 JS 可用性：关闭 JS 后首屏 CTA 与三步条是否仍可用（渐进增强）
 *   4) 键盘可达：Tab 序列前若干元素是否有可见焦点环
 *   5) 对比度：关键文本 / CTA 的 WCAG 2.x 对比度实测
 *   6) 动效偏好：prefers-reduced-motion 下是否仍触发过渡
 *   7) SEO：canonical / JSON-LD / robots / sitemap / hreflang / x-default
 *
 * 用法：
 *   node scripts/audit-ux8-quality.mjs                # 默认审线上
 *   SITE=http://127.0.0.1:8798 node scripts/audit-ux8-quality.mjs
 * 依赖：本机 Edge + puppeteer-core（同 verify-ux8，不进 package.json）
 */
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

let puppeteer;
try {
  puppeteer = (await import('puppeteer-core')).default;
} catch {
  console.error('缺少 puppeteer-core。请先：npm i -D puppeteer-core');
  process.exit(2);
}

const SITE = (process.env.SITE || 'https://dimensionscosmos.pages.dev').replace(/\/$/, '');
const EDGE = process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const CDP = 9381;
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

const edge = spawn(EDGE, ['--headless=new', `--remote-debugging-port=${CDP}`,
  `--user-data-dir=${path.join(process.env.TEMP, 'edge-uq-' + Date.now())}`,
  '--no-first-run', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });

const ws = await (async () => {
  for (let i = 0; i < 60; i++) {
    try {
      // 必须取 browser 级 ws（/json/version），page 级 ws 连上去会报 Target.getBrowserContexts: Not allowed
      const v = await (await fetch(`http://127.0.0.1:${CDP}/json/version`)).json();
      if (v?.webSocketDebuggerUrl) return v.webSocketDebuggerUrl;
    } catch {}
    await wait(300);
  }
  throw new Error('Edge CDP 未就绪');
})();

const browser = await puppeteer.connect({ browserWSEndpoint: ws, defaultViewport: { width: 1280, height: 900 } });

// ── 采集：CWV + 资源 ────────────────────────────────────────────────────────
// MOBILE=1 时按一线口径复测移动端：Slow 4G + 4x CPU 节流 + 393x852 视口
const MOBILE = process.env.MOBILE === '1';

async function metrics(url) {
  const page = await browser.newPage();
  if (MOBILE) {
    await page.setViewport({ width: 393, height: 852, deviceScaleFactor: 2.75, isMobile: true, hasTouch: true });
    const cdp = await page.createCDPSession();
    await cdp.send('Network.enable');
    await cdp.send('Network.emulateNetworkConditions', {
      offline: false, latency: 150,
      downloadThroughput: (1.6 * 1024 * 1024) / 8, // ~1.6Mbps，Slow 4G 下限
      uploadThroughput: (750 * 1024) / 8,
    });
    await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
  }
  await page.evaluateOnNewDocument(() => {
    window.__lcp = 0; window.__cls = 0; window.__lt = 0;
    new PerformanceObserver((l) => {
      for (const e of l.getEntries()) window.__lcp = Math.max(window.__lcp, e.startTime);
    }).observe({ type: 'largest-contentful-paint', buffered: true });
    new PerformanceObserver((l) => {
      for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value;
    }).observe({ type: 'layout-shift', buffered: true });
    new PerformanceObserver((l) => {
      for (const e of l.getEntries()) window.__lt = e.loadTime;
    }).observe({ type: 'navigation', buffered: true });
  });
  const t0 = Date.now();
  await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
  // 给 LCP 一个静默窗口，避免过早读取
  await wait(600);
  const m = await page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation')[0] || {};
    const res = performance.getEntriesByType('resource').map((r) => ({
      name: r.name.replace(location.origin, ''), type: r.initiatorType,
      bytes: r.transferSize || 0, ms: Math.round(r.duration),
    }));
    const blocking = res.filter((r) => r.type === 'link' || r.type === 'script');
    return {
      lcp: Math.round(window.__lcp),
      cls: Math.round(window.__cls * 1000) / 1000,
      fcp: Math.round(performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? 0),
      ttfb: Math.round(nav.responseStart ?? 0),
      domContentLoaded: Math.round(nav.domContentLoadedEventEnd ?? 0),
      requests: res.length,
      bytes: res.reduce((a, b) => a + b.bytes, 0),
      renderBlocking: blocking.length,
      heaviest: res.sort((a, b) => b.bytes - a.bytes).slice(0, 5),
      fonts: res.filter((r) => /woff|font/i.test(r.name)).length,
    };
  });
  m.wall = Date.now() - t0;
  await page.close();
  return m;
}

// ── 采集：无 JS 可用性 ──────────────────────────────────────────────────────
async function noJs(url) {
  const page = await browser.newPage();
  await page.setJavaScriptEnabled(false);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  const r = await page.evaluate(() => ({
    primary: document.querySelector('[data-hero-cta="primary"]')?.textContent?.trim() || null,
    primaryHref: document.querySelector('[data-hero-cta="primary"]')?.getAttribute('href') || null,
    steps: document.querySelectorAll('[data-start] .step').length,
    stepLinks: Array.from(document.querySelectorAll('[data-start] .step a')).map((a) => a.getAttribute('href')),
    featuredCards: document.querySelectorAll('[data-featured] .feat-card').length,
    featuredFallback: !!document.querySelector('[data-featured-empty]'),
  }));
  await page.close();
  return r;
}

// ── 采集：键盘焦点可见性 ────────────────────────────────────────────────────
async function keyboard(url, n = 8) {
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
  const seq = [];
  for (let i = 0; i < n; i++) {
    await page.keyboard.press('Tab');
    await wait(60);
    seq.push(await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return { tag: 'body', visible: false };
      const cs = getComputedStyle(el);
      const outline = cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0;
      const shadow = cs.boxShadow && cs.boxShadow !== 'none';
      return {
        tag: el.tagName.toLowerCase(),
        text: (el.textContent || '').trim().slice(0, 18),
        outline, shadow,
        visible: outline || shadow,
      };
    }));
  }
  await page.close();
  return seq;
}

// ── 采集：对比度（WCAG 2.x） ────────────────────────────────────────────────
async function contrast(url) {
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
  const r = await page.evaluate(() => {
    const parse = (c) => {
      const m = c.match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/);
      return m ? { r: +m[1], g: +m[2], b: +m[3], a: m[4] === undefined ? 1 : +m[4] } : null;
    };
    const lum = ({ r, g, b }) => {
      const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
    };
    const bgOf = (el) => {
      let cur = el;
      while (cur) {
        const bg = parse(getComputedStyle(cur).backgroundColor);
        if (bg && bg.a > 0.05) return bg;
        cur = cur.parentElement;
      }
      return { r: 255, g: 255, b: 255, a: 1 };
    };
    const ratio = (fg, bg) => {
      const l1 = lum(fg), l2 = lum(bg);
      const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1];
      return Math.round(((hi + 0.05) / (lo + 0.05)) * 100) / 100;
    };
    const sample = (sel, label) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const cs = getComputedStyle(el);
      const fg = parse(cs.color), bg = bgOf(el);
      if (!fg) return null;
      const size = parseFloat(cs.fontSize);
      const bold = (parseInt(cs.fontWeight, 10) || 400) >= 700;
      const large = size >= 24 || (size >= 18.66 && bold);
      return { label, ratio: ratio(fg, bg), size, large, need: large ? 3 : 4.5 };
    };
    return [
      sample('[data-hero-cta="primary"]', 'hero 主 CTA'),
      sample('.hero p, .hero-sub, .hero-hint', 'hero 说明文字'),
      sample('[data-start] .step .n', '步骤序号'),
      sample('[data-start] .step h3', '步骤标题'),
      sample('[data-start] .step p', '步骤说明'),
      sample('.aud-tab[data-aud="general"]', '身份栏标签'),
    ].filter(Boolean);
  });
  await page.close();
  return r;
}

// ── 采集：动效偏好 ──────────────────────────────────────────────────────────
async function reducedMotion(url) {
  const page = await browser.newPage();
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
  const r = await page.evaluate(() => {
    const els = Array.from(document.querySelectorAll('a, button, [data-start] .step'));
    let withTransition = 0;
    for (const el of els) {
      const d = getComputedStyle(el).transitionDuration;
      if (d && d !== '0s' && !/^0s(,\s*0s)*$/.test(d)) withTransition++;
    }
    const hasRule = Array.from(document.styleSheets).some((ss) => {
      try {
        return Array.from(ss.cssRules).some((r) => String(r.cssText).includes('prefers-reduced-motion'));
      } catch { return false; }
    });
    return { interactive: els.length, withTransition, hasReducedMotionRule: hasRule };
  });
  await page.close();
  return r;
}

// ── 采集：SEO 基础 ──────────────────────────────────────────────────────────
async function seo(url) {
  const page = await browser.newPage();
  const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  const r = await page.evaluate(() => ({
    canonical: document.querySelector('link[rel="canonical"]')?.href || null,
    ldJson: document.querySelectorAll('script[type="application/ld+json"]').length,
    hreflang: Array.from(document.querySelectorAll('link[rel="alternate"][hreflang]')).map((l) => l.hreflang),
    xDefault: !!document.querySelector('link[rel="alternate"][hreflang="x-default"]'),
    metaDesc: document.querySelector('meta[name="description"]')?.content?.length ?? 0,
    ogTags: document.querySelectorAll('meta[property^="og:"]').length,
    titleZh: document.title.slice(0, 40),
  }));
  r.status = resp?.status() ?? 0;
  await page.close();
  for (const f of ['/robots.txt', '/sitemap.xml']) {
    try {
      const res = await fetch(SITE + f, { method: 'GET' });
      r[f] = res.status;
      if (f === '/sitemap.xml' && res.ok) {
        const t = await res.text();
        r.sitemapUrls = (t.match(/<loc>/g) || []).length;
      }
    } catch (e) { r[f] = 'ERR'; }
  }
  return r;
}

const out = { site: SITE, at: new Date().toISOString(), mode: MOBILE ? 'mobile-slow4g-cpu4x' : 'desktop' };
try {
  out.home = await metrics(SITE + '/');
  out.detail = await metrics(SITE + '/books/13-%E5%8F%B2%E8%AE%B0/');
  out.noJs = await noJs(SITE + '/');
  out.keyboard = await keyboard(SITE + '/');
  out.contrast = await contrast(SITE + '/');
  out.reducedMotion = await reducedMotion(SITE + '/');
  out.seo = await seo(SITE + '/');
} finally {
  await browser.close();
  edge.kill();
}

console.log(JSON.stringify(out, null, 2));

const dir = path.resolve('temp');
fs.mkdirSync(dir, { recursive: true });
const f = path.join(dir, `ux8-quality-${SITE.includes('127.0.0.1') ? 'local' : 'online'}.json`);
fs.writeFileSync(f, JSON.stringify(out, null, 2), 'utf-8');
console.log('\n已写入', f);
