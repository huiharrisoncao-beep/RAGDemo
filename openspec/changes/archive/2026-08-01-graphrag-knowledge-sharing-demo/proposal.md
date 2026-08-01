## Why

我们要做一场关于 GraphRAG 的知识分享，需要既能"讲清原理"又能"现场跑起来对比"。传统 RAG 基于扁平的语义相似度召回，天然缺乏跨文档、跨片段把线索串联起来的能力，在多跳推理和聚合查询上会真实翻车；GraphRAG 通过显式的实体-关系图把"串联"变成图上的路径遍历，能解决这类问题。本次变更交付一套讲解材料 + 一个可开箱运行的对比 Demo，让观众亲眼看到"传统 RAG 做不到、GraphRAG 怎么做到"。

## What Changes

- **新增双语语料库** `Docs/cn/`（中文原版）与 `Docs/en/`（英文翻译版），题材为虚构科技公司生态（公司 → 子公司 → 高管 → 母校 → 城市 → 投资方）。语料被**刻意设计**为：每一跳的事实分散在不同文档、且措辞互不相似，从而让传统 RAG 的相似度召回在多跳场景下必然漏召回。
- **新增传统 RAG 问答程序** `RAG/`：embedding → Faiss 向量库 → top-k 检索 → 拼接上下文 → LLM 生成。用于展示"扁平召回"的局限。
- **新增手写轻量 GraphRAG 问答程序** `GraphRAG/`：LLM 抽取实体与关系 → 构建知识图 → 从问题实体出发沿边多跳遍历 → 把路径上下文喂给 LLM 生成。**每一步中间结果可打印可见**（实体抽取结果、图结构、逐跳遍历路径），用于现场演示"它是如何做到多跳的"。
- **新增讲解材料**：涵盖传统 RAG 原理、GraphRAG 原理、GraphRAG 优势（多跳推理、跨文档串联、聚合查询、可解释路径、抗幻觉），以及一个贯穿全场的对比案例（同一道多跳题，两个程序跑出不同结果）。
- **LLM 与 Embedding 可配置**：生成环节走 OpenAI 兼容 API（读环境变量 API Key）；由于部分兼容 API（如 DeepSeek）无 embedding 接口，embedding 独立为可配置项（OpenAI embedding 或本地 `sentence-transformers` 兜底），并可通过配置切换语料语言（cn/en）。

## Capabilities

### New Capabilities
- `demo-corpus`: 双语虚构科技公司生态语料库，含多跳推理与聚合查询所需的、被刻意拆散到不同文档的事实链。
- `traditional-rag-qa`: 基于 embedding + Faiss 向量检索的传统 RAG 问答程序，展示扁平相似度召回在多跳场景的局限。
- `graphrag-qa`: 手写轻量 GraphRAG 问答程序，三步透明（抽取 → 建图 → 多跳遍历），中间结果可视，能解决传统 RAG 做不到的多跳与聚合查询。
- `sharing-material`: GraphRAG 知识分享讲解材料，含原理、优势、贯穿式对比案例。

### Modified Capabilities
<!-- 无既有 spec 变更，全部为新增能力。 -->

## Impact

- **新增目录/代码**：`Docs/cn/`、`Docs/en/`、`RAG/`、`GraphRAG/`，以及讲解材料（`SHARING.md` 或 `slides/`）与根 `README.md` 的运行说明。
- **依赖**：`faiss`（向量库）、OpenAI 兼容 SDK、`networkx`（图结构，待 design 确认）、可选 `sentence-transformers`（本地 embedding 兜底）。
- **外部依赖/配置**：需要 OpenAI 兼容 API 的 Base URL 与 API Key（通过环境变量注入）；离线场景可用本地 embedding。
- **无破坏性变更**：仓库当前仅有 README，全部为新增。
