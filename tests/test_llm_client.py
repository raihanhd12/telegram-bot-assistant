"""Tests for direct OpenAI-compatible LLM integration helpers."""

from src.app.services.chat.service import ChatAgentService
from src.app.services.llm.client import OpenAICompatClient
from src.app.services.llm.service import TaskIntentParserService


def test_openai_compat_client_extracts_text_from_chat_completion_payload():
    payload = {
        "choices": [
            {
                "message": {
                    "content": "halo dunia",
                }
            }
        ]
    }

    assert OpenAICompatClient.extract_text(payload) == "halo dunia"


def test_task_parser_reads_json_from_openai_compatible_payload():
    parser = TaskIntentParserService(llm_url="", llm_model_name="")
    payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        '{"intent":"create_task","task_id":null,"assignee_username":"budi",'
                        '"description":"kerjain landing page","due_text":null}'
                    )
                }
            }
        ]
    }

    parsed = parser.generate._parse_output(payload)

    assert parsed["intent"] == "create_task"
    assert parsed["assignee_username"] == "budi"
    assert parsed["description"] == "kerjain landing page"


def test_chat_service_extracts_text_from_openai_compatible_payload():
    payload = {
        "choices": [
            {
                "message": {
                    "content": "siap, noted",
                }
            }
        ]
    }

    assert ChatAgentService._extract_text(payload) == "siap, noted"
