// 词典覆盖率自检：把「界面词缺失 → 静默回落中文原文」变成显式告警。
//
// 背景：书卡上的部类（经/史/子/集）与朝代走 src/i18n/pages/book.ts 的映射，
// 未收录的值不会报错，而是直接回落中文——新增古籍一旦带来新朝代（如「后秦」
// 「南朝梁」），英文/西语站就会静默出现汉字，肉眼很难在 108 部书里发现。
//
// 用法：
//   node scripts/check-i18n-coverage.mjs            # 告警，退出码 0（不阻断构建）
//   node scripts/check-i18n-coverage.mjs --strict   # 有缺口时退出码 1
//
// 依赖：只读 public/data/book-*.json 与 src/i18n/pages/book.ts，不写任何文件。
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const DATA_DIR = path.join(ROOT, "public", "data");
const BOOK_TS = path.join(ROOT, "src", "i18n", "pages", "book.ts");
const STRICT = process.argv.includes("--strict");

const LOCALE_LABEL = { zh: "简中", "zh-TW": "繁中", en: "英文", es: "西语" };

/** 从 openIdx 处的 `{` 起做花括号配对，返回匹配的 `}` 下标 */
function matchBrace(src, openIdx) {
  let depth = 0;
  for (let i = openIdx; i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}") {
      depth--;
      if (depth === 0) return i;
    }
  }
  return -1;
}

/** 取出对象体里所有中文键名（值均为译文，不含中文，无歧义） */
function cjkKeys(body) {
  return new Set(
    [...body.matchAll(/[\u4e00-\u9fff]+(?=\s*:)/g)].map((m) => m[0]),
  );
}

function objectBodyAfter(src, marker) {
  const at = src.indexOf(marker);
  if (at < 0) return null;
  const brace = src.indexOf("{", at);
  if (brace < 0) return null;
  const end = matchBrace(src, brace);
  return end < 0 ? null : src.slice(brace, end + 1);
}

// ── 1. 读词典 ───────────────────────────────────────────────────────────────
if (!fs.existsSync(BOOK_TS)) {
  console.warn("[i18n] 未找到 src/i18n/pages/book.ts，跳过覆盖率自检");
  process.exit(0);
}
const ts = fs.readFileSync(BOOK_TS, "utf-8");

const dynastyBodies = {
  en: objectBodyAfter(ts, "const dynastyEn"),
  es: objectBodyAfter(ts, "const dynastyEs"),
};
const dynastyKeys = {};
for (const [loc, body] of Object.entries(dynastyBodies)) {
  dynastyKeys[loc] = body ? cjkKeys(body) : new Set();
}

// bookDict 顶层按 locale 切块，再取每块的 bu: { ... }
const buKeys = {};
const dictBody = objectBodyAfter(ts, "export const bookDict");
if (dictBody) {
  const starts = [...dictBody.matchAll(/(?:^|\n)\s{2}'?([A-Za-z-]+)'?\s*:\s*\{/g)];
  starts.forEach((m, i) => {
    const loc = m[1];
    const from = m.index + m[0].length - 1;
    const to = i + 1 < starts.length ? starts[i + 1].index : dictBody.length;
    const chunk = dictBody.slice(from, to);
    const buBody = objectBodyAfter(chunk, "bu:");
    buKeys[loc] = buBody ? cjkKeys(buBody) : new Set();
  });
}

const locales = Object.keys(buKeys);
if (!locales.length) {
  console.warn("[i18n] 未能解析 bookDict 的 bu 表，跳过自检（词典结构可能已改动）");
  process.exit(0);
}

// ── 2. 读数据 ───────────────────────────────────────────────────────────────
if (!fs.existsSync(DATA_DIR)) {
  console.warn("[i18n] public/data 不存在，跳过覆盖率自检");
  process.exit(0);
}
const files = fs.readdirSync(DATA_DIR).filter((f) => /^book-\d+\.json$/.test(f));
if (!files.length) {
  console.warn("[i18n] public/data 下没有 book-*.json，跳过覆盖率自检");
  process.exit(0);
}

const books = [];
for (const f of files) {
  try {
    const d = JSON.parse(fs.readFileSync(path.join(DATA_DIR, f), "utf-8"));
    books.push({ title: d.seed_title || f, bu: d.bu || "", dynasty: d.dynasty || "" });
  } catch (_) {
    /* 单本损坏不阻断自检，构建阶段另有 JSON 解析会报错 */
  }
}

const buValues = [...new Set(books.map((b) => b.bu).filter(Boolean))].sort();
const dynastyValues = [...new Set(books.map((b) => b.dynasty).filter(Boolean))].sort();

const byValue = (field, value) => books.filter((b) => b[field] === value);

// ── 3. 比对 ─────────────────────────────────────────────────────────────────
const gaps = []; // { loc, kind, value, sample: [] }

for (const loc of locales) {
  for (const v of buValues) {
    if (!buKeys[loc].has(v)) {
      gaps.push({ loc, kind: "bu", value: v, sample: byValue("bu", v) });
    }
  }
  // 简中/繁中的 dynasty 表为空 ＝ 直出原名，不做比对
  const dk = dynastyKeys[loc];
  if (!dk || dk.size === 0) continue;
  for (const v of dynastyValues) {
    if (!dk.has(v)) {
      gaps.push({ loc, kind: "dynasty", value: v, sample: byValue("dynasty", v) });
    }
  }
}

// ── 4. 报告 ─────────────────────────────────────────────────────────────────
console.log(
  `[i18n] 扫描 ${books.length} 部书 · 部类 ${buValues.length} 种 · 朝代 ${dynastyValues.length} 种 · 语言 ${locales.length} 种`,
);

if (!gaps.length) {
  console.log("[i18n] 覆盖率 100%：部类与朝代在全部语言均有译文");
  process.exit(0);
}

const KIND_LABEL = { bu: "部类", dynasty: "朝代" };
for (const loc of locales) {
  const mine = gaps.filter((g) => g.loc === loc);
  if (!mine.length) continue;
  const names = mine.map((g) => `${g.value}（${g.sample.length} 部）`).join("、");
  console.warn(`[i18n] ${LOCALE_LABEL[loc] || loc} 缺 ${mine.length} 项：${names}`);
  for (const g of mine) {
    const titles = g.sample.map((b) => b.title).slice(0, 3).join("、");
    const more = g.sample.length > 3 ? " 等" : "";
    console.warn(
      `[i18n]   - ${KIND_LABEL[g.kind]}「${g.value}」影响：${titles}${more}`,
    );
  }
  const patch = mine
    .map((g) => `  ${g.value}: '',`)
    .join("\n");
  console.warn(
    `[i18n] 补法：在 src/i18n/pages/book.ts 的 ${
      mine[0].kind === "dynasty" ? (loc === "en" ? "dynastyEn" : "dynastyEs") : `${loc} 的 bu`
    } 中加：\n${patch}`,
  );
}

console.warn(
  `[i18n] 共 ${gaps.length} 处会回落中文原文（已告警，不阻断构建）。加 --strict 可在有缺口时失败。`,
);
process.exit(STRICT ? 1 : 0);
