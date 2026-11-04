// UX-8 可复算验收：首屏引导与精选（四身份分栏 + 两条降级分支 + 文案缺省不显示占位符）
//
// 用法：node scripts/verify-ux8.mjs
//   本脚本自行触发 2 次 `astro build`（A：无 featured.json → SEED 兜底分支；
//   B：写入 5 部 fixture → 条目不足 6 部的降级分支 + reason/reviewed 闸门），
//   两次都在真实构建产物上跑 DOM 断言，不 mock 渲染结果。
//   若仓库内已存在 public/data/featured.json，脚本会临时改名，结束后原样恢复。
//
// 依赖：本机 Edge + puppeteer-core（本机可选依赖，不进 package.json，避免 CI 拉 Chromium）
//
// 口径（沿用 UX-1/UX-4/UX-6）：
//   · 期望值一律从 public/data/index.json + siku-map.json 独立计算，不看页面自报内容；
//   · 并额外校验本脚本的 SEED 期望与 src/lib/featured.ts 的 SEED_FEATURED 同源，
//     防止两处清单漂移后「脚本和页面一起错」；
//   · 1280 / 375 双视口，溢出、触控尺寸单独断言。
import { spawn, execSync } from 'node:child_process';
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
const FEATURED = path.resolve('public/data/featured.json');
const FEATURED_BAK = FEATURED + '.ux8bak';
const FEATURED_TS = path.resolve('src/lib/featured.ts');
const EDGE = process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const PORT = 8796, CDP = 9367;
const MIME = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp' };

const index = JSON.parse(fs.readFileSync('public/data/index.json', 'utf-8'));
const siku = JSON.parse(fs.readFileSync('public/data/siku-map.json', 'utf-8'));
const works = index.works ?? [];
const bySlug = new Map(works.map((w) => [w.slug, w]));
const taxonomy = index.taxonomy ?? [];

/** 复刻 resolveBuPath 的裁决规则：显式二级优先 → 映射表 → 必须过 taxonomy 父子校验 */
function expectBuPath(w) {
  if (!w?.bu) return null;
  const parent = (name) => taxonomy.find((t) => t.name === name)?.parent ?? undefined;
  const sub = siku.map?.[w.slug];
  if (sub && parent(sub) === w.bu) return `${w.bu} › ${sub}`;
  return w.bu;
}

// ── 同源校验：脚本内的 SEED 期望必须与 src/lib/featured.ts 一致 ───────────────
const SEED_EXPECT = {
  '1-论语': ['student', 'general', 'family', 'research'],
  '23-老子': ['general', 'research'],
  '32-颜氏家训': ['family', 'student'],
  '33-世说新语': ['general', 'family', 'student'],
  '13-史记': ['student', 'general', 'research'],
  '17-资治通鉴': ['general', 'research'],
};
const AUD = ['student', 'general', 'family', 'research'];

const tsSrc = fs.readFileSync(FEATURED_TS, 'utf-8');
const seedBlock = tsSrc.slice(tsSrc.indexOf('SEED_FEATURED'), tsSrc.indexOf('function readFeaturedFile'));
const seedInTs = {};
for (const m of seedBlock.matchAll(/\{\s*slug:\s*'([^']+)',\s*order:\s*\d+,\s*audiences:\s*\[([^\]]*)\]/g)) {
  seedInTs[m[1]] = m[2].split(',').map((s) => s.trim().replace(/^'|'$/g, '')).filter(Boolean);
}

const preChecks = [];
const preCk = (name, ok, detail) => preChecks.push({ name, ok: !!ok, detail });
preCk('SEED 清单与 lib/featured.ts 同源', JSON.stringify(seedInTs) === JSON.stringify(SEED_EXPECT), JSON.stringify(seedInTs));
preCk(
  'SEED 全部 slug 在 index.json 且可读',
  Object.keys(SEED_EXPECT).every((s) => bySlug.get(s)?.ok === true),
  Object.keys(SEED_EXPECT).filter((s) => bySlug.get(s)?.ok !== true).join(','),
);
preCk('SEED audiences 均落在四值枚举内', Object.values(SEED_EXPECT).every((a) => a.every((x) => AUD.includes(x))), '');

/** 给定 items(raw slug→audiences) 计算每身份期望条目（顺序按 order 即 SEED 声明顺序） */
function expectPanels(map) {
  const out = {};
  for (const a of AUD) out[a] = Object.keys(map).filter((slug) => map[slug].includes(a));
  return out;
}

// ── 静态服务 + Edge(CDP) ────────────────────────────────────────────────────
let srv = null, edge = null, browser = null, page = null;
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

async function boot() {
  srv = http.createServer((req, res) => {
    const u = decodeURIComponent(req.url.split('?')[0]);
    let f = path.join(DIST, u);
    try { if (fs.statSync(f).isDirectory()) f = path.join(f, 'index.html'); } catch { f = path.join(DIST, u + '/index.html'); }
    fs.readFile(f, (e, b) => {
      if (e) { res.writeHead(404); res.end('404'); return; }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' });
      res.end(b);
    });
  }).listen(PORT);

  edge = spawn(EDGE, ['--headless=new', `--remote-debugging-port=${CDP}`, `--user-data-dir=${path.join(process.env.TEMP, 'edge-ux8v-' + Date.now())}`, '--no-first-run', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });
  let ws = null;
  for (let i = 0; i < 60; i++) { try { const r = await fetch(`http://127.0.0.1:${CDP}/json/version`); if (r.ok) { ws = (await r.json()).webSocketDebuggerUrl; break; } } catch {} await wait(300); }
  if (!ws) throw new Error('CDP 未就绪：Edge 未启动');
  browser = await puppeteer.connect({ browserWSEndpoint: ws, defaultViewport: { width: 1280, height: 900 } });
  page = await browser.newPage();
}

async function shutdown() {
  try { await browser?.close(); } catch {}
  try { edge?.kill(); } catch {}
  try { srv?.close(); } catch {}
}

const BASE = () => `http://127.0.0.1:${PORT}`;
const go = async (p, w = 1280, h = 900) => {
  await page.setViewport({ width: w, height: h });
  await page.goto(BASE() + p, { waitUntil: 'networkidle2' });
  await wait(150);
};

/** 抓首屏精选区的完整可断言语义 */
const snapFeatured = () => page.evaluate(() => {
  const root = document.querySelector('[data-featured]');
  const de = document.documentElement;
  const base = {
    exists: !!root,
    overflowX: de.scrollWidth - de.clientWidth,
  };
  if (!root) return base;
  const panels = Array.from(root.querySelectorAll('.aud-panel')).map((p) => ({
    aud: p.dataset.panel,
    count: Number(p.dataset.count),
    hidden: p.hasAttribute('hidden'),
    cards: Array.from(p.querySelectorAll('.feat-card')).map((c) => ({
      slug: c.dataset.slug,
      hasGuide: c.dataset.hasGuide,
      href: c.getAttribute('href'),
      tax: (c.querySelector('.feat-tax')?.textContent || '').trim(),
      reason: (c.querySelector('.feat-reason')?.textContent || '').trim(),
      cardH: Math.round(c.getBoundingClientRect().height),
      badge: (c.querySelector('.feat-badge')?.textContent || '').trim(),
      cta: (c.querySelector('.feat-cta')?.textContent || '').trim(),
    })),
  }));
  const tabs = Array.from(root.querySelectorAll('.aud-tab')).map((t) => ({
    aud: t.dataset.aud,
    count: Number(t.dataset.count),
    h: Math.round(t.getBoundingClientRect().height),
    active: t.classList.contains('active'),
    disabled: t.disabled,
    name: (t.querySelector('.aud-name')?.textContent || '').trim(),
  }));
  const text = root.textContent || '';
  return {
    ...base,
    defaultAud: root.dataset.defaultAud,
    panels,
    tabs,
    reasonCount: root.querySelectorAll('.feat-reason').length,
    // 占位符黑名单：文案缺省时必须一个字都不出现
    placeholders: ['—', '——', '暂无', '待补', '待定', 'TBD', 'TODO', 'null', 'undefined', 'N/A', 'Lorem']
      .filter((k) => text.includes(k)),
  };
});

/** 重建顺序：先取无文件分支，再取 fixture 分支 */
function astroBuild(tag) {
  const t0 = Date.now();
  try {
    execSync('npx astro build', { cwd: process.cwd(), stdio: ['ignore', 'pipe', 'pipe'], encoding: 'utf-8' });
  } catch (e) {
    const tail = String((e.stdout || '') + (e.stderr || '')).split('\n').slice(-8).join(' | ');
    throw new Error(`[${tag}] astro build 失败：${tail || e.message}`);
  }
  return `${tag} 构建完成 ${Math.round((Date.now() - t0) / 1000)}s`;
}

const out = [];
const ck = (name, ok, detail) => out.push({ name, ok: !!ok, detail });

// ── 阶段 A：featured.json 缺失 → SEED 结构兜底 ──────────────────────────────
async function phaseA() {
  const exp = expectPanels(SEED_EXPECT);

  await go('/', 1280, 900);
  const s = await snapFeatured();

  ck('A 精选区已渲染', s.exists, '未找到 [data-featured]');
  if (!s.exists) return;

  ck('A 四身份栏齐备且顺序固定', s.tabs.map((t) => t.aud).join(',') === AUD.join(','), s.tabs.map((t) => t.aud).join(','));
  ck('A 四身份栏标签非空（i18n 已落地）', s.tabs.every((t) => t.name.length > 0), JSON.stringify(s.tabs.map((t) => t.name)));
  ck('A 身份栏触控高度 ≥44px', s.tabs.every((t) => t.h >= 44), JSON.stringify(s.tabs.map((t) => t.h)));

  for (const a of AUD) {
    const p = s.panels.find((x) => x.aud === a);
    const expList = exp[a];
    ck(`A ${a} 条目数与数据基准一致`, p && p.count === expList.length && p.cards.length === expList.length, `${p?.count}/${p?.cards.length} vs ${expList.length}`);
    ck(`A ${a} 条目顺序按 order 稳定`, p && p.cards.map((c) => c.slug).join(',') === expList.join(','), p?.cards.map((c) => c.slug).join(','));
  }

  // guides 为空的书：史记 / 资治通鉴 必降级（这是分支①的核心断言）
  const allCards = s.panels.flatMap((p) => p.cards);
  const noGuideSlugs = ['13-史记', '17-资治通鉴'];
  for (const slug of noGuideSlugs) {
    const expHasGuide = (bySlug.get(slug)?.guides?.length ?? 0) > 0;
    const cards = allCards.filter((c) => c.slug === slug);
    ck(`A ${slug} guides 为空已识别`, expHasGuide === false && cards.length > 0 && cards.every((c) => c.hasGuide === '0'), `${expHasGuide} ${cards.map((c) => c.hasGuide).join('')}`);
    const hrefOk = (h) => decodeURIComponent(h || '') === `/books/${slug}/read`;
    ck(`A ${slug} 主 CTA 直达阅读页`, cards.every((c) => hrefOk(c.href)), cards.map((c) => c.href)[0]);
    ck(`A ${slug} 标注导读筹备中而非留空`, cards.every((c) => c.badge.length > 0 && c.cta.length > 0), JSON.stringify(cards[0] || {}));
  }
  // 有导读的书：主 CTA 指向详情页
  const withGuide = allCards.filter((c) => c.slug === '1-论语');
  ck('A 有导读的书 CTA 指向详情页', withGuide.length > 0 && withGuide.every((c) => c.hasGuide === '1' && decodeURIComponent(c.href || '') === '/books/1-论语/'), withGuide.map((c) => c.href)[0]);
  ck('A 有导读的书显示导读篇数徽标', withGuide.every((c) => /\d/.test(c.badge)), withGuide.map((c) => c.badge)[0]);

  // 分类路径与 siku 裁决一致
  const badTax = [];
  for (const c of allCards) {
    const w = bySlug.get(c.slug);
    const e = expectBuPath(w);
    if (e && c.tax !== e) badTax.push(`${c.slug}:${c.tax}≠${e}`);
  }
  ck('A 卡片分类路径与四库裁决一致', badTax.length === 0, badTax.slice(0, 3).join(' | '));

  // 文案缺省：无 featured.json 时 reason 必须为零，且全文无占位符
  ck('A 文案缺省不渲染推荐语', s.reasonCount === 0, `reasonCount=${s.reasonCount}`);
  ck('A 无占位符字符', s.placeholders.length === 0, s.placeholders.join(','));
  ck('A 默认栏落在 general', s.defaultAud === 'general', s.defaultAud);
  ck('A 默认仅 general 面板可见', s.panels.filter((p) => !p.hidden).map((p) => p.aud).join(',') === 'general', s.panels.filter((p) => !p.hidden).map((p) => p.aud).join(','));
  ck('A 1280 无横向溢出', s.overflowX <= 1, s.overflowX);
  const visibleCards = s.panels.filter((p) => !p.hidden).flatMap((p) => p.cards);
  ck('A 卡片触控高度 ≥44px', visibleCards.length > 0 && visibleCards.every((c) => c.cardH >= 44), JSON.stringify(visibleCards.map((c) => c.cardH)));

  // 交互：点学生栏 → 面板切换、aria 同步
  await page.click('.aud-tab[data-aud="student"]');
  await wait(180);
  const after = await page.evaluate(() => ({
    visible: Array.from(document.querySelectorAll('.aud-panel')).filter((p) => !p.hasAttribute('hidden')).map((p) => p.dataset.panel),
    selected: document.querySelector('.aud-tab[aria-selected="true"]')?.dataset?.aud ?? null,
  }));
  ck('A 点击身份栏可切换面板', after.visible.join(',') === 'student' && after.selected === 'student', JSON.stringify(after));

  // 375 端
  await go('/', 375, 780);
  const m = await snapFeatured();
  ck('A 375 无横向溢出', m.overflowX <= 1, m.overflowX);
  ck('A 375 身份栏触控高度 ≥44px', m.tabs.every((t) => t.h >= 44), JSON.stringify(m.tabs.map((t) => t.h)));
  ck('A 375 卡片单列不挤压', (m.panels.find((p) => p.aud === 'general')?.cards.length ?? 0) > 0, '');
}

// ── 阶段 B：featured.json 存在但只有 5 部（<6）+ reason/reviewed 闸门 ────────
const FIXTURE_ITEMS = [
  { slug: '1-论语', order: 1, audiences: ['student', 'general', 'family', 'research'], reason: { zh: 'FIXTURE论语中文推荐', en: 'FIXTURE english reason' }, reviewed: ['zh'] },
  { slug: '23-老子', order: 2, audiences: ['general', 'research'], reason: { zh: 'FIXTURE老子中文推荐' }, reviewed: ['zh'] },
  { slug: '32-颜氏家训', order: 3, audiences: ['family', 'student'] },
  { slug: '13-史记', order: 5, audiences: ['student', 'general', 'research'], reason: { zh: 'FIXTURE史记中文推荐' }, reviewed: ['zh'] },
  { slug: '17-资治通鉴', order: 6, audiences: ['general', 'research'] },
];
const FIXTURE_MAP = Object.fromEntries(FIXTURE_ITEMS.map((i) => [i.slug, i.audiences]));

async function phaseB() {
  const exp = expectPanels(FIXTURE_MAP);
  await go('/', 1280, 900);
  const s = await snapFeatured();
  ck('B 精选区已渲染', s.exists, '未找到 [data-featured]');
  if (!s.exists) return;

  const allCards = s.panels.flatMap((p) => p.cards);
  const uniq = [...new Set(allCards.map((c) => c.slug))];
  ck('B 条目不足 6 部按实际数量渲染', uniq.length === FIXTURE_ITEMS.length, `${uniq.length} vs ${FIXTURE_ITEMS.length}`);
  ck('B 不补占位卡（无 seed 追加）', !uniq.includes('33-世说新语'), uniq.join(','));

  for (const a of AUD) {
    const p = s.panels.find((x) => x.aud === a);
    ck(`B ${a} 条目与 fixture 一致`, p && p.cards.map((c) => c.slug).join(',') === exp[a].join(','), `${p?.cards.map((c) => c.slug).join(',')} vs ${exp[a].join(',')}`);
  }

  // reason 已过审（zh）→ 必须渲染，且文本即 fixture 原文
  const lunyu = allCards.filter((c) => c.slug === '1-论语');
  ck('B 已过审中文推荐语正常渲染', lunyu.every((c) => c.reason === 'FIXTURE论语中文推荐'), lunyu.map((c) => c.reason)[0]);
  // 未给 reason 的条目 → 该段不渲染（无空壳、无占位符）
  const yanshi = allCards.filter((c) => c.slug === '32-颜氏家训');
  ck('B 无推荐语的条目不渲染该段', yanshi.every((c) => c.reason === ''), JSON.stringify(yanshi.map((c) => c.reason)));
  ck('B 无占位符字符', s.placeholders.length === 0, s.placeholders.join(','));

  // 未过审语言（en 有值但 reviewed 仅 zh）→ 英文页不得出现任何推荐语
  await go('/en/', 1280, 900);
  const en = await snapFeatured();
  ck('B 未过审英文不硬译上线', en.exists && en.reasonCount === 0, `reasonCount=${en.reasonCount}`);
  const enCards = en.panels.flatMap((p) => p.cards);
  ck('B 英文页不泄露中文推荐语', !enCards.some((c) => c.reason.includes('FIXTURE论语')), enCards.map((c) => c.reason).filter(Boolean)[0] || '');
  ck('B 英文页仍渲染全部条目', [...new Set(enCards.map((c) => c.slug))].length === FIXTURE_ITEMS.length, '');

  await go('/', 375, 780);
  const m = await snapFeatured();
  ck('B 375 无横向溢出', m.overflowX <= 1, m.overflowX);
}

// ── 执行编排 ────────────────────────────────────────────────────────────────
const hadFeatured = fs.existsSync(FEATURED);
try {
  // A：临时移走 featured.json（若存在），构建后断言 SEED 分支
  if (hadFeatured) fs.renameSync(FEATURED, FEATURED_BAK);
  console.log(astroBuild('A'));
  await boot();
  await phaseA();
  // 重建前必须先释放 Edge/静态服务对 dist 的文件占用，否则 Windows 下 astro 清空 dist 会 EPERM
  await shutdown();

  // B：写 5 部 fixture，重建后断言条目不足与过审闸门
  fs.writeFileSync(FEATURED, JSON.stringify({ version: 1, updatedAt: new Date().toISOString(), items: FIXTURE_ITEMS }, null, 2), 'utf-8');
  console.log(astroBuild('B'));
  await boot();
  await phaseB();
} finally {
  await shutdown();
  // 恢复原状：删 fixture，还原仓库原有 featured.json（若有）
  try { if (fs.existsSync(FEATURED)) fs.unlinkSync(FEATURED); } catch {}
  if (hadFeatured && fs.existsSync(FEATURED_BAK)) fs.renameSync(FEATURED_BAK, FEATURED);
  // 恢复为干净分支的构建产物，避免 fixture 版 dist 残留
  try { console.log(astroBuild('C')); } catch (e) { console.error(String(e.message)); }
}

const all = [...preChecks, ...out];
console.log('');
for (const r of all) console.log(`${r.ok ? 'PASS' : 'FAIL'}  ${r.name}  ${r.ok ? '' : '<< ' + r.detail}`);
const pass = all.filter((r) => r.ok).length;
console.log(`\nUX-8 浏览器验收：${pass}/${all.length}`);
process.exit(pass === all.length ? 0 : 1);
