import type { Locale } from '../config';

/**
 * 首页文案（B1 三语）。
 * h1 与少数需要强调的句子用 HTML 片段，因为各语言的语序不同（中文「读原文，见底本」，
 * 英文得写成「Read the source, see the base text」），硬套占位符会译出译文腔。
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
  /** {n} 会被替换成在架书数 */
  stripSub: string;
  /** {n} 会被替换成剩余书数 */
  stripMore: string;
  band: { title: string; desc: string }[];
}

export const home: Record<Locale, HomeDict> = {
  zh: {
    title: '维点图书馆 · 古籍原文在线阅读',
    description: '公有领域古籍原文在线阅读库：按经史子集整理卷次章节，保留底本原貌，缺章缺字显式标注、绝不补写。浇灌自由生长的文明。',
    kicker: '古籍 · 原文 · 底本',
    h1Html: '读<em>原文</em>，<br>见<em>底本</em>',
    motto: '浇灌自由生长的文明',
    sub: '一个只做原文的图书馆：卷次与章节按经史子集整理，缺章缺字显式标注、不做补写，全文可检索、可离线读。读法不在本站，在你自己手里。',
    searchPlaceholder: '搜书名：论语 / 史记 / 庄子 ……',
    searchBtn: '检索',
    statBooks: '部经典可读',
    statMethods: '篇校勘记',
    statFree: '全部免费阅读',
    heroArt: ['经部 × 史部 × 子部', '集部 × 别集 × 总集', '底本 × 校勘 × 存真'],
    verticalNote: '存真 · 索引 · 开卷',
    libTitle: '经典书库',
    libSub: '经史子集 · 首批 {n} 部 · 原文来自中文维基文库（CC BY-SA）',
    browseAll: '浏览全部书库 →',
    stripTitle: '原文即正文',
    stripSub: '每部书按底本逐章整理，共 {n} 部在架，缺章缺字显式标注',
    stripMore: '+{n} 部 →',
    band: [
      { title: '📖 原文优先', desc: '本站只做原文：按卷次与章节整理，能读、能检索、能离线保存。' },
      { title: '🔍 底本存真', desc: '底本缺章、缺字（以 □ 标注）或篇幅异常时，页面显式提示，不做补写、不做臆改。' },
      { title: '📤 开放来源', desc: '原文底本主要来自中文维基文库（CC BY-SA 4.0）等开放许可来源，经清洗去标记后入库。' },
      { title: '🧭 读法由你', desc: '本站不预设读法，只把原文与底本信息摆清楚，读法由读者自己生长。' },
    ],
  },

  'zh-TW': {
    title: '維點圖書館 · 古籍原文線上閱讀',
    description: '公有領域古籍原文線上閱讀庫：按經史子集整理卷次章節，保留底本原貌，缺章缺字顯式標註、絕不補寫。澆灌自由生長的文明。',
    kicker: '古籍 · 原文 · 底本',
    h1Html: '讀<em>原文</em>，<br>見<em>底本</em>',
    motto: '澆灌自由生長的文明',
    sub: '一個只做原文的圖書館：卷次與章節按經史子集整理，缺章缺字顯式標註、不做補寫，全文可檢索、可離線讀。讀法不在本站，在你自己手裡。',
    searchPlaceholder: '搜書名：論語 / 史記 / 莊子 ……',
    searchBtn: '檢索',
    statBooks: '部經典可讀',
    statMethods: '篇校勘記',
    statFree: '全部免費閱讀',
    heroArt: ['經部 × 史部 × 子部', '集部 × 別集 × 總集', '底本 × 校勘 × 存真'],
    verticalNote: '存真 · 索引 · 開卷',
    libTitle: '經典書庫',
    libSub: '經史子集 · 首批 {n} 部 · 原文來自中文維基文庫（CC BY-SA）',
    browseAll: '瀏覽全部書庫 →',
    stripTitle: '原文即正文',
    stripSub: '每部書按底本逐章整理，共 {n} 部在架，缺章缺字顯式標註',
    stripMore: '+{n} 部 →',
    band: [
      { title: '📖 原文優先', desc: '本站只做原文：按卷次與章節整理，能讀、能檢索、能離線保存。' },
      { title: '🔍 底本存真', desc: '底本缺章、缺字（以 □ 標註）或篇幅異常時，頁面顯式提示，不做補寫、不做臆改。' },
      { title: '📤 開放來源', desc: '原文底本主要來自中文維基文庫（CC BY-SA 4.0）等開放許可來源，經清洗去標記後入庫。' },
      { title: '🧭 讀法由你', desc: '本站不預設讀法，只把原文與底本資訊擺清楚，讀法由讀者自己生長。' },
    ],
  },

  en: {
    title: 'DimensionsCosmos Library · Read classical texts in the original',
    description:
      'An online reading library for public-domain classical Chinese texts: volumes and chapters organised by the classic fourfold division, kept as the base text has them, with missing chapters or characters marked explicitly and never filled in. Watering a civilisation that grows freely.',
    kicker: 'CLASSICS · SOURCE TEXT · BASE EDITION',
    h1Html: 'Read the <em>source</em>,<br>see the <em>base text</em>',
    motto: 'Watering a civilisation that grows freely',
    sub: 'A library that carries only primary texts: volumes and chapters organised by the classic fourfold division, missing chapters and characters marked explicitly and never filled in, all searchable and readable offline. How to read is not decided here; it is yours.',
    searchPlaceholder: 'Search a title: Analects / Records of the Grand Historian / Zhuangzi…',
    searchBtn: 'Search',
    statBooks: 'classics to read',
    statMethods: 'collation notes',
    statFree: 'free to read',
    heroArt: ['Classics × History × Masters', 'Collections × Anthologies × Individual works', 'Base text × Collation × Fidelity'],
    verticalNote: 'FIDELITY · INDEX · OPEN',
    libTitle: 'The Classics Library',
    libSub: 'Classics, history, masters, collected works · first {n} titles · source texts from Chinese Wikisource (CC BY-SA)',
    browseAll: 'Browse the full library →',
    stripTitle: 'The source text is the content',
    stripSub: 'Every title is organised chapter by chapter after its base edition — {n} volumes on the shelf, gaps marked explicitly',
    stripMore: '+{n} more volumes →',
    band: [
      { title: '📖 Source text first', desc: 'This site carries primary texts only: organised by volume and chapter, readable, searchable, and saveable for offline use.' },
      { title: '🔍 Fidelity to the base edition', desc: 'Where the base edition lacks a chapter, lacks characters (marked with □) or shows an abnormal length, the page says so plainly — nothing is filled in, nothing is emended silently.' },
      { title: '📤 Open sources', desc: 'Base texts come chiefly from open-licensed sources such as Chinese Wikisource (CC BY-SA 4.0), cleaned of markup before entering the database.' },
      { title: '🧭 The way of reading is yours', desc: 'No reading method is prescribed here; the source text and its provenance are laid out clearly, and each reader\u2019s way of reading grows on its own.' },
    ],
  },

  // B2：西班牙语首页。西语语序与中文差异最大的是 h1 与副标题，故同样用 HTML 片段/整句重写，
  // 不做逐字直译——直译会译出明显的"译文腔"，这是翻译质量的第一道分水岭。
  es: {
    title: 'Biblioteca DimensionsCosmos · Lee los textos clásicos en su original',
    description:
      'Una biblioteca de lectura en línea de textos clásicos chinos de dominio público: volúmenes y capítulos organizados según las cuatro divisiones clásicas, tal como los presenta la edición de base, con los capítulos o caracteres faltantes señalados explícitamente y nunca completados. Regar una civilización que crece en libertad.',
    kicker: 'CLÁSICOS · TEXTO ORIGINAL · EDICIÓN DE BASE',
    h1Html: 'Lee el <em>original</em>,<br>mira la <em>edición de base</em>',
    motto: 'Regar una civilización que crece en libertad',
    sub: 'Una biblioteca que solo alberga textos primarios: volúmenes y capítulos organizados por las cuatro divisiones clásicas, con los faltantes señalados explícitamente y sin rellenos, todo consultable y legible sin conexión. Aquí no se dicta cómo leer: eso es tuyo.',
    searchPlaceholder: 'Busca un título: Analectas / Memorias del gran historiador / Zhuangzi…',
    searchBtn: 'Buscar',
    statBooks: 'clásicos por leer',
    statMethods: 'notas de colación',
    statFree: 'lectura gratuita',
    heroArt: ['Clásicos × Historia × Filósofos', 'Colecciones × Antologías × Obras individuales', 'Edición de base × Colación × Fidelidad'],
    verticalNote: 'FIDELIDAD · ÍNDICE · ABRIR',
    libTitle: 'La biblioteca de clásicos',
    libSub: 'Clásicos, historia, maestros y obras reunidas · primeros {n} títulos · textos originales de Wikisource en chino (CC BY-SA)',
    browseAll: 'Ver toda la biblioteca →',
    stripTitle: 'El texto original es el contenido',
    stripSub: 'Cada título se organiza capítulo a capítulo según su edición de base: {n} volúmenes disponibles, con los faltantes señalados',
    stripMore: '+{n} volúmenes más →',
    band: [
      { title: '📖 El texto original primero', desc: 'Este sitio solo alberga textos primarios: organizados por volumen y capítulo, legibles, consultables y guardables sin conexión.' },
      { title: '🔍 Fidelidad a la edición de base', desc: 'Cuando la edición de base carece de un capítulo, de caracteres (marcados con □) o muestra una extensión anómala, la página lo indica con claridad: nada se rellena ni se enmienda por conjetura.' },
      { title: '📤 Fuentes abiertas', desc: 'Los textos de base provienen sobre todo de fuentes de licencia abierta como Wikisource en chino (CC BY-SA 4.0), depuradas de marcas antes de entrar en la base de datos.' },
      { title: '🧭 La manera de leer es tuya', desc: 'Aquí no se prescribe ninguna manera de leer: se exponen con claridad el texto original y los datos de su edición, y la manera de leer de cada lector crece por su cuenta.' },
    ],
  },
};
