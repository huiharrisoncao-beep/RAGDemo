# RAGDemo — 传统 RAG vs GraphRAG 对比 Demo

一个用于**知识分享**的最小对比 Demo：同一份语料、同一批多跳问题，分别用**传统 RAG**（向量检索）和**手写轻量 GraphRAG**（实体关系图 + 多跳遍历）回答，直观展示 GraphRAG 在**多跳推理**与**聚合查询**上的质变能力。

> 📖 配套讲解材料见 [SHARING.md](./SHARING.md)（原理、优势、逐跳拆解）。

## 目录结构

```
Docs/            双语语料库（事实链被刻意拆散到不同文档）
  cn/            中文语料
  en/            英文平行语料
RAG/             传统 RAG：切块 → embedding → Faiss → top-k → 生成
GraphRAG/        手写 GraphRAG：LLM抽取三元组 → 建图 → 多跳遍历 → 生成
common/          共享层：配置、chat 客户端、embedding、语料加载、基准问题
compare.py       并排对比入口
SHARING.md       知识分享讲解材料
```

## 环境准备

需要 Python 3.10+。

```bash
pip install -r requirements.txt
```

## 配置

复制 `.env.example` 为 `.env` 并填写：

```bash
cp .env.example .env
```

关键变量：

| 变量 | 说明 |
|---|---|
| `OPENAI_BASE_URL` | chat 服务地址（OpenAI 兼容），如 DeepSeek 为 `https://api.deepseek.com` |
| `OPENAI_API_KEY` | chat API Key（**请勿提交到仓库**，`.env` 已被 gitignore） |
| `CHAT_MODEL` | 生成模型，如 `deepseek-chat` |
| `EMBEDDING_PROVIDER` | `local`（本地 sentence-transformers，离线可用）或 `openai` |
| `EMBEDDING_MODEL` | 本地默认 `paraphrase-multilingual-MiniLM-L12-v2` |
| `CORPUS_LANG` | 语料语言：`cn` 或 `en` |

> **为什么 embedding 与 chat 解耦？** DeepSeek 等部分 OpenAI 兼容服务**没有 embedding 接口**。默认 `EMBEDDING_PROVIDER=local`，用本地模型生成向量，chat 仍走你配置的兼容 API，二者互不影响。

## 运行

```bash
# 传统 RAG（内置 Q1/Q2，或传入自定义问题）
python RAG/rag_qa.py
python RAG/rag_qa.py "云枢智能的CEO毕业于哪所大学？"

# GraphRAG（首次会用 LLM 抽取三元组并缓存；--rebuild 可强制重抽）
python GraphRAG/graphrag_qa.py
python GraphRAG/graphrag_qa.py --rebuild

# 并排对比
python compare.py
```

切换语言：

```bash
CORPUS_LANG=en python compare.py
```

## 预期效果

**Q1（线性多跳）**：云枢智能的 CEO 毕业于哪所大学？那所大学在哪个城市？

- 传统 RAG：相似度检索只召回「李明是CEO」，漏掉「李明→未名理工」「未名理工→江城」两跳 → **答不出**。
- GraphRAG：从「云枢智能」沿边遍历 `→李明→未名理工大学→江城` → **答对**，并打印逐跳路径。

**Q2（聚合多跳）**：星环科技旗下所有子公司的 CEO 里，谁的母校在江城？

- 传统 RAG：无遍历+过滤能力 → **答不出**。
- GraphRAG：展开全部子公司→CEO→母校→城市，过滤城市=江城 → **李明**。

## 缓存

- `RAG/.cache/`：Faiss 索引 + 块元数据
- `GraphRAG/.cache/`：抽取的三元组 `graph_<lang>_<fingerprint>.json`

语料内容变化会自动失效重建；也可删除 `.cache/` 或用 `--rebuild`。抽取结果为纯 JSON，可人工校对。

## 说明

- 语料与实体均为**虚构**，避免版权与事实错误问题。
- GraphRAG 为**教学向手写实现**，刻意打印每步中间结果，非生产级方案。
