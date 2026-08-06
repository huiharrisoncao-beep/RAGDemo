## Why

现有 `TEGraphRAG/` 是**手写的教学向轻量 GraphRAG**（固定关系集 + `networkx` + 显式 BFS），并**没有真正使用微软的 GraphRAG 框架**。知识分享时观众会问"官方 GraphRAG 到底怎么工作、和手写版有何不同"。为此需要基于**微软官方 `graphrag` 框架**、用**同一份语料库**、回答**同一批多跳问题**（Q1 线性多跳 / Q2 聚合多跳），交付一个可开箱运行的对照程序，直观呈现"社区检测 + local/global search"与"显式多跳遍历"两条技术路线的差异。

## What Changes

- **新增微软 GraphRAG 问答程序** `MicrosoftGraphRAG/`：调用官方 `graphrag` 框架完成 **索引（index）→ 查询（query）** 全流程，复用 `common/` 的配置、语料与基准问题，保证与 `RAG/`、`TEGraphRAG/` 三者语料与问题一致、对比公平。
- **同一份语料库**：把 `Docs/<lang>/*.md` 物化为 GraphRAG 要求的 `input/*.txt` 输入，不改写语料内容。
- **索引流程**：首次运行触发官方索引管线（分块 → 实体/关系抽取 → Leiden 社区发现 → 社区报告 → 向量化），产物（parquet）缓存到 `MicrosoftGraphRAG/` 下，语料指纹变化或 `--rebuild` 时重建。
- **问题 → 检索模式映射**：Q1（实体锚定的线性多跳）走 **local search**；Q2（跨子公司聚合）走 **global search**；自由问题给出默认模式。复用 `common/questions.py` 的 Q1/Q2 与交互循环。
- **Embedding 走本地 Ollama**：chat 仍用现有 DeepSeek（`common/config.py`），embedding 指向本机 Ollama 的 OpenAI 兼容端点（`http://localhost:11434/v1`，模型 `embeddinggemma`，768 维，已验证可用），使索引所需的向量化**离线、免费**，并让 local search 可用。
- **过程可视化让步**：官方框架是黑盒管线，**无法逐跳打印**遍历路径（这是与 `TEGraphRAG` 的本质差异）；按需求"输出过程细节做不到就不输出"，本程序默认只输出最终答案，可选地展示索引产物摘要（实体/社区数量）作为轻量过程视图。
- **依赖与文档**：`requirements.txt` 增加 `graphrag`；`README.md` 增补运行方式与 Ollama embedding 前置条件。

## Capabilities

### New Capabilities
- `microsoft-graphrag-qa`: 基于微软官方 `graphrag` 框架的问答程序——用同一语料与同一 Q1/Q2 完成索引与 local/global 查询，以本机 Ollama `embeddinggemma` 作为 embedding 后端；作为手写 `graphrag-qa` 的官方框架对照。

### Modified Capabilities
<!-- 无既有 spec 的需求变更；graphrag-qa（手写版）保持不变，本次为独立新增能力。 -->

## Impact

- **新增目录/代码**：`MicrosoftGraphRAG/`（问答入口 `msgraphrag_qa.py`、生成的 `settings.yaml`/`.env`、`input/` 与索引产物缓存）。
- **依赖**：新增 `graphrag`（官方框架，较重）；运行期依赖本机 **Ollama** 已拉起 `embeddinggemma`。
- **外部依赖/配置**：chat 复用现有 DeepSeek 的 `OPENAI_*`；embedding 走 `http://localhost:11434/v1`（dummy key）。索引会产生多次 LLM 调用（抽取 + 社区报告），对小语料成本可控。
- **无破坏性变更**：`common/`、`RAG/`、`TEGraphRAG/` 均不改动行为；`common/config.py` 若需扩展 embedding 端点为可选增强，不影响既有默认。
