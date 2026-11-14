/**
 * 「关于本站」页面词典（B3 批二）
 *
 * 口径同 books.ts / methods.ts：文案随语言走，运营主体、邮箱、仓库地址等
 * 事实性内容仍从 src/config/commerce.ts 注入，词典只管「怎么说」。
 */
import type { Locale } from '../config';

export interface AboutDict {
  /** <title> 与分享卡片标题 */
  pageTitle: string;
  h1: string;
  meta: string;

  whatTitle: string;
  whatBody: string;

  scaleTitle: string;
  statBooks: string;
  statChapters: string;
  statChars: string;
  statGuides: string;
  /** 数据生成时间的前缀，如「数据生成时间：」 */
  generatedAt: string;
  /** 时区说明，如「（北京时间）」 */
  timezoneNote: string;

  sourceTitle: string;
  sourceItems: string[];

  aiTitle: string;
  aiItems: string[];

  priceTitle: string;
  priceOn: string;
  priceOff: string;

  operatorTitle: string;
  labelOperator: string;
  labelEmail: string;
  labelRepo: string;
  labelRegion: string;
  labelDocs: string;
  docTerms: string;
  docRefund: string;
  docPrivacy: string;

  hint: string;
}

export const aboutDict: Record<Locale, AboutDict> = {
  zh: {
    pageTitle: '关于本站 · 维点图书馆',
    h1: '关于维点图书馆',
    meta: '古籍 · 全文 · 在线阅读',
    whatTitle: '本站是什么',
    whatBody:
      '一个中国古典文献的在线阅读库：原文按卷次与章节整理，保留底本原貌，缺章缺字显式标注、不做补写，并提供全文检索式浏览。本站只做浇灌——把原文与底本信息摆清楚，读法由读者自己生长。',
    scaleTitle: '当前收录规模（实时取自构建数据）',
    statBooks: '部书',
    statChapters: '章正文',
    statChars: '万字',
    statGuides: '处底本标注',
    generatedAt: '数据生成时间：',
    timezoneNote: '（北京时间）',
    sourceTitle: '内容来源与许可',
    sourceItems: [
      '原文底本主要来自中文维基文库（CC BY-SA 4.0）等开放许可来源，经清洗流程去除维基标记、注脚与模板残留。',
      '底本存在缺章、缺字（以 □ 标注）或篇幅异常时，页面会显式提示，不做补写，以免混淆原文。',
      '原文的再分发需遵守原许可协议（署名—相同方式共享）。',
    ],
    aiTitle: 'AI 内容的边界',
    aiItems: [
      '本站不使用语言模型生成解读或推荐文本；页面呈现的是原文与底本整理信息。',
      '原文缺章、缺字、篇幅异常等底本状况，均在页面显式标注，不做补写，也不替代原典与研究文献。',
      '如未来引入任何模型生成内容，将在相应页面显著标识并单独说明其范围。',
    ],
    priceTitle: '收费状态',
    priceOn: '站内目前不含付费内容；如未来开放，价格与交付范围将在本页说明。',
    priceOff: '尚未开放线上收款，站内全部内容免费阅读，也不会以任何形式向您索取款项。',
    operatorTitle: '运营主体与联系',
    labelOperator: '运营方：',
    labelEmail: '联系邮箱：',
    labelRepo: '项目仓库：',
    labelRegion: '服务地区：',
    labelDocs: '相关条款：',
    docTerms: '服务条款',
    docRefund: '退款说明',
    docPrivacy: '隐私政策',
    hint: '运营主体与联系邮箱当前为待填占位，集中在 src/config/commerce.ts 中维护；对外正式运营（尤其收费）前必须补齐真实信息。',
  },

  'zh-TW': {
    pageTitle: '關於本站 · 維點圖書館',
    h1: '關於維點圖書館',
    meta: '古籍 · 全文 · 多視角解讀',
    whatTitle: '本站是什麼',
    whatBody:
      '一個中國古典文獻的線上閱讀庫：原文按卷次與章節整理，保留底本原貌，缺章缺字顯式標註、不做補寫，並提供全文檢索式瀏覽。本站只做澆灌——把原文與底本資訊擺清楚，讀法由讀者自己生長。',
    scaleTitle: '當前收錄規模（即時取自建置資料）',
    statBooks: '部書',
    statChapters: '章正文',
    statChars: '萬字',
    statGuides: '處底本標註',
    generatedAt: '資料產生時間：',
    timezoneNote: '（北京時間）',
    sourceTitle: '內容來源與授權',
    sourceItems: [
      '原文底本主要來自中文維基文庫（CC BY-SA 4.0）等開放授權來源，經清洗流程去除維基標記、註腳與模板殘留。',
      '底本存在缺章、缺字（以 □ 標註）或篇幅異常時，頁面會明確提示，不做補寫，以免混淆原文。',
      '原文的再散布需遵守原授權條款（姓名標示—相同方式分享）。',
    ],
    aiTitle: 'AI 內容的界線',
    aiItems: [
      '本站不使用語言模型生成解讀或推薦文本；頁面呈現的是原文與底本整理資訊。',
      '原文缺章、缺字、篇幅異常等底本狀況，均在頁面顯式標註，不做補寫，也不替代原典與研究文獻。',
      '如未來引入任何模型生成內容，將在相應頁面顯著標識並單獨說明其範圍。',
    ],
    priceTitle: '收費狀態',
    priceOn: '站內目前不含付費內容；如未來開放，價格與交付範圍將在本頁說明。',
    priceOff: '尚未開放線上收款，站內全部內容免費閱讀，也不會以任何形式向您索取款項。',
    operatorTitle: '營運主體與聯絡',
    labelOperator: '營運方：',
    labelEmail: '聯絡信箱：',
    labelRepo: '專案倉庫：',
    labelRegion: '服務地區：',
    labelDocs: '相關條款：',
    docTerms: '服務條款',
    docRefund: '退款說明',
    docPrivacy: '隱私政策',
    hint: '營運主體與聯絡信箱目前為待填佔位，集中在 src/config/commerce.ts 中維護；對外正式營運（尤其收費）前必須補齊真實資訊。',
  },

  en: {
    pageTitle: 'About · DimensionsCosmos',
    h1: 'About DimensionsCosmos',
    meta: 'Classics · Full text · Multiple readings',
    whatTitle: 'What this site is',
    whatBody:
      'An online reading library for classical Chinese literature: primary texts are organised by volume and chapter, kept in their original form with missing chapters or characters explicitly marked and never filled in, browsable with full-text search. The site only irrigates: it lays the source text and its provenance out clearly, and lets each reader\'s own way of reading grow.',
    scaleTitle: 'Current holdings (read from the build data)',
    statBooks: 'works',
    statChapters: 'chapters',
    statChars: '×10k characters',
    statGuides: 'base-text notes',
    generatedAt: 'Data generated: ',
    timezoneNote: ' (Beijing time)',
    sourceTitle: 'Sources and licensing',
    sourceItems: [
      'Base texts come mainly from Chinese Wikisource (CC BY-SA 4.0) and other openly licensed sources, cleaned of wiki markup, footnotes and template residue.',
      'Where a base text has missing chapters, missing characters (marked □) or abnormal length, the page says so explicitly. Nothing is filled in, so the original is never blurred.',
      'Redistribution of the base texts must follow their original licences (attribution — share alike).',
    ],
    aiTitle: 'Where AI content stops',
    aiItems: [
      'This site does not use a language model to generate commentary or recommendations; what the pages show is the source text and notes on its base edition.',
      'Where the base edition lacks chapters or characters, or shows an abnormal length, the page says so plainly — nothing is filled in, and none of it replaces the classics or the research literature.',
      'Should any model-generated content be introduced later, it will be marked prominently on the relevant pages and its scope described separately.',
    ],
    priceTitle: 'Paid or free',
    priceOn: 'The site currently contains no paid content. If that changes, prices and what is delivered will be set out on this page.',
    priceOff: 'Online payment is not open yet. Everything on the site is free to read, and nothing will ever be charged to you here.',
    operatorTitle: 'Operator and contact',
    labelOperator: 'Operated by: ',
    labelEmail: 'Email: ',
    labelRepo: 'Repository: ',
    labelRegion: 'Service region: ',
    labelDocs: 'Documents: ',
    docTerms: 'Terms of Service',
    docRefund: 'Refund Policy',
    docPrivacy: 'Privacy Policy',
    hint: 'The operator name and contact email are still placeholders kept in src/config/commerce.ts; real details must be filled in before formal operation, especially before charging anyone.',
  },

  es: {
    pageTitle: 'Acerca de · DimensionsCosmos',
    h1: 'Acerca de DimensionsCosmos',
    meta: 'Clásicos · Texto completo · Lecturas múltiples',
    whatTitle: 'Qué es este sitio',
    whatBody:
      'Una biblioteca de lectura en línea de literatura clásica china: los textos primarios se organizan por volumen y capítulo, se conservan tal como están en el original, con los capítulos o caracteres faltantes señalados explícitamente y nunca completados, y pueden consultarse con búsqueda de texto completo. Este sitio solo riega: deja claro el texto fuente y su procedencia, y permite que crezca la manera de leer de cada lector.',
    scaleTitle: 'Fondos actuales (leídos de los datos de compilación)',
    statBooks: 'obras',
    statChapters: 'capítulos',
    statChars: '×10 mil caracteres',
    statGuides: 'notas de la edición',
    generatedAt: 'Datos generados: ',
    timezoneNote: ' (hora de Pekín)',
    sourceTitle: 'Fuentes y licencias',
    sourceItems: [
      'Los textos base proceden sobre todo de Wikisource en chino (CC BY-SA 4.0) y otras fuentes de licencia abierta, depurados de marcas wiki, notas y restos de plantillas.',
      'Cuando un texto base tiene capítulos faltantes, caracteres ausentes (marcados con □) o una extensión anómala, la página lo indica de forma explícita. No se rellena nada, para no difuminar el original.',
      'La redistribución de los textos debe respetar sus licencias originales (atribución — compartir igual).',
    ],
    aiTitle: 'Dónde termina el contenido de IA',
    aiItems: [
      'Este sitio no emplea modelos de lenguaje para generar comentarios ni recomendaciones; las páginas muestran el texto original y las notas sobre su edición de base.',
      'Cuando la edición de base carece de capítulos o caracteres, o muestra una extensión anómala, la página lo indica con claridad: nada se rellena y nada sustituye a los clásicos ni a la bibliografía académica.',
      'Si en el futuro se incorpora contenido generado por modelos, se señalará de forma destacada en las páginas correspondientes y se explicará por separado su alcance.',
    ],
    priceTitle: 'Gratuito o de pago',
    priceOn: 'Actualmente el sitio no contiene contenido de pago. Si eso cambia, los precios y el alcance de la entrega se detallarán en esta página.',
    priceOff: 'El pago en línea aún no está abierto. Todo el sitio es de lectura gratuita y nunca se te pedirá dinero aquí.',
    operatorTitle: 'Titular y contacto',
    labelOperator: 'Titular: ',
    labelEmail: 'Correo: ',
    labelRepo: 'Repositorio: ',
    labelRegion: 'Región de servicio: ',
    labelDocs: 'Documentos: ',
    docTerms: 'Términos del servicio',
    docRefund: 'Política de reembolso',
    docPrivacy: 'Política de privacidad',
    hint: 'El nombre del titular y el correo de contacto son aún marcadores de posición definidos en src/config/commerce.ts; deben completarse con datos reales antes de operar formalmente, y sobre todo antes de cobrar.',
  },
};
