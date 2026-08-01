## Context

本次变更交付一场 GraphRAG 知识分享所需的**讲解材料**与一个**可开箱运行的对比 Demo**。Demo 由三部分组成：双语语料库（`Docs/cn`、`Docs/en`）、传统 RAG 问答程序（`RAG/`）、手写轻量 GraphRAG 问答程序（`GraphRAG/`）。

核心教学目标：用**同一道多跳/聚合问题**，让传统 RAG 真实翻车（因扁平相似度召回漏掉散落线索），而 GraphRAG 沿实体-关系图多跳遍历答对，并且**每一步中间结果可见**（实体抽取 → 建图 → 逐跳遍历路径）。

当前仓库为空（仅 README）。约束：生成环节使用 OpenAI 兼容 API（读环境变量），部分兼容 API（如 DeepSeek）无 embedding 接口，需将 embedding 独立可配置；语料需支持中英双语切换。

## Goals / Non-Goals

**Goals:**

- 提供一套讲解材料，覆盖：传统 RAG 原理、GraphRAG 原理、GraphRAG 优势（多跳推理、跨文档串联、聚合查询、可解释路径、抗幻觉）、贯穿式对比案例。
- 语料被刻意设计成"每跳事实分散在不同文档、措辞互不相似"，使传统 RAG 在多跳场景**可复现地**失败。
- 两个程序共享同一份语料与同一套问题，输出可直接并排对比。
- GraphRAG 三步透明：实体/关系抽取结果、图结构、逐跳遍历路径都能打印出来，供现场演示。
- LLM（chat）与 embedding 解耦、均可配置，支持离线 embedding 兜底，让 Demo 在无 embedding API 的兼容服务下也能跑。
- 语料语言可通过配置在 cn/en 间切换。

**Non-Goals:**

- 不追求生产级检索质量或性能优化（这是教学 Demo）。
- 不使用微软官方 `graphrag` 库（探索阶段已决定走手写教学版，保证每步可见）。
- 不做前端 / Web UI；命令行输出即可。
- 不做通用文档解析（PDF/HTML 等）；语料统一为 Markdown。
- 不实现实体消歧、共指消解等复杂 NLP（用 LLM 抽取 + 简单归一化即可）。

## Decisions

### 决策 1：实现语言与运行形态 — Python + CLI 脚本

- **选择**：Python 3.10+，两个程序各自是可独立运行的 CLI 脚本（`RAG/rag_qa.py`、`GraphRAG/graphrag_qa.py`），外加一个可选的并排对比入口（`compare.py`）。
- **理由**：Faiss、OpenAI SDK、sentence-transformers、networkx 生态都在 Python；CLI 最利于现场打印中间结果。
- **备选**：Node/TS（Faiss 生态弱）、Jupyter Notebook（现场演示好但不利于"程序"交付，且 diff/版本管理差）。可后续补一个 notebook，但主交付是脚本。

### 决策 2：共享配置层 — `.env` + 环境变量，chat 与 embedding 解耦

- **选择**：统一从环境变量读取配置，两程序共用一个 `common/`（或各自读同名变量）：
  - Chat：`OPENAI_BASE_URL`、`OPENAI_API_KEY`、`CHAT_MODEL`
  - Embedding：`EMBEDDING_PROVIDER`（`openai` | `local`）、`EMBEDDING_MODEL`、可选 `EMBEDDING_BASE_URL`/`EMBEDDING_API_KEY`
  - 语料：`CORPUS_LANG`（`cn` | `en`）
- **理由**：DeepSeek 等无 embedding 接口 → 允许 chat 用 DeepSeek、embedding 用 OpenAI 或本地。解耦后离线也能跑（`EMBEDDING_PROVIDER=local` 用 sentence-transformers）。
- **备选**：写死单一 provider（不灵活，离线跑不了）。

### 决策 3：向量检索 — Faiss `IndexFlatL2/IP`，索引落盘缓存

- **选择**：语料按 Markdown 段落切块（chunk），embedding 后建 Faiss 扁平索引；索引 + chunk 元数据缓存到磁盘（如 `RAG/.cache/`），避免每次重复 embedding。
- **理由**：语料规模小（几十个 chunk），扁平索引精确且够快，无需 IVF/HNSW；落盘缓存让现场演示秒级启动。
- **备选**：IVF/HNSW（小语料无必要）、内存 numpy 余弦检索（用 Faiss 更贴合"向量数据库"分享主题）。

### 决策 4：GraphRAG 三步流水线（教学透明版）

```
① 抽取   每篇文档 ──LLM──▶ 三元组 (subject, relation, object)
② 建图   三元组 ──networkx──▶ 有向图 (节点=实体, 边=关系, 边带来源文档)
③ 检索   问题 ──LLM 抽取起点实体──▶ 从起点 BFS/DFS 多跳遍历(限深度)
         ──▶ 收集路径上的三元组作为上下文 ──LLM──▶ 生成答案
```

- **选择**：
  - **抽取**用 LLM，按固定 JSON schema 输出三元组；实体做轻量归一化（去空格/统一大小写/别名表），结果缓存到 `GraphRAG/.cache/graph.json`。
  - **图结构**用 `networkx.MultiDiGraph`，边属性含 `relation` 和 `source`（来源文档），便于展示"这条线索来自哪篇文档"。
  - **遍历**：从问题实体出发，做限深（默认 3~4 跳）的 BFS，收集经过的三元组；聚合类问题额外支持"遍历某节点的所有某类邻居再逐个下钻"。
  - **可视化**：每步打印中间结果（抽取的三元组数、图节点/边数、逐跳访问序列与命中路径）。
- **理由**：这是分享的灵魂——观众要能"看到它怎么走通那条链"。networkx 轻、够用、可导出。
- **备选**：Neo4j（重、要起服务，违背"开箱即跑"）、纯 dict 邻接表（可行但 networkx 更省事且自带遍历/导出）。

### 决策 5：抽取所用图 schema — 面向语料的固定关系集

- **选择**：预定义关系类型：`子公司(subsidiary_of)`、`CEO(ceo_of)`、`毕业于(graduated_from)`、`位于(located_in)`、`投资(invested_in)`。抽取 prompt 里给定这套关系，降低 LLM 抽取发散。
- **理由**：固定 schema 让抽取稳定、图干净、遍历可控，教学效果好。
- **备选**：开放式关系抽取（图更"真"但噪声大、遍历不稳定，不利于可复现的现场演示）。

### 决策 6：语料设计 — 事实链刻意"跨文档拆散"

- **选择**：把每条多跳链的相邻两跳事实放进**不同文档**，且每篇文档**不出现下一跳的关键词**。示例主链：
  ```
  companies.md   : 云枢智能 是 星环科技 的子公司        (不含 CEO/人名)
  leadership.md  : 李明 担任 云枢智能 CEO               (不含母校)
  people.md      : 李明 毕业于 未名理工大学             (不含城市)
  universities.md: 未名理工大学 坐落于 江城             (不含人名)
  investors.md   : 磐石资本 投资 星环科技               (聚合题用)
  ```
- **理由**：这是让传统 RAG **可复现失败**的关键——单次相似度召回拿不全跨文档链条。
- **备选**：把链条写在同一篇文档（传统 RAG 也能答对 → 失去对比意义）。

### 决策 7：双语语料 — cn 为源、en 为对照翻译，结构一一对应

- **选择**：`Docs/cn/` 与 `Docs/en/` 文件名一一对应，实体用可翻译的中英对照命名（如 云枢智能 / Yunshu Intelligence）。程序按 `CORPUS_LANG` 选目录。
- **理由**：证明 GraphRAG 能力与语言无关；也方便英文听众。
- **备选**：单语（不满足需求）；机器实时翻译（不稳定、离线不可用）。

### 决策 8：两个案例问题（讲解与 Demo 共用）

- **Q1 线性多跳**：「云枢智能的 CEO 毕业于哪所大学？那所大学在哪个城市？」→ 需 3 跳，传统 RAG 漏召回 → GraphRAG 沿链答"江城"。
- **Q2 聚合多跳**：「星环科技旗下所有子公司的 CEO 里，谁的母校在江城？」→ 需遍历所有子公司 + 逐个查母校 + 按城市过滤，传统 RAG 更彻底无能。
- **理由**：Q1 直观讲清"链"，Q2 展示"遍历+过滤"的图独有能力。

## Risks / Trade-offs

- **LLM 抽取不稳定/漏抽三元组** → 固定关系 schema + 少样本示例 + 抽取结果缓存并允许人工校对 `graph.json`；语料措辞尽量规整以利抽取。
- **"传统 RAG 一定失败"不够稳健**（top-k 调大可能碰巧召回） → 通过语料设计（跨文档、去关键词）+ 固定较小 top-k 保证可复现失败；并在讲解中说明这是"结构性"局限而非调参问题。
- **无 embedding API 时跑不动** → `EMBEDDING_PROVIDER=local` 用 sentence-transformers 离线兜底；README 写清两种配置。
- **API Key / 网络依赖导致现场翻车** → 索引与图结果落盘缓存，可提前预跑生成缓存；离线 embedding + 已缓存图可在无网时演示检索/遍历（仅最终生成需 chat API）。
- **中英实体归一化不一致导致图断裂** → 每种语言独立建图，实体名以该语言语料为准；提供别名/归一化表。
- **依赖 faiss 安装在 macOS 上偶有坑** → 使用 `faiss-cpu` wheel；README 标注安装命令与 Python 版本。

## Open Questions

- Chat 具体用哪个兼容服务（OpenAI / DeepSeek / 通义）？影响是否需要额外配 embedding provider——建议默认 `EMBEDDING_PROVIDER=local` 以保证开箱即跑，chat 由用户填 Base URL/Key。
- 讲解材料形态：单文件 `SHARING.md`（Markdown，含 ASCII 图）还是 `slides/`（多页/可转 PPT）？建议先 `SHARING.md`，需要再转 slides。
- 是否额外附一个 Jupyter notebook 版做现场演示？（非必须，可作为 nice-to-have 任务。）
