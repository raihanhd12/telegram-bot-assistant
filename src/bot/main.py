"""Telegram task assignment bot entry point."""

import asyncio
import logging
import os
import sys

from telegram import BotCommand, Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import src.config.env as env
from src.bot.dependencies import get_chat_service, get_task_parser_service, get_task_service
from src.bot.handlers.commands import (
    assigned_command,
    deinitiate_command,
    help_command,
    initiate_command,
    mytasks_command,
    start_command,
    tasks_command,
)
from src.bot.utils.helpers import build_scope_chat_id, get_message_thread_id, is_topic_allowed
from src.bot.utils.reminders import (
    cancel_task_due_reminder,
    daily_reminder_time,
    restore_due_task_reminders,
    schedule_task_due_reminder,
    send_daily_task_reminders,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, env.LOG_LEVEL),
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Post-initialization hook."""
    await application.bot.set_my_commands(
        commands=[
            BotCommand("start", "Mulai bot dan tampilkan panduan"),
            BotCommand("help", "Lihat panduan penggunaan"),
            BotCommand("tasks", "Lihat task aktif di topic ini"),
            BotCommand("mytasks", "Lihat task aktif untuk kamu"),
            BotCommand("assigned", "Lihat task aktif yang kamu buat"),
            BotCommand("initiate", "Kunci bot di topic ini (admin)"),
            BotCommand("deinitiate", "Lepas kunci topic (admin)"),
        ]
    )
    bot_info = await application.bot.get_me()
    logger.info("Task bot started successfully")
    logger.info("Environment: %s", env.ENVIRONMENT)
    logger.info(
        "Bot identity: username=@%s can_read_all_group_messages=%s",
        bot_info.username,
        getattr(bot_info, "can_read_all_group_messages", None),
    )
    if getattr(bot_info, "can_read_all_group_messages", None) is False:
        logger.error(
            "Bot privacy mode appears enabled. Non-command group messages will not reach the bot."
        )
        raise RuntimeError(
            "Telegram bot privacy mode is still enabled. Disable it via @BotFather /setprivacy before starting the bot."
        )
    if application.job_queue is not None:
        application.job_queue.run_daily(
            send_daily_task_reminders,
            time=daily_reminder_time(),
            name="daily-task-reminders",
        )
        await restore_due_task_reminders(application)
        logger.info(
            "Daily task reminder scheduled at %02d:%02d %s",
            env.TASK_DAILY_REMINDER_HOUR,
            env.TASK_DAILY_REMINDER_MINUTE,
            env.TASK_TIMEZONE,
        )
    else:
        logger.warning(
            "Job queue is unavailable; due reminders and daily reminders will not run. "
            "Install dependencies with the python-telegram-bot[job-queue] extra."
        )


async def error_handler(_update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logger.error("Exception while handling an update: %s", context.error, exc_info=context.error)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle non-command text messages for natural-language task actions."""
    if not update.effective_message or not update.effective_message.text or not update.effective_chat:
        return
    if update.edited_message is not None:
        logger.info("Ignored edited message update for message_id=%s", update.edited_message.message_id)
        return

    user = update.effective_user
    if not user:
        return

    # Block private chats — bot only works in groups/topics
    chat_type = update.effective_chat.type
    if chat_type not in {"group", "supergroup"}:
        return

    chat_id = update.effective_chat.id
    thread_id = get_message_thread_id(update)
    scoped_chat_id = build_scope_chat_id(chat_id, thread_id)
    if not is_topic_allowed(chat_id, thread_id):
        logger.info(
            "Ignored message outside allowed topic: chat_id=%s thread_id=%s user=%s",
            chat_id,
            thread_id,
            user.username,
        )
        return

    message_text = update.effective_message.text.strip()
    if not message_text or message_text.startswith("/"):
        return

    logger.info(
        "Incoming text message: chat_id=%s scoped_chat_id=%s thread_id=%s user=%s(%s) text=%r",
        chat_id,
        scoped_chat_id,
        thread_id,
        user.username,
        user.id,
        message_text,
    )

    reply_text = None
    if update.effective_message.reply_to_message:
        reply_text = getattr(update.effective_message.reply_to_message, "text", None)

    # Auto-track every user who chats so the bot learns who's in the group
    parser_service = get_task_parser_service()
    task_service = get_task_service()
    typing_task = _start_typing_indicator(context, chat_id, thread_id)
    try:
        task_service.ensure_member(user.id, user.username, user.full_name)
    except Exception:
        logger.debug("Failed to track member", exc_info=True)
    try:
        logger.info("Calling task intent parser")
        parsed_intent = await parser_service.parse_intent(message_text, reply_text=reply_text)
        logger.info("Task intent parser result: %s", parsed_intent)
        is_admin = await _is_user_admin(update, context, user.id, user.username)
        logger.info("Resolved actor admin status: user=%s is_admin=%s", user.username, is_admin)
        handled, response = task_service.handle_intent(
            parsed_intent=parsed_intent,
            scope_chat_id=scoped_chat_id,
            raw_chat_id=chat_id,
            thread_id=thread_id,
            source_message_id=update.effective_message.message_id,
            source_text=message_text,
            reply_text=reply_text,
            actor_telegram_id=user.id,
            actor_username=user.username,
            actor_full_name=user.full_name,
            is_admin=is_admin,
        )
        logger.info("Task service result: handled=%s response=%r", handled, response)
        if response:
            await update.effective_message.reply_text(response, parse_mode=None)
            logger.info("Response sent for message_id=%s", update.effective_message.message_id)
            if handled and not response.startswith("❌"):
                _sync_due_reminder_job(context, task_service, scoped_chat_id, response)
                # DM the assignee only after successful task actions.
                await _notify_assignee(context, parsed_intent, task_service)
        elif not handled:
            # Fall through to general chat agent
            chat_service = get_chat_service()
            chat_response = await chat_service.chat(
                message_text,
                user.full_name,
                db=task_service.db,
                scope_chat_id=scoped_chat_id,
            )
            if chat_response:
                await update.effective_message.reply_text(chat_response, parse_mode=None)
                logger.info("Chat agent response sent for message_id=%s", update.effective_message.message_id)
            else:
                logger.info("Message produced no action and chat agent returned no response")
    except Exception:
        logger.exception("Failed to process task intent message")
    finally:
        await _stop_typing_indicator(typing_task)
        task_service.db.close()


async def _is_user_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    telegram_user_id: int,
    username: str | None,
) -> bool:
    if env.ADMIN_TELEGRAM_USERNAMES:
        return env.is_admin_username(username)
    if not update.effective_chat:
        return False
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, telegram_user_id)
    except Exception:
        logger.exception("Failed to check admin status")
        return False
    return member.status in {"administrator", "creator"}


async def _notify_assignee(
    context: ContextTypes.DEFAULT_TYPE,
    parsed_intent: dict,
    task_service,
) -> None:
    """Send a DM to the assignee after task creation or due date change."""
    intent = parsed_intent.get("intent")
    if intent not in {"create_task", "set_task_due", "reassign_task"}:
        return

    from src.app.repositories.member import MemberRepository
    from src.app.services.task.modules.validators import TaskValidators

    assignee_username = TaskValidators.normalize_username(parsed_intent.get("assignee_username"))
    if not assignee_username:
        return

    assignee = MemberRepository.find_by_handle(task_service.db, assignee_username)
    if not assignee or not assignee.telegram_id:
        logger.info("Cannot DM assignee: no telegram_id for %s", assignee_username)
        return

    # Skip if actor is the same as assignee
    # (we don't have actor info here, so we always notify)

    if intent == "create_task":
        desc = parsed_intent.get("description") or ""
        text = (
            f"📌 Kamu dapet task baru!\n\n"
            f"Task: {desc}\n"
            f"Cek di group ya."
        )
    elif intent == "set_task_due":
        due_text = parsed_intent.get("due_text") or ""
        text = (
            f"⏰ Deadline task kamu di-update!\n\n"
            f"Due: {due_text}\n"
            f"Cek di group ya."
        )
    elif intent == "reassign_task":
        text = (
            f"🔁 Ada task yang dipindah ke kamu.\n"
            f"Cek di group ya."
        )
    else:
        return

    try:
        await context.bot.send_message(chat_id=assignee.telegram_id, text=text, parse_mode=None)
        logger.info("DM notification sent to %s (telegram_id=%s)", assignee_username, assignee.telegram_id)
    except Exception:
        logger.warning(
            "Failed to send DM to %s (telegram_id=%s). User may need to /start the bot first.",
            assignee_username,
            assignee.telegram_id,
        )


def _sync_due_reminder_job(
    context: ContextTypes.DEFAULT_TYPE,
    task_service,
    scope_chat_id: int,
    response_text: str,
) -> None:
    """Keep one-off due reminder jobs in sync with the latest task state."""
    from src.app.services.task.modules.validators import TaskValidators

    task_id = TaskValidators.extract_task_id(response_text)
    if task_id is None:
        return

    task = task_service.read.get_task(task_id, scope_chat_id)
    if task is None:
        cancel_task_due_reminder(context.job_queue, task_id)
        return

    if TaskValidators.is_open(task) and task.due_at and task.assigned_to:
        scheduled = schedule_task_due_reminder(context.job_queue, task)
        if not scheduled and context.job_queue is None:
            logger.warning(
                "Cannot schedule due reminder for task_id=%s because job queue is unavailable",
                task_id,
            )
    else:
        cancel_task_due_reminder(context.job_queue, task_id)


def _start_typing_indicator(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    thread_id: int | None,
) -> asyncio.Task:
    """Continuously send typing action while a message is being processed."""
    return asyncio.create_task(_typing_indicator_loop(context, chat_id, thread_id))


async def _stop_typing_indicator(task: asyncio.Task | None) -> None:
    """Stop a running typing indicator task."""
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def _typing_indicator_loop(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    thread_id: int | None,
) -> None:
    """Send typing action every few seconds until cancelled."""
    try:
        while True:
            kwargs = {"chat_id": chat_id, "action": ChatAction.TYPING}
            if thread_id is not None:
                kwargs["message_thread_id"] = thread_id
            await context.bot.send_chat_action(**kwargs)
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Failed to send typing indicator")


def main() -> None:
    """Start the bot."""
    if not env.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set! Please set it in .env or environment variables.")
        sys.exit(1)

    application = Application.builder().token(env.BOT_TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("tasks", tasks_command))
    application.add_handler(CommandHandler("mytasks", mytasks_command))
    application.add_handler(CommandHandler("assigned", assigned_command))
    application.add_handler(CommandHandler("initiate", initiate_command))
    application.add_handler(CommandHandler("deinitiate", deinitiate_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    logger.info("Starting task bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
