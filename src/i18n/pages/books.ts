import type { Locale } from '../config';

/**
 * 书库页（/books）界面词。
 * 书名、作者属原典专名，保留汉字；部类与朝代由 book.ts 的 bookDict 负责，
 * 这里只管这一页自己的标题、提示、计数与空态。
 */
export interface BooksDict {
  /** <title>；{q} 为搜索词占位 */
  title: (q: string) => string;
  /** 页头主标题 */
  heading: string;
  /** 页头副标题；{n} 为可读书目数 */
  sub: (n: number) => string;
  searchPlaceholder: string;
  searchAria: string;
  clear: string;
  /** 结果计数；{n} 数量，{q} 搜索词，{bu} 部类 */
  count: (n: number, q: string, bu: string) => string;
  emptyTitle: string;
  emptyHint: string;
  /** 客户端脚本用的短空态第二行 */
  emptyShort: string;
  /** 客户端脚本重算计数时用：仅数量 */
  countShort: (n: number) => string;
  /** 客户端脚本重算计数时用：数量 + 搜索词 */
  countQ: (n: number, q: string) => string;
  /** 二期筛选：朝代行的“全部朝代”标签 */
  dynAll: string;
  /** 二期筛选：朝代按频次收口后，其余归入此标签 */
  dynOther: string;
  /** 二期筛选：排序行标题（屏幕阅读器用） */
  sortLabel: string;
  /** 二期筛选：排序项 —— 书目序（默认） */
  sortDefault: string;
  /** 二期筛选：排序项 —— 章数降序 */
  sortChapters: string;
  /** 二期筛选：排序项 —— 字数降序 */
  sortChars: string;
}

export const booksDict: Record<Locale, BooksDict> = {
  zh: {
    title: (q) => `书库 · 维点图书馆${q ? ' · 搜索：' + q : ''}`,
    heading: '经典书库',
    sub: (n) => `经史子集 · ${n} 部可读 · 选一部，再选一位大师的视角`,
    searchPlaceholder: '搜书名或作者……',
    searchAria: '检索书库',
    clear: '清除',
    count: (n, q, bu) => `${n} 部书${q ? `匹配「${q}」` : ''}${bu ? `· ${bu}` : ''}`,
    emptyTitle: '没有找到匹配的书。',
    emptyHint: '这个搜索词已被记录，会成为后续选书的依据。',
    emptyShort: '换个分类或关键词再试。',
    countShort: (n) => `${n} 部书`,
    countQ: (n, q) => `${n} 部书匹配「${q}」`,
    dynAll: '全部朝代',
    dynOther: '其他',
    sortLabel: '排序',
    sortDefault: '书目序',
    sortChapters: '章数',
    sortChars: '字数',
  },

  'zh-TW': {
    title: (q) => `書庫 · 維點圖書館${q ? ' · 搜尋：' + q : ''}`,
    heading: '經典書庫',
    sub: (n) => `經史子集 · ${n} 部可讀 · 選一部，再選一位大師的視角`,
    searchPlaceholder: '搜書名或作者……',
    searchAria: '檢索書庫',
    clear: '清除',
    count: (n, q, bu) => `${n} 部書${q ? `符合「${q}」` : ''}${bu ? `· ${bu}` : ''}`,
    emptyTitle: '沒有找到符合的書。',
    emptyHint: '這個搜尋詞已被記錄，會成為後續選書的依據。',
    emptyShort: '換個分類或關鍵詞再試。',
    countShort: (n) => `${n} 部書`,
    countQ: (n, q) => `${n} 部書符合「${q}」`,
    dynAll: '全部朝代',
    dynOther: '其他',
    sortLabel: '排序',
    sortDefault: '書目序',
    sortChapters: '章數',
    sortChars: '字數',
  },

  en: {
    title: (q) => `Library · DimensionsCosmos${q ? ' · Search: ' + q : ''}`,
    heading: 'The Classics Library',
    sub: (n) => `Canon, history, masters, collections · ${n} readable volumes · pick a book, then pick a master's eye`,
    searchPlaceholder: 'Search title or author…',
    searchAria: 'Search the library',
    clear: 'Clear',
    count: (n, q, bu) => `${n} ${n === 1 ? 'book' : 'books'}${q ? ` matching “${q}”` : ''}${bu ? ` · ${bu}` : ''}`,
    emptyTitle: 'No matching books.',
    emptyHint: 'Your query has been recorded and will inform future acquisitions.',
    emptyShort: 'Try another category or keyword.',
    countShort: (n) => `${n} ${n === 1 ? 'book' : 'books'}`,
    countQ: (n, q) => `${n} ${n === 1 ? 'book' : 'books'} matching “${q}”`,
    dynAll: 'All eras',
    dynOther: 'Other',
    sortLabel: 'Sort',
    sortDefault: 'Catalogue',
    sortChapters: 'Chapters',
    sortChars: 'Length',
  },

  es: {
    title: (q) => `Biblioteca · DimensionsCosmos${q ? ' · Búsqueda: ' + q : ''}`,
    heading: 'Biblioteca de clásicos',
    sub: (n) => `Clásicos, historia, maestros y obras reunidas · ${n} volúmenes legibles · elige un libro y luego la mirada de un maestro`,
    searchPlaceholder: 'Buscar título o autor…',
    searchAria: 'Buscar en la biblioteca',
    clear: 'Borrar',
    count: (n, q, bu) => `${n} ${n === 1 ? 'libro' : 'libros'}${q ? ` que coinciden con «${q}»` : ''}${bu ? ` · ${bu}` : ''}`,
    emptyTitle: 'No se han encontrado libros.',
    emptyHint: 'Tu búsqueda queda registrada y orientará las próximas incorporaciones.',
    emptyShort: 'Prueba otra categoría u otra palabra clave.',
    countShort: (n) => `${n} ${n === 1 ? 'libro' : 'libros'}`,
    countQ: (n, q) => `${n} ${n === 1 ? 'libro' : 'libros'} que coinciden con «${q}»`,
    dynAll: 'Todas las épocas',
    dynOther: 'Otras',
    sortLabel: 'Ordenar',
    sortDefault: 'Catálogo',
    sortChapters: 'Capítulos',
    sortChars: 'Extensión',
  },
};
