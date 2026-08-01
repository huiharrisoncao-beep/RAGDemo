"""语料加载器：按 CORPUS_LANG 读取 Docs/<lang>/ 下全部 Markdown，并按段落切块。"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .config import PROJECT_ROOT, load_corpus_lang


@dataclass
class Chunk:
    text: str
    source: str  # 来源文档文件名


def _split_paragraphs(text: str) -> List[str]:
    """按空行切分段落，过滤纯标题/空块。"""
    blocks = [b.strip() for b in text.split("\n\n")]
    chunks: List[str] = []
    for b in blocks:
        if not b:
            continue
        # 跳过仅由 Markdown 标题行组成的块
        lines = [ln for ln in b.splitlines() if ln.strip()]
        non_heading = [ln for ln in lines if not ln.lstrip().startswith("#")]
        if not non_heading:
            continue
        chunks.append(b)
    return chunks


def load_chunks(lang: str | None = None) -> List[Chunk]:
    """加载指定语言的语料并切块。"""
    lang = lang or load_corpus_lang()
    docs_dir = PROJECT_ROOT / "Docs" / lang
    if not docs_dir.exists():
        raise FileNotFoundError(f"语料目录不存在：{docs_dir}")
    chunks: List[Chunk] = []
    for md in sorted(docs_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        for para in _split_paragraphs(text):
            chunks.append(Chunk(text=para, source=md.name))
    if not chunks:
        raise ValueError(f"语料目录为空或无有效段落：{docs_dir}")
    return chunks


def corpus_fingerprint(lang: str | None = None) -> str:
    """语料内容指纹，用于缓存失效判断。"""
    lang = lang or load_corpus_lang()
    docs_dir = PROJECT_ROOT / "Docs" / lang
    h = hashlib.sha256()
    for md in sorted(docs_dir.glob("*.md")):
        h.update(md.name.encode("utf-8"))
        h.update(md.read_bytes())
    return h.hexdigest()[:16]
