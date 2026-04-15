"""LLM service modules package"""

from src.app.services.llm.modules.generate import LLMGenerateService
from src.app.services.llm.modules.prompts import LPrompts

__all__ = [
    "LPrompts",
    "LLMGenerateService",
]
