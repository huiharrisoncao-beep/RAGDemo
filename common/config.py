"""配置加载：从环境变量读取 chat / embedding / 语料语言配置。

缺失必需项时抛出清晰的 ConfigError，而非隐晦崩溃。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv 可选
    load_dotenv = None


# 项目根目录（common/ 的上一级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ConfigError(RuntimeError):
    """配置缺失或非法。"""


def _load_env() -> None:
    if load_dotenv is not None:
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)


@dataclass
class ChatConfig:
    base_url: str
    api_key: str
    model: str


@dataclass
class EmbeddingConfig:
    provider: str  # "local" | "openai"
    model: str
    base_url: str | None = None
    api_key: str | None = None


@dataclass
class AppConfig:
    chat: ChatConfig
    embedding: EmbeddingConfig
    corpus_lang: str  # "cn" | "en"

    @property
    def docs_dir(self) -> Path:
        return PROJECT_ROOT / "Docs" / self.corpus_lang


def load_chat_config() -> ChatConfig:
    _load_env()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "sk-your-api-key-here":
        raise ConfigError(
            "缺少 OPENAI_API_KEY。请复制 .env.example 为 .env 并填入你的 chat API Key。"
        )
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com").strip()
    model = os.getenv("CHAT_MODEL", "deepseek-chat").strip()
    return ChatConfig(base_url=base_url, api_key=api_key, model=model)


def load_embedding_config() -> EmbeddingConfig:
    _load_env()
    provider = os.getenv("EMBEDDING_PROVIDER", "local").strip().lower()
    if provider not in ("local", "openai"):
        raise ConfigError(
            f"EMBEDDING_PROVIDER 非法：{provider!r}，应为 'local' 或 'openai'。"
        )
    if provider == "local":
        model = os.getenv(
            "EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
        ).strip()
        return EmbeddingConfig(provider="local", model=model)

    # openai provider：缺省复用 chat 的 OPENAI_* 配置
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small").strip()
    base_url = os.getenv("EMBEDDING_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "sk-your-api-key-here":
        raise ConfigError(
            "EMBEDDING_PROVIDER=openai 但缺少 EMBEDDING_API_KEY/OPENAI_API_KEY。"
        )
    return EmbeddingConfig(
        provider="openai", model=model, base_url=base_url, api_key=api_key
    )


def load_corpus_lang() -> str:
    _load_env()
    lang = os.getenv("CORPUS_LANG", "cn").strip().lower()
    if lang not in ("cn", "en"):
        raise ConfigError(f"CORPUS_LANG 非法：{lang!r}，应为 'cn' 或 'en'。")
    return lang


def load_config(require_chat: bool = True) -> AppConfig:
    """加载完整配置。

    require_chat=False 时允许在没有 chat key 的情况下只做检索/遍历演示。
    """
    embedding = load_embedding_config()
    corpus_lang = load_corpus_lang()
    if require_chat:
        chat = load_chat_config()
    else:
        try:
            chat = load_chat_config()
        except ConfigError:
            chat = ChatConfig(base_url="", api_key="", model="")
    return AppConfig(chat=chat, embedding=embedding, corpus_lang=corpus_lang)
