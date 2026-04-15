"""Environment configuration for Telegram Bot application.

This module loads and provides access to environment variables for:
- Application settings (host, port, environment)
- Database configuration
- Security settings (API keys, secrets)
- Telegram Bot settings
- Task bot settings
- Task parser integration settings

Priority: OS environment > .env file > default value
"""

import logging
import os

from dotenv import dotenv_values

# Load from .env
file_config = dotenv_values(".env")

# Logger for debugging env values
_env_logger = logging.getLogger(__name__)


def get_env(key: str, default: str = "") -> str:
    """Get environment variable from OS or .env file.

    Priority: OS environment > .env file > default value

    Args:
        key: Environment variable name
        default: Default value if not found

    Returns:
        Environment variable value
    """
    value = os.getenv(key)
    if value is None:
        value = file_config.get(key, default)
    if value is None:
        return default
    text = str(value).strip()
    # Handle accidental quoted values from env files or injected variables.
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()
    return text


def parse_bool_env(key: str, default: bool = False) -> bool:
    """Parse boolean environment variable.

    Args:
        key: Environment variable name
        default: Default value if not found

    Returns:
        True if variable is "1", "true", "yes", or "on" (case-insensitive)
    """
    return get_env(key, "true" if default else "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def parse_int_env(key: str, default: int = 0) -> int:
    """Parse integer environment variable.

    Args:
        key: Environment variable name
        default: Default value if not found or invalid

    Returns:
        Integer value
    """
    try:
        return int(get_env(key, str(default)) or str(default))
    except (ValueError, TypeError):
        return default


def parse_list_env(key: str, default: list | None = None, separator: str = ",") -> list[str]:
    """Parse list environment variable.

    Args:
        key: Environment variable name
        default: Default value if not found
        separator: Character to split the list on

    Returns:
        List of string values
    """
    if default is None:
        default = []
    value = get_env(key, "")
    if not value:
        return default
    return [item.strip() for item in value.split(separator) if item.strip()]


def normalize_telegram_username(username: str | None) -> str:
    """Normalize Telegram username for matching."""
    if not username:
        return ""
    cleaned = username.strip().lstrip("@").lower()
    return cleaned


# ================================
# 🏗️ APPLICATION SETTINGS
# ================================
ENVIRONMENT = (get_env("ENVIRONMENT", "development") or "development").strip().lower()
PRODUCTION = ENVIRONMENT in {"production", "prod"}
STAGING = ENVIRONMENT in {"staging", "stage"}
DEVELOPMENT = not (PRODUCTION or STAGING)
DEBUG = "true" if DEVELOPMENT else "false"  # Auto-handled by environment

# ================================
# 🌐 API SETTINGS
# ================================
API_HOST = get_env("API_HOST") or "127.0.0.1"
API_PORT = parse_int_env("API_PORT", 8000)

# ================================
# 🔐 SECURITY SETTINGS
# ================================
API_KEY = get_env("API_KEY") or "your-secret-api-key-here"
SECRET_KEY = get_env("SECRET_KEY") or "change-this-secret-key-in-production"
ALGORITHM = get_env("ALGORITHM") or "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = parse_int_env("ACCESS_TOKEN_EXPIRE_MINUTES", 30)

# ================================
# 🗄️ DATABASE SETTINGS
# ================================
DATABASE_URL = (
    get_env("DATABASE_URL") or "postgresql+psycopg://postgres:postgres@localhost:5432/fastapi_db"
)
DATABASE_ECHO = parse_bool_env("DATABASE_ECHO", default=DEVELOPMENT)
DATABASE_POOL_SIZE = parse_int_env("DATABASE_POOL_SIZE", 5)
DATABASE_MAX_OVERFLOW = parse_int_env("DATABASE_MAX_OVERFLOW", 10)

# SQLite fallback for development
# DATABASE_URL = "sqlite:///./fastapi.db"

# ================================
# 🚀 SERVER SETTINGS (Production)
# ================================
WORKERS = parse_int_env("WORKERS", 4 if PRODUCTION else 1)
RELOAD = parse_bool_env("RELOAD", default=DEVELOPMENT)
LOG_LEVEL = get_env("LOG_LEVEL", "INFO" if PRODUCTION else "DEBUG")

# ================================
# 📦 REDIS SETTINGS (Optional)
# ================================
REDIS_URL = get_env("REDIS_URL") or "redis://localhost:6379/0"

# ================================
# 🌍 CORS SETTINGS
# ================================
CORS_ORIGINS = parse_list_env(
    "CORS_ORIGINS",
    default=["http://localhost:3000", "http://localhost:8000"] if DEVELOPMENT else [],
)
CORS_ALLOW_CREDENTIALS = parse_bool_env("CORS_ALLOW_CREDENTIALS", default=True)
CORS_ALLOW_METHODS = parse_list_env("CORS_ALLOW_METHODS", default=["*"])
CORS_ALLOW_HEADERS = parse_list_env("CORS_ALLOW_HEADERS", default=["*"])

# ================================
# 🎯 ENVIRONMENT-SPECIFIC BEHAVIOR
# ================================
if PRODUCTION:
    # Production specific settings
    _env_logger.info("Running in PRODUCTION mode")
elif STAGING:
    # Staging specific settings
    _env_logger.info("Running in STAGING mode")
else:
    # Development specific settings
    _env_logger.info("Running in DEVELOPMENT mode")


# ================================
# 🤖 TELEGRAM BOT SETTINGS
# ================================
BOT_TOKEN = get_env("BOT_TOKEN") or ""
BOT_USERNAME = get_env("BOT_USERNAME") or ""
ADMIN_TELEGRAM_USERNAMES = tuple(
    normalize_telegram_username(item)
    for item in parse_list_env("ADMIN_TELEGRAM_USERNAMES", default=[])
    if normalize_telegram_username(item)
)
ADMIN_TELEGRAM_USERNAMES_SET = set(ADMIN_TELEGRAM_USERNAMES)


def is_admin_username(username: str | None) -> bool:
    """Check whether username is in configured admin allowlist."""
    normalized = normalize_telegram_username(username)
    return normalized in ADMIN_TELEGRAM_USERNAMES_SET if normalized else False

# ================================
# 🗂️ TASK BOT SETTINGS
# ================================
TASK_LIST_LIMIT = max(1, parse_int_env("TASK_LIST_LIMIT", 20))
TASK_TIMEZONE = get_env("TASK_TIMEZONE", "Asia/Jakarta") or "Asia/Jakarta"
TASK_DAILY_REMINDER_HOUR = min(23, max(0, parse_int_env("TASK_DAILY_REMINDER_HOUR", 9)))
TASK_DAILY_REMINDER_MINUTE = min(59, max(0, parse_int_env("TASK_DAILY_REMINDER_MINUTE", 0)))

# ================================
# 🧠 LLM SETTINGS (Direct vLLM / OpenAI-compatible)
# ================================
LLM_URL = get_env("LLM_URL") or get_env("TASK_PARSER_URL") or get_env("CHAT_AGENT_URL") or ""
LLM_MODEL_NAME = get_env("LLM_MODEL_NAME") or get_env("TASK_PARSER_MODEL_NAME") or get_env("CHAT_MODEL_NAME") or ""
LLM_API_KEY = (
    get_env("LLM_API_KEY")
    or get_env("LLM_HEADER_API_KEY")
    or get_env("LLM_MODEL_API_KEY")
    or get_env("TASK_PARSER_API_KEY")
    or get_env("TASK_PARSER_HEADER_API_KEY")
    or get_env("TASK_PARSER_MODEL_API_KEY")
    or get_env("CHAT_API_KEY")
    or get_env("CHAT_AGENT_HEADER_API_KEY")
    or get_env("CHAT_AGENT_MODEL_API_KEY")
    or ""
)
LLM_OUTPUT_TYPE = get_env("LLM_OUTPUT_TYPE", "json") or "json"

# ================================
# 🧠 TASK PARSER SETTINGS
# ================================
TASK_PARSER_URL = get_env("TASK_PARSER_URL") or LLM_URL
TASK_PARSER_MODEL_NAME = get_env("TASK_PARSER_MODEL_NAME") or LLM_MODEL_NAME
TASK_PARSER_API_KEY = (
    get_env("TASK_PARSER_API_KEY")
    or get_env("TASK_PARSER_HEADER_API_KEY")
    or get_env("TASK_PARSER_MODEL_API_KEY")
    or LLM_API_KEY
)
TASK_PARSER_OUTPUT_TYPE = get_env("TASK_PARSER_OUTPUT_TYPE", LLM_OUTPUT_TYPE) or "json"

# Legacy no-op settings kept for compatibility with older env files.
TASK_PARSER_AGENT_ID = get_env("TASK_PARSER_AGENT_ID") or get_env("LLM_AGENT_ID") or ""
TASK_PARSER_RAG_ENABLED = parse_bool_env("TASK_PARSER_RAG_ENABLED", default=False)
TASK_PARSER_RAG_FILE_IDS = parse_list_env("TASK_PARSER_RAG_FILE_IDS", default=[])
TASK_PARSER_RAG_INCLUDE_SOURCES = parse_bool_env("TASK_PARSER_RAG_INCLUDE_SOURCES", default=True)
TASK_PARSER_RAG_MAX_CONTEXT_CHUNKS = parse_int_env("TASK_PARSER_RAG_MAX_CONTEXT_CHUNKS", 0)
TASK_PARSER_RAG_SCORE_THRESHOLD = get_env("TASK_PARSER_RAG_SCORE_THRESHOLD", "")

# Backward-compatible aliases for older code paths.
LLM_HEADER_API_KEY = LLM_API_KEY
LLM_MODEL_API_KEY = LLM_API_KEY
LLM_AGENT_ID = TASK_PARSER_AGENT_ID

# ================================
# 💬 CHAT LLM SETTINGS (General AI Assistant)
# ================================
CHAT_LLM_URL = get_env("CHAT_LLM_URL") or get_env("CHAT_AGENT_URL") or LLM_URL
CHAT_MODEL_NAME = get_env("CHAT_MODEL_NAME") or LLM_MODEL_NAME
CHAT_API_KEY = (
    get_env("CHAT_API_KEY")
    or get_env("CHAT_AGENT_HEADER_API_KEY")
    or get_env("CHAT_AGENT_MODEL_API_KEY")
    or LLM_API_KEY
)
