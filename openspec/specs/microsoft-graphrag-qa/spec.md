# microsoft-graphrag-qa Specification

## Purpose
基于微软官方 `graphrag` 框架的问答程序——用与传统 RAG / 手写 GraphRAG 相同的语料（`Docs/<lang>/`）与相同的基准问题（`common/questions.py` 的 Q1/Q2）完成官方索引（index）与 local/global 查询，以本机 Ollama `embeddinggemma` 作为 embedding 后端；作为手写 `graphrag-qa` 的官方框架对照，直观呈现"社区检测 + local/global search"与"显式多跳遍历"两条技术路线的差异。

## Requirements

### Requirement: 使用微软官方 GraphRAG 框架

`MicrosoftGraphRAG` 程序 SHALL 通过微软官方 `graphrag` 框架完成索引与查询，而非手写图遍历实现。程序 MUST 复用与 `RAG/`、`TEGraphRAG/` 相同的语料（`Docs/<lang>/`）与相同的基准问题（`common/questions.py` 的 Q1/Q2）。

#### Scenario: 调用官方框架完成问答
- **WHEN** 运行 `MicrosoftGraphRAG` 程序回答某个问题
- **THEN** 程序经由官方 `graphrag` 的索引产物与 search 引擎生成答案，且所用语料与问题与其他两个程序一致

#### Scenario: 语料与问题一致
- **WHEN** 检查 `MicrosoftGraphRAG` 使用的语料与预备问题
- **THEN** 语料来自 `Docs/<lang>/`、问题为 `common/questions.py` 中的 Q1/Q2，无额外改写

### Requirement: 语料物化为官方输入格式

程序 SHALL 将 `Docs/<lang>/*.md` 物化为官方 `graphrag` 要求的 `input/*.txt`，MUST 不改写语料事实内容。

#### Scenario: 生成 input 文本
- **WHEN** 首次为某语言运行程序
- **THEN** 程序把该语言下的 Markdown 语料写入官方索引所需的 `input/` 目录，内容与来源文档一致

### Requirement: 本地 Ollama Embedding 后端

索引所需的向量化 SHALL 使用本机 Ollama 的 OpenAI 兼容端点（默认 `http://localhost:11434/v1`）与 `embeddinggemma` 模型；chat SHALL 复用现有 DeepSeek 配置。程序在索引前 MUST 校验 embedding 端点可达，不可达时 MUST 给出清晰错误提示。

#### Scenario: 使用 Ollama 进行向量化
- **WHEN** 程序执行索引管线的向量化步骤
- **THEN** 向量请求发送至配置的 Ollama 端点与 `embeddinggemma` 模型，chat 请求仍走 DeepSeek

#### Scenario: Embedding 端点不可达
- **WHEN** 索引前 Ollama 端点不可达或模型未部署
- **THEN** 程序中止并提示需先启动 Ollama 并拉起 `embeddinggemma`，而非隐晦崩溃

### Requirement: 索引与缓存

程序 SHALL 首次运行时触发官方索引管线（分块 → 实体/关系抽取 → 社区发现 → 社区报告 → 向量化）并缓存产物；语料内容未变化时 MUST 复用缓存，变化或 `--rebuild` 时 MUST 重建。

#### Scenario: 首次索引并缓存
- **WHEN** 语料尚无索引产物时运行程序
- **THEN** 程序运行官方索引管线并将产物缓存到 `MicrosoftGraphRAG/` 下

#### Scenario: 二次运行复用索引
- **WHEN** 语料指纹未变化时再次运行
- **THEN** 程序复用已有索引产物，不重新索引

#### Scenario: 强制重建
- **WHEN** 以 `--rebuild` 运行或语料指纹变化
- **THEN** 程序忽略旧缓存重新执行索引

### Requirement: 问题到检索模式的映射

程序 SHALL 依据问题类型选择官方检索模式：线性多跳问题（Q1）MUST 使用 local search；聚合多跳问题（Q2）MUST 使用 global search；自由问题给出默认模式。

#### Scenario: 线性多跳走 local search
- **WHEN** 提出线性多跳问题 Q1
- **THEN** 程序以 local search 检索实体邻域与相关文本单元并生成答案

#### Scenario: 聚合多跳走 global search
- **WHEN** 提出聚合问题 Q2
- **THEN** 程序以 global search 基于社区报告做 map-reduce 生成答案

### Requirement: 正确回答多跳与聚合问题

程序 SHALL 在与传统 RAG 相同的语料与问题上，对 Q1 与 Q2 给出正确答案。

#### Scenario: 多跳问题答对
- **WHEN** 向程序提出 Q1
- **THEN** 程序给出正确的最终城市答案（含链条终点实体）

#### Scenario: 聚合问题答对
- **WHEN** 向程序提出 Q2
- **THEN** 程序给出母校在指定城市的正确子公司 CEO

### Requirement: 输出以最终答案为主

由于官方框架为黑盒管线、无法逐跳打印遍历路径，程序 SHALL 默认只输出最终答案；MAY 可选展示索引产物摘要（如实体数、关系数、社区数）作为轻量过程视图。程序 MUST NOT 因缺少逐跳过程输出而中断作答。

#### Scenario: 仅输出答案
- **WHEN** 程序回答一个问题
- **THEN** 输出包含最终答案，且不要求逐跳遍历路径的打印

#### Scenario: 可选产物摘要
- **WHEN** 启用产物摘要展示
- **THEN** 程序打印索引产物的规模统计（实体/关系/社区数量等）作为过程概览
