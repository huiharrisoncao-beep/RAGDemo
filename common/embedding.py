"""Embedding 封装：支持 local（sentence-transformers）与 openai 两种 provider。

与 chat 解耦，使得 chat 用 DeepSeek、embedding 用本地模型的组合可运行。
"""
from __future__ import annotations

from typing import List

from .config import EmbeddingConfig, load_embedding_config


class Embedder:
    def __init__(self, config: EmbeddingConfig | None = None):
        self.config = config or load_embedding_config()
        self._backend = None  # 懒加载

    # -- 公共接口 --
    def embed(self, texts: List[str]) -> "list[list[float]]":
        if self.config.provider == "local":
            return self._embed_local(texts)
        return self._embed_openai(texts)

    def embed_one(self, text: str) -> "list[float]":
        return self.embed([text])[0]

    @property
    def dim(self) -> int:
        # 通过一次探测获取维度
        return len(self.embed_one("dimension probe"))

    # -- local backend --
    def _embed_local(self, texts: List[str]) -> "list[list[float]]":
        if self._backend is None:
            from sentence_transformers import SentenceTransformer

            self._backend = SentenceTransformer(self.config.model)
        vectors = self._backend.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True
        )
        return vectors.tolist()

    # -- openai backend --
    def _embed_openai(self, texts: List[str]) -> "list[list[float]]":
        if self._backend is None:
            from openai import OpenAI

            self._backend = OpenAI(
                base_url=self.config.base_url, api_key=self.config.api_key
            )
        resp = self._backend.embeddings.create(
            model=self.config.model, input=texts
        )
        return [item.embedding for item in resp.data]
