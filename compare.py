"""并排对比：对同一问题分别运行传统 RAG 与 GraphRAG，直观展示差异。

用法：
    python compare.py            # 对比内置 Q1/Q2
    python compare.py "你的问题"  # 对比自定义问题
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common.chat import ChatClient  # noqa: E402
from common.config import ConfigError, load_config  # noqa: E402
from common.embedding import Embedder  # noqa: E402
from common.questions import get_questions  # noqa: E402

import importlib.util  # noqa: E402


def _load(module_name, rel_path):
    spec = importlib.util.spec_from_file_location(
        module_name, Path(__file__).resolve().parent / rel_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    try:
        cfg = load_config(require_chat=False)
    except ConfigError as e:
        print(f"配置错误：{e}")
        sys.exit(1)

    chat = ChatClient(cfg.chat) if cfg.chat.api_key else None

    rag = _load("rag_qa", "RAG/rag_qa.py")
    graph = _load("graphrag_qa", "GraphRAG/graphrag_qa.py")

    # 传统 RAG 向量库
    embedder = Embedder(cfg.embedding)
    store = rag.VectorStore(embedder, cfg.corpus_lang)

    # GraphRAG 图
    triples = graph.extract_triples(chat, cfg.corpus_lang)
    g = graph.build_graph(triples)

    qs = get_questions(cfg.corpus_lang)
    if len(sys.argv) > 1:
        fb = [e for q in qs.values() for e in q.start_entities]
        pairs = [(" ".join(sys.argv[1:]), fb)]
    else:
        pairs = [(q.text, q.start_entities) for q in qs.values()]

    for question, starts in pairs:
        print("\n" + "#" * 72)
        print(f"# 对比问题：{question}")
        print("#" * 72)
        print("\n>>> 方案 A：传统 RAG")
        rag.answer(store, chat, question)
        print("\n>>> 方案 B：GraphRAG")
        graph.answer(g, chat, question, starts)


if __name__ == "__main__":
    main()
