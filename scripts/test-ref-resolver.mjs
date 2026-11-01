/**
 * /r 解析路由逻辑自测（无浏览器）：
 * 从 dist/r/index.html 抽出内联脚本，用最小 DOM/location 桩跑一遍，
 * 断言合法 URN 跳到阅读页、非法 URN 给出明确错误、越界章号被拦下。
 */
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const ROOT = path.resolve(import.meta.dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "dist", "r", "index.html"), "utf8");
const m = html.match(/<script[^>]*>([\s\S]*?)<\/script>/);
if (!m) throw new Error("dist/r/index.html 中未找到内联脚本");
const code = m[1];

const index = JSON.parse(
  fs.readFileSync(path.join(ROOT, "dist", "data", "ref-index.json"), "utf8"),
);

function run(search, hash = "") {
  const out = { urn: "", msg: "", msgClass: "", target: null, canon: null };
  const els = {
    urn: { textContent: "", className: "" },
    msg: { textContent: "", className: "" },
    jump: { href: "", hidden: true },
  };
  const canon = { href: "" };
  const sandbox = {
    document: {
      getElementById: (id) => els[id],
      querySelector: () => canon,
    },
    location: {
      search,
      hash,
      replace: (u) => (out.target = u),
    },
    fetch: (url) => {
      if (!url.includes("ref-index.json")) throw new Error("unexpected fetch " + url);
      return { ok: true, json: async () => index };
    },
    setTimeout: (fn) => fn(),
    encodeURIComponent,
    URLSearchParams,
    location_: null,
  };
  const vm_ = vm;
  vm_.createContext(sandbox);
  vm_.runInContext(code, sandbox);
  return new Promise((r) => setTimeout(() => r({ ...out }), 30)).then((res) => ({
    ...res,
    urnText: els.urn.textContent,
    msg: els.msg.textContent,
    msgClass: els.msg.className,
    jumpHref: els.jump.href,
    canon: canon.href,
  }));
}

const cases = [
  ["?urn=dc:Q276015/c002", "", "dc:Q276015/c002", "跳转"],
  ["?urn=dc%3AQ276015%2Fc002%2Fb003", "", "dc:Q276015/c002/b003", "块级"],
  ["", "#dc:Q276015/c002", "dc:Q276015/c002", "hash 形式"],
  ["?urn=dc:Q276015/c999", "", "dc:Q276015/c999", "章号越界"],
  ["?urn=dc:Q999999/c001", "", "dc:Q999999/c001", "未知书"],
  ["?urn=bad/ref", "", "bad/ref", "格式错误"],
  ["", "", "", "缺参数"],
];

let fail = 0;
for (const [search, hash, label, desc] of cases) {
  const r = await run(search, hash);
  const ok = r.target
    ? r.target.startsWith("/books/") && r.target.includes("#" + label)
    : r.msgClass === "err";
  const detail = r.target ? `→ ${r.target}` : `✗ ${r.msg}`;
  if (!ok) fail++;
  console.log(`${ok ? "PASS" : "FAIL"}  [${desc}] ${search || hash || "(空)"}  ${detail}`);
  if (r.canon && !r.canon.endsWith(r.target)) {
    console.log("      canonical 未同步：", r.canon);
    fail++;
  }
}
console.log(fail === 0 ? "\n全部通过" : `\n${fail} 项失败`);
process.exit(fail === 0 ? 0 : 1);
