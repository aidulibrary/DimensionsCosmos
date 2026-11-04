import type { Locale } from '../config';

/**
 * 首页首屏引导文案（UX-8 增补）：hero 主 CTA + 「从这里开始」三步条。
 *
 * 为什么独立成文件而不并进 home.ts：home.ts 是双机并行改动的高冲突文件，
 * 引导文案自成一块、与其余首页文案无耦合，独立文件可把 rebase 冲突面降到零。
 *
 * 翻译口径：四语均为人工撰写（非机器硬译），不是 featured 数据侧的 reason 文案——
 * 后者必须带 reviewed 白名单才放行，本文件属前端自带 UI 文案。
 */
export interface StartStep {
  /** 步骤序号前缀，如「第一步」 */
  n: string;
  title: string;
  desc: string;
  cta: string;
}

export interface StartDict {
  /** 首屏主 CTA（backlog UX-8 验收项：3 秒内可见「开始阅读」主按钮） */
  heroPrimary: string;
  heroSecondary: string;
  /** 主 CTA 下方的分流向导，指向精选区锚点 */
  heroHint: string;
  kicker: string;
  title: string;
  sub: string;
  steps: StartStep[];
}

export const start: Record<Locale, StartDict> = {
  zh: {
    heroPrimary: '开始阅读 →',
    heroSecondary: '先看大师怎么读',
    heroHint: '不知道从哪本开始？看精选',
    kicker: '三步读完第一本',
    title: '从这里开始',
    sub: '不用先懂古籍学。选一部、选一位大师、读一章——第一章通常不超过五分钟。',
    steps: [
      { n: '第一步', title: '选一部', desc: '112 部里挑一本你听说过的；拿不定主意就往下看精选。', cta: '去书库挑 →' },
      { n: '第二步', title: '选一位大师', desc: '朱熹带你涵泳，费曼把话说明白，苏格拉底追着你问。', cta: '看大师怎么读 →' },
      { n: '第三步', title: '读一章', desc: '原文与解读并排，读完就能留下一段自己的批注。', cta: '直接开读 →' },
    ],
  },
  'zh-TW': {
    heroPrimary: '開始閱讀 →',
    heroSecondary: '先看大師怎麼讀',
    heroHint: '不知道從哪本開始？看精選',
    kicker: '三步讀完第一本',
    title: '從這裡開始',
    sub: '不必先懂古籍學。選一部、選一位大師、讀一章——第一章通常不超過五分鐘。',
    steps: [
      { n: '第一步', title: '選一部', desc: '112 部裡挑一本你聽說過的；拿不定主意就往下看精選。', cta: '去書庫挑 →' },
      { n: '第二步', title: '選一位大師', desc: '朱熹帶你涵泳，費曼把話說明白，蘇格拉底追著你問。', cta: '看大師怎麼讀 →' },
      { n: '第三步', title: '讀一章', desc: '原文與解讀並排，讀完就能留下一段自己的批註。', cta: '直接開讀 →' },
    ],
  },
  en: {
    heroPrimary: 'Start reading →',
    heroSecondary: 'See how a master reads',
    heroHint: 'Not sure which book? Browse the picks',
    kicker: 'THREE STEPS TO YOUR FIRST BOOK',
    title: 'Start here',
    sub: 'No background in classical Chinese required. Pick a book, pick a master, read one chapter — the first chapter usually takes under five minutes.',
    steps: [
      { n: 'Step 1', title: 'Pick a book', desc: 'Choose one you have heard of, or let the picks below choose for you.', cta: 'Browse the library →' },
      { n: 'Step 2', title: 'Pick a master', desc: 'Zhu Xi reads line by line, Feynman puts it in plain words, Socrates keeps asking you why.', cta: 'See the methods →' },
      { n: 'Step 3', title: 'Read a chapter', desc: 'Text and commentary side by side; finish with a note of your own.', cta: 'Read now →' },
    ],
  },
  es: {
    heroPrimary: 'Empezar a leer →',
    heroSecondary: 'Ver cómo lee un maestro',
    heroHint: '¿No sabes por dónde empezar? Mira la selección',
    kicker: 'TRES PASOS HASTA TU PRIMER LIBRO',
    title: 'Empieza aquí',
    sub: 'No hace falta saber chino clásico. Elige un libro, elige un maestro y lee un capítulo: el primero suele tomar menos de cinco minutos.',
    steps: [
      { n: 'Paso 1', title: 'Elige un libro', desc: 'Toma uno que hayas oído nombrar, o deja que la selección elija por ti.', cta: 'Ir a la biblioteca →' },
      { n: 'Paso 2', title: 'Elige un maestro', desc: 'Zhu Xi lee verso a verso, Feynman lo dice en palabras llanas, Sócrates te pregunta por qué.', cta: 'Ver los métodos →' },
      { n: 'Paso 3', title: 'Lee un capítulo', desc: 'Texto y comentario en paralelo; al terminarlo puedes dejar tu propia nota.', cta: 'Leer ahora →' },
    ],
  },
};
