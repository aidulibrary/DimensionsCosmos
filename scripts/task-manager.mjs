#!/usr/bin/env node
/**
 * task-manager.mjs
 * DimensionsCosmos 任务管理 CLI
 *
 * 用法：
 *   node scripts/task-manager.mjs status       → 进度报告
 *   node scripts/task-manager.mjs next          → 下一步行动
 *   node scripts/task-manager.mjs phase M2      → 某阶段详情
 *   node scripts/task-manager.mjs handoff M1.1  → 生成本地AI派发模板
 *   node scripts/task-manager.mjs blockers      → 列出所有阻塞项
 *   node scripts/task-manager.mjs done M0.1     → 标记任务完成
 *   node scripts/task-manager.mjs export        → 导出 JSON 到 data/tasks.json
 */

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const ROOT = join(__dirname, "..");
const PLAN_PATH = join(ROOT, "里程碑规划_任务分配.md");
const STATE_PATH = join(ROOT, "public", "data", "tasks-state.json");

// ---- 解析里程碑文档 ----
function parsePlan(md) {
  const phases = [];
  const current = { tasks: [] };
  let phase = null;
  let inTable = false;
  let subPhase = null;

  const lines = md.split("\n");

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Phase header: ## M0 · xxx
    const pm = line.match(/^## M(\d+[A-Z]?)\s*[·]\s*(.+)/);
    if (pm) {
      if (phase) phases.push({ ...phase, tasks: [...phase.tasks] });
      phase = { id: `M${pm[1]}`, title: pm[2].trim(), tasks: [] };
      subPhase = null;
      inTable = false;
      continue;
    }

    // Sub-phase: ### 5A · xxx
    const sm = line.match(/^### (\d+[A-Z])\s*[·]\s*(.+)/);
    if (sm) {
      subPhase = { id: `${sm[1]}`, title: sm[2].trim() };
      inTable = false;
      continue;
    }

    // Table header
    if (line.includes("| #") && line.includes("任务") && phase) {
      inTable = true;
      continue;
    }
    // Table separator
    if (inTable && line.match(/^\|\s*-+\s*\|/)) continue;

    // Task row
    if (inTable && phase) {
      const m = line.match(/^\|\s*([\d]+[A-Za-z]?(?:\.[\d]+)?)\s*\|(.+)\|/);
      if (m) {
        const cols = line.split("|").map((c) => c.trim());
        if (cols.length >= 4) {
          const taskId = cols[1];
          const title = cols[2];
          const executor = cols[3] || "";
          const desc = cols[4] || "";

          const task = {
            id: taskId,
            phase: phase.id,
            subPhase: subPhase?.id ?? null,
            title: cleanText(title),
            executor: classifyExecutor(executor),
            description: cleanText(desc),
            status: "todo",
            dependsOn: extractDeps(taskId, phases),
          };

          phase.tasks.push(task);
        }
      }
    }
  }

  if (phase) phases.push({ ...phase, tasks: [...phase.tasks] });

  return phases;
}

function cleanText(s) {
  return s
    .replace(/\*\*/g, "")
    .replace(/`/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .trim();
}

function classifyExecutor(raw) {
  if (raw.includes("用户手动") || raw.includes("👤")) return "👤用户";
  if (raw.includes("命令行") || raw.includes("用户本地") || raw.includes("🤖"))
    return "🤖命令行";
  if (raw.includes("Claude") || raw.includes("🧠")) return "🧠Claude";
  if (raw.includes("GitHub Actions")) return "🤖Actions";
  return "👤用户";
}

function extractDeps(taskId, phases) {
  const deps = [];
  const num = parseFloat(taskId);
  if (num > 0.1) deps.push(`${(num - 0.1).toFixed(1)}`);
  return deps;
}

// ---- 状态持久化 ----
function loadState() {
  if (existsSync(STATE_PATH)) {
    return JSON.parse(readFileSync(STATE_PATH, "utf-8"));
  }
  return {};
}

function saveState(state) {
  writeFileSync(STATE_PATH, JSON.stringify(state, null, 2), "utf-8");
}

function mergeState(phases, state) {
  for (const p of phases) {
    for (const t of p.tasks) {
      if (state[t.id]) t.status = state[t.id];
    }
  }
}

// ---- 报告生成 ----
function progressBar(done, total) {
  const pct = total ? Math.round((done / total) * 100) : 0;
  const bars = Math.round((pct / 100) * 10);
  return "█".repeat(bars) + "░".repeat(10 - bars) + ` ${pct}%`;
}

function report(phases) {
  console.log("📊 DimensionsCosmos 项目进度\n");
  for (const p of phases) {
    const tasks = p.tasks;
    const done = tasks.filter((t) => t.status === "done").length;
    const blocked = tasks.filter((t) => t.status === "blocked").length;
    const total = tasks.length;
    const blockedMsg = blocked ? ` ⚠️ ${blocked} blocked` : "";
    console.log(
      `  ${p.id.padEnd(6)} ${p.title.padEnd(16)} ${progressBar(done, total)}  ${done}/${total} done${blockedMsg}`,
    );
  }
  console.log("");
}

function nextActions(phases) {
  const state = loadState();
  mergeState(phases, state);

  const allTasks = phases.flatMap((p) =>
    p.tasks.map((t) => ({ ...t, phase: p.id })),
  );
  const blockedIds = new Set(
    allTasks.filter((t) => t.status === "blocked").map((t) => t.id),
  );
  const doneIds = new Set(
    allTasks.filter((t) => t.status === "done").map((t) => t.id),
  );

  // 优先：解除 blocked 的依赖
  const unblockTasks = [];
  for (const t of allTasks.filter((t) => t.status === "blocked")) {
    const blocking = t.dependsOn.filter((d) => !doneIds.has(d));
    if (blocking.length === 0) {
      unblockTasks.push(t);
    }
  }

  // 其次：todo 任务中依赖全满足的
  const todoTasks = allTasks.filter(
    (t) =>
      t.status === "todo" &&
      t.dependsOn.every(
        (d) => doneIds.has(d) || !allTasks.some((x) => x.id === d),
      ),
  );

  const candidates = [...unblockTasks, ...todoTasks].slice(0, 3);

  console.log("📌 下一步行动\n");
  for (const t of candidates) {
    const icon = t.status === "blocked" ? "🔓 可解除阻塞" : "";
    console.log(`  [${t.id}] ${icon} ${t.title}`);
    console.log(
      `     执行方: ${t.executor}  |  ${t.description.substring(0, 60)}...`,
    );
    console.log("");
  }

  if (candidates.length === 0) {
    console.log("  🎉 所有任务已完成或等待人工确认！");
  }
}

function phaseDetail(phases, phaseId) {
  const phase = phases.find((p) => p.id === phaseId || p.id === `M${phaseId}`);
  if (!phase) {
    console.log(`❌ 未找到阶段 ${phaseId}`);
    return;
  }

  const state = loadState();
  mergeState(phases, state);

  console.log(`\n📋 ${phase.id} · ${phase.title}\n`);
  for (const t of phase.tasks) {
    const icon =
      t.status === "done"
        ? "✅"
        : t.status === "blocked"
          ? "🚫"
          : t.status === "doing"
            ? "🔄"
            : "⬜";
    console.log(`  ${icon} [${t.id}] ${t.title}`);
    console.log(
      `     执行方: ${t.executor}  |  ${t.description.substring(0, 80)}`,
    );
    if (t.dependsOn.length) console.log(`     依赖: ${t.dependsOn.join(", ")}`);
    console.log("");
  }
}

function handoffTemplate(phases, taskId) {
  const allTasks = phases.flatMap((p) =>
    p.tasks.map((t) => ({ ...t, phase: p.id })),
  );
  const task = allTasks.find((t) => t.id === taskId);
  if (!task) {
    console.log(`❌ 未找到任务 ${taskId}`);
    return;
  }

  console.log("\n--- 复制以下内容发送给本地 AI ---\n");
  console.log(`@Marvis / @本地AI\n`);
  console.log(`请执行 DimensionsCosmos 任务 [${task.id}]：${task.title}\n`);
  console.log(`操作指引：${task.description}\n`);
  console.log(`完成后请在 \`里程碑规划_任务分配.md\` 中标记为 ✅，或运行：`);
  console.log(`  node scripts/task-manager.mjs done ${task.id}\n`);
  console.log("--- 复制以上内容 ---\n");
}

function listBlockers(phases) {
  const allTasks = phases.flatMap((p) =>
    p.tasks.map((t) => ({ ...t, phase: p.id })),
  );
  const doneIds = new Set(
    allTasks.filter((t) => t.status === "done").map((t) => t.id),
  );
  const blockers = allTasks.filter((t) => t.status === "blocked");

  console.log("\n🚫 阻塞项清单\n");
  if (blockers.length === 0) {
    console.log("  ✅ 当前无阻塞项");
    return;
  }
  for (const t of blockers) {
    const blocking = t.dependsOn.filter((d) => !doneIds.has(d));
    console.log(`  🚫 [${t.id}] ${t.title}`);
    console.log(`     等待依赖: ${blocking.join(", ")}`);
    console.log(`     执行方: ${t.executor}`);
    console.log("");
  }
}

function markDone(phases, taskId) {
  const allTasks = phases.flatMap((p) =>
    p.tasks.map((t) => ({ ...t, phase: p.id })),
  );
  const task = allTasks.find((t) => t.id === taskId);
  if (!task) {
    console.log(`❌ 未找到任务 ${taskId}`);
    return;
  }

  const state = loadState();
  mergeState(phases, state);
  state[taskId] = "done";
  saveState(state);
  console.log(`\n✅ [${taskId}] ${task.title} → 已标记为完成\n`);

  // 检查是否有依赖解除
  const blockedTasks = allTasks.filter((t) => state[t.id] === "blocked");
  const unblocked = blockedTasks.filter((t) =>
    t.dependsOn.every((d) => state[d] === "done"),
  );
  if (unblocked.length) {
    console.log("🔓 以下任务依赖已解除，可继续：");
    for (const t of unblocked) {
      console.log(`  → [${t.id}] ${t.title}`);
      state[t.id] = "todo";
    }
    saveState(state);
  }
}

function exportJSON(phases) {
  const state = loadState();
  mergeState(phases, state);

  const output = {
    generated_at: new Date().toISOString(),
    phases: phases.map((p) => ({
      id: p.id,
      title: p.title,
      tasks: p.tasks.map((t) => ({
        id: t.id,
        title: t.title,
        executor: t.executor,
        status: t.status,
        dependsOn: t.dependsOn,
        description: t.description,
      })),
    })),
  };

  writeFileSync(
    join(ROOT, "public", "data", "tasks.json"),
    JSON.stringify(output, null, 2),
    "utf-8",
  );
  console.log("✅ 已导出到 public/data/tasks.json");
}

// ---- Main ----
function main() {
  const md = readFileSync(PLAN_PATH, "utf-8");
  const phases = parsePlan(md);
  const state = loadState();
  mergeState(phases, state);

  const cmd = process.argv[2];
  const arg = process.argv[3];

  switch (cmd) {
    case "status":
    case "s":
      report(phases);
      break;
    case "next":
    case "n":
      nextActions(phases);
      break;
    case "phase":
    case "p":
      phaseDetail(phases, arg);
      break;
    case "handoff":
    case "h":
      handoffTemplate(phases, arg);
      break;
    case "blockers":
    case "b":
      listBlockers(phases);
      break;
    case "done":
    case "d":
      markDone(phases, arg);
      break;
    case "export":
    case "e":
      exportJSON(phases);
      break;
    default:
      console.log(`
🧭 DimensionsCosmos · 任务管理 CLI

用法: node scripts/task-manager.mjs <command> [arg]

命令:
  status, s          查看项目进度报告
  next, n            获取下一步行动建议
  phase, p <Mx>      查看某阶段详情（如: p M2）
  handoff, h <id>    生成本地AI派发模板（如: h M0.7）
  blockers, b        列出所有阻塞项
  done, d <id>       标记任务完成（如: d M0.1）
  export, e          导出任务数据到 public/data/tasks.json
      `);
  }
}

main();
