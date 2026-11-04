import type { Locale } from '../config';

/**
 * 首页文案（B1 三语）。
 * h1 与少数需要强调的句子用 HTML 片段，因为各语言的语序不同（中文「用大师的方法读书」，
 * 英文得写成「Read any book through a master's eyes」），硬套占位符会译出译文腔。
 * 译者即本文件作者，内容可信，模板处用 set:html 渲染。
 */
export interface HomeDict {
  title: string;
  description: string;
  kicker: string;
  h1Html: string;
  motto: string;
  sub: string;
  searchPlaceholder: string;
  searchBtn: string;
  statBooks: string;
  statMethods: string;
  statFree: string;
  heroArt: [string, string, string];
  verticalNote: string;
  libTitle: string;
  /** {n} 会被替换成实际书数 */
  libSub: string;
  browseAll: string;
  stripTitle: string;
  /** {n} 会被替换成方法数 */
  stripSub: string;
  /** {n} 会被替换成剩余方法数 */
  stripMore: string;
  band: { title: string; desc: string }[];
  /** UX-8 首屏引导与精选。文案缺省（featured.json 无 reason 时）不渲染，不写占位符 */
  featured: FeaturedDict;
}

/** 读者身份四值枚举，与 lib/featured.ts 的 Audience 保持一一对应 */
export interface FeaturedDict {
  kicker: string;
  title: string;
  sub: string;
  /** tablist 的 aria-label */
  tabsLabel: string;
  aud: Record<'student' | 'general' | 'family' | 'research', string>;
  audDesc: Record<'student' | 'general' | 'family' | 'research', string>;
  /** {n} 会被替换成该书导读篇数 */
  badgeGuide: string;
  /** guides 为空时的降级标记 */
  noGuideFlag: string;
  ctaGuide: string;
  ctaRead: string;
  panelEmpty: string;
}

export const home: Record<Locale, HomeDict> = {
  zh: {
    title: '维点图书馆 · 用大师的方法读一切书',
    description: '伟大心智的阅读操作系统：用苏格拉底的方法读庄子，用费曼的方法读相对论，用朱熹的方法读古兰经。',
    kicker: '伟大心智 · 阅读操作系统',
    h1Html: '用<em>大师</em>的方法，<br>读<em>一切</em>书',
    motto: '浇灌自由生长的文明',
    sub: '同样的文本，不同的大师会看到完全不同的东西。选一部经典，再选一位大师的视角——朱熹带你涵泳，费曼帮你白话，苏格拉底追着你问。',
    searchPlaceholder: '搜书名：论语 / 史记 / 庄子 ……',
    searchBtn: '检索',
    statBooks: '部经典可读',
    statMethods: '种大师视角',
    statFree: '个免费体验',
    heroArt: ['朱熹 × 费曼 × 苏格拉底', '苏轼 × 钱锺书 × 王阳明', '阿伦特 × 伊本·赫勒敦 × 阿德勒'],
    verticalNote: '筛选 · 组织 · 导读',
    libTitle: '经典书库',
    libSub: '经史子集 · 首批 {n} 部 · 原文来自中文维基文库（CC BY-SA）',
    browseAll: '浏览全部书库 →',
    stripTitle: '🧠 选好书了？挑一种大师视角来读',
    stripSub: '每本书都内置 {n} 种解读方法——从朱熹到苏格拉底，从费曼到阿伦特',
    stripMore: '+{n} 种更多 →',
    band: [
      { title: '📖 先选书，再选方法', desc: '主流流程：浏览书库 → 找到感兴趣的书 → 选择一位大师的视角 → 开始阅读。' },
      { title: '🧪 创建自己的读书法', desc: '即将开放：上传你的阅读方法论（系统提示词 + 输出模板），转换为可售卖插件，获得收益分成。' },
      { title: '📤 上传你的藏书', desc: '即将开放：像识典古籍一样整理并上传自己的文本，经 AI 自动校勘、标点、分段后入库。' },
      { title: '🔌 方法即插件', desc: '每种大师方法都是一个独立 AI 插件——可组合、可复用、可导出为 Markdown / JSON。' },
    ],
    featured: {
      kicker: '第一次来？从这里开始',
      title: '按你的身份挑好的入门精选',
      sub: '同一部经典，学生、普通读者、一家人、研究者该从哪儿读进去并不一样。选一个最像你的身份，直接开始。',
      tabsLabel: '读者身份',
      aud: { student: '学生', general: '普通读者', family: '亲子共读', research: '研究者' },
      audDesc: {
        student: '从必读篇目入门',
        general: '不必专业背景',
        family: '一家人一起读',
        research: '要版本与脉络',
      },
      badgeGuide: '{n} 种大师解读',
      noGuideFlag: '原文可读 · 导读筹备中',
      ctaGuide: '选一种大师视角 →',
      ctaRead: '直接读原文 →',
      panelEmpty: '该身份下的精选正在编排中。',
    },
  },

  'zh-TW': {
    title: '維點圖書館 · 用大師的方法讀一切書',
    description: '偉大心智的閱讀作業系統：用蘇格拉底的方法讀莊子，用費曼的方法讀相對論，用朱熹的方法讀古蘭經。',
    kicker: '偉大心智 · 閱讀作業系統',
    h1Html: '用<em>大師</em>的方法，<br>讀<em>一切</em>書',
    motto: '澆灌自由生長的文明',
    sub: '同樣的文本，不同的大師會看到完全不同的東西。選一部經典，再選一位大師的視角——朱熹帶你涵泳，費曼幫你白話，蘇格拉底追著你問。',
    searchPlaceholder: '搜書名：論語 / 史記 / 莊子 ……',
    searchBtn: '檢索',
    statBooks: '部經典可讀',
    statMethods: '種大師視角',
    statFree: '個免費體驗',
    heroArt: ['朱熹 × 費曼 × 蘇格拉底', '蘇軾 × 錢鍾書 × 王陽明', '阿倫特 × 伊本·赫勒敦 × 阿德勒'],
    verticalNote: '篩選 · 組織 · 導讀',
    libTitle: '經典書庫',
    libSub: '經史子集 · 首批 {n} 部 · 原文來自中文維基文庫（CC BY-SA）',
    browseAll: '瀏覽全部書庫 →',
    stripTitle: '🧠 選好書了？挑一種大師視角來讀',
    stripSub: '每本書都內建 {n} 種解讀方法——從朱熹到蘇格拉底，從費曼到阿倫特',
    stripMore: '+{n} 種更多 →',
    band: [
      { title: '📖 先選書，再選方法', desc: '主流流程：瀏覽書庫 → 找到感興趣的書 → 選擇一位大師的視角 → 開始閱讀。' },
      { title: '🧪 建立自己的讀書法', desc: '即將開放：上傳你的閱讀方法論（系統提示詞 + 輸出範本），轉換為可販售外掛，獲得收益分潤。' },
      { title: '📤 上傳你的藏書', desc: '即將開放：像識典古籍一樣整理並上傳自己的文本，經 AI 自動校勘、標點、分段後入庫。' },
      { title: '🔌 方法即外掛', desc: '每種大師方法都是一個獨立 AI 外掛——可組合、可重複使用、可匯出為 Markdown / JSON。' },
    ],
    featured: {
      kicker: '第一次來？從這裡開始',
      title: '按你的身分挑好的入門精選',
      sub: '同一部經典，學生、一般讀者、一家人、研究者該從哪裡讀進去並不一樣。選一個最像你的身分，直接開始。',
      tabsLabel: '讀者身分',
      aud: { student: '學生', general: '一般讀者', family: '親子共讀', research: '研究者' },
      audDesc: {
        student: '從必讀篇目入門',
        general: '不必專業背景',
        family: '一家人一起讀',
        research: '要版本與脈絡',
      },
      badgeGuide: '{n} 種大師解讀',
      noGuideFlag: '原文可讀 · 導讀籌備中',
      ctaGuide: '選一種大師視角 →',
      ctaRead: '直接讀原文 →',
      panelEmpty: '此身分下的精選正在編排中。',
    },
  },

  en: {
    title: 'DimensionsCosmos Library · Read any book through a master\u2019s eyes',
    description:
      'A reading operating system for great minds: read Zhuangzi the way Socrates would, relativity the way Feynman would, the Quran the way Zhu Xi would.',
    kicker: 'GREAT MINDS · A READING OS',
    h1Html: 'Read <em>any</em> book<br>through a <em>master</em>\u2019s eyes',
    motto: 'Watering a civilisation that grows freely',
    sub: 'The same text looks different to every great mind. Pick a classic, then pick a master\u2019s vantage point — Zhu Xi reads with you line by line, Feynman puts it in plain words, Socrates keeps asking why.',
    searchPlaceholder: 'Search a title: Analects / Records of the Grand Historian / Zhuangzi…',
    searchBtn: 'Search',
    statBooks: 'classics to read',
    statMethods: 'master perspectives',
    statFree: 'free to try',
    heroArt: ['Zhu Xi × Feynman × Socrates', 'Su Shi × Qian Zhongshu × Wang Yangming', 'Arendt × Ibn Khaldun × Adler'],
    verticalNote: 'FILTER · ORGANISE · GUIDE',
    libTitle: 'The Classics Library',
    libSub: 'Classics, history, masters, collected works · first {n} titles · source texts from Chinese Wikisource (CC BY-SA)',
    browseAll: 'Browse the full library →',
    stripTitle: '🧠 Found your book? Now pick a master\u2019s vantage point',
    stripSub: 'Every title ships with {n} interpretive methods — from Zhu Xi to Socrates, from Feynman to Arendt',
    stripMore: '+{n} more methods →',
    band: [
      { title: '📖 Pick the book, then the method', desc: 'The main path: browse the library → find a title that pulls you in → choose a master\u2019s vantage point → start reading.' },
      { title: '🧪 Build your own reading method', desc: 'Coming soon: upload your own methodology (system prompt + output template), publish it as a sellable plugin and share the revenue.' },
      { title: '📤 Upload your own collection', desc: 'Coming soon: organise and upload your own texts the way classical-text platforms do. AI handles collation, punctuation and paragraphing.' },
      { title: '🔌 Methods are plugins', desc: 'Each master\u2019s method is a standalone AI plugin — composable, reusable, and exportable as Markdown or JSON.' },
    ],
    featured: {
      kicker: 'NEW HERE? START HERE',
      title: 'Starter picks, chosen for who you are',
      sub: 'The same classic opens differently to a student, a general reader, a family, a researcher. Pick the reader closest to you and start there.',
      tabsLabel: 'Reader profile',
      aud: { student: 'Student', general: 'General reader', family: 'Reading as a family', research: 'Researcher' },
      audDesc: {
        student: 'Set texts first',
        general: 'No background needed',
        family: 'Read it together',
        research: 'Editions and lineage',
      },
      badgeGuide: '{n} master readings',
      noGuideFlag: 'Full text ready · guide in preparation',
      ctaGuide: 'Pick a master\u2019s view →',
      ctaRead: 'Read the full text →',
      panelEmpty: 'Picks for this profile are still being curated.',
    },
  },

  // B2：西班牙语首页。西语语序与中文差异最大的是 h1 与副标题，故同样用 HTML 片段/整句重写，
  // 不做逐字直译——直译会译出明显的"译文腔"，这是翻译质量的第一道分水岭。
  es: {
    title: 'Biblioteca DimensionsCosmos · Lee cualquier libro con los ojos de un maestro',
    description:
      'Un sistema operativo de lectura para grandes mentes: lee a Zhuangzi como lo haría Sócrates, la relatividad como lo haría Feynman, el Corán como lo haría Zhu Xi.',
    kicker: 'GRANDES MENTES · UN SO DE LECTURA',
    h1Html: 'Lee <em>cualquier</em> libro<br>con los ojos de un <em>maestro</em>',
    motto: 'Regar una civilización que crece en libertad',
    sub: 'Un mismo texto se ve distinto para cada gran mente. Elige un clásico y después el punto de vista de un maestro: Zhu Xi lee contigo verso a verso, Feynman lo explica en palabras llanas y Sócrates no deja de preguntar por qué.',
    searchPlaceholder: 'Busca un título: Analectas / Memorias del gran historiador / Zhuangzi…',
    searchBtn: 'Buscar',
    statBooks: 'clásicos por leer',
    statMethods: 'perspectivas de maestros',
    statFree: 'gratis para probar',
    heroArt: ['Zhu Xi × Feynman × Sócrates', 'Su Shi × Qian Zhongshu × Wang Yangming', 'Arendt × Ibn Jaldún × Adler'],
    verticalNote: 'FILTRAR · ORGANIZAR · GUIAR',
    libTitle: 'La biblioteca de clásicos',
    libSub: 'Clásicos, historia, maestros y obras reunidas · primeros {n} títulos · textos originales de Wikisource en chino (CC BY-SA)',
    browseAll: 'Ver toda la biblioteca →',
    stripTitle: '🧠 ¿Ya tienes tu libro? Elige el punto de vista de un maestro',
    stripSub: 'Cada título incluye {n} métodos de interpretación: de Zhu Xi a Sócrates, de Feynman a Arendt',
    stripMore: '+{n} métodos más →',
    band: [
      { title: '📖 Primero el libro, después el método', desc: 'La ruta principal: explora la biblioteca → encuentra un título que te atraiga → elige el punto de vista de un maestro → empieza a leer.' },
      { title: '🧪 Crea tu propio método de lectura', desc: 'Muy pronto: sube tu metodología (prompt de sistema + plantilla de salida), publícala como complemento de pago y comparte los ingresos.' },
      { title: '📤 Sube tu propia colección', desc: 'Muy pronto: organiza y sube tus textos como hacen las plataformas de clásicos. La IA se encarga de la colación, la puntuación y los párrafos.' },
      { title: '🔌 Los métodos son complementos', desc: 'Cada método de un maestro es un complemento de IA independiente: se puede combinar, reutilizar y exportar como Markdown o JSON.' },
    ],
    featured: {
      kicker: '¿PRIMERA VEZ? EMPIEZA AQUÍ',
      title: 'Clásicos de entrada elegidos según quién eres',
      sub: 'Un mismo clásico se abre de forma distinta para un estudiante, un lector general, una familia o un investigador. Elige el perfil que más se te parezca y empieza por ahí.',
      tabsLabel: 'Perfil de lector',
      aud: { student: 'Estudiante', general: 'Lector general', family: 'En familia', research: 'Investigador' },
      audDesc: {
        student: 'Textos obligados',
        general: 'Sin formación previa',
        family: 'Para leer juntos',
        research: 'Ediciones y linaje',
      },
      badgeGuide: '{n} lecturas de maestros',
      noGuideFlag: 'Texto completo listo · guía en preparación',
      ctaGuide: 'Elige la mirada de un maestro →',
      ctaRead: 'Leer el texto completo →',
      panelEmpty: 'La selección para este perfil aún se está preparando.',
    },
  },
};
