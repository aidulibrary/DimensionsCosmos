// 构建前置守卫：只在「有本地 DB」且「当前 Node 支持 node:sqlite」时才生成数据。
// 目的：Cloudflare Pages 等 CI 环境既没有 data/guji.db、Node 版本也可能 <22.5，
//       此时必须安静跳过，直接复用已入库的 public/data（ch/*.json 已全部提交）。
// 本地要真正重新生成时用：npm run gen（带 --experimental-sqlite）。
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DB = path.join(ROOT, "data", "guji.db");

if (!fs.existsSync(DB)) {
  console.log("[gen] 未发现 data/guji.db —— 跳过生成，直接使用已提交的 public/data");
  process.exit(0);
}

try {
  await import("node:sqlite");
} catch (e) {
  console.warn(
    "[gen] 当前 Node 不支持 node:sqlite（需 22.5+ 且 --experimental-sqlite）—— 跳过生成，使用已提交的 public/data",
  );
  process.exit(0);
}

try {
  await import("./gen-data.mjs");
} catch (e) {
  // CI 上生成失败不应阻断整站构建：已有 JSON 仍可用
  console.warn("[gen] 生成失败，回退到已提交的 public/data：", e?.message || e);
  process.exit(0);
}
