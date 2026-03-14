# Pulsar Future Roadmap

> 从链接收集到知识输出的完整闭环
> 定位：个人知识加工流水线，而非书签仓库

## 核心问题

收集不是瓶颈，**加工**才是。大多数知识工作者的断裂点：

```
收集（已解决）→ 阅读（在做）→ [断裂] → 思考 → 输出
```

断裂发生在三处：
1. **高亮了但不回顾** — 没有触发机制重新看到自己的高亮
2. **回顾了但不加工** — 看到原文，但没有追问"所以呢？对我意味着什么？"
3. **想了但不写下来** — 灵感转瞬即逝，没有低摩擦的捕获方式

这是典型的 **Collector's Fallacy**（收藏家谬误）：收藏了 ≠ 读了 ≠ 理解了 ≠ 能运用。

## 当前状态

```
收集 → 富化 → 浏览
```

## 目标

```
输入层：  Telegram + Obsidian + Readwise + RSS
加工层：  inbox → reading → processing → done
          ↑ AI 辅助          ↑ 间隔重现
输出层：  Obsidian 笔记 + Weekly Digest + 研究报告
```

---

## 零、知识加工流水线（核心机制）

这是 Pulsar 从"仓库"变成"加工厂"的关键设计。

### 状态流转

现在链接只有 `done: true/false`。改为状态流：

| 状态 | 含义 | 停留时间 |
|------|------|---------|
| `inbox` | 刚收藏，还没看 | 应尽快分流 |
| `reading` | 正在读 / 已在 Readwise 里读 | 天级 |
| `processing` | **读完了，需要提炼笔记** | 关键状态 |
| `done` | 已产出笔记，归档 | 永久 |
| `archived` | 看了但不值得深入 | 永久 |

**processing 是最重要的状态** — 代表"我读完了，这篇有价值，但还没变成自己的知识"。

### 每日加工仪式（Daily Processing）

Pulsar 首页应该是**今天需要处理的东西**，而非所有链接的列表：

```
┌─────────────────────────────────┐
│  Today's Processing Queue       │
│                                 │
│  3 items from Readwise highlights│
│  2 items in "processing" state  │
│  1 item revisited (7 days ago)  │
│                                 │
│  [Start Processing →]           │
└─────────────────────────────────┘
```

每天 10 分钟处理 3-5 条。不是重读全文，而是回答一个问题：

> **"这篇内容，用一句话告诉三个月后的自己，为什么它重要？"**

这句话就是 Obsidian 笔记的种子。

### 间隔重现（Spaced Repetition）

不需要 Anki 那样复杂。最简单的实现：

```
高亮第一次出现：收藏当天
第二次出现：3 天后
第三次出现：7 天后
第四次出现：30 天后
```

每次出现时问：**还值得保留吗？有什么新想法？**
三次跳过 → 自动降级为 archived。写了笔记 → 标记为 done。

### 最小摩擦输出

从 processing 到 Obsidian 笔记应该是**一次点击**：

```
[卡片] → 点击 "Note" 按钮
  ↓
预填模板（自动生成，只需补"我的想法"）：
---
title: "文章标题"
source: "URL"
date: 2026-03-15
tags: [AI, regulation]
---

## AI 摘要
{Pulsar 的 ai_summary}

## 我的高亮
{从 Readwise 拉取的 highlights}

## 我的想法
> [光标在这里，只需写一句话]

## 关联
- 相关链接 1（Pulsar 自动关联）
- 相关链接 2
```

### 学习科学依据

| 学习要素 | 机制 | Pulsar 实现 |
|---------|------|-----------|
| **Elaboration**（精加工） | 用自己的话重述 | processing 状态 + "一句话"模板 |
| **Spacing**（间隔重复） | 隔段时间再看一遍 | 高亮间隔重现 |
| **Interleaving**（交叉） | 不同主题交替出现 | 每日队列混合不同 category |

### 最重要的原则

**不要试图同时做所有事情。** 先加 `processing` 状态和"一句话"输入框。每天 10 分钟处理 3 条。坚持两周 = Obsidian 里多 40+ 条有自己思考的笔记。这比任何技术方案都有价值。

---

## 一、消化层 — 从"存了"到"读了"

Pulsar 存了大量文章，但没有机制帮助真正消化。

- **阅读视图**：点开卡片直接读 `content/` 全文，不跳转原站
- **渐进式摘要**：AI 一句话摘要 → 三段摘要 → 全文，降低阅读门槛
- **每日推荐**：从未读链接中根据阅读偏好推 3-5 篇
- **阅读队列**：拖拽排优先级，读完标记，形成阅读节奏

## 二、连接层 — 从"单篇"到"网络"

知识的价值在于连接。零散的文章之间可能在讨论同一件事。

- **自动关联**：向量相似度找出相关文章，卡片底部显示 "Related"
- **主题聚合**：AI 把零散链接归纳成主题串——"过去 3 个月收集了 12 篇 AI 监管内容，核心观点有三个…"
- **知识图谱**：链接之间的引用关系、主题交叉可视化

### 向量搜索方案

```
content/*.md → 分段 → Embedding API → 本地向量文件（JSON/npy）
                                          ↓
用户查询 → Embedding → 余弦相似度 → Top K 结果
                                          ↓
                                    （可选）送入 Claude 做 RAG 问答
```

技术选型：
- Embedding: Voyage 3 / OpenAI text-embedding-3-small（便宜，中文好）
- 向量存储: JSON 文件或 numpy .npy（几百篇不需要向量数据库）
- 相似度: numpy dot（毫秒级）
- RAG: Claude Haiku

成本：~1500 片段，一次性 embedding < $0.01，向量文件 < 5MB

## 三、Obsidian 双向流动 — 从"单向推送"到"知识融合"

当前数据流是 `Obsidian → Pulsar` 单向。反向流动价值更大。

```
当前：  Obsidian Links.md → Pulsar（收集）
未来：  Pulsar → Obsidian（输出笔记）
```

- **一键生成笔记**：读完文章，自动生成 Obsidian 笔记草稿（AI 摘要 + 关键观点），写入 SOLARIS vault
- **自动反向链接**：分析 Obsidian 笔记，发现"这篇笔记提到了 X 概念，你收藏的这 3 篇文章也在讨论 X"
- **阅读笔记模板**：标记 done 时弹出模板写一句启发，同步到 Obsidian

## 四、输出层 — 从"输入"到"产出"

收集和阅读都是输入，真正的价值在输出。

- **Weekly Digest**：每周自动生成阅读摘要，Markdown 格式，可发博客或 Newsletter
- **主题研究报告**：选一个 topic，综合所有相关文章 + content/ 全文 + AI 分析，输出结构化报告
- **对话式探索**（RAG）：对收藏库提问——"收藏内容里对 2026 年经济走势有哪些不同观点？"

## 五、Readwise 整合 — 打通深度阅读与广度收集

Pulsar 和 Readwise 在知识工作流里是互补的：

```
Readwise = 深度阅读 + 高亮摘录（精读层）
Pulsar   = 广度收集 + AI 分析（速览层）
Obsidian = 思考 + 连接 + 输出（加工层）
```

### 三角闭环

```
         Readwise
        ↗        ↘
  深度阅读高亮    highlights API
       ↑              ↓
   Obsidian  ←——  Pulsar
   笔记+思考      AI分析+关联
       ↓
     输出
```

- **Readwise → Pulsar**：高亮和文章 URL 自动进入 Pulsar，AI 做跨文章分析
- **Readwise → Obsidian**：原始高亮同步（已有 Readwise 插件）
- **Pulsar → Obsidian**：AI 生成的主题归纳、关联发现、研究报告写入 vault
- **Obsidian → Pulsar**：Links.md 新链接推送（已实现）

### 实现路径

**Phase 1：Readwise 作为数据源（1-2 天）**

Readwise 成为 Pulsar 的第三个输入源，和 Telegram 类似：

```python
# readwise.py — 新增 pipeline 步骤
READWISE_TOKEN = os.environ.get("READWISE_TOKEN")

def fetch_readwise_highlights():
    resp = requests.get(
        "https://readwise.io/api/v2/highlights/",
        headers={"Authorization": f"Token {READWISE_TOKEN}"},
        params={"page_size": 100, "updated__gt": last_sync_date}
    )
```

sync.py 合并时，Readwise 链接额外带上 `highlights` 字段。

三个输入汇聚到统一视图：

```
碎片发现 → Telegram bot  → Pulsar
主动收藏 → Obsidian Links → Pulsar
深度阅读 → Readwise       → Pulsar（新）
```

**Phase 2：高亮展示（几小时）**

卡片上显示高亮数量徽标，点开查看具体摘录。Reader 里高亮的内容直接在 Pulsar 可见。

**Phase 3：跨文章 AI 分析（需要向量搜索）**

把所有 highlights 向量化，实现：
- 跨文章主题归纳："你在 5 篇文章里都高亮了关于 AI 监管的内容"
- 观点矛盾发现："这篇说通胀见顶，那篇说还会持续"
- 知识密度排序："这本书你高亮了 47 处，核心观点是…"

### Readwise API 要点

| 端点 | 数据 | 用途 |
|------|------|------|
| `/v2/highlights/` | 高亮文本 + 源 URL + 标签 | 主要数据源 |
| `/v2/books/` | 书籍/文章元数据 | 补充 title/author |
| `/v2/export/` | 批量导出 | 首次全量同步 |

免费 API，无速率限制，token 在 readwise.io/access_token。

## 六、个人 API + MCP — 让 AI 成为知识的接口

Pulsar 的收藏库是一个结构化的兴趣图谱。开放只读 API 后，其他工具可以接入：

### API 端点

```
GET /api/links?topic=crypto&limit=10
GET /api/search?q=monetary+policy
GET /api/highlights?tag=AI
GET /api/stats                        # 阅读画像数据
```

### 接入场景

- **MCP Tool for Claude**：在 Claude 对话中直接搜索 Pulsar——"我之前收藏过哪些关于日本经济的文章？"你的收藏变成 AI 的长期记忆
- **Obsidian 插件**：写笔记时侧边栏自动显示相关收藏和高亮
- **Alfred/Raycast**：`pls bitcoin etf` 快捷搜索 Pulsar
- **写作辅助**：检测到你正在写的主题，自动推送相关文章 + 你的高亮 + 之前写的"一句话想法"

MCP 接入技术上很简单——Pulsar 已经有 HTTP API，只需要写一个 MCP server 定义 tools 即可。

## 七、多格式统一 inbox — 不只是链接

现在 Pulsar 只收集网页链接。但知识输入还有：
- 灵感和想法（没有 URL 的纯文本）
- PDF 论文
- 播客片段（timestamp + 笔记）
- 书籍章节（Readwise 接入后）

Pulsar 可以变成**统一的知识 inbox**：

```
POST /api/add
{
  "type": "thought",       // link | thought | highlight | pdf
  "content": "突然想到，AI 监管的本质是...",
  "tags": ["AI", "regulation"]
}
```

灵感和阅读放在一起，才能产生化学反应。改动极小——给 link 加一个 `type` 字段，前端加一个"快速想法"输入框。

## 八、内容衰减 — 自动区分时效性与常青内容

不是所有链接的价值都恒定。

```
时效性内容（新闻、市场分析）  → 自动降权，6个月后 archive
常青内容（原理、方法论）      → 权重不变，反复浮出
```

AI 在 analyze.py 中自动判断 `ephemeral` 还是 `evergreen`，确保每日队列不被过期内容占满。

## 九、反收藏 — 减法思维

大多数工具鼓励收藏更多。但真正的价值可能是**定期清理**。

- **90 天审查**：超过 90 天未读的自动进入"要不要删？"队列
- **价值密度**：按 highlights 数量 / 文章长度排序，密度低的可能不值得保留
- **断舍离模式**：每月展示 10 条"你可能不再需要这些"，一键 archive

收藏 300 篇但真正有价值的 50 篇，比 300 篇全部堆着好得多。和每日加工队列自然结合。

## 十、阅读画像 — 你读什么定义了你是谁

```
┌──────────────────────────────┐
│  2026 Q1 阅读画像             │
│                              │
│  主题分布：                    │
│  ████████░░ Crypto    38%    │
│  ██████░░░░ Tech      28%    │
│  ████░░░░░░ Economics 18%    │
│                              │
│  阅读趋势：                    │
│  本月比上月多读了 40%          │
│  新增兴趣：AI safety          │
│                              │
│  知识缺口：                    │
│  你大量收藏 AI 内容            │
│  但几乎没有 AI safety 相关    │
│  推荐补充阅读...              │
└──────────────────────────────┘
```

既是自省工具，也能发现盲区。

## 十一、输入拓展 — 从"手动收藏"到"智能发现"

- **RSS 监控**：关注特定博客/作者，新文章自动进入 pipeline
- **推荐引擎**：基于收藏偏好，从公开 RSS 源中推荐可能感兴趣的内容
- **Twitter/X 书签同步**：类似 Telegram 通道，自动抓取

---

## 价值评估

从核心痛点（碎片化、不回顾、输入输出断裂）出发：

| 方向 | 解决核心痛点 | 技术复杂度 | 建议 |
|------|------------|-----------|------|
| 状态流转 + 每日队列 + 间隔重现 | ✅ 直接解决 | 低 | **V1 必做** |
| Obsidian 笔记导出 | ✅ 推动输出 | 低 | **V1 必做** |
| MCP 接入 | ✅ 让知识活过来 | 低 | **高价值** |
| 多格式 inbox | ✅ 捕获灵感 | 极低 | **高价值** |
| 内容衰减 | ✅ 减少噪音 | 极低 | 加一个字段 |
| 反收藏/断舍离 | ✅ 对抗收藏家谬误 | 低 | 和每日队列结合 |
| Readwise 接入 | ✅ 打通深度阅读 | 中 | V2 |
| 写作辅助 | ✅ 最后一公里 | 中高 | 需要向量搜索 |
| 阅读画像 | 间接（自省） | 低 | 有趣但不急 |
| 推荐引擎 | 间接 | 高 | 远期 |

---

## 技术评估

当前代码量：**~3300 行**（含前端），非常精简。

### 各功能实现成本

| 功能 | 新增代码 | 新文件 | 新依赖 | 臃肿风险 |
|------|---------|--------|--------|---------|
| 状态流转 | ~50 行 | 无 | 无 | ⬜ 零 |
| 每日加工队列 | ~80 行 | 无 | 无 | ⬜ 零 |
| 间隔重现 | ~60 行 | 无 | 无 | ⬜ 零 |
| Obsidian 笔记导出 | ~100 行 | 无 | 无 | 🟨 低 |
| Readwise 接入 | ~120 行 | readwise.py | 无 | 🟨 低 |
| 全文搜索 | ~40 行 | 无 | Fuse.js CDN | ⬜ 零 |
| 向量搜索 + RAG | ~200 行 | embed.py | numpy 等 | 🟧 中 |

### 代码增长预估

```
当前：                 3,300 行
+核心机制（前4项）：    3,590 行  (+290,  +9%)
+Readwise+全文搜索：   3,750 行  (+450, +14%)
+向量搜索：            3,950 行  (+650, +20%)
```

### 关键结论

- **前 4 项（状态 + 队列 + 间隔 + 导出）是一个整体**，建议作为一个版本一起做，~290 行，ROI 最高
- 做完全部 7 项，总代码仅增长 ~20%，**不会臃肿**
- **不需要**：Vite、前端框架、数据库、新的构建流程
- 项目结构不变，每个功能都是现有模式的自然延伸
- 向量搜索是复杂度跳变的分界线，但 embed.py 与主代码完全解耦

### 建议实施顺序

```
Version 1（知识加工）：状态流转 + 每日队列 + 间隔重现 + Obsidian 导出
Version 2（数据源）：  Readwise 接入 + 全文搜索（Fuse.js）
Version 3（智能层）：  向量搜索 + RAG + 自动关联
```

---

## 优先级矩阵

```
V1 核心机制               V2 数据源+搜索          V3 智能层            远期
────────────────         ─────────────         ──────────────      ──────────────
链接状态流转              Readwise 数据源接入     向量语义搜索          知识图谱可视化
  (inbox→processing→done) 全文搜索（Fuse.js）     自动关联             推荐引擎
每日加工队列              阅读视图               跨文章高亮分析        对话式 RAG
间隔重现                  内容衰减标记           写作辅助             双向 Obsidian 同步
一键输出 Obsidian 笔记     反收藏/断舍离          主题研究报告
MCP 接入 Claude           Weekly Digest          阅读画像
多格式 inbox（thought）    RSS 监控
```

## 架构演进

| 阶段 | 定位 | 架构变化 |
|------|------|---------|
| **现在** | 链接书签管理器 | 单文件 + JSON + Python |
| **+阅读视图+笔记导出** | 个人阅读器 | 不需要改 |
| **+向量搜索+RAG** | 个人知识库 | 加 embed.py + numpy |
| **+知识图谱+推荐** | 个人知识助手 | 考虑前端框架 + Vite |

## Pipeline 演进

```
当前输入：  Obsidian Links.md + Telegram bot
未来输入：  + Readwise highlights + RSS feeds

当前：  sync → fetch → analyze → assets
未来：  sync → fetch → analyze → assets → embed → connect
         ↑                                  ↑        ↑
    +readwise.py                        向量化    关联/推荐
```
