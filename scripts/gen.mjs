// 构建前置守卫：有本地 DB 就真正生成数据；没有 DB（Cloudflare/CI）才复用已入库的 public/data。
//
// 历史坑：旧版守卫用 import("node:sqlite") 探测能力，Node 22.12 不带 flag 会直接抛错，
// 于是本地每次 build 都静默 exit(0) 跳过生成，长期复用一份空产物（0 书 0 章）并部署上线。
// 现在：有 DB 时必须真跑生成，生成失败或产物为空一律硬失败，绝不允许空数据通过构建。
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DB = path.join(ROOT, "data", "guji.db");
const INDEX = path.join(ROOT, "public", "data", "index.json");

const readIndexStats = () => {
  try {
    const j = JSON.parse(fs.readFileSync(INDEX, "utf-8"));
    const works = Array.isArray(j.works) ? j.works : [];
    const chapters = works.reduce((s, w) => s + (w.chapter_count || 0), 0);
    return { ok: works.filter((w) => w.ok).length, chapters };
  } catch {
    return { ok: 0, chapters: 0 };
  }
};

const fail = (msg) => {
  console.error(`[gen] ${msg}`);
  process.exit(1);
};

// 1) 无 DB：CI 环境，只能复用已提交的 public/data，但必须确认它不是空壳
if (!fs.existsSync(DB)) {
  const s = readIndexStats();
  if (!s.ok || !s.chapters) {
    fail(
      `未发现 data/guji.db，且已提交的 public/data 为空（可读 ${s.ok} 部 / ${s.chapters} 章）——无法构建出可阅读站点`,
    );
  }
  console.log(
    `[gen] 未发现 data/guji.db —— 复用已提交的 public/data（${s.ok} 部 / ${s.chapters} 章）`,
  );
  process.exit(0);
}

// 2) 有 DB：必须真正生成（node:sqlite 在 Node 22.5+ 需要 --experimental-sqlite）
const r = spawnSync(
  process.execPath,
  ["--experimental-sqlite", path.join(ROOT, "scripts", "gen-data.mjs")],
  { cwd: ROOT, stdio: "inherit", env: process.env },
);

if (r.status !== 0) {
  fail(`数据生成失败（退出码 ${r.status}）—— 拒绝使用可疑/陈旧的 public/data 继续构建`);
}

// 3) 产物校验：空产物一律拦下
const s = readIndexStats();
if (!s.ok || !s.chapters) {
  fail(`生成后产物为空（可读 ${s.ok} 部 / ${s.chapters} 章）—— 拒绝构建`);
}

console.log(`[gen] 产物校验通过：可读 ${s.ok} 部 / ${s.chapters} 章`);
