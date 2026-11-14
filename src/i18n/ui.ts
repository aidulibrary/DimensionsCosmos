import type { Locale } from './config';

/**
 * 壳层文案（导航、页脚、通用按钮、无障碍标签）。
 * 只放「每页都会出现」的字，页面正文各自放在 pages/*.ts，避免一个词典膨胀到不可维护。
 */
export interface UiDict {
  brand: string;
  brandSub: string;
  /** 品牌标语：用于分享卡 og:image:alt。各语言惯用写法，不做直译 */
  tagline: string;
  /** 页脚数据时间的时区注记 */
  utcNote: string;
  nav: { home: string; books: string; tasks: string; methods: string; pricing: string; cta: string };
  a11y: { themeToggle: string; themeToDark: string; themeToLight: string; langSwitch: string };
  footer: {
    motto: string;
    source: string;
    aiNotice: string;
    aiNoticeDetail: string;
    aiNoticeLink: string;
    slogan: string;
    about: string;
    terms: string;
    refund: string;
    privacy: string;
    updated: string;
  };
  common: { search: string; all: string; more: string; free: string; back: string };
}

export const ui: Record<Locale, UiDict> = {
  zh: {
    brand: '维点图书馆',
    brandSub: 'DimensionsCosmos',
    tagline: '古籍原文在线阅读',
    utcNote: '（UTC+8）',
    nav: { home: '首页', books: '书库', tasks: '任务中心', methods: '原文', pricing: '免费阅读', cta: '浏览书库' },
    a11y: { themeToggle: '切换夜间模式', themeToDark: '切换到夜间模式', themeToLight: '切换到日间模式', langSwitch: '切换语言' },
    footer: {
      motto: '浇灌自由生长的文明',
      source: '原文 © 中文维基文库（CC BY-SA 4.0）及其他开放来源',
      aiNotice: '底本与数据说明',
      aiNoticeDetail: '原文底本来源与整理说明详见',
      aiNoticeLink: '关于本站',
      slogan: '浇灌自由生长的文明',
      about: '关于',
      terms: '服务条款',
      refund: '退款说明',
      privacy: '隐私政策',
      updated: '数据更新',
    },
    common: { search: '检索', all: '全部', more: '种更多', free: '免费', back: '返回' },
  },

  'zh-TW': {
    brand: '維點圖書館',
    brandSub: 'DimensionsCosmos',
    tagline: '古籍原文線上閱讀',
    utcNote: '（UTC+8）',
    nav: { home: '首頁', books: '書庫', tasks: '任務中心', methods: '原文', pricing: '免費閱讀', cta: '瀏覽書庫' },
    a11y: { themeToggle: '切換夜間模式', themeToDark: '切換到夜間模式', themeToLight: '切換到日間模式', langSwitch: '切換語言' },
    footer: {
      motto: '澆灌自由生長的文明',
      source: '原文 © 中文維基文庫（CC BY-SA 4.0）及其他開放來源',
      aiNotice: '底本與資料說明',
      aiNoticeDetail: '原文底本來源與整理說明詳見',
      aiNoticeLink: '關於本站',
      slogan: '澆灌自由生長的文明',
      about: '關於',
      terms: '服務條款',
      refund: '退款說明',
      privacy: '隱私政策',
      updated: '資料更新',
    },
    common: { search: '檢索', all: '全部', more: '種更多', free: '免費', back: '返回' },
  },

  en: {
    brand: 'DimensionsCosmos Library',
    brandSub: '维点图书馆',
    tagline: 'Classical texts in the original',
    utcNote: '(UTC+8)',
    nav: { home: 'Home', books: 'Library', tasks: 'Tasks', methods: 'Texts', pricing: 'Free to read', cta: 'Browse the library' },
    a11y: { themeToggle: 'Toggle dark mode', themeToDark: 'Switch to dark mode', themeToLight: 'Switch to light mode', langSwitch: 'Change language' },
    footer: {
      motto: 'Watering a civilisation that grows freely',
      source: 'Source texts © Chinese Wikisource (CC BY-SA 4.0) and other open sources',
      aiNotice: 'Base text & data notice',
      aiNoticeDetail: 'Notes on base texts and how they were prepared: see',
      aiNoticeLink: 'About',
      slogan: 'Watering a civilisation that grows freely',
      about: 'About',
      terms: 'Terms',
      refund: 'Refunds',
      privacy: 'Privacy',
      updated: 'Data updated',
    },
    common: { search: 'Search', all: 'All', more: 'more methods', free: 'Free', back: 'Back' },
  },

  // B2：西班牙语。用国际通用西语（es-ES 拼写习惯），避免拉美/西班牙地区俚语，
  // 以便一次覆盖西班牙与拉美两大市场；专名（书名、人名、朝代）保留汉字原文。
  es: {
    brand: 'Biblioteca DimensionsCosmos',
    brandSub: '维点图书馆',
    tagline: 'Textos clásicos en su original',
    utcNote: '(UTC+8)',
    nav: { home: 'Inicio', books: 'Biblioteca', tasks: 'Tareas', methods: 'Textos', pricing: 'Lectura gratuita', cta: 'Ver la biblioteca' },
    a11y: {
      themeToggle: 'Cambiar el modo nocturno',
      themeToDark: 'Cambiar al modo nocturno',
      themeToLight: 'Cambiar al modo diurno',
      langSwitch: 'Cambiar de idioma',
    },
    footer: {
      motto: 'Regar una civilización que crece en libertad',
      source: 'Textos originales © Wikisource en chino (CC BY-SA 4.0) y otras fuentes abiertas',
      aiNotice: 'Aviso sobre textos y datos',
      aiNoticeDetail:
        'Notas sobre los textos de base y su preparación. Más información en',
      aiNoticeLink: 'Acerca de',
      slogan: 'Regar una civilización que crece en libertad',
      about: 'Acerca de',
      terms: 'Términos del servicio',
      refund: 'Reembolsos',
      privacy: 'Privacidad',
      updated: 'Datos actualizados',
    },
    common: { search: 'Buscar', all: 'Todos', more: 'métodos más', free: 'Gratis', back: 'Volver' },
  },
};
