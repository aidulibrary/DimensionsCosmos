// UX-8 线上复测：首屏引导与精选（pages.dev）
// 用法：node scripts/verify-ux8-online.mjs
// 依赖：本机 Edge + puppeteer-core（可选本机依赖，不入 package.json，避免 CI 拉取 Chromium）
// 口径：
//   · 期望值一律取自线上 /data/index.json 与 /data/featured.json（404 则按 SEED 分支期望），
//     线上数据取不到就整轮判失败，不拿本地数据代答线上结果；
//   · URL 统一带尾斜杠规避 308 与旧 HTML 缓存；
//   · 线上若仍是旧版（无精选区），首轮断言即失败，不静默放行。
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
const CDP = 9373;
const AUD = ['student', 'general', 'family', 'research'];
const SEED = {
  '1-论语': ['student', 'general', 'family', 'research'],
  '23-老子': ['general', 'research'],
  '32-颜氏家训': ['family', 'student'],
  '33-世说新语': ['general', 'family', 'student'],
  '13-史记': ['student', 'general', 'research'],
  '17-资治通鉴': ['general', 'research'],
};

const edge = spawn(EDGE, ['--headless=new', `--remote-debugging-port=${CDP}`, `--user-data-dir=${path.join(process.env.TEMP, 'edge-ux8on-' + Date.now())}`, '--no-first-run', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

let ws = null;
for (let i = 0; i < 80; i++) { try { const r = await fetch(`http://127.0.0.1:${CDP}/json/version`); if (r.ok) { ws = (await r.json()).webSocketDebuggerUrl; break; } } catch {} await wait(300); }
if (!ws) { console.error('CDP 未就绪：Edge 未启动'); process.exit(1); }

const out = [];
const ck = (name, ok, detail) => out.push({ name, ok: !!ok, detail });
const bust = `?v=${Date.now()}`;

// ── 线上数据基准 ────────────────────────────────────────────────────────────
let index;
try {
  index = await (await fetch(`${SITE}/data/index.json${bust}`)).json();
} catch (e) {
  console.error('线上 /data/index.json 取不到，无法建立基准：' + e);
  process.exit(1);
}
const works = index.works ?? [];
const bySlug = new Map(works.map((w) => [w.slug, w]));

// featured.json 是否已供数（404 = 未供数，走 SEED 分支期望）
let featured = null;
try {
  const r = await fetch(`${SITE}/data/featured.json${bust}`);
  if (r.ok) featured = await r.json();
} catch {}
const usingFile = !!(featured && Array.isArray(featured.items) && featured.items.length);
const EXPECT = usingFile
  ? Object.fromEntries(featured.items.map((i) => [i.slug, i.audiences || []]))
  : SEED;
const expPanels = Object.fromEntries(AUD.map((a) => [a, Object.keys(EXPECT).filter((s) => EXPECT[s].includes(a))]));
ck('线上 featured.json 状态可判定', true, usingFile ? `已供数 ${featured.items.length} 部` : '未供数，按 SEED 分支断言');

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
  const root = document.querySelector('[data-featured]');
  const de = document.documentElement;
  if (!root) return { exists: false, overflowX: de.scrollWidth - de.clientWidth };
  return {
    exists: true,
    overflowX: de.scrollWidth - de.clientWidth,
    defaultAud: root.dataset.defaultAud,
    reasonCount: root.querySelectorAll('.feat-reason').length,
    tabs: Array.from(root.querySelectorAll('.aud-tab')).map((t) => ({ aud: t.dataset.aud, count: Number(t.dataset.count), h: Math.round(t.getBoundingClientRect().height) })),
    panels: Array.from(root.querySelectorAll('.aud-panel')).map((p) => ({
      aud: p.dataset.panel,
      hidden: p.hasAttribute('hidden'),
      cards: Array.from(p.querySelectorAll('.feat-card')).map((c) => ({
        slug: c.dataset.slug,
        hasGuide: c.dataset.hasGuide,
        href: c.getAttribute('href'),
        reason: (c.querySelector('.feat-reason')?.textContent || '').trim(),
      })),
    })),
    placeholders: ['—', '——', '暂无', '待补', '待定', 'TBD', 'TODO', 'null', 'undefined', 'N/A']
      .filter((k) => (root.textContent || '').includes(k)),
  };
});

// ── 中文首页 ────────────────────────────────────────────────────────────────
await go('/');
const s = await snap();
ck('线上 首屏精选区已上线', s.exists, '未找到 [data-featured]（多半为旧版 HTML 或部署未生效）');
if (s.exists) {
  ck('线上 四身份栏齐备且顺序固定', s.tabs.map((t) => t.aud).join(',') === AUD.join(','), s.tabs.map((t) => t.aud).join(','));
  ck('线上 身份栏触控高度 ≥44px', s.tabs.every((t) => t.h >= 44), JSON.stringify(s.tabs.map((t) => t.h)));
  ck('线上 默认栏落在 general', s.defaultAud === 'general', s.defaultAud);
  ck('线上 默认仅 general 可见', s.panels.filter((p) => !p.hidden).map((p) => p.aud).join(',') === 'general', s.panels.filter((p) => !p.hidden).map((p) => p.aud).join(','));
  ck('线上 无占位符字符', s.placeholders.length === 0, s.placeholders.join(','));
  ck('线上 1280 无横向溢出', s.overflowX <= 1, s.overflowX);

  for (const a of AUD) {
    const p = s.panels.find((x) => x.aud === a);
    ck(`线上 ${a} 条目与线上数据一致`, p && p.cards.map((c) => c.slug).join(',') === expPanels[a].join(','), `${p?.cards?.map((c) => c.slug).join(',')} vs ${expPanels[a].join(',')}`);
  }

  const allCards = s.panels.flatMap((p) => p.cards);
  // 降级分支①：guides 为空的书（史记 / 资治通鉴）
  for (const slug of ['13-史记', '17-资治通鉴']) {
    const w = bySlug.get(slug);
    if (!w) { ck(`线上 ${slug} 存在于线上数据`, false, 'index.json 无此书'); continue; }
    const expHasGuide = (w.guides?.length ?? 0) > 0;
    const cards = allCards.filter((c) => c.slug === slug);
    ck(`线上 ${slug} guides 为空则降级`, expHasGuide || (cards.length > 0 && cards.every((c) => c.hasGuide === '0')), `${expHasGuide} ${cards.map((c) => c.hasGuide).join('')}`);
    if (!expHasGuide) {
      ck(`线上 ${slug} CTA 直达阅读页`, cards.every((c) => decodeURIComponent(c.href || '') === `/books/${slug}/read`), cards.map((c) => c.href)[0]);
    }
  }

  // 有导读的书：CTA 指详情页
  const lunyu = allCards.filter((c) => c.slug === '1-论语');
  ck('线上 有导读的书 CTA 指详情页', lunyu.length > 0 && lunyu.every((c) => c.hasGuide === '1' && decodeURIComponent(c.href || '') === '/books/1-论语/'), lunyu.map((c) => c.href)[0]);

  // 交互：点学生栏
  await page.click('.aud-tab[data-aud="student"]');
  await wait(220);
  const after = await page.evaluate(() => ({
    visible: Array.from(document.querySelectorAll('.aud-panel')).filter((p) => !p.hasAttribute('hidden')).map((p) => p.dataset.panel),
    selected: document.querySelector('.aud-tab[aria-selected="true"]')?.dataset?.aud ?? null,
  }));
  ck('线上 点击身份栏可切换面板', after.visible.join(',') === 'student' && after.selected === 'student', JSON.stringify(after));

  await go('/', 375, 780);
  const m = await snap();
  ck('线上 375 无横向溢出', m.overflowX <= 1, m.overflowX);
  ck('线上 375 身份栏触控高度 ≥44px', m.tabs.every((t) => t.h >= 44), JSON.stringify(m.tabs.map((t) => t.h)));
}

// ── 英文页：未过审不硬译 ────────────────────────────────────────────────────
await go('/en/');
const en = await snap();
ck('线上 英文页精选区已上线', en.exists, '未找到 [data-featured]');
if (en.exists) {
  ck('线上 英文页 1280 无横向溢出', en.overflowX <= 1, en.overflowX);
  ck('线上 英文页身份栏齐备', en.tabs.map((t) => t.aud).join(',') === AUD.join(','), en.tabs.map((t) => t.aud).join(','));
  if (!usingFile) ck('线上 未供数时不渲染推荐语', en.reasonCount === 0, `reasonCount=${en.reasonCount}`);
}

// ── 首屏引导（hero 主 CTA + 三步条）：线上断言 ─────────────────────────────
// 期望值独立计算：第三步 = 精选顺序里第一个线上 guides 非空的书
const startSlug = Object.keys(SEED).find((slug) => (bySlug.get(slug)?.guides?.length ?? 0) > 0) ?? Object.keys(SEED)[0];
const startHref = `/books/${startSlug}/read`;

const snapStart = () => page.evaluate(() => {
  const dec = (u) => { try { return decodeURIComponent(u); } catch { return u; } };
  const bx = (el) => { const r = el.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height, top: r.top + scrollY }; };
  const p = document.querySelector('[data-hero-cta="primary"]');
  const s = document.querySelector('[data-hero-cta="secondary"]');
  const hint = document.querySelector('[data-hero-hint]');
  const steps = Array.from(document.querySelectorAll('[data-start] .step'));
  return {
    primary: p ? { text: p.textContent.trim(), href: dec(p.getAttribute('href') || ''), ...bx(p) } : null,
    secondary: s ? { text: s.textContent.trim(), href: dec(s.getAttribute('href') || ''), ...bx(s) } : null,
    hint: hint ? { href: hint.getAttribute('href') || '', target: !!document.querySelector('#start') } : null,
    vh: innerHeight,
    steps: steps.map((el) => ({
      mark: el.querySelector('.n')?.textContent?.trim() || '',
      title: el.querySelector('h3')?.textContent?.trim() || '',
      href: dec(el.querySelector('a')?.getAttribute('href') || ''),
      ctaH: el.querySelector('a')?.getBoundingClientRect().height ?? 0,
      ...bx(el),
    })),
    overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  };
});

await go('/');
const st = await snapStart();
ck('线上 首屏主 CTA 已上线', !!st.primary && st.primary.href === '/books', st.primary?.href ?? '未找到 [data-hero-cta=primary]');
ck('线上 首屏主 CTA 首屏内可见', !!st.primary && st.primary.top < st.vh && st.primary.h >= 48, JSON.stringify(st.primary && [st.primary.top, st.vh, st.primary.h]));
ck('线上 首屏次 CTA 指向方法页', st.secondary?.href === '/methods', st.secondary?.href ?? '未找到');
ck('线上 首屏分流提示锚点存在', st.hint?.href === '#start' && st.hint?.target, JSON.stringify(st.hint));
ck('线上 三步条三步齐全', st.steps.length === 3 && st.steps.every((x) => x.mark && x.title), JSON.stringify(st.steps.map((x) => x.title)));
ck('线上 三步链接与线上数据一致', st.steps.map((x) => x.href).join(',') === ['/books', '/methods', startHref].join(','), `${st.steps.map((x) => x.href).join(',')} vs /books,/methods,${startHref}`);
ck('线上 步骤 CTA 触控 ≥44px', st.steps.every((x) => x.ctaH >= 44), JSON.stringify(st.steps.map((x) => x.ctaH)));

await go('/', 375, 780);
const stm = await snapStart();
const stacked = stm.steps.length === 3 && stm.steps[0].y < stm.steps[1].y && stm.steps[1].y < stm.steps[2].y;
ck('线上 375 三步单列排布', stacked, JSON.stringify(stm.steps.map((x) => [x.x, x.y])));
ck('线上 375 首屏无横向溢出', stm.overflowX <= 1, stm.overflowX);

await go('/en/');
const ste = await snapStart();
ck('线上 英文页首屏 CTA 已本地化', !!ste.primary?.text && !/[\u4e00-\u9fff]/.test(ste.primary.text), ste.primary?.text ?? '未找到');

// ── UX-6 / UX-1 关键回归（防新版覆盖旧交付） ────────────────────────────────
await go('/books/13-%E5%8F%B2%E8%AE%B0/');
const reg = await page.evaluate(() => {
  const h1 = document.querySelector('.book-header h1');
  return {
    h1: h1?.textContent?.trim() ?? null,
    tax: (document.querySelector('.tax-line')?.textContent || '').replace(/\s+/g, ' ').trim(),
    buHref: document.querySelector('.tax-bu')?.getAttribute('href') ?? null,
  };
});
const shiji = bySlug.get('13-史记');
const expTitle = shiji?.ws_title && shiji.ws_title !== shiji.seed_title ? shiji.ws_title : shiji?.seed_title;
ck('线上 UX-6 回归 h1=繁正名', reg.h1 === expTitle, `${reg.h1} vs ${expTitle}`);
ck('线上 UX-6 回归 分类路径含部', (reg.tax || '').includes(shiji?.bu || '史部'), reg.tax);
ck('线上 UX-6 回归 部级可点', reg.buHref === `/books?bu=${encodeURIComponent(shiji?.bu || '史部')}`, reg.buHref);

await go('/books/?bu=%E5%8F%B2%E9%83%A8');
const n = await page.evaluate(() => document.querySelectorAll('.book-card:not([hidden])').length);
ck('线上 UX-1 回归 史部结果数', n === works.filter((w) => w.bu === '史部').length, `${n} vs ${works.filter((w) => w.bu === '史部').length}`);

ck('线上 无 JS 运行错误', errs.length === 0, errs.join(' | ').slice(0, 200));

console.log('');
for (const r of out) console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.name}  ${r.ok ? '' : '<< ' + r.detail}`);
const pass = out.filter((r) => r.ok).length;
console.log(`\nUX-8 线上验收：${pass}/${out.length}`);

await browser.close();
edge.kill();
process.exit(pass === out.length ? 0 : 1);
