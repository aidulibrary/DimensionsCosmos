# DimensionsCosmos · Marvis 任务手册 v1.0

> **使用者**：腾讯 Marvis（本地 AI 操作助手）  
> **项目负责人**：用户  
> **派发日期**：2026-09-17  
> **适用阶段**：M0 内容底座 + M2 质量验证

---

## 一、项目是什么（一句话）

**维点图书馆（DimensionsCosmos）** = 把古籍 / 公版书 / 开放教材导入 AI，用不同大师的阅读方法（朱熹、费曼、苏格拉底式提问……）自动生成解读，按篇售卖，最终做成「全球可售卖 AI 解读引擎」。

---

## 二、当前版本状态

### 已完成（无需你再做）

- ✅ Astro 前端 32 个页面构建通过（`npm run build` ✓）
- ✅ 书库首页、书详情页、方法选择器、付费墙组件全部就位
- ✅ Cloudflare Worker 鉴权脚本（`workers/token-auth.js`）
- ✅ Global CSS 全局统一样式
- ✅ GitHub Actions 全自动管线（抓取→AI→构建→部署）
- ✅ 多语 Wikisource 抓取脚本（12 语种）
- ✅ 任务管理 CLI（`node scripts/task-manager.mjs`）

### 正在推进

- 🔄 M0 内容底座：下载脚本就绪，文件尚未全部到位

### 阻塞卡点

- ⚠️ M1（AI 解读生成）：缺 API Key（需注册 Groq 免费账号）
- ⚠️ M2（预览 + 部署）：需本地逐页检查 + Cloudflare Pages 连接仓库
- ⚠️ M3（付费闭环）：缺面包多收款账号

---

## 三、你的任务范围（限定边界）

你只负责 **可直接操作的本地任务**，不涉及代码编写和架构决策。以下是本次派发给你的任务清单，按优先级排列。

> **执行原则**：每完成一项，立刻汇报格式为 `[任务ID] 完成` 或 `[任务ID] 遇到问题: xxx`。  
> **绝对不要**：修改任何代码文件、执行 `git push`、安装未列出的依赖包。

---

### 任务 M0.7 · 放置殆知阁全集 ⚡

| 属性     | 值       |
| -------- | -------- |
| 优先级   | 🔴 最高  |
| 建议耗时 | 10 min   |
| 操作类型 | 文件复制 |

#### 目标

将已下载到本机的殆知阁古籍 TXT 文件，复制到项目的 `data/sources/daizhige/` 目录下。

#### 操作步骤

1. 确认殆知阁文件所在位置（例如 `D:\殆知阁\` 或用户的下载目录）
2. 在项目目录创建目标文件夹：
   ```
   mkdir -p d:\DimensionsCosmos\data\sources\daizhige
   ```
3. 将所有 `.txt` 文件复制到 `d:\DimensionsCosmos\data\sources\daizhige\`
4. 验证：统计文件数量并报告

#### 交付标准

- ✅ `data/sources/daizhige/` 目录存在
- ✅ 目录下至少有 100+ 个 `.txt` 文件
- ✅ 报告具体文件数量（如：`共 2,345 个文件，总计 X.XX GB`）

#### 验证命令（可选）

```
dir d:\DimensionsCosmos\data\sources\daizhige\*.txt | Measure-Object | Select-Object -ExpandProperty Count
```

---

### 任务 M0.8 · 放置 ctext 下载内容 ⚡

| 属性     | 值                          |
| -------- | --------------------------- |
| 优先级   | 🟡 中（如有下载内容才执行） |
| 建议耗时 | 10 min                      |
| 操作类型 | 文件复制                    |

#### 目标

把 ctext.org（中国哲学书电子化计划）已下载的文本放到 `data/sources/ctext/`。

#### 操作步骤

1. 确认是否已有 ctext 本地下载内容（XML 或 TXT 格式）
   - 如果没有 → 直接报告「M0.8 跳过：未找到 ctext 本地下载内容」
2. 创建目录：`mkdir -p d:\DimensionsCosmos\data\sources\ctext`
3. 将文件复制到该目录

#### 交付标准

- ✅ 目录存在，或明确报告「无内容可放置，建议后续从 https://ctext.org 手动下载」

---

### 任务 M1.1 · 注册 Groq API Key ⚡

| 属性     | 值                              |
| -------- | ------------------------------- |
| 优先级   | 🔴 最高（阻塞 M1 阶段全部任务） |
| 建议耗时 | 5 min                           |
| 操作类型 | 浏览器注册                      |

#### 目标

在 Groq 平台注册免费 API Key，用于后续 AI 解读生成。

#### 操作步骤

1. 打开浏览器，访问：`https://console.groq.com`
2. 注册账号（支持 GitHub 快捷登录）
3. 进入 API Keys 页面 → 创建新 Key
4. **复制 Key 并安全保存**（只显示一次）

#### 交付标准

- ✅ 获得一个有效的 `gsk_` 开头的 API Key
- ✅ 将 Key 设置为 Windows 环境变量：

  **二选一**（推荐方式1）：

  **方式1**：写入 `.env` 文件（项目根目录）

  ```
  在 d:\DimensionsCosmos\.env 文件中添加一行：
  GROQ_API_KEY=gsk_your_key_here
  ```

  **方式2**：系统环境变量

  ```
  [System.Environment]::SetEnvironmentVariable('GROQ_API_KEY','gsk_your_key_here','User')
  ```

- ✅ Key 已就位后报告「M1.1 完成，Key 已配置」

> ⚠️ **安全提醒**：`gsk_xxx` 是敏感信息，绝不要把 Key 原文贴到任何对话或公开文档中。

---

### 任务 M2.2 · 本地预览逐页检查

| 属性     | 值         |
| -------- | ---------- |
| 优先级   | 🟡 中      |
| 建议耗时 | 10 min     |
| 操作类型 | 浏览器检查 |

#### 目标

启动开发服务器，在浏览器中逐页验证所有页面是否正常渲染。

#### 操作步骤

1. 打开终端，进入项目目录：
   ```
   cd d:\DimensionsCosmos
   ```
2. 启动开发服务器：
   ```
   npm run dev
   ```
3. 等待终端输出 `Local: http://localhost:4321/DimensionsCosmos/`
4. 在浏览器中依次打开并截图或文字描述以下页面：

| 序号 | URL                                                   | 检查要点                                       |
| ---- | ----------------------------------------------------- | ---------------------------------------------- |
| 1    | `http://localhost:4321/DimensionsCosmos/`             | 首页：是否展示书库卡片、导航栏正常             |
| 2    | `http://localhost:4321/DimensionsCosmos/books`        | 书库页：卡片网格是否排列整齐、12+ 书目可见     |
| 3    | `http://localhost:4321/DimensionsCosmos/books/1-论语` | 书详情页：书名、朝代、作者、方法选择器是否显示 |
| 4    | `http://localhost:4321/DimensionsCosmos/methods`      | 方法页：9 种方法卡片是否全部显示、图标无乱码   |
| 5    | `http://localhost:4321/DimensionsCosmos/pricing`      | 定价页：价格卡片、付费方法明细表是否正常       |

#### 交付标准

- ✅ 首页正常渲染
- ✅ 书库页 ≥ 12 本书卡片可见
- ✅ 书详情页包含「选择读书法」按钮
- ✅ 方法页 9 种方法卡片完整
- ✅ 定价页无空链接或错位

#### 停止条件

如果遇到 404 或白屏，**立即停止并报告错误信息**，不要尝试修改代码。

---

### 任务 M2.4 · 部署到 Cloudflare Pages

| 属性     | 值                      |
| -------- | ----------------------- |
| 优先级   | 🟢 低（所有前置完成后） |
| 建议耗时 | 15 min                  |
| 操作类型 | 网页操作 + Git          |

#### 前置条件

- GitHub 仓库已推送（`aidulibrary/DimensionsCosmos`）
- Cloudflare 账号已注册

#### 操作步骤

1. 打开 `https://dash.cloudflare.com`
2. 左侧菜单 → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
3. 选择 GitHub → 授权 → 选择仓库 `aidulibrary/DimensionsCosmos`
4. 构建设置：
   | 配置项 | 值 |
   |--------|-----|
   | Framework preset | **Astro** |
   | Build command | `npm run build` |
   | Build output directory | `dist/` |
   | Root directory | `/` |
5. 点击 **Save and Deploy**
6. 等待部署完成，记录生成的域名（如 `dimensions-cosmos.pages.dev`）

#### 交付标准

- ✅ 部署状态显示 **Active**
- ✅ 域名 `.pages.dev` 可正常访问
- ✅ 报告最终域名

#### 停止条件

如果 Cloudflare 返回构建错误，**复制错误日志全文**，不要自行修改配置重试。

---

## 四、追加可选项（优先级低，可用剩余精力）

### A. 执行一键下载脚本（M0.6）

```
cd d:\DimensionsCosmos
python scripts/download_all.py --skip tech_books
```

> ⚠️ 需 2–3 小时，无人值守。如果执行，完成后报告「全量下载完毕」即可，无需汇报细节。

### B. 验证 AI 管线（M1.2）

```
python -c "from pipeline.ai_client import chat; print(chat('你好'))"
```

> 前提：M1.1 已完成。

---

## 五、执行共识与禁止事项

### ✅ 你可以做的

- 复制文件、创建目录
- 运行 `npm run dev` / `npm run build`
- 运行 Python 脚本（`python scripts/xxx.py`）
- 打开浏览器访问 URL 并检查页面
- 粘贴错误日志

### ❌ 你绝对不能做的

- 修改 `.astro`、`.ts`、`.js`、`.py`、`.css` 等任何代码文件
- 执行 `git push` 或 `git commit`
- 安装未在 `package.json` / `requirements.txt` 中列出的包
- 删除 `node_modules/`、`dist/`、`data/` 等目录
- 执行 `format` 或 `clean` 类破坏性命令

---

## 六、汇报模板

每完成一个任务，请使用以下格式汇报：

```
[任务ID] 状态: 完成 | 问题
结果描述: xxx
关键数据: xxx（文件数/大小/URL等）
耗时: x 分钟
```

如遇问题：

```
[任务ID] 状态: 阻塞
问题描述: xxx
错误日志: （粘贴完整日志）
需要决策: （明确你需要我做什么）
```

---

> **文档版本**：v1.0 · 2026-09-17  
> **下次更新时机**：所有 M0/M1/M2 任务完成后，更新为 M3（付费闭环）任务手册。
