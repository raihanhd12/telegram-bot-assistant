"""Bot dependency providers."""

import src.config.env as env
from src.app.services.chat import ChatAgentService
from src.app.services.llm import TaskIntentParserService
from src.app.services.task import TaskService
from src.database.session import SessionLocal

# Singleton instance — preserves conversation history across messages
_chat_service: ChatAgentService | None = None


def get_task_service() -> TaskService:
    """Get a task service instance with a fresh DB session."""
    db = SessionLocal()
    return TaskService(db=db)


def get_task_parser_service() -> TaskIntentParserService:
    """Get a task intent parser service."""
    return TaskIntentParserService(
        llm_url=env.TASK_PARSER_URL,
        llm_model_name=env.TASK_PARSER_MODEL_NAME,
        llm_api_key=env.TASK_PARSER_API_KEY,
        llm_output_type=env.TASK_PARSER_OUTPUT_TYPE,
        rag_enabled=env.TASK_PARSER_RAG_ENABLED,
        rag_file_ids=env.TASK_PARSER_RAG_FILE_IDS,
        rag_include_sources=env.TASK_PARSER_RAG_INCLUDE_SOURCES,
        rag_max_context_chunks=env.TASK_PARSER_RAG_MAX_CONTEXT_CHUNKS,
        rag_score_threshold=env.TASK_PARSER_RAG_SCORE_THRESHOLD,
    )


def get_chat_service() -> ChatAgentService:
    """Get the singleton chat agent service (preserves conversation history)."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatAgentService(
            llm_url=env.CHAT_LLM_URL,
            llm_model_name=env.CHAT_MODEL_NAME,
            llm_api_key=env.CHAT_API_KEY,
        )
    return _chat_service
