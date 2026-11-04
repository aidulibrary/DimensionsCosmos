/**
 * 首屏引导与精选（UX-8）。
 *
 * 数据契约由数据侧定（marvis #9 方案 a）：`public/data/featured.json`
 *   { version, updatedAt, items: [{ slug, order, audiences[], reason{zh,zh-TW,en,es}, reviewed[] }] }
 *
 * 本模块只做三件事：读取、校验、降级。渲染在 components/FeaturedGuide.astro。
 *
 * 三条硬约束：
 *   1. **文案缺省即不显示**。reason 某语言没有值就不渲染该段，绝不写「—」「暂无」「待补」
 *      之类占位符——占位符进生产页面等于向读者宣告「这里本该有东西」，比留白更糟。
 *   2. **未过审不硬译**。zh-TW / en / es 的 reason 只有在 item.reviewed 明确列入该语言时
 *      才上线；否则一律不渲染。reviewed 缺省时仅放行 zh（中文由数据侧与作者共同校对）。
 *      这条不是流程洁癖：机器硬译的导读推荐语出现在四语站点上，是对读者的误导。
 *   3. **缺失不空白**。featured.json 不存在、或校验后条目为空时，退回 SEED_FEATURED
 *      （只有 slug/order/audiences 的结构兜底，零文案），保证首屏引导线上始终可用。
 *      条目少于 6 部时不补占位卡、不报错、不显示「应有 6 部」的计数——有多少显示多少。
 *
 * 注意：本文件不含任何面向读者的文案，文案全部走 i18n/pages/home.ts 的 featured 段。
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

/** 读者身份，四值枚举固定，禁止同义词（student/general/family/research） */
export type Audience = 'student' | 'general' | 'family' | 'research';
export const AUDIENCES: readonly Audience[] = ['student', 'general', 'family', 'research'] as const;

/** 精选目标部数（数据侧口径）；仅用于文档与数据侧核对，不用于页面计数展示 */
export const FEATURED_TARGET = 6;

export interface FeaturedReason {
  zh?: string;
  'zh-TW'?: string;
  en?: string;
  es?: string;
}

interface FeaturedItemRaw {
  slug?: unknown;
  order?: unknown;
  audiences?: unknown;
  reason?: unknown;
  reviewed?: unknown;
}

interface FeaturedFileRaw {
  version?: unknown;
  updatedAt?: unknown;
  items?: unknown;
}

/** 归一化后的精选条目：结构字段走数据，书名/著者等展示字段从 index.json 取，保证同源 */
export interface FeaturedItem {
  slug: string;
  order: number;
  audiences: Audience[];
  /** 原始 reason 对象，是否上线由 pickReason 按 reviewed 裁决 */
  reason: FeaturedReason;
  reviewed: string[];
  title: string;
  /** 繁体正名（与 seed_title 相同则为空串），用于 lang=zh-Hant 标注 */
  wsTitle: string;
  author: string;
  dynasty: string;
  bu: string;
  /** 导读篇数；0 表示该书尚无导读，属 guides 为空的降级态 */
  guides: number;
  readable: boolean;
  hasGuide: boolean;
}

/** index.json works 的最小投影，避免本模块依赖完整 IndexData */
export interface FeaturedWorkRef {
  slug: string;
  seed_title?: string;
  ws_title?: string;
  author?: string;
  dynasty?: string;
  bu?: string;
  ok?: boolean;
  readable?: boolean;
  guides?: unknown[];
}

/**
 * 结构兜底清单：数据侧供数前的可用形态。
 * 只含 slug / order / audiences 三项，**不含任何 reason 文案**——文案缺失即不显示，
 * 这正是「缺省不显示占位符」的直接体现。6 部取自 marvis #9 方案 a：
 *   1-论语、23-老子、32-颜氏家训、33-世说新语、13-史记、17-资治通鉴
 * audiences 为按书性给出的初始分配，数据侧 featured.json 一到即整体替换本表。
 */
export const SEED_FEATURED: readonly { slug: string; order: number; audiences: Audience[] }[] = [
  { slug: '1-论语', order: 1, audiences: ['student', 'general', 'family', 'research'] },
  { slug: '23-老子', order: 2, audiences: ['general', 'research'] },
  { slug: '32-颜氏家训', order: 3, audiences: ['family', 'student'] },
  { slug: '33-世说新语', order: 4, audiences: ['general', 'family', 'student'] },
  { slug: '13-史记', order: 5, audiences: ['student', 'general', 'research'] },
  { slug: '17-资治通鉴', order: 6, audiences: ['general', 'research'] },
];

function readFeaturedFile(): FeaturedFileRaw | null {
  try {
    const raw = readFileSync(join(process.cwd(), 'public', 'data', 'featured.json'), 'utf-8');
    const parsed = JSON.parse(raw) as FeaturedFileRaw;
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch {
    // 文件不存在 / 非法 JSON / 读取失败：一律走 SEED 兜底，不阻断构建
    return null;
  }
}

function asAudiences(v: unknown): Audience[] {
  if (!Array.isArray(v)) return [];
  const out: Audience[] = [];
  for (const x of v) {
    const s = String(x ?? '').trim() as Audience;
    // 只接受四值枚举，同义词一律丢弃（宁缺不错，避免出现第五个隐形身份栏）
    if (AUDIENCES.includes(s) && !out.includes(s)) out.push(s);
  }
  return out;
}

function asReason(v: unknown): FeaturedReason {
  if (!v || typeof v !== 'object') return {};
  const src = v as Record<string, unknown>;
  const out: FeaturedReason = {};
  for (const k of ['zh', 'zh-TW', 'en', 'es'] as const) {
    const val = src[k];
    if (typeof val === 'string' && val.trim()) out[k] = val.trim();
  }
  return out;
}

function asStringArray(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.map((x) => String(x ?? '').trim()).filter(Boolean);
}

interface RawItem {
  slug: string;
  order: number;
  audiences: Audience[];
  reason: FeaturedReason;
  reviewed: string[];
}

/** 把任意来源（featured.json 或 SEED）压成统一的 raw item 列表 */
function collectRaw(file: FeaturedFileRaw | null): RawItem[] {
  const items = file && Array.isArray(file.items) ? (file.items as FeaturedItemRaw[]) : [];
  const list: RawItem[] = [];
  for (const it of items) {
    const slug = typeof it?.slug === 'string' ? it.slug.trim() : '';
    if (!slug) continue;
    list.push({
      slug,
      order: Number.isFinite(Number(it.order)) ? Number(it.order) : 999,
      audiences: asAudiences(it.audiences),
      reason: asReason(it.reason),
      reviewed: asStringArray(it.reviewed),
    });
  }
  if (list.length) return list;
  // 文件缺失 / items 为空 / 全部不合法 → 结构兜底（零文案）
  return SEED_FEATURED.map((s) => ({
    slug: s.slug,
    order: s.order,
    audiences: [...s.audiences],
    reason: {} as FeaturedReason,
    reviewed: [] as string[],
  }));
}

/**
 * 归一化精选清单。
 * - slug 必须存在于 index.json 且 ok=true（不把不可读书塞进首屏）
 * - audiences 必须非空，否则该条目不会出现在任何身份栏里，等于无效条目，直接剔除
 * - 按 order 升序，order 相同按 slug 数字序，保证多次构建顺序稳定（避免 diff 抖动）
 */
export function normalizeFeatured(
  works: readonly FeaturedWorkRef[],
  file: FeaturedFileRaw | null = readFeaturedFile(),
): FeaturedItem[] {
  const bySlug = new Map<string, FeaturedWorkRef>();
  for (const w of works) bySlug.set(w.slug, w);

  const raw = collectRaw(file);
  const out: FeaturedItem[] = [];
  const seen = new Set<string>();

  for (const it of raw) {
    if (seen.has(it.slug)) continue;
    const w = bySlug.get(it.slug);
    if (!w || w.ok === false) continue;
    if (!it.audiences.length) continue;
    seen.add(it.slug);

    const seedTitle = (w.seed_title ?? it.slug).trim();
    const wsTitle = (w.ws_title ?? '').trim();
    const guides = Array.isArray(w.guides) ? w.guides.length : 0;

    out.push({
      slug: it.slug,
      order: it.order,
      audiences: it.audiences,
      reason: it.reason,
      reviewed: it.reviewed,
      title: wsTitle && wsTitle !== seedTitle ? wsTitle : seedTitle,
      wsTitle: wsTitle && wsTitle !== seedTitle ? wsTitle : '',
      author: (w.author ?? '').trim(),
      dynasty: (w.dynasty ?? '').trim(),
      bu: (w.bu ?? '').trim(),
      guides,
      readable: w.readable !== false,
      hasGuide: guides > 0,
    });
  }

  out.sort((a, b) => a.order - b.order || a.slug.localeCompare(b.slug, 'zh-Hans-CN'));
  return out;
}

/**
 * 取某语言的推荐语。
 * - reviewed 非空：只有列入白名单的语言放行（人工过审闸门）
 * - reviewed 为空：仅放行 zh（中文由数据侧与作者共同校对，其余语言需显式过审）
 * - 无值返回空串，调用方据此**不渲染**该段，不用占位符顶替
 */
export function pickReason(item: FeaturedItem, lang: string): string {
  const gate = item.reviewed.length ? item.reviewed : ['zh'];
  if (!gate.includes(lang)) return '';
  return item.reason[lang as keyof FeaturedReason] ?? '';
}

/** 按身份取条目，保持全局 order 序 */
export function itemsOf(items: readonly FeaturedItem[], audience: Audience): FeaturedItem[] {
  return items.filter((it) => it.audiences.includes(audience));
}

/** 是否存在至少一个非空身份栏；首页据此决定整块是否渲染 */
export function hasAnyItem(items: readonly FeaturedItem[]): boolean {
  return AUDIENCES.some((a) => itemsOf(items, a).length > 0);
}
