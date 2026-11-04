/**
 * 四部分类路径（UX-6）。
 *
 * 背景：`bu` 只有部（经/史/子/集）一级，原页面把它当一个标签渲染，等于有分类法之名而无层级之实。
 * 本模块把「部 → 类」拼成通行分类路径（如 经部 › 四书类），用于详情页著录区。
 *
 * 二级来源优先级：
 *   1. book.bu_sub（数据侧将来并入 index.json 的字段，权威）
 *   2. public/data/siku-map.json（本机构建的过渡映射，四库总目通行归类）
 * 无论来自哪里，都必须过 taxonomy 父子校验：类目的 parent 不等于当前部时一律丢弃，
 * 避免出现「集部 › 小说家类」这种体系错乱，宁可只显示一级。
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

export interface TaxonomyNode {
  name: string;
  parent: string | null;
}

interface SikuMapFile {
  map?: Record<string, string>;
  pending?: Record<string, string>;
}

let cache: SikuMapFile | null = null;

function loadSikuMap(): SikuMapFile {
  if (cache) return cache;
  try {
    const raw = readFileSync(join(process.cwd(), 'public', 'data', 'siku-map.json'), 'utf-8');
    cache = JSON.parse(raw) as SikuMapFile;
  } catch {
    // 映射文件缺失不应阻断构建：退化为只显示部级
    cache = { map: {}, pending: {} };
  }
  return cache;
}

export interface BuPath {
  bu: string | null;
  sub: string | null;
}

/**
 * 解析一本书的四部分类路径。
 * @param bu       部（经部/史部/子部/集部）
 * @param slug     书 slug，用于查过渡映射
 * @param taxonomy index.json 自带的四库类目父子表
 * @param explicitSub 数据侧显式给出的二级类目（优先）
 */
export function resolveBuPath(
  bu: string | null | undefined,
  slug: string | null | undefined,
  taxonomy: TaxonomyNode[] | null | undefined,
  explicitSub?: string | null,
): BuPath {
  const buName = (bu ?? '').trim();
  if (!buName) return { bu: null, sub: null };

  const parentOf = new Map<string, string | null>();
  for (const t of taxonomy ?? []) parentOf.set(t.name, t.parent);

  const candidates = [explicitSub, slug ? loadSikuMap().map?.[slug] : null];
  for (const c of candidates) {
    const name = (c ?? '').trim();
    if (!name) continue;
    // 父类必须是当前部；taxonomy 里查不到也视为不可信
    if (parentOf.get(name) === buName) return { bu: buName, sub: name };
  }
  return { bu: buName, sub: null };
}

/** 分类路径的纯文本形式，供 title/aria/JSON 使用 */
export function buPathText(p: BuPath): string {
  return [p.bu, p.sub].filter(Boolean).join(' › ');
}

/** 该书二级类目待复核原因（映射文件里有登记时返回，用于页脚说明） */
export function sikuPendingReason(slug: string | null | undefined): string | null {
  if (!slug) return null;
  return loadSikuMap().pending?.[slug] ?? null;
}
