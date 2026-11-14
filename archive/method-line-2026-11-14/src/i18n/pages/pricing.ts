/**
 * 「定价」页面词典（B3 批二）
 *
 * 说明：价格数字、已上架清单、付费方法表都由构建数据实时算出，
 * 词典只负责这些数字周围的说法；方法名（朱熹、尼采…）作为专名保留中文，
 * 与 methods 页口径一致。
 */
import type { Locale } from '../config';

export interface PricingDict {
  pageTitle: string;
  h2: string;
  /** 网页模式：含"按篇购买"表述 */
  taglineWeb: string;
  /** 商店模式：不得出现任何购买语境 */
  taglineStore: string;

  supplyBooks: string;
  supplyChapters: string;
  supplyChars: string;
  supplyShelf: string;

  freeBadge: string;
  freeTitle: string;
  freeDesc: (works: string, chapters: string) => string;
  freeItems: string[];
  freeCta: string;

  guideBadgeOn: string;
  guideBadgeOff: string;
  guideTitle: string;
  guidePerUnit: string;
  guideLimited: string;
  guideDescOn: (shelfCount: number) => string;
  guideDescOff: (shelfCount: number) => string;
  guideItemsOn: string[];
  guideItemsOff: string[];
  guideCtaOn: string;
  guideCtaOff: string;

  packBadge: string;
  packTitle: string;
  packPerUnit: string;
  packDesc: string;
  packItems: (methodCount: number) => string[];
  packCta: string;

  shelfTitle: (shelfCount: number, covered: number) => string;
  shelfEmpty: string;
  shelfFree: string;
  shelfNotePrefix: string;
  shelfNoteBold: string;
  shelfNoteSuffix: string;

  tableTitle: string;
  thMethod: string;
  thEra: string;
  thPrice: string;
  thDesc: string;
  tableNote: string;

  payTitle: string;
  payOn: string;
  payOff: string;
  refundTitle: string;
  refundPrefix: string;
  refundLink: string;
  refundSuffix: string;
  contactTitle: string;
  contactPrefix: string;
  contactTerms: string;
  contactMid: string;
  contactAbout: string;
  contactSuffix: string;
}

export const pricingDict: Record<Locale, PricingDict> = {
  zh: {
    pageTitle: '定价 · 维点图书馆',
    h2: '简单定价',
    taglineWeb: '全文阅读永久免费；AI 深度导读按篇购买，不囤课、不年费',
    taglineStore: '全文阅读永久免费；AI 导读现阶段同样免费开放，无购买项、无内购',
    supplyBooks: '部古籍全文',
    supplyChapters: '章可读',
    supplyChars: '万字',
    supplyShelf: '篇导读已上架',
    freeBadge: '永久免费',
    freeTitle: '全文阅读',
    freeDesc: (works, chapters) => `全部 ${works} 部书、${chapters} 章原文`,
    freeItems: ['原文全文在线阅读', '章节目录 / 卷次分组', '简繁原文与缺字标注', '无需注册、无广告'],
    freeCta: '开始阅读',
    guideBadgeOn: '可购买',
    guideBadgeOff: '当前免费开放',
    guideTitle: '单篇导读',
    guidePerUnit: '/篇起',
    guideLimited: '· 限时',
    guideDescOn: (n) => `已上架 ${n} 篇，买一篇看一篇、永久可读`,
    guideDescOff: (n) => `已生成 ${n} 篇深度导读，现阶段免费阅读`,
    guideItemsOn: ['按方法深度解读一本书', '结构化拆解与阅读路径', '一次性购买、永久访问', '7 天内不满意可退'],
    guideItemsOff: ['按方法深度解读一本书', '结构化拆解与阅读路径', '正式收费前不产生任何费用'],
    guideCtaOn: '查看已上架导读',
    guideCtaOff: '查看可读清单',
    packBadge: '筹备中',
    packTitle: '方法包',
    packPerUnit: '/年',
    packDesc: '全部方法无限次使用',
    packItems: (n) => [`全部 ${n} 种方法`, '新方法自动解锁', '优先投票新书入库', 'B 端 API 折扣'],
    packCta: '尚未开放',
    shelfTitle: (shelf, covered) => `已上架导读（${shelf} 篇 · 覆盖 ${covered} 部书）`,
    shelfEmpty: '目前还没有已上架的导读，全部内容以原文阅读开放。',
    shelfFree: '免费',
    shelfNotePrefix: '其余 ',
    shelfNoteBold: '未生成的一律不售卖、页面上也不会出现购买入口',
    shelfNoteSuffix: '，生成完成后会在此清单中自动出现。',
    tableTitle: '付费方法单价',
    thMethod: '方法',
    thEra: '时代',
    thPrice: '单价',
    thDesc: '说明',
    tableNote: '单价为正式开放销售后的定价；当前阶段已上架导读免费阅读。',
    payTitle: '如何付款',
    payOn: '通过商品页完成支付，支付后即可解锁对应导读。',
    payOff: '尚未开放付款。开放前站内所有内容均不收费，也不会向您索取任何款项。',
    refundTitle: '退款政策',
    refundPrefix: '数字化内容一经解锁不支持无理由退款；内容与描述不符或无法访问的，按 ',
    refundLink: '退款说明',
    refundSuffix: ' 处理。',
    contactTitle: '联系我们',
    contactPrefix: '条款与主体信息见 ',
    contactTerms: '服务条款',
    contactMid: '、',
    contactAbout: '关于本站',
    contactSuffix: '；问题反馈：',
  },

  'zh-TW': {
    pageTitle: '定價 · 維點圖書館',
    h2: '簡單定價',
    taglineWeb: '全文閱讀永久免費；AI 深度導讀按篇購買，不囤課、不年費',
    taglineStore: '全文閱讀永久免費；AI 導讀現階段同樣免費開放，無購買項、無內購',
    supplyBooks: '部古籍全文',
    supplyChapters: '章可讀',
    supplyChars: '萬字',
    supplyShelf: '篇導讀已上架',
    freeBadge: '永久免費',
    freeTitle: '全文閱讀',
    freeDesc: (works, chapters) => `全部 ${works} 部書、${chapters} 章原文`,
    freeItems: ['原文全文線上閱讀', '章節目錄 / 卷次分組', '簡繁原文與缺字標註', '無需註冊、無廣告'],
    freeCta: '開始閱讀',
    guideBadgeOn: '可購買',
    guideBadgeOff: '目前免費開放',
    guideTitle: '單篇導讀',
    guidePerUnit: '/篇起',
    guideLimited: '· 限時',
    guideDescOn: (n) => `已上架 ${n} 篇，買一篇看一篇、永久可讀`,
    guideDescOff: (n) => `已產生 ${n} 篇深度導讀，現階段免費閱讀`,
    guideItemsOn: ['按方法深度解讀一本書', '結構化拆解與閱讀路徑', '一次性購買、永久存取', '7 天內不滿意可退'],
    guideItemsOff: ['按方法深度解讀一本書', '結構化拆解與閱讀路徑', '正式收費前不產生任何費用'],
    guideCtaOn: '查看已上架導讀',
    guideCtaOff: '查看可讀清單',
    packBadge: '籌備中',
    packTitle: '方法包',
    packPerUnit: '/年',
    packDesc: '全部方法無限次使用',
    packItems: (n) => [`全部 ${n} 種方法`, '新方法自動解鎖', '優先投票新書入庫', 'B 端 API 折扣'],
    packCta: '尚未開放',
    shelfTitle: (shelf, covered) => `已上架導讀（${shelf} 篇 · 涵蓋 ${covered} 部書）`,
    shelfEmpty: '目前還沒有已上架的導讀，全部內容以原文閱讀開放。',
    shelfFree: '免費',
    shelfNotePrefix: '其餘 ',
    shelfNoteBold: '未產生的一律不販售、頁面上也不會出現購買入口',
    shelfNoteSuffix: '，產生完成後會在此清單中自動出現。',
    tableTitle: '付費方法單價',
    thMethod: '方法',
    thEra: '時代',
    thPrice: '單價',
    thDesc: '說明',
    tableNote: '單價為正式開放銷售後的定價；現階段已上架導讀免費閱讀。',
    payTitle: '如何付款',
    payOn: '透過商品頁完成付款，付款後即可解鎖對應導讀。',
    payOff: '尚未開放付款。開放前站內所有內容均不收費，也不會向您索取任何款項。',
    refundTitle: '退款政策',
    refundPrefix: '數位內容一經解鎖不支援無理由退款；內容與描述不符或無法存取者，依 ',
    refundLink: '退款說明',
    refundSuffix: ' 處理。',
    contactTitle: '聯絡我們',
    contactPrefix: '條款與主體資訊見 ',
    contactTerms: '服務條款',
    contactMid: '、',
    contactAbout: '關於本站',
    contactSuffix: '；問題回報：',
  },

  en: {
    pageTitle: 'Pricing · DimensionsCosmos',
    h2: 'Simple pricing',
    taglineWeb: 'Full-text reading is free forever; in-depth AI commentaries are bought per piece — no course bundles, no annual fee',
    taglineStore: 'Full-text reading is free forever; AI commentaries are also free at this stage — no purchases, no in-app items',
    supplyBooks: 'full texts',
    supplyChapters: 'chapters readable',
    supplyChars: '×10k characters',
    supplyShelf: 'commentaries on the shelf',
    freeBadge: 'Free forever',
    freeTitle: 'Full-text reading',
    freeDesc: (works, chapters) => `All ${works} works, ${chapters} chapters of primary text`,
    freeItems: ['Read the full text online', 'Chapter list grouped by volume', 'Simplified and traditional text, missing characters marked', 'No sign-up, no ads'],
    freeCta: 'Start reading',
    guideBadgeOn: 'Available now',
    guideBadgeOff: 'Free at this stage',
    guideTitle: 'Single commentary',
    guidePerUnit: '/piece',
    guideLimited: '· limited time',
    guideDescOn: (n) => `${n} on the shelf — buy one, read one, keep it for good`,
    guideDescOff: (n) => `${n} in-depth commentaries ready, free to read at this stage`,
    guideItemsOn: ['One book read deeply through one method', 'Structured breakdown and reading route', 'One-time purchase, permanent access', 'Refund within 7 days if unsatisfied'],
    guideItemsOff: ['One book read deeply through one method', 'Structured breakdown and reading route', 'No charge at all before sales open'],
    guideCtaOn: 'See the available commentaries',
    guideCtaOff: 'See what is readable',
    packBadge: 'In preparation',
    packTitle: 'Method bundle',
    packPerUnit: '/year',
    packDesc: 'Every method, unlimited use',
    packItems: (n) => [`All ${n} methods`, 'New methods unlock automatically', 'Early vote on which works to add', 'Business API discount'],
    packCta: 'Not open yet',
    shelfTitle: (shelf, covered) => `Commentaries on the shelf (${shelf} · covering ${covered} works)`,
    shelfEmpty: 'No commentaries are on the shelf yet; everything is open as primary-text reading.',
    shelfFree: 'Free',
    shelfNotePrefix: 'The remaining ',
    shelfNoteBold: 'are never sold and show no purchase entry',
    shelfNoteSuffix: '; each appears in this list automatically once generated.',
    tableTitle: 'Price per paid method',
    thMethod: 'Method',
    thEra: 'Era',
    thPrice: 'Price',
    thDesc: 'Notes',
    tableNote: 'Prices apply once sales open; commentaries already on the shelf are free to read at this stage.',
    payTitle: 'How payment works',
    payOn: 'Pay on the item page; the commentary unlocks immediately afterwards.',
    payOff: 'Payment is not open yet. Until it is, nothing on this site costs anything and nothing will be charged to you.',
    refundTitle: 'Refund policy',
    refundPrefix: 'Unlocked digital content is not refundable on a change of mind; if the content does not match its description or cannot be opened, follow the ',
    refundLink: 'refund policy',
    refundSuffix: '.',
    contactTitle: 'Contact',
    contactPrefix: 'Terms and operator details: ',
    contactTerms: 'Terms of Service',
    contactMid: ' · ',
    contactAbout: 'About',
    contactSuffix: '. Feedback: ',
  },

  es: {
    pageTitle: 'Precios · DimensionsCosmos',
    h2: 'Precios sencillos',
    taglineWeb: 'La lectura del texto completo es gratuita para siempre; los comentarios de IA se compran por pieza: sin packs de cursos ni cuota anual',
    taglineStore: 'La lectura del texto completo es gratuita para siempre; los comentarios de IA también son gratuitos en esta etapa: sin compras ni artículos integrados',
    supplyBooks: 'obras completas',
    supplyChapters: 'capítulos legibles',
    supplyChars: '×10 mil caracteres',
    supplyShelf: 'comentarios publicados',
    freeBadge: 'Gratis para siempre',
    freeTitle: 'Lectura del texto completo',
    freeDesc: (works, chapters) => `Las ${works} obras, ${chapters} capítulos de texto original`,
    freeItems: ['Lectura del texto completo en línea', 'Índice de capítulos agrupado por volúmenes', 'Texto simplificado y tradicional, caracteres ausentes marcados', 'Sin registro y sin publicidad'],
    freeCta: 'Empezar a leer',
    guideBadgeOn: 'Disponible',
    guideBadgeOff: 'Gratis en esta etapa',
    guideTitle: 'Comentario suelto',
    guidePerUnit: '/pieza',
    guideLimited: '· por tiempo limitado',
    guideDescOn: (n) => `${n} publicados: compras uno, lees uno y lo conservas`,
    guideDescOff: (n) => `${n} comentarios en profundidad ya generados, gratuitos en esta etapa`,
    guideItemsOn: ['Un libro leído a fondo con un método', 'Desglose estructurado y ruta de lectura', 'Pago único, acceso permanente', 'Reembolso en 7 días si no te convence'],
    guideItemsOff: ['Un libro leído a fondo con un método', 'Desglose estructurado y ruta de lectura', 'Ningún cargo antes de abrir la venta'],
    guideCtaOn: 'Ver los comentarios disponibles',
    guideCtaOff: 'Ver qué se puede leer',
    packBadge: 'En preparación',
    packTitle: 'Pack de métodos',
    packPerUnit: '/año',
    packDesc: 'Todos los métodos, uso ilimitado',
    packItems: (n) => [`Los ${n} métodos`, 'Los métodos nuevos se desbloquean solos', 'Voto prioritario sobre nuevas obras', 'Descuento en la API para empresas'],
    packCta: 'Aún no disponible',
    shelfTitle: (shelf, covered) => `Comentarios publicados (${shelf} · cubren ${covered} obras)`,
    shelfEmpty: 'Todavía no hay comentarios publicados; todo está abierto como lectura del texto original.',
    shelfFree: 'Gratis',
    shelfNotePrefix: 'Las otras ',
    shelfNoteBold: 'nunca se venden ni muestran entrada de compra',
    shelfNoteSuffix: '; aparecerán en esta lista en cuanto se generen.',
    tableTitle: 'Precio por método de pago',
    thMethod: 'Método',
    thEra: 'Época',
    thPrice: 'Precio',
    thDesc: 'Notas',
    tableNote: 'Los precios se aplican cuando se abra la venta; los comentarios ya publicados son gratuitos en esta etapa.',
    payTitle: 'Cómo se paga',
    payOn: 'El pago se hace en la página del artículo y el comentario se desbloquea al instante.',
    payOff: 'El pago aún no está abierto. Hasta entonces nada en este sitio tiene coste y nunca se te cobrará nada.',
    refundTitle: 'Política de reembolso',
    refundPrefix: 'El contenido digital desbloqueado no se reembolsa por cambio de opinión; si no coincide con su descripción o no se puede abrir, aplica la ',
    refundLink: 'política de reembolso',
    refundSuffix: '.',
    contactTitle: 'Contacto',
    contactPrefix: 'Términos y datos del titular: ',
    contactTerms: 'Términos del servicio',
    contactMid: ' · ',
    contactAbout: 'Acerca de',
    contactSuffix: '. Comentarios: ',
  },
};
