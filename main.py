"""Telegram task assignment bot - main entry point."""
import logging
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import src.config.env as env
from src.bot.main import main as bot_main

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, env.LOG_LEVEL),
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("Starting Telegram Task Assignment Bot...")
    logger.info(f"Environment: {env.ENVIRONMENT}")

    # Check for bot token
    if not env.BOT_TOKEN:
        logger.error(
            "BOT_TOKEN is not set! Please set it in .env or environment variables."
        )
        logger.info("Get your bot token from @BotFather on Telegram")
        sys.exit(1)

    try:
        bot_main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
        sys.exit(1)
