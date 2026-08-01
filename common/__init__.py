"""共享层：配置、LLM/embedding 客户端、语料加载。

两个程序（RAG/ 与 GraphRAG/）都复用这里的组件，保证：
- chat 与 embedding 配置解耦（应对 DeepSeek 等无 embedding 接口的服务）
- 语料语言可通过 CORPUS_LANG 切换（cn/en）
"""
