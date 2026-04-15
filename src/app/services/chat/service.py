"""General-purpose chat service backed by an OpenAI-compatible LLM API."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import Any

import httpx
from sqlalchemy.orm import Session

from src.app.services.chat.prompts import ChatPrompts
from src.app.services.llm.client import OpenAICompatClient

logger = logging.getLogger(__name__)

# Max conversation turns to keep per scope (each turn = 1 user + 1 assistant message)
_MAX_HISTORY_TURNS = 10


class ChatAgentService:
    """Call an OpenAI-compatible chat completion API for general responses."""

    def __init__(
        self,
        llm_url: str,
        llm_model_name: str,
        llm_api_key: str = "",
    ):
        self.client = OpenAICompatClient(
            base_url=llm_url,
            model_name=llm_model_name,
            api_key=llm_api_key,
        )
        self.prompts = ChatPrompts()
        # In-memory conversation history: scope_chat_id -> deque of (role, text)
        self._history: dict[int, deque[tuple[str, str]]] = {}

    async def chat(
        self,
        message_text: str,
        user_name: str | None = None,
        db: Session | None = None,
        scope_chat_id: int | None = None,
    ) -> str | None:
        """Send a message to the LLM and return the response text."""
        if not self.client.is_enabled:
            logger.info("Chat LLM skipped: no URL or model configured")
            return None

        context_block = self._build_context(db, scope_chat_id)
        history_block = self._format_history(scope_chat_id)
        user_context = f"[{user_name}]: " if user_name else ""
        current_msg = f"{user_context}{message_text}"

        # Combine: context + history + current message
        prompt_parts: list[str] = []
        if context_block:
            prompt_parts.append(context_block)
        if history_block:
            prompt_parts.append(history_block)
        prompt_parts.append(current_msg)
        user_prompt = "\n\n".join(prompt_parts)

        messages = [
            {"role": "system", "content": self.prompts.get_system_prompt()},
            {"role": "user", "content": user_prompt},
        ]

        try:
            logger.info("Sending chat LLM request: model=%s", self.client.model_name)
            response_payload = await self.client.create_chat_completion(messages, temperature=0.4)
            reply = self._extract_text(response_payload)
            # Save to history
            if scope_chat_id is not None:
                self._add_to_history(scope_chat_id, "user", f"{user_context}{message_text}")
                if reply:
                    self._add_to_history(scope_chat_id, "assistant", reply)
            return reply
        except (httpx.TimeoutException, asyncio.TimeoutError):
            logger.warning("Chat LLM timed out")
            return None
        except Exception:
            logger.exception("Chat LLM request failed")
            return None

    def _add_to_history(self, scope_chat_id: int, role: str, text: str) -> None:
        """Add a message to the conversation history for this scope."""
        if scope_chat_id not in self._history:
            self._history[scope_chat_id] = deque(maxlen=_MAX_HISTORY_TURNS * 2)
        self._history[scope_chat_id].append((role, text))

    def _format_history(self, scope_chat_id: int | None) -> str | None:
        """Format conversation history as a chat log for the prompt."""
        if scope_chat_id is None or scope_chat_id not in self._history:
            return None
        history = self._history[scope_chat_id]
        if not history:
            return None
        lines = []
        for role, text in history:
            label = "User" if role == "user" else "Kamu"
            lines.append(f"{label}: {text}")
        return "[Riwayat chat sebelumnya]:\n" + "\n".join(lines)

    def _build_context(self, db: Session | None, scope_chat_id: int | None) -> str | None:
        """Build group context from database: known members and open tasks."""
        if db is None or scope_chat_id is None:
            return None

        parts: list[str] = []

        # All known members (everyone who ever chatted or got assigned a task)
        try:
            from src.app.models import Member

            members = db.query(Member).filter(Member.is_active == True).all()  # noqa: E712
            names = []
            for m in members:
                if m.full_name and m.username:
                    names.append(f"{m.full_name} (@{m.username})")
                elif m.username:
                    names.append(f"@{m.username}")
                elif m.full_name:
                    names.append(m.full_name)
            if names:
                parts.append(f"Anggota grup yang dikenal: {', '.join(names)}")
        except Exception:
            logger.debug("Failed to build member context", exc_info=True)

        # Open task count
        try:
            from src.app.models import Task

            open_count = (
                db.query(Task)
                .filter(Task.scope_chat_id == scope_chat_id, Task.status == "assigned")
                .count()
            )
            if open_count > 0:
                parts.append(f"Task aktif saat ini: {open_count}")
        except Exception:
            logger.debug("Failed to build task count context", exc_info=True)

        return "[Konteks grup]: " + "; ".join(parts) if parts else None

    @staticmethod
    def _extract_text(payload: Any) -> str | None:
        """Extract the response text from an OpenAI-compatible payload."""
        return OpenAICompatClient.extract_text(payload)
