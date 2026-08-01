## 1. 项目脚手架与依赖

- [x] 1.1 创建目录结构：`Docs/cn/`、`Docs/en/`、`RAG/`、`GraphRAG/`、`common/`（共享配置/LLM/embedding 客户端）
- [x] 1.2 添加 `requirements.txt`：`faiss-cpu`、`openai`、`networkx`、`sentence-transformers`、`python-dotenv`
- [x] 1.3 添加 `.env.example`，声明 `OPENAI_BASE_URL`、`OPENAI_API_KEY`、`CHAT_MODEL`、`EMBEDDING_PROVIDER`、`EMBEDDING_MODEL`、可选 `EMBEDDING_BASE_URL`/`EMBEDDING_API_KEY`、`CORPUS_LANG`
- [x] 1.4 添加 `.gitignore`（忽略 `.env`、`**/.cache/`、`__pycache__/`）

## 2. 共享层（common/）

- [x] 2.1 实现配置加载：从环境变量读取 chat / embedding / 语料语言，缺失必需项时给出清晰报错
- [x] 2.2 实现 chat 客户端封装（OpenAI 兼容 API）
- [x] 2.3 实现 embedding 封装，支持 `openai` 与 `local`（sentence-transformers）两种 provider
- [x] 2.4 实现语料加载器：按 `CORPUS_LANG` 读取 `Docs/<lang>/` 下全部 Markdown，并按段落切块（返回块文本 + 来源文档）

## 3. 语料库（demo-corpus）

- [x] 3.1 设计实体与关系清单：星环科技 + 多个子公司（含 云枢智能）、各 CEO、各母校、各城市、投资方；固定关系集 {子公司, CEO, 毕业于, 位于, 投资}
- [x] 3.2 撰写中文语料 `Docs/cn/`：`companies.md`、`leadership.md`、`people.md`、`universities.md`、`investors.md`，确保相邻跳事实跨文档且不含下一跳关键词
- [x] 3.3 自检语料：Q1 需跨 4 篇文档串联、Q2 可遍历+过滤；单篇文档无法独立回答 Q1
- [x] 3.4 生成英文平行语料 `Docs/en/`：文件名一一对应，实体中英对照命名一致
- [x] 3.5 在语料或 README 中固定两道基准问题 Q1（线性多跳）与 Q2（聚合多跳）及标准答案

## 4. 传统 RAG 程序（RAG/）

- [x] 4.1 实现切块 → embedding → 构建 Faiss 索引，并将索引与块元数据缓存到 `RAG/.cache/`
- [x] 4.2 实现二次运行命中缓存（语料未变化不重复 embedding）
- [x] 4.3 实现问答：query embedding → top-k 检索 → 拼接上下文 → chat 生成答案
- [x] 4.4 打印被召回的 top-k 语料块及来源文档
- [x] 4.5 提供 CLI 入口 `RAG/rag_qa.py`，支持传入问题或运行内置 Q1/Q2

## 5. GraphRAG 程序（GraphRAG/）

- [x] 5.1 实现实体关系抽取：LLM 按固定关系 schema 输出三元组（含来源文档），结果缓存到 `GraphRAG/.cache/graph.json`；二次运行复用
- [x] 5.2 实体轻量归一化（去空格/别名表），保证同一实体节点合并
- [x] 5.3 用 `networkx` 构建有向图，边带 `relation` 与 `source`；打印节点数/边数
- [x] 5.4 实现起点实体识别（从问题中定位图内实体）
- [x] 5.5 实现线性多跳遍历（限深 BFS，收集路径三元组）
- [x] 5.6 实现聚合多跳遍历（遍历某类邻居 + 逐个下钻 + 按属性过滤）
- [x] 5.7 实现遍历可视化：打印起点、逐跳访问序列、最终命中路径
- [x] 5.8 实现基于路径上下文的答案生成（chat）
- [x] 5.9 提供 CLI 入口 `GraphRAG/graphrag_qa.py`，支持传入问题或运行内置 Q1/Q2

## 6. 讲解材料与并排对比

- [x] 6.1 编写 `SHARING.md`：传统 RAG 原理、GraphRAG 原理（含 ASCII 数据流图）
- [x] 6.2 编写 GraphRAG 优势章节：多跳推理、跨文档串联、聚合查询、可解释路径、抗幻觉，各配可解决的问题场景
- [x] 6.3 编写贯穿式对比案例：用 Q1/Q2 展示传统 RAG 召回缺口 + GraphRAG 逐跳路径如何补全
- [x] 6.4 实现可选 `compare.py`：对同一问题并排运行两个程序并对照输出
- [x] 6.5 更新根 `README.md`：依赖安装、环境变量、如何分别运行与对比

## 7. 验证

- [x] 7.1 配置离线 embedding（`EMBEDDING_PROVIDER=local`）+ chat API，端到端跑通两个程序
- [x] 7.2 验证传统 RAG 在 Q1 召回不全、答案缺失/错误
- [x] 7.3 验证 GraphRAG 在 Q1/Q2 均答对，且逐跳路径正确打印
- [x] 7.4 切换 `CORPUS_LANG=en` 重跑，确认双语均可用
- [x] 7.5 校对 `graph.json` 抽取结果，确认无缺边导致链断裂
