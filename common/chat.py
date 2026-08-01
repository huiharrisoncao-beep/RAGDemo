"""Chat 客户端封装（OpenAI 兼容 API）。"""
from __future__ import annotations

from .config import ChatConfig, load_chat_config


class ChatClient:
    def __init__(self, config: ChatConfig | None = None):
        self.config = config or load_chat_config()
        from openai import OpenAI

        self._client = OpenAI(
            base_url=self.config.base_url, api_key=self.config.api_key
        )

    def complete(self, system: str, user: str, temperature: float = 0.0) -> str:
        """给定 system/user 提示，返回生成文本。"""
        resp = self._client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        return (resp.choices[0].message.content or "").strip()
