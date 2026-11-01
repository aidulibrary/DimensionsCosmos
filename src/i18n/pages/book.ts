import type { Locale } from '../config';

/**
 * 书卡与书库的界面词（不含书名本身）。
 * 书名与作者属原典专名，三语版本一律保留汉字原文——这是国际汉学出版物的通行处理
 * （如 Library of Chinese Humanities 保留原题并附译名）；英文题名映射列入 B2。
 */
export interface BookDict {
  /** 部类（四部分类法） */
  bu: Record<string, string>;
  /** 朝代 */
  dynasty: Record<string, string>;
  /** {n} 种解读 */
  guides: (n: number) => string;
  read: string;
  readAria: (title: string) => string;
  /** 无解读时的占位 */
  fallback: string;
  all: string;
}

const dynastyEn: Record<string, string> = {
  先秦: 'Pre-Qin', 春秋: 'Spring and Autumn', 战国: 'Warring States', 秦: 'Qin',
  西汉: 'Western Han', 东汉: 'Eastern Han', 三国: 'Three Kingdoms',
  西晋: 'Western Jin', 东晋: 'Eastern Jin', 南朝宋: 'Liu Song',
  北齐: 'Northern Qi', 北魏: 'Northern Wei', 隋: 'Sui', 唐: 'Tang',
  五代: 'Five Dynasties', 北宋: 'Northern Song', 南宋: 'Southern Song',
  元: 'Yuan', 明: 'Ming', 清: 'Qing', 近现代: 'Modern', 佚名: 'Anonymous',
};

// 西语朝代名沿用汉学界通行译法（Primaveras y Otoños / Reinos Combatientes 等），
// 比音译更易被西语读者识别；卡片宽度有限，一律取短形式。
const dynastyEs: Record<string, string> = {
  先秦: 'Pre-Qin', 春秋: 'Primaveras y Otoños', 战国: 'Reinos Combatientes', 秦: 'Qin',
  西汉: 'Han Occidental', 东汉: 'Han Oriental', 三国: 'Tres Reinos',
  西晋: 'Jin Occidental', 东晋: 'Jin Oriental', 南朝宋: 'Liu Song',
  北齐: 'Qi del Norte', 北魏: 'Wei del Norte', 隋: 'Sui', 唐: 'Tang',
  五代: 'Cinco Dinastías', 北宋: 'Song del Norte', 南宋: 'Song del Sur',
  元: 'Yuan', 明: 'Ming', 清: 'Qing', 近现代: 'Época moderna', 佚名: 'Anónimo',
};

export const bookDict: Record<Locale, BookDict> = {
  zh: {
    bu: { 经部: '经部', 史部: '史部', 子部: '子部', 集部: '集部' },
    dynasty: {},
    guides: (n) => `${n} 种解读`,
    read: '读原文',
    readAria: (t) => `阅读《${t}》原文`,
    fallback: '已有 AI 解读',
    all: '全部',
  },
  'zh-TW': {
    bu: { 经部: '經部', 史部: '史部', 子部: '子部', 集部: '集部' },
    dynasty: {},
    guides: (n) => `${n} 種解讀`,
    read: '讀原文',
    readAria: (t) => `閱讀《${t}》原文`,
    fallback: '已有 AI 解讀',
    all: '全部',
  },
  en: {
    bu: { 经部: 'Canon', 史部: 'History', 子部: 'Masters', 集部: 'Collections' },
    dynasty: dynastyEn,
    guides: (n) => (n === 1 ? '1 reading' : `${n} readings`),
    read: 'Read the source',
    readAria: (t) => `Read the source text of ${t}`,
    fallback: 'AI commentary available',
    all: 'All',
  },
  es: {
    bu: { 经部: 'Clásicos', 史部: 'Historia', 子部: 'Maestros', 集部: 'Obras reunidas' },
    dynasty: dynastyEs,
    guides: (n) => (n === 1 ? '1 lectura' : `${n} lecturas`),
    read: 'Leer el original',
    readAria: (t) => `Leer el texto original de ${t}`,
    fallback: 'Comentario de IA disponible',
    all: 'Todos',
  },
};
