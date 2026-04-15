"""LLM-backed task intent parsing with local fallback heuristics."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import httpx

from src.app.services.llm.client import OpenAICompatClient
from src.app.services.llm.modules.prompts import LPrompts

logger = logging.getLogger(__name__)


class LLMGenerateService:
    """Parse Telegram messages into task intents."""

    _INTENTS_WITH_EXPLICIT_TASK_IDS = {"set_task_due"}

    _TASK_INTENTS_WITH_ASSIGNEE = {
        "cancel_task",
        "create_task",
        "reassign_task",
        "list_member_tasks",
        "set_task_due",
    }
    _PRONOUN_USERNAMES = {
        "beliau",
        "dia",
        "doi",
        "ia",
        "mereka",
        "nya",
        "seseorang",
        "someone",
    }

    _LIST_MEMBER_TASKS_PATTERN = re.compile(
        r"(?:reminder\s+@?(?P<username_a>[A-Za-z0-9_]{3,32})(?:\s+dong)?(?:\s+task(?:\s*nya)?\s+apa\s+aja)?|@?(?P<username_b>[A-Za-z0-9_]{3,32})\s+(?:ada|punya)\s+task(?:\s*nya)?\s+apa\s+aja)",
        flags=re.IGNORECASE,
    )
    _CREATE_MENTION_PATTERN = re.compile(
        r"(?:assign|kasih(?:in)?|buat(?:in)?|tugas(?:kan|in)?|suruh)\b"
        r"(?:\s+(?:lah|dong|ya|nih|aja|task|tugas|kerjaan|kerja))*"
        r"(?:\s+(?:ke|buat|untuk))?"
        r"\s+@(?P<username>[A-Za-z0-9_]{3,32})"
        r"(?:\s+(?P<description>.+))?",
        flags=re.IGNORECASE,
    )
    _CREATE_PLAIN_PATTERN = re.compile(
        r"(?:assign|kasih(?:in)?|buat(?:in)?|tugas(?:kan|in)?|suruh)\b"
        r"(?:\s+(?:lah|dong|ya|nih|aja|task|tugas|kerjaan|kerja))*"
        r"\s+(?:ke|buat|untuk)\s+"
        r"(?P<username>[A-Za-z0-9_]{3,32})"
        r"(?:\s+(?P<description>.+))?",
        flags=re.IGNORECASE,
    )
    _REASSIGN_PATTERN = re.compile(
        r"(?:pindah(?:kan|in)?|reassign)(?:\s+task)?\s*#?(?P<task_id>\d+).*(?:ke|buat)\s+@(?P<username>[A-Za-z0-9_]{3,32})",
        flags=re.IGNORECASE,
    )
    _DONE_PATTERN = re.compile(
        r"(?:(?:task\s*)?#?(?P<task_id>\d+).*)?(?:selesai|done|beres)\b",
        flags=re.IGNORECASE,
    )
    _CANCEL_PATTERN = re.compile(
        r"(?:(?:batal(?:kan)?|cancel|g(?:a|ak)\s+jadi|nggak\s+jadi))(?:\s+task)?\s*#?(?P<task_id>\d+)?",
        flags=re.IGNORECASE,
    )
    _DUE_PATTERN = re.compile(
        r"(?:aku\s+mau\s+)?@?(?P<username>[A-Za-z0-9_]{3,32}).*?(?:s?selesai|nyelesai)i?(?:kan|in|n)?\s+task(?:\s+(?:nya|yang))?\s*(?P<description>.*?)\s+(?P<due_text>nanti\s+(?:pagi|siang|sore|malam)|besok\s+(?:pagi|siang|sore|malam)|jam\s+\d{1,2}(?:\s*(?:pagi|siang|sore|malam))?(?:\s*(?:ini|hari\s+ini))?(?:(?:\s*lewat\s*\d{1,2}(?:\s*menit)?)|(?:(?::|\.)\s*\d{1,2}))?(?:\s*(?:pagi|siang|sore|malam))?)\b",
        flags=re.IGNORECASE,
    )
    _DUE_PATTERN_SHORT = re.compile(
        r"(?:task(?:\s*nya)?\s*#?(?P<task_id>\d+).*?|aku\s+mau\s+)(?:sekarang|paling|paling\s+telat|akhir|before)?\s*(?P<due_text2>jam\s+\d{1,2}(?:\s*(?:pagi|siang|sore|malam))?(?:\s*(?:ini|hari\s+ini))?(?:(?:\s*lewat\s*\d{1,2}(?:\s*menit)?)|(?:(?::|\.)\s*\d{1,2}))?(?:\s*(?:pagi|siang|sore|malam))?)\b",
        flags=re.IGNORECASE,
    )
    _DUE_TEXT_PATTERN = re.compile(
        r"(nanti\s+(?:pagi|siang|sore|malam)|besok\s+(?:pagi|siang|sore|malam)|jam\s+\d{1,2}(?:\s*(?:pagi|siang|sore|malam))?(?:\s*(?:ini|hari\s+ini))?(?:(?:\s*lewat\s*\d{1,2}(?:\s*menit)?)|(?:(?::|\.)\s*\d{1,2}))?(?:\s*(?:pagi|siang|sore|malam))?)",
        flags=re.IGNORECASE,
    )
    _TASK_REFERENCE_PATTERN = re.compile(r"(?:\btask\s*#?|\B#)(?P<task_id>\d+)\b", flags=re.IGNORECASE)
    _REMINDER_DUE_KEYWORDS = re.compile(
        r"\b(?:ingetin|ingatkan|remind(?:er)?)\b",
        flags=re.IGNORECASE,
    )
    _CANCEL_PHRASE_PATTERN = re.compile(r"\b(?:g(?:a|ak)\s+jadi|nggak\s+jadi)\b", flags=re.IGNORECASE)
    _TASK_KEYWORDS = re.compile(
        r"\b(assign|kasih|buat|suruh|task|tugas|kerjaan|kerja|selesai|done|beres|batal|cancel|reassign|pindah|reminder|ingetin|ingatkan|deadline|due|nanti|besok|jam)\b",
        flags=re.IGNORECASE,
    )

    def __init__(
        self,
        llm_url: str,
        llm_header_api_key: str = "",
        llm_model_api_key: str = "",
        llm_agent_id: str = "",
        llm_output_type: str = "json",
        llm_model_name: str = "",
        llm_api_key: str = "",
        rag_enabled: bool = False,
        rag_file_ids: list[str] | None = None,
        rag_include_sources: bool = True,
        rag_max_context_chunks: int = 0,
        rag_score_threshold: str | float | None = None,
    ):
        self.llm_url = llm_url.rstrip("/")
        self.llm_api_key = (llm_api_key or llm_model_api_key or llm_header_api_key or "").strip()
        self.llm_model_name = (llm_model_name or "").strip()
        self.llm_agent_id = llm_agent_id
        self.llm_output_type = llm_output_type or "json"
        self.rag_enabled = rag_enabled
        self.rag_file_ids = rag_file_ids or []
        self.rag_include_sources = rag_include_sources
        self.rag_max_context_chunks = max(0, int(rag_max_context_chunks or 0))
        self.rag_score_threshold = rag_score_threshold
        self.prompts = LPrompts()
        self.client = OpenAICompatClient(
            base_url=self.llm_url,
            model_name=self.llm_model_name,
            api_key=self.llm_api_key,
        )

    async def parse_intent(
        self,
        message_text: str,
        reply_text: str | None = None,
    ) -> dict[str, Any]:
        clean_text = self._sanitize(message_text)
        if not clean_text or (not self._TASK_KEYWORDS.search(clean_text) and not self._CANCEL_PHRASE_PATTERN.search(clean_text)):
            logger.info("Parser skipped message because no task keywords matched: %r", clean_text)
            return self._unknown()

        if self._can_call_llm():
            logger.info("Trying LLM parser for message: %r", clean_text)
            parsed = await self._parse_with_llm(clean_text, reply_text)
            if parsed.get("intent") != "unknown":
                logger.info("LLM parser produced non-unknown intent: %s", parsed)
                return self._normalize(parsed, clean_text)
            logger.info("LLM parser returned unknown, falling back to local heuristics")

        logger.info("Using fallback parser for message: %r", clean_text)
        return self._fallback_parse(clean_text, reply_text)

    def _can_call_llm(self) -> bool:
        return self.client.is_enabled

    async def _parse_with_llm(self, message_text: str, reply_text: str | None) -> dict[str, Any]:
        system_prompt = self.prompts.get_system_prompt()
        user_prompt = self.prompts.get_parse_prompt(message_text, reply_text)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            logger.info(
                "Sending task parser request: url=%s model=%s output_type=%s",
                self.client.chat_completions_url,
                self.llm_model_name,
                self.llm_output_type,
            )
            response_payload = await self.client.create_chat_completion(messages, temperature=0.0)
            parsed = self._parse_output(response_payload)
            logger.info("LLM parser parsed output: %s", parsed)
            return parsed
        except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
            logger.warning("Task parser LLM timed out: %s", exc)
            return self._unknown()
        except Exception as exc:
            logger.warning("Task parser LLM request failed: %s", exc)
            return self._unknown()

    def _parse_output(self, payload: Any) -> dict[str, Any]:
        output = OpenAICompatClient.extract_text(payload)
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except json.JSONDecodeError:
                return self._unknown()
        return output if isinstance(output, dict) else self._unknown()

    def _fallback_parse(self, message_text: str, reply_text: str | None) -> dict[str, Any]:
        match = self._LIST_MEMBER_TASKS_PATTERN.search(message_text)
        if match:
            logger.info("Fallback parser matched list_member_tasks")
            return self._normalize(
                {
                    "intent": "list_member_tasks",
                    "task_id": None,
                    "assignee_username": match.group("username_a") or match.group("username_b"),
                    "description": None,
                    "due_text": None,
                },
                message_text,
            )

        match = self._DUE_PATTERN.search(message_text)
        if match:
            logger.info("Fallback parser matched set_task_due")
            return self._normalize(
                {
                    "intent": "set_task_due",
                    "task_id": None,
                    "assignee_username": match.group("username"),
                    "description": match.group("description"),
                    "due_text": match.group("due_text"),
                },
                message_text,
            )

        match = self._DUE_PATTERN_SHORT.search(message_text)
        if match:
            logger.info("Fallback parser matched set_task_due (short)")
            return self._normalize(
                {
                    "intent": "set_task_due",
                    "task_id": self._extract_task_id(message_text) or match.group("task_id"),
                    "assignee_username": None,
                    "description": None,
                    "due_text": match.group("due_text2"),
                },
                message_text,
            )

        due_text = self._extract_due_text(message_text)
        if due_text and self._REMINDER_DUE_KEYWORDS.search(message_text):
            logger.info("Fallback parser matched set_task_due via reminder phrase")
            return self._normalize(
                {
                    "intent": "set_task_due",
                    "task_id": self._extract_task_id(message_text) or self._extract_task_id(reply_text),
                    "assignee_username": None,
                    "description": None,
                    "due_text": due_text,
                },
                message_text,
            )

        match = self._CREATE_MENTION_PATTERN.search(message_text) or self._CREATE_PLAIN_PATTERN.search(message_text)
        if match:
            logger.info("Fallback parser matched create_task")
            return self._normalize(
                {
                    "intent": "create_task",
                    "task_id": None,
                    "assignee_username": match.group("username"),
                    "description": match.group("description"),
                    "due_text": None,
                },
                message_text,
            )

        match = self._REASSIGN_PATTERN.search(message_text)
        if match:
            logger.info("Fallback parser matched reassign_task")
            return self._normalize(
                {
                    "intent": "reassign_task",
                    "task_id": match.group("task_id"),
                    "assignee_username": match.group("username"),
                    "description": None,
                    "due_text": None,
                },
                message_text,
            )

        match = self._DONE_PATTERN.search(message_text)
        if match:
            logger.info("Fallback parser matched mark_done")
            return self._normalize(
                {
                    "intent": "mark_done",
                    "task_id": match.group("task_id") or self._extract_task_id(reply_text),
                    "assignee_username": None,
                    "description": None,
                    "due_text": None,
                },
                message_text,
            )

        match = self._CANCEL_PATTERN.search(message_text)
        if match:
            logger.info("Fallback parser matched cancel_task")
            return self._normalize(
                {
                    "intent": "cancel_task",
                    "task_id": match.group("task_id") or self._extract_task_id(reply_text),
                    "assignee_username": None,
                    "description": None,
                    "due_text": None,
                },
                message_text,
            )

        logger.info("Fallback parser could not determine intent")
        return self._unknown()

    def _normalize(self, parsed: dict[str, Any], raw_text: str) -> dict[str, Any]:
        usernames = self._extract_usernames(raw_text)
        description = self._sanitize(parsed.get("description"))
        assignee_username = self._sanitize_username(parsed.get("assignee_username"))
        if assignee_username in self._PRONOUN_USERNAMES:
            assignee_username = None

        explicit_task_id = self._extract_task_id(raw_text)
        task_id = parsed.get("task_id")
        try:
            task_id = int(task_id) if task_id is not None else None
        except (TypeError, ValueError):
            task_id = explicit_task_id

        normalized = {
            "intent": parsed.get("intent") if parsed.get("intent") in {
                "create_task",
                "reassign_task",
                "mark_done",
                "cancel_task",
                "list_member_tasks",
                "set_task_due",
            } else "unknown",
            "task_id": task_id,
            "assignee_username": assignee_username,
            "description": description or None,
            "due_text": self._sanitize(parsed.get("due_text")) or None,
        }

        if explicit_task_id is not None:
            normalized["task_id"] = explicit_task_id
        elif normalized["intent"] in self._INTENTS_WITH_EXPLICIT_TASK_IDS:
            normalized["task_id"] = None

        if usernames and normalized["intent"] in self._TASK_INTENTS_WITH_ASSIGNEE:
            if assignee_username is None and len(usernames) == 1:
                normalized["assignee_username"] = usernames[0]
            elif len(usernames) == 1 and assignee_username not in usernames:
                normalized["assignee_username"] = usernames[0]

        normalized_assignee = normalized["assignee_username"]
        if normalized["intent"] == "create_task" and normalized["description"] is None and normalized_assignee:
            marker = f"@{normalized_assignee}"
            idx = raw_text.lower().find(marker.lower())
            if idx >= 0:
                normalized["description"] = self._sanitize(raw_text[idx + len(marker):]) or None
        return normalized

    @staticmethod
    def _sanitize(text: Any) -> str:
        if text is None:
            return ""
        return re.sub(r"\s+", " ", str(text)).strip()

    @staticmethod
    def _sanitize_username(username: Any) -> str | None:
        if username is None:
            return None
        cleaned = str(username).strip().lstrip("@").lower()
        return cleaned or None

    @staticmethod
    def _extract_task_id(text: str | None) -> int | None:
        if not text:
            return None
        match = LLMGenerateService._TASK_REFERENCE_PATTERN.search(text)
        return int(match.group("task_id")) if match else None

    @staticmethod
    def _extract_usernames(text: str | None) -> list[str]:
        if not text:
            return []
        return [item.lower() for item in re.findall(r"@([A-Za-z0-9_]{3,32})", text)]

    @classmethod
    def _extract_due_text(cls, text: str | None) -> str | None:
        if not text:
            return None
        match = cls._DUE_TEXT_PATTERN.search(text)
        return cls._sanitize(match.group(1)) if match else None

    @staticmethod
    def _unknown() -> dict[str, Any]:
        return {
            "intent": "unknown",
            "task_id": None,
            "assignee_username": None,
            "description": None,
            "due_text": None,
        }
