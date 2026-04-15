"""Facade service for parsing task intents via direct LLM calls and fallback heuristics."""

from __future__ import annotations

from src.app.services.llm.modules import LLMGenerateService


class TaskIntentParserService:
    """Service wrapper for task intent parsing."""

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
        self.generate = LLMGenerateService(
            llm_url=llm_url,
            llm_header_api_key=llm_header_api_key,
            llm_model_api_key=llm_model_api_key,
            llm_agent_id=llm_agent_id,
            llm_output_type=llm_output_type,
            llm_model_name=llm_model_name,
            llm_api_key=llm_api_key,
            rag_enabled=rag_enabled,
            rag_file_ids=rag_file_ids or [],
            rag_include_sources=rag_include_sources,
            rag_max_context_chunks=rag_max_context_chunks,
            rag_score_threshold=rag_score_threshold,
        )

    async def parse_intent(self, message_text: str, reply_text: str | None = None) -> dict:
        return await self.generate.parse_intent(message_text, reply_text=reply_text)
