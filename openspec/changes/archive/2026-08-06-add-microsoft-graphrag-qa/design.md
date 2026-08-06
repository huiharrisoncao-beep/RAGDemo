## Context

仓库已有两个问答程序共享 `common/`（配置、chat、语料、基准问题 Q1/Q2）：`RAG/`（向量检索）与 `TEGraphRAG/`（手写轻量 GraphRAG，固定关系集 + `networkx` + 显式 BFS + 逐跳打印）。`TEGraphRAG` 并未使用微软官方 `graphrag` 框架。本变更新增 `MicrosoftGraphRAG/`，用**官方框架**、**同一语料**、**同一 Q1/Q2** 做对照。

关键现状约束：
- chat 为 DeepSeek（OpenAI 兼容），**无 embedding 接口**；`common/config.py` 的 embedding 默认走本地 `sentence-transformers`（非 HTTP 端点）。
- 官方 `graphrag` 索引需要一个 OpenAI 兼容的 `/embeddings` 端点。
- 本机已用 **Ollama** 部署 `embeddinggemma`（`http://localhost:11434/v1`，768 维，已 `curl` 验证返回向量）。
- 语料在 `Docs/<lang>/*.md`；官方框架输入约定为 `input/*.txt`。

## Goals / Non-Goals

**Goals:**
- 用官方 `graphrag` 框架跑通 index → query，正确回答 Q1（线性多跳）与 Q2（聚合多跳）。
- 复用 `common/` 的语料与 Q1/Q2，保证与 `RAG/`、`TEGraphRAG/` 对比公平。
- Embedding 用本机 Ollama `embeddinggemma`，全程离线、免费，且使 local search 可用。
- 索引产物可缓存复用，语料指纹变化或 `--rebuild` 时重建。

**Non-Goals:**
- 不复刻 `TEGraphRAG` 的逐跳遍历可视化（官方管线是黑盒，无法逐跳打印）。
- 不改写语料内容，不改动 `RAG/`、`TEGraphRAG/`、`common/` 既有行为。
- 不追求生产级调优（并发、成本、大语料）；面向教学演示。
- 不替换手写版；两者并存作为对照。

## Decisions

### D1: 用官方 `graphrag` 框架，chat=DeepSeek，embedding=Ollama `embeddinggemma`
在生成的 `settings.yaml` 中配置两套 model：chat 指向现有 DeepSeek（复用 `common/config.py` 的 base_url/key/model）；embedding 指向 `http://localhost:11434/v1`、模型 `embeddinggemma`、dummy key。
- 备选：全用 OpenAI（需额外付费 key，违背离线目标）；global-search-only 跳过 embedding（Q1 是 local 问题会退化，且默认索引仍会向量化）。均劣于 Ollama 方案。

### D2: 索引用 CLI 子进程，查询用 Python API
`graphrag index` 以子进程执行（官方主推、稳定）；查询用 `graphrag.api`（`local_search` / `global_search`）便于复用 `common/` 配置并直接拿到答案文本。
- 备选：全 CLI（查询需解析 stdout，脆弱）；全 Python API（索引 API 版本耦合更重）。折中取两者优点。

### D3: 问题 → 检索模式映射
Q1（实体锚定线性多跳）→ **local search**；Q2（跨子公司聚合）→ **global search**；自由问题默认 local。此映射本身即教学点：官方框架用两种 search 模式覆盖手写版靠一套 BFS 覆盖的两类问题。
- 依据 `common/questions.py` 中 `kind` 字段（`linear`/`aggregate`）自动路由。

### D4: 语料物化与缓存失效
将 `Docs/<lang>/*.md` 复制/转写为 `MicrosoftGraphRAG/ragtest/<lang>/input/*.txt`；用 `common/corpus.corpus_fingerprint(lang)` 作为索引缓存键；指纹变化或 `--rebuild` 时重跑 index，否则复用 parquet 产物。

### D5: 过程输出让步 + 轻量产物摘要
默认只打印最终答案。可选打印索引产物摘要（实体数、关系数、社区数，读 parquet 统计），作为"能做到"的轻量过程视图，替代无法实现的逐跳路径。

### D6: 配置桥接方式
新增 `MicrosoftGraphRAG/` 内部的配置生成逻辑，从 `common/config.py` 读取 chat 配置 + 从环境变量（新增可选 `OLLAMA_BASE_URL`/`GRAPHRAG_EMBED_MODEL`，默认 `http://localhost:11434/v1` 与 `embeddinggemma`）生成 `settings.yaml`/`.env`，不侵入 `common/` 既有默认。

## Risks / Trade-offs

- [官方框架 `settings.yaml` 结构随版本变动] → 锁定 `requirements.txt` 中 `graphrag` 版本，生成配置集中在一处便于适配。
- [Ollama embedding 与官方默认批处理/参数不匹配导致索引报错] → 在 `settings.yaml` 调小 embedding `batch_size`、设置合适并发，必要时限制 max tokens。
- [DeepSeek 与官方 prompt 兼容性（抽取/社区报告输出格式）] → 保持官方默认 prompt；小语料先跑通，若解析失败再微调 prompt 或温度。
- [索引多次 LLM 调用带来时延/成本] → 小语料（5 篇）可控；结果缓存，二次运行不重复索引。
- [local search 未必一次覆盖 3 跳] → 依赖官方检索把相关实体/关系/文本单元召回后由 LLM 串联；若 Q1 不达标，考虑对该问句改走 drift/global 或调 local 检索参数。

## Migration Plan

纯新增，无迁移。落地顺序：加依赖 → 前置校验 Ollama/`embeddinggemma` 可达 → 物化 input → 生成 settings → index（缓存）→ query 路由 → README 说明。回滚：删除 `MicrosoftGraphRAG/` 与 `requirements.txt` 中新增行即可，不影响其他程序。

## Open Questions

- 是否需要把 `MicrosoftGraphRAG` 也接入 `compare.py` 的并排对比？（本次先独立入口，后续可选）
- 轻量产物摘要展示到什么粒度（仅计数 vs. 列出命中社区标题）？实现时按演示效果定。
