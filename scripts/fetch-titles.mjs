/**
 * fetch-titles.mjs —— 为「章名只剩卷号」的章节回填篇名（一次性数据管道）
 *
 * 问题：部分书籍章节标题形如「史記/卷001」，缺篇名（应为「五帝本紀第一」），
 *       目录与阅读页只能显示卷号，读者无法判断本卷内容。
 *
 * 方案：底本为维基文库（zh.wikisource.org）。每卷 wikitext 的 header2 模板带
 *       `| section = 卷一 五帝本紀第一` 字段，正是该卷篇名，属原文题名，非编者自拟。
 *       以章节 title 作为维基文库页面名逐卷抓取，抽取 section 值，写 data/titles.json。
 *
 * 特性：断点续抓（已抓到的页面不重复请求）、失败重试 + 指数退避、限速、可反复重跑。
 * 仅生成数据，不改动 public/data；注入由 scripts/gen-data.mjs 在构建期完成。
 *
 * 用法：node scripts/fetch-titles.mjs [--limit N] [--book 13,17] [--verbose]
 */

import fs from 'node:fs';
import path from 'node:path';

const ROOT = process.cwd();
const DATA_DIR = path.join(ROOT, 'public', 'data');
const OUT = path.join(ROOT, 'data', 'titles.json');
const API = 'https://zh.wikisource.org/w/api.php';
const UA = 'DimensionsCosmos/1.0 (title backfill; contact wuguz@outlook.com)';

const args = process.argv.slice(2);
const limitArg = args.includes('--limit') ? Number(args[args.indexOf('--limit') + 1]) : 0;
const bookArg = args.includes('--book') ? args[args.indexOf('--book') + 1].split(',').map(Number) : null;
const verbose = args.includes('--verbose');

/** 标题形如「史記/卷001」——去掉书名与卷号后无实质篇名 */
const BARE = /^[^/]+\/(?:卷)?[0-9〇零一二三四五六七八九十百]+$/;

function collectTargets() {
  const files = fs.readdirSync(DATA_DIR).filter((f) => /^book-\d+\.json$/.test(f));
  const targets = new Map(); // page title -> 章节元信息
  for (const f of files) {
    const book = JSON.parse(fs.readFileSync(path.join(DATA_DIR, f), 'utf8'));
    if (bookArg && !bookArg.includes(book.id)) continue;
    for (const c of book.chapters ?? []) {
      const t = (c.title ?? '').trim();
      if (!BARE.test(t)) continue;
      if (!targets.has(t)) targets.set(t, { bookId: book.id, bookTitle: book.seed_title, chapterId: c.id, rawTitle: t });
    }
  }
  return targets;
}

function loadDone() {
  if (!fs.existsSync(OUT)) return { meta: {}, items: {} };
  try {
    return JSON.parse(fs.readFileSync(OUT, 'utf8'));
  } catch {
    return { meta: {}, items: {} };
  }
}

function save(store) {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(store, null, 1), 'utf8');
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function apiOnce(params) {
  const url = `${API}?${new URLSearchParams(params)}`;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 25000);
  try {
    const res = await fetch(url, { headers: { 'User-Agent': UA }, signal: ctrl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

async function api(params, tries = 5) {
  let last;
  for (let i = 0; i < tries; i++) {
    try {
      return await apiOnce(params);
    } catch (e) {
      last = e;
      const wait = 1200 * Math.pow(2, i);
      if (verbose) console.warn(`  重试 ${i + 1}/${tries}（${e.message}），等待 ${wait}ms`);
      await sleep(wait);
    }
  }
  throw last;
}

/** 从 header2/wikitext 中提取 section 字段 */
function extractSection(text) {
  const m = text.match(/\|\s*section\s*=\s*([^\n|}]+)/);
  if (!m) return null;
  const v = m[1]
    .replace(/\[\[([^\]|]*\|)?([^\]]*)\]\]/g, '$2')
    .replace(/'''?/g, '')
    .replace(/\{\{[^}]*\}\}/g, '')
    .trim();
  return v || null;
}

/** section 形如「卷一 五帝本紀第一」→ 篇名「五帝本紀第一」 */
function sectionToTitle(section) {
  const s = section.trim();
  const m = s.match(/^(?:卷|第)?\s*[0-9〇零一二三四五六七八九十百千]+\s*[卷回]?\s*(.+)$/);
  const candidate = m ? m[1].trim() : s;
  return candidate || s;
}

async function fetchBatch(pages) {
  const data = await api({
    action: 'query',
    prop: 'revisions',
    rvprop: 'content',
    rvslots: 'main',
    titles: pages.join('|'),
    format: 'json',
    formatversion: '2',
    redirects: '1',
  });
  const out = new Map();
  for (const pg of data?.query?.pages ?? []) {
    const title = pg.title;
    if (pg.missing) {
      out.set(title, { error: 'missing' });
      continue;
    }
    const text = pg.revisions?.[0]?.slots?.main?.content ?? '';
    const section = extractSection(text);
    out.set(title, section ? { section, title: sectionToTitle(section) } : { error: 'no-section' });
  }
  return out;
}

const BATCH = 40;

async function main() {
  const targets = collectTargets();
  const store = loadDone();
  store.items = store.items ?? {};
  const todo = [...targets.keys()].filter((t) => !store.items[t]);
  console.log(`[titles] 待回填页面 ${targets.size} 个，已完成 ${targets.size - todo.length}，本次处理 ${limitArg ? Math.min(limitArg, todo.length) : todo.length}`);

  let ok = 0;
  let fail = 0;
  let round = 0;
  const queue = limitArg ? todo.slice(0, limitArg) : todo;

  for (let i = 0; i < queue.length; i += BATCH) {
    const batch = queue.slice(i, i + BATCH);
    round++;
    try {
      const res = await fetchBatch(batch);
      for (const page of batch) {
        const r = res.get(page) ?? { error: 'absent' };
        store.items[page] = { ...r, ...targets.get(page), fetchedAt: new Date().toISOString() };
        if (r.title) ok++;
        else fail++;
      }
      save(store);
      console.log(`  批次 ${round}：${batch.length} 页，累计成功 ${ok} / 失败 ${fail}`);
    } catch (e) {
      console.error(`  批次 ${round} 失败：${e.message}`);
      fail += batch.length;
    }
    if (i + BATCH < queue.length) await sleep(800);
  }

  store.meta = {
    source: 'zh.wikisource.org header2 | section',
    updatedAt: new Date().toISOString(),
    totalTargets: targets.size,
    resolved: Object.values(store.items).filter((v) => v.title).length,
    failed: Object.values(store.items).filter((v) => !v.title).length,
  };
  save(store);
  console.log(`[titles] 完成：解析成功 ${store.meta.resolved} / 失败 ${store.meta.failed}，输出 ${path.relative(ROOT, OUT)}`);
}

main().catch((e) => {
  console.error('[titles] 中止：', e.message);
  process.exitCode = 1;
});
