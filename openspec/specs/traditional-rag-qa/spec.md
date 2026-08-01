# traditional-rag-qa Specification

## Purpose
TBD - Documents traditional RAG question answering behavior using vector retrieval and its expected limitations on multi-hop questions.

## Requirements

### Requirement: 基于 Faiss 的向量检索问答

传统 RAG 程序 SHALL 将语料切块、生成 embedding、构建 Faiss 向量索引，并在问答时按查询向量检索 top-k 相似块作为上下文交由 LLM 生成答案。

#### Scenario: 端到端问答
- **WHEN** 用户向 `RAG/` 程序提出一个问题
- **THEN** 程序对问题生成 embedding，从 Faiss 索引检索 top-k 语料块，拼接为上下文并调用 chat LLM 生成答案

#### Scenario: 展示被检索到的上下文
- **WHEN** 程序完成一次检索
- **THEN** 程序打印出实际被召回的 top-k 语料块（含来源文档），以便与 GraphRAG 对比

### Requirement: 可配置的 LLM 与 Embedding

传统 RAG 程序 SHALL 从环境变量读取 chat 与 embedding 配置，二者解耦；embedding MUST 支持 `openai` 与 `local`（sentence-transformers）两种 provider。

#### Scenario: 使用 OpenAI 兼容 chat + 本地 embedding
- **WHEN** 设置 `EMBEDDING_PROVIDER=local` 且提供 `OPENAI_BASE_URL`/`OPENAI_API_KEY`/`CHAT_MODEL`
- **THEN** 程序用本地模型生成 embedding、用 OpenAI 兼容 API 生成答案，全流程可运行

#### Scenario: 缺少必要配置时明确报错
- **WHEN** chat 所需的 `OPENAI_API_KEY` 未设置
- **THEN** 程序给出清晰的配置缺失提示而非隐晦崩溃

### Requirement: 索引落盘缓存

传统 RAG 程序 SHALL 将 Faiss 索引与块元数据缓存到磁盘，语料未变化时重复运行 MUST NOT 重新计算 embedding。

#### Scenario: 二次运行命中缓存
- **WHEN** 语料未变化时第二次运行程序
- **THEN** 程序从磁盘加载已有索引，不重新调用 embedding

### Requirement: 在多跳问题上暴露局限

传统 RAG 程序 SHALL 使用与 GraphRAG 相同的语料与问题；在线性多跳问题 Q1 上，因跨文档线索无法被单次相似度召回完整命中，其答案 SHALL 展现出信息缺失或错误。

#### Scenario: 多跳问题召回不全
- **WHEN** 向 `RAG/` 程序提出多跳问题 Q1
- **THEN** 被召回的上下文缺少链条中后续跳所需的文档，导致答案无法给出正确的最终城市
