import type { Locale } from '../config';

/**
 * 方法库页（/methods）界面词。
 * 注意：method 的 era / summary / tags 来自数据层（中文原典语汇），本节不译，
 * 非中文环境下列表仍显示中文摘要，页面底部会加一行说明，避免读者误以为整页已英化。
 */
export interface MethodsDict {
  title: string;
  heading: (n: number) => string;
  sub: string;
  freeHeading: string;
  freeDesc: string;
  paidHeading: string;
  paidDesc: string;
  priceFree: string;
  pricePaid: (p: number) => string;
  pricePromo: string;
  cta: string;
  ctaPlain: string;
  comingHeading: string;
  coming: { name: string; meta: string; desc: string }[];
  /** 卡片主名是否优先用英文名（en/es 为 true） */
  preferEnName: boolean;
  /** 非中文环境下的数据语言说明；中文环境为 null 不渲染 */
  dataNote: string | null;
}

export const methodsDict: Record<Locale, MethodsDict> = {
  zh: {
    title: '大师视角 · 阅读方法库 · 维点图书馆',
    heading: (n) => `${n} 种大师视角`,
    sub: '每位大师的阅读方法都是一个独立的 AI 插件——可以应用到任意文明的任意文本',
    freeHeading: '🆓 免费体验',
    freeDesc: '每本书都附赠朱熹视角——这是我们给所有读者的见面礼。',
    paidHeading: '🔐 付费解锁',
    paidDesc: '单次购买、永久可读。所有方法都支持 Markdown/JSON 导出。',
    priceFree: '免费 · 永久',
    pricePaid: (p) => `¥${p} / 篇`,
    pricePromo: '限时免费',
    cta: '去解锁 →',
    ctaPlain: '查看说明 →',
    comingHeading: '🚧 即将上线的方法',
    coming: [
      { name: '培根归纳法', meta: 'Francis Bacon · 17世纪英国', desc: '从具体观察到普遍原则' },
      { name: '布鲁姆分类学', meta: "Bloom's Taxonomy · 20世纪美国", desc: '记忆→理解→应用→分析→评价→创造' },
      { name: '普鲁斯特阅读法', meta: 'Proust · 20世纪法国', desc: '阅读是自我发现的触发剂' },
      { name: '顾炎武考据法', meta: '明末清初 · 中国', desc: '一字一句皆有出处' },
      { name: '西蒙东技术哲学透镜', meta: 'Simondon · 20世纪法国', desc: '透过技术演化看一切' },
    ],
    preferEnName: false,
    dataNote: null,
  },

  'zh-TW': {
    title: '大師視角 · 閱讀方法庫 · 維點圖書館',
    heading: (n) => `${n} 種大師視角`,
    sub: '每位大師的閱讀方法都是一個獨立的 AI 外掛——可以套用到任意文明的任意文本',
    freeHeading: '🆓 免費體驗',
    freeDesc: '每本書都附贈朱熹視角——這是我們給所有讀者的見面禮。',
    paidHeading: '🔐 付費解鎖',
    paidDesc: '單次購買、永久可讀。所有方法都支援 Markdown/JSON 匯出。',
    priceFree: '免費 · 永久',
    pricePaid: (p) => `¥${p} / 篇`,
    pricePromo: '限時免費',
    cta: '去解鎖 →',
    ctaPlain: '查看說明 →',
    comingHeading: '🚧 即將上線的方法',
    coming: [
      { name: '培根歸納法', meta: 'Francis Bacon · 17世紀英國', desc: '從具體觀察到普遍原則' },
      { name: '布魯姆分類學', meta: "Bloom's Taxonomy · 20世紀美國", desc: '記憶→理解→應用→分析→評價→創造' },
      { name: '普魯斯特閱讀法', meta: 'Proust · 20世紀法國', desc: '閱讀是自我發現的觸發劑' },
      { name: '顧炎武考據法', meta: '明末清初 · 中國', desc: '一字一句皆有出處' },
      { name: '西蒙東技術哲學透鏡', meta: 'Simondon · 20世紀法國', desc: '透過技術演化看一切' },
    ],
    preferEnName: false,
    dataNote: null,
  },

  en: {
    title: 'Masters’ Eyes · Reading Methods · DimensionsCosmos',
    heading: (n) => `${n} master perspectives`,
    sub: 'Each master’s reading method is a standalone AI plugin — applicable to any text from any civilisation',
    freeHeading: '🆓 Free to try',
    freeDesc: 'Every book comes with Zhu Xi’s perspective — our gift to every reader.',
    paidHeading: '🔐 Paid unlock',
    paidDesc: 'One-time purchase, permanent access. All methods export to Markdown/JSON.',
    priceFree: 'Free · forever',
    pricePaid: (p) => `¥${p} / reading`,
    pricePromo: 'Free for a limited time',
    cta: 'Unlock →',
    ctaPlain: 'View details →',
    comingHeading: '🚧 Methods in the pipeline',
    coming: [
      { name: 'Bacon’s induction', meta: 'Francis Bacon · 17th-century England', desc: 'From particular observations to general principles' },
      { name: 'Bloom’s taxonomy', meta: "Bloom's Taxonomy · 20th-century USA", desc: 'Remember → understand → apply → analyse → evaluate → create' },
      { name: 'Proust’s reading', meta: 'Proust · 20th-century France', desc: 'Reading as a trigger for self-discovery' },
      { name: 'Gu Yanwu’s evidential method', meta: 'Late Ming–early Qing · China', desc: 'Every character traced to its source' },
      { name: 'Simondon’s technical lens', meta: 'Simondon · 20th-century France', desc: 'See everything through the evolution of technique' },
    ],
    preferEnName: true,
    dataNote: 'Method descriptions are quoted from the Chinese source data and remain in Chinese in this release.',
  },

  es: {
    title: 'La mirada de los maestros · Métodos de lectura · DimensionsCosmos',
    heading: (n) => `${n} perspectivas de maestros`,
    sub: 'El método de lectura de cada maestro es un complemento de IA independiente, aplicable a cualquier texto de cualquier civilización',
    freeHeading: '🆓 Prueba gratuita',
    freeDesc: 'Cada libro incluye la perspectiva de Zhu Xi: nuestro regalo para todo lector.',
    paidHeading: '🔐 Desbloqueo de pago',
    paidDesc: 'Compra única, acceso permanente. Todos los métodos se exportan a Markdown/JSON.',
    priceFree: 'Gratis · para siempre',
    pricePaid: (p) => `¥${p} / lectura`,
    pricePromo: 'Gratis por tiempo limitado',
    cta: 'Desbloquear →',
    ctaPlain: 'Ver detalles →',
    comingHeading: '🚧 Métodos en preparación',
    coming: [
      { name: 'La inducción de Bacon', meta: 'Francis Bacon · Inglaterra, siglo XVII', desc: 'De las observaciones concretas a los principios generales' },
      { name: 'La taxonomía de Bloom', meta: "Bloom's Taxonomy · EE. UU., siglo XX", desc: 'Recordar → comprender → aplicar → analizar → evaluar → crear' },
      { name: 'La lectura de Proust', meta: 'Proust · Francia, siglo XX', desc: 'La lectura como desencadenante del autodescubrimiento' },
      { name: 'El método evidencial de Gu Yanwu', meta: 'Finales Ming–inicios Qing · China', desc: 'Cada carácter con su fuente documentada' },
      { name: 'La lente técnica de Simondon', meta: 'Simondon · Francia, siglo XX', desc: 'Verlo todo a través de la evolución de la técnica' },
    ],
    preferEnName: true,
    dataNote: 'Las descripciones de los métodos proceden de los datos originales en chino y se mantienen en chino en esta versión.',
  },
};
