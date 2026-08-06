## 1. 依赖与前置校验

- [x] 1.1 在 `requirements.txt` 增加并锁定 `graphrag` 版本
- [x] 1.2 在 `MicrosoftGraphRAG/` 实现启动前校验：Ollama 端点（默认 `http://localhost:11434/v1`）可达且 `embeddinggemma` 可用，失败时给出清晰提示
- [x] 1.3 在 `README.md` 增补前置条件（`ollama pull embeddinggemma`）与运行说明

## 2. 配置桥接与语料物化

- [x] 2.1 从 `common/config.py` 读取 chat（DeepSeek）配置，从环境变量读取可选 `OLLAMA_BASE_URL`/`GRAPHRAG_EMBED_MODEL`（默认 `http://localhost:11434/v1`、`embeddinggemma`）
- [x] 2.2 生成官方 `settings.yaml` 与 `.env`：chat=DeepSeek，embedding=Ollama（含调小 `batch_size`/并发以适配 Ollama）
- [x] 2.3 将 `Docs/<lang>/*.md` 物化为 `MicrosoftGraphRAG/ragtest/<lang>/input/*.txt`，不改写内容
- [x] 2.4 用 `common/corpus.corpus_fingerprint(lang)` 作为索引缓存键

## 3. 索引流程

- [x] 3.1 以子进程调用 `graphrag index` 运行官方索引管线，产物缓存到 `MicrosoftGraphRAG/` 下
- [x] 3.2 实现缓存命中判断：指纹未变复用产物；`--rebuild` 或指纹变化则重建
- [x] 3.3 索引失败时输出可诊断的错误信息（区分 embedding 端点问题与 chat/prompt 解析问题）

## 4. 查询与问题路由

- [x] 4.1 用 `graphrag.api` 实现 local search 与 global search 查询封装
- [x] 4.2 依据 `common/questions.py` 的 `kind` 路由：`linear`(Q1)→local、`aggregate`(Q2)→global、自由问题默认 local
- [x] 4.3 复用 `common/questions.run_interactive` 提供交互循环与 Q1/Q2 快捷选择
- [x] 4.4 支持命令行单问模式：`python MicrosoftGraphRAG/msgraphrag_qa.py "问题"`

## 5. 输出与可选产物摘要

- [x] 5.1 默认只输出最终答案（不强求逐跳过程）
- [x] 5.2 可选：读取索引产物 parquet，打印实体数/关系数/社区数作为轻量过程视图

## 6. 验证

- [x] 6.1 中文语料下 Q1 走 local search 给出正确城市答案（含链条终点）
- [x] 6.2 中文语料下 Q2 走 global search 给出正确子公司 CEO
- [x] 6.3 二次运行复用索引不重跑；`--rebuild` 能强制重建
- [x] 6.4 `CORPUS_LANG=en` 下 Q1/Q2 同样可跑通
