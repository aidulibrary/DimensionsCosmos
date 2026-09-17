export interface Chapter {
  id: number;
  title: string;
  text: string;
  excerpt: string;
  chars: number;
}

export interface GuideContent {
  structure?: string;
  keywords?: { term: string; frequency?: number; meaning: string }[];
  suspension_of_judgment?: string;
  personal_application?: string;
  faces?: { name: string; insight: string; key_points?: string[] }[];
  deep_dive?: { face_name: string; analysis: string };
  coup_de_grace?: string;
  motif_parallels?: {
    motif: string;
    chinese_source?: string;
    western_source?: string;
    comparison: string;
  }[];
  ironies_and_paradoxes?: string[];
  cross_civilization_insight?: string;
  inner_resonance?: string;
  actionable_insight?: string;
  conscience_check?: string;
  today_practice?: string;
  classification?: { type: string; sub_type: string; rationale: string };
  unity?: { one_sentence_summary: string; paragraph_summary: string };
  outline?: { section: string; key_argument: string }[];
  key_terms?: { term: string; author_meaning: string }[];
  key_propositions?: string[];
  judgment?: { agree: string; disagree_reason: string; suspension: string };
  explain_to_12_year_old?: string;
  gaps_found?: string[];
  re_read_insight?: string;
  analogy?: string;
  key_questions?: string[];
  exposed_assumptions?: string[];
  reductio_ad_absurdum?: string;
  maieutic_insight?: string;
  historical_situation?: string;
  what_author_fought_against?: string;
  excluded_voices?: string[];
  thinking_without_banisters?: string;
  civilization_phase?: string;
  asabiyyah_analysis?: string;
  causal_chain?: { cause: string; effect: string }[];
  badawa_vs_hadara?: { nomadic_view: string; settled_view: string };
  lenses_used?: { name: string; era: string; angle: string }[];
  per_lens_reading?: Record<string, string>;
  tensions_and_syntheses?: string[];
  emergent_insight?: string;
  [key: string]: unknown;
}

export interface Guide {
  method_id: string;
  generated_at: string;
  model_used: string;
  content: GuideContent;
}

export interface BookMeta {
  id: number;
  seed_title: string;
  ws_title: string | null;
  bu: string;
  author: string;
  dynasty: string;
  status: string;
  wikidata_qid: string | null;
  fetched_at: string | null;
  chapter_count: number;
  slug: string;
  ok: boolean;
  chapters: Chapter[];
  guides: Guide[];
}

export interface IndexData {
  generatedAt: string;
  total: number;
  ok: number;
  taxonomy: { name: string; parent: string | null }[];
  byBu: Record<string, BookMeta[]>;
  works: BookMeta[];
  guidesCount: number;
}

export function loadIndex(): IndexData | null {
  try {
    const raw = require("fs").readFileSync(
      require("path").join(
        require("process").cwd(),
        "public",
        "data",
        "index.json",
      ),
      "utf-8",
    );
    return JSON.parse(raw) as IndexData;
  } catch {
    return null;
  }
}

export function loadBookSync(id: number): BookMeta | null {
  try {
    const raw = require("fs").readFileSync(
      require("path").join(process.cwd(), "public", "data", `book-${id}.json`),
      "utf-8",
    );
    return JSON.parse(raw) as BookMeta;
  } catch {
    return null;
  }
}

const METHODS_INFO: Record<
  string,
  {
    name_zh: string;
    name_en: string;
    era: string;
    tags: string[];
    summary: string;
    icon: string;
    price: number;
    free: boolean;
  }
> = {
  zhuxi: {
    name_zh: "朱熹读书法",
    name_en: "Zhu Xi's Reading Method",
    era: "南宋 · 1130–1200",
    tags: ["循序渐进", "熟读精思", "虚心涵泳", "切己体察"],
    summary: "逐字逐句、反复涵泳，把一本书读到「熟」而非「多」。",
    icon: "📖",
    price: 0,
    free: true,
  },
  feynman: {
    name_zh: "费曼教学法",
    name_en: "The Feynman Technique",
    era: "20世纪 · 美国",
    tags: ["白话解释", "发现缺口", "日常类比"],
    summary: "如果你不能向 12 岁的孩子解释清楚，说明你自己也没懂。",
    icon: "⚛️",
    price: 3.9,
    free: false,
  },
  socratic: {
    name_zh: "苏格拉底诘问法",
    name_en: "The Socratic Method",
    era: "古希腊 · 469–399 BC",
    tags: ["追问定义", "揭露矛盾", "助产术"],
    summary: "不告诉你答案，通过一连串问题让你自己发现。",
    icon: "🏛️",
    price: 3.9,
    free: false,
  },
  adler: {
    name_zh: "阿德勒分析阅读",
    name_en: "Adler's Analytical Reading",
    era: "20世纪 · 美国",
    tags: ["检视阅读", "分析阅读", "主题阅读"],
    summary: "像外科手术一样精确理解一本书的论证结构。",
    icon: "🔍",
    price: 5.9,
    free: false,
  },
  qianzhongshu: {
    name_zh: "钱锺书打通法",
    name_en: "Qian Zhongshu's Cross-Reference",
    era: "20世纪 · 中国",
    tags: ["打通", "中西互参", "比较文学"],
    summary: "让中西古今所有相关文本在同一个对话现场互相解释。",
    icon: "🌐",
    price: 5.9,
    free: false,
  },
  sushi: {
    name_zh: "苏轼八面受敌",
    name_en: "Su Shi's Eight-Front Assault",
    era: "北宋 · 1037–1101",
    tags: ["每次一意", "分而治之", "多角度"],
    summary: "一本书读八遍，每遍只取一个角度——每次一种收获。",
    icon: "🎯",
    price: 3.9,
    free: false,
  },
  wangyangming: {
    name_zh: "王阳明心学法",
    name_en: "Wang Yangming's Mind-Study",
    era: "明 · 1472–1529",
    tags: ["知行合一", "致良知", "事上磨炼"],
    summary: "读书不是为了记住，是为了让心与理合一。",
    icon: "💡",
    price: 3.9,
    free: false,
  },
  arendt: {
    name_zh: "阿伦特理解法",
    name_en: "Arendt's Understanding Method",
    era: "20世纪 · 德国",
    tags: ["理解≠知识", "没有扶手的思想", "公共性"],
    summary: "不去解释或解决，而是「理解」——没有任何意识形态拐杖。",
    icon: "🕯️",
    price: 5.9,
    free: false,
  },
  ibn_khaldun: {
    name_zh: "伊本·赫勒敦历史透镜",
    name_en: "Ibn Khaldun's Historical Lens",
    era: "14世纪 · 突尼斯",
    tags: ["阿萨比亚", "文明兴衰", "因果分析"],
    summary: "透过群体凝聚力和文明生命周期看一切文本。",
    icon: "🕌",
    price: 5.9,
    free: false,
  },
  multimodal: {
    name_zh: "多维透镜",
    name_en: "Multi-Dimensional Lens",
    era: "当代 · AI-Native",
    tags: ["多视角", "认知多样性", "对比融合"],
    summary: "三位大师同时解读，在一个屏幕上看到文明的对话。",
    icon: "🔮",
    price: 12.9,
    free: false,
  },
};

export function getMethodInfo(methodId: string) {
  return (
    METHODS_INFO[methodId] ?? {
      name_zh: methodId,
      name_en: methodId,
      era: "",
      tags: [],
      summary: "",
      icon: "📚",
      price: 3.9,
      free: false,
    }
  );
}

export function getAllMethods() {
  return Object.entries(METHODS_INFO).map(([id, info]) => ({ id, ...info }));
}
