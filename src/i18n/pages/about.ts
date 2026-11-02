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
    meta: '古籍 · 全文 · 多视角解读',
    whatTitle: '本站是什么',
    whatBody:
      '一个中国古典文献的在线阅读库，把「读原文」和「换视角读」放在同一处：原文按卷次与章节整理，可全文检索式浏览；解读用不同的读书方法（朱熹读书法、费曼、苏格拉底、钱钟书、苏轼、王阳明、阿伦特、伊本·赫勒敦等）逐篇生成，方便对照不同进路。',
    scaleTitle: '当前收录规模（实时取自构建数据）',
    statBooks: '部书',
    statChapters: '章正文',
    statChars: '万字',
    statGuides: '篇 AI 解读',
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
      '解读类内容由语言模型辅助生成，页面顶部标注「AI 辅助生成」，并注明生成模型与时间。',
      'AI 解读用于提供阅读路径与提问角度，不是校勘结论，也不能替代原典与研究文献。',
      '未生成的书目不会展示任何购买入口；上架清单以定价页为准。',
    ],
    priceTitle: '收费状态',
    priceOn: '已开放线上销售，价格与交付范围见定价页。',
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
      '一個中國古典文獻的線上閱讀庫，把「讀原文」和「換視角讀」放在同一處：原文按卷次與章節整理，可全文檢索式瀏覽；解讀用不同的讀書方法（朱熹讀書法、費曼、蘇格拉底、錢鍾書、蘇軾、王陽明、阿倫特、伊本·赫勒敦等）逐篇生成，方便對照不同進路。',
    scaleTitle: '當前收錄規模（即時取自建置資料）',
    statBooks: '部書',
    statChapters: '章正文',
    statChars: '萬字',
    statGuides: '篇 AI 解讀',
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
      '解讀類內容由語言模型輔助生成，頁面頂部標註「AI 輔助生成」，並註明生成模型與時間。',
      'AI 解讀用於提供閱讀路徑與提問角度，不是校勘結論，也不能替代原典與研究文獻。',
      '未生成的書目不會顯示任何購買入口；上架清單以定價頁為準。',
    ],
    priceTitle: '收費狀態',
    priceOn: '已開放線上銷售，價格與交付範圍見定價頁。',
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
      'An online reading library for classical Chinese literature that keeps "reading the source" and "reading from another angle" in one place: the primary text is organised by volume and chapter and can be browsed with full-text search, while commentaries are generated reading by reading using different methods (Zhu Xi’s reading method, Feynman, Socratic questioning, Qian Zhongshu, Su Shi, Wang Yangming, Hannah Arendt, Ibn Khaldun and others), so the approaches can be compared side by side.',
    scaleTitle: 'Current holdings (read from the build data)',
    statBooks: 'works',
    statChapters: 'chapters',
    statChars: '×10k characters',
    statGuides: 'AI commentaries',
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
      'Commentaries are drafted with the help of a language model; the page header marks them "AI-assisted" and names the model and generation time.',
      'AI commentaries offer reading routes and questions to ask. They are not textual scholarship, and they do not replace the classics or the research literature.',
      'Works without a commentary show no purchase entry at all; the shelf list on the pricing page is the single source of truth.',
    ],
    priceTitle: 'Paid or free',
    priceOn: 'Online sales are open. Prices and what is delivered are listed on the pricing page.',
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
      'Una biblioteca de lectura en línea de literatura clásica china que reúne «leer el texto original» y «leerlo desde otro ángulo» en un mismo lugar: el texto se organiza por volúmenes y capítulos y puede recorrerse con búsqueda de texto completo, mientras que los comentarios se generan obra por obra con distintos métodos de lectura (el método de Zhu Xi, Feynman, la pregunta socrática, Qian Zhongshu, Su Shi, Wang Yangming, Hannah Arendt, Ibn Jaldún y otros), para comparar enfoques.',
    scaleTitle: 'Fondos actuales (leídos de los datos de compilación)',
    statBooks: 'obras',
    statChapters: 'capítulos',
    statChars: '×10 mil caracteres',
    statGuides: 'comentarios de IA',
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
      'Los comentarios se redactan con ayuda de un modelo de lenguaje; la cabecera indica «generado con asistencia de IA» y señala el modelo y la fecha.',
      'Los comentarios de IA ofrecen rutas de lectura y preguntas que hacerse. No son crítica textual ni sustituyen a los clásicos o a la bibliografía académica.',
      'Las obras sin comentario no muestran ninguna entrada de compra; la lista del catálogo en la página de precios es la referencia única.',
    ],
    priceTitle: 'Gratuito o de pago',
    priceOn: 'La venta en línea está abierta. Los precios y el alcance de la entrega figuran en la página de precios.',
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
