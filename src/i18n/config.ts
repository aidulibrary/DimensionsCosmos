/**
 * 多语言配置（B1：先启用 zh / zh-TW / en）
 *
 * 设计原则（国际通行做法）：
 * 1. 默认语言不带前缀（/books），其他语言带前缀（/en/books、/zh-TW/books）
 *    —— 保住既有中文链接、商店 start_url 与已收录的 SEO 权重，不让老链接 301 抖动。
 * 2. html lang 用 BCP 47 规范值：zh-Hant 而非 zh-TW（台湾仅作地区标记，语言本质是繁体中文）
 *    —— 这是 W3C / Google hreflang 的通行口径。
 * 3. dir 字段预留：ar（阿拉伯语）、he、fa 在 B4 阶段接 RTL，届时只加 dir='rtl' 即可。
 */

export type Locale = 'zh' | 'zh-TW' | 'en' | 'es';

export interface LocaleMeta {
  /** URL 前缀，默认语言为空串 */
  prefix: string;
  /** <html lang> 的 BCP 47 值 */
  htmlLang: string;
  /** og:locale 值 */
  ogLocale: string;
  /** 语言切换器上的显示名（用本语言自称，而非英文转写） */
  label: string;
  /** Intl 日期格式用的 locale */
  dateLocale: string;
  dir: 'ltr' | 'rtl';
}

export const DEFAULT_LOCALE: Locale = 'zh';

export const LOCALES: Record<Locale, LocaleMeta> = {
  zh: { prefix: '', htmlLang: 'zh-Hans', ogLocale: 'zh_CN', label: '简体中文', dateLocale: 'zh-CN', dir: 'ltr' },
  'zh-TW': { prefix: '/zh-TW', htmlLang: 'zh-Hant', ogLocale: 'zh_TW', label: '繁體中文', dateLocale: 'zh-TW', dir: 'ltr' },
  en: { prefix: '/en', htmlLang: 'en', ogLocale: 'en_US', label: 'English', dateLocale: 'en-US', dir: 'ltr' },
  es: { prefix: '/es', htmlLang: 'es', ogLocale: 'es_ES', label: 'Español', dateLocale: 'es-ES', dir: 'ltr' },
};

/** 已上线的语言（顺序即切换器顺序） */
export const ACTIVE_LOCALES: Locale[] = ['zh', 'zh-TW', 'en', 'es'];

/** 给站内路径加上语言前缀：localePath('en', '/pricing') → '/en/pricing' */
export function localePath(locale: Locale, path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${LOCALES[locale].prefix}${p === '/' ? '/' : p}`;
}

/**
 * 该语言是否已存在这一页的真实译文。
 * 未翻译的页面在非中文环境下仍指向中文页（不带前缀），
 * 避免出现「英文站里点书库 404」——宁可语言混杂，也不能断链。
 */
export const TRANSLATED_PAGES: Record<Locale, string[]> = {
  zh: ['*'],
  // B1 已上线：首页。其余页在 B2 逐页补齐（补一页就往这里加一条，切换器自动生效）
  'zh-TW': ['/'],
  en: ['/'],
  es: ['/'],
};

/** 解析某语言下某个路径的最终 href */
export function href(locale: Locale, path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`;
  const list = TRANSLATED_PAGES[locale];
  const hit = list.includes('*') || list.includes(p);
  if (!hit) return p; // 回落到中文原文页
  return localePath(locale, p);
}
