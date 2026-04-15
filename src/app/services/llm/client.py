"""OpenAI-compatible HTTP client helpers for direct LLM access."""

from __future__ import annotations

from typing import Any

import httpx


class OpenAICompatClient:
    """Minimal client for OpenAI-compatible chat completion APIs such as vLLM."""

    def __init__(
        self,
        base_url: str,
        model_name: str,
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = (model_name or "").strip()
        self.api_key = (api_key or "").strip()
        self.timeout = timeout

    @property
    def is_enabled(self) -> bool:
        return bool(self.base_url and self.model_name)

    @property
    def chat_completions_url(self) -> str:
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/chat/completions"
        return f"{self.base_url}/v1/chat/completions"

    def build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def create_chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.chat_completions_url,
                headers=self.build_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    def extract_text(payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None

        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            choice = choices[0]
            if isinstance(choice, dict):
                message = choice.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str) and content.strip():
                        return content.strip()
                    if isinstance(content, list):
                        parts: list[str] = []
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                                parts.append(item["text"])
                        joined = "".join(parts).strip()
                        if joined:
                            return joined
                text = choice.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()

        output = payload.get("output") or payload.get("result")
        if isinstance(output, str) and output.strip():
            return output.strip()
        return None
