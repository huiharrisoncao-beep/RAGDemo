"""传统 RAG 问答程序。

流程：语料切块 → embedding → 构建 Faiss 索引（落盘缓存）
     → 查询 embedding → top-k 检索 → 拼接上下文 → chat 生成。

用法：
    python RAG/rag_qa.py            # 运行内置 Q1/Q2
    python RAG/rag_qa.py "你的问题"  # 自定义问题
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

# 允许直接以脚本方式运行（把项目根加入 sys.path）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.chat import ChatClient  # noqa: E402
from common.config import ConfigError, load_config  # noqa: E402
from common.corpus import corpus_fingerprint, load_chunks  # noqa: E402
from common.embedding import Embedder  # noqa: E402
from common.questions import get_questions  # noqa: E402

CACHE_DIR = Path(__file__).resolve().parent / ".cache"
TOP_K = 3

SYSTEM_PROMPT = (
    "你是一个严谨的问答助手。只能依据提供的【上下文】回答问题。"
    "如果上下文中没有足够信息来回答，必须明确说明“根据现有资料无法确定”，"
    "不要臆测或编造。"
)


class VectorStore:
    """基于 Faiss 的向量库，带磁盘缓存。"""

    def __init__(self, embedder: Embedder, lang: str):
        self.embedder = embedder
        self.lang = lang
        self.chunks = load_chunks(lang)
        self.index = None
        self._build_or_load()

    def _cache_paths(self):
        fp = corpus_fingerprint(self.lang)
        tag = f"{self.lang}_{self.embedder.config.provider}_{fp}"
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        return (
            CACHE_DIR / f"index_{tag}.faiss",
            CACHE_DIR / f"meta_{tag}.json",
        )

    def _build_or_load(self):
        import faiss

        index_path, meta_path = self._cache_paths()
        if index_path.exists() and meta_path.exists():
            print(f"[RAG] 命中缓存，加载已有索引：{index_path.name}")
            self.index = faiss.read_index(str(index_path))
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self.chunk_texts = meta["texts"]
            self.chunk_sources = meta["sources"]
            return

        print(f"[RAG] 未命中缓存，开始为 {len(self.chunks)} 个语料块生成 embedding …")
        texts = [c.text for c in self.chunks]
        sources = [c.source for c in self.chunks]
        vectors = np.array(self.embedder.embed(texts), dtype="float32")
        dim = vectors.shape[1]
        index = faiss.IndexFlatIP(dim)  # 归一化向量下内积≈余弦
        faiss.normalize_L2(vectors)
        index.add(vectors)
        self.index = index
        self.chunk_texts = texts
        self.chunk_sources = sources

        faiss.write_index(index, str(index_path))
        meta_path.write_text(
            json.dumps({"texts": texts, "sources": sources}, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"[RAG] 索引已构建并缓存到 {index_path.name}")

    def search(self, query: str, top_k: int = TOP_K):
        import faiss

        qv = np.array([self.embedder.embed_one(query)], dtype="float32")
        faiss.normalize_L2(qv)
        scores, ids = self.index.search(qv, top_k)
        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0:
                continue
            results.append(
                {
                    "score": float(score),
                    "text": self.chunk_texts[idx],
                    "source": self.chunk_sources[idx],
                }
            )
        return results


def answer(store: VectorStore, chat: ChatClient | None, question: str):
    print("\n" + "=" * 70)
    print(f"[传统 RAG] 问题：{question}")
    print("-" * 70)
    hits = store.search(question)
    print(f"[检索] top-{len(hits)} 召回片段：")
    for i, h in enumerate(hits, 1):
        snippet = h["text"].replace("\n", " ")
        print(f"  {i}. (score={h['score']:.3f}, 来源={h['source']}) {snippet[:60]}…")

    context = "\n\n".join(
        f"[来源：{h['source']}] {h['text']}" for h in hits
    )
    if chat is None:
        print("\n[生成] 未配置 chat API，仅展示召回上下文（无法生成最终答案）。")
        return

    user = f"【上下文】\n{context}\n\n【问题】{question}"
    result = chat.complete(SYSTEM_PROMPT, user)
    print(f"\n[生成] 答案：\n{result}")


def main():
    try:
        cfg = load_config(require_chat=False)
    except ConfigError as e:
        print(f"配置错误：{e}")
        sys.exit(1)

    embedder = Embedder(cfg.embedding)
    store = VectorStore(embedder, cfg.corpus_lang)

    chat = None
    if cfg.chat.api_key:
        chat = ChatClient(cfg.chat)
    else:
        print("[提示] 未配置 chat API Key，将只展示召回结果。")

    args = sys.argv[1:]
    if args:
        answer(store, chat, " ".join(args))
    else:
        qs = get_questions(cfg.corpus_lang)
        for q in qs.values():
            answer(store, chat, q.text)


if __name__ == "__main__":
    main()
