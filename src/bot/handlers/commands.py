"""Telegram bot command handlers for task assignment bot."""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import src.config.env as env
from src.bot.dependencies import get_task_service
from src.bot.keyboards import main_menu_keyboard
from src.bot.utils.helpers import (
    bind_topic,
    build_scope_chat_id,
    get_bound_topic,
    get_message_thread_id,
    is_user_admin,
    unbind_topic,
)

logger = logging.getLogger(__name__)


def _resolve_scope(update: Update) -> tuple[int, int | None, int] | None:
    if not update.effective_chat:
        return None
    # Block private chats — bot only works in groups/topics
    if update.effective_chat.type not in {"group", "supergroup"}:
        return None
    chat_id = update.effective_chat.id
    thread_id = get_message_thread_id(update)
    scoped_chat_id = build_scope_chat_id(chat_id, thread_id)
    return chat_id, thread_id, scoped_chat_id


def _get_topic_lock_message(chat_id: int, thread_id: int | None) -> str | None:
    bound_topic = get_bound_topic(chat_id)
    if bound_topic is None or bound_topic == thread_id:
        return None
    return (
        f"🔒 Bot ini sedang dikunci ke topic `{bound_topic}`.\n"
        "Jalankan /deinitiate di topic tersebut, atau /initiate di topic ini oleh admin."
    )


async def _is_bot_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    telegram_user_id: int,
    username: str | None,
) -> bool:
    if env.ADMIN_TELEGRAM_USERNAMES:
        return env.is_admin_username(username)
    return await is_user_admin(update, context, telegram_user_id)


async def start_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if not update.effective_message or not update.effective_chat:
        return
    user = update.effective_user
    if not user:
        return
    if update.effective_chat.type == "private":
        task_service = get_task_service()
        try:
            task_service.ensure_member(user.id, user.username, user.full_name)
        finally:
            task_service.db.close()
        message = (
            "📌 *Adma Thunder Lab Assistant*\n\n"
            "Kamu sudah terdaftar untuk notifikasi DM dari bot.\n"
            "Kalau ada task atau reminder yang diarahkan ke kamu, bot bisa kirim ke chat pribadi ini.\n\n"
            "Penggunaan utama tetap di group/topic tim."
        )
        await update.effective_message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        return
    scope = _resolve_scope(update)
    if not scope:
        return
    chat_id, thread_id, _ = scope
    topic_lock_message = _get_topic_lock_message(chat_id, thread_id)
    if topic_lock_message:
        await update.effective_message.reply_text(topic_lock_message, parse_mode=ParseMode.MARKDOWN)
        return

    message = (
        "📌 *Telegram Task Assignment Bot*\n\n"
        "Gunakan bot ini untuk assign task di group/topic Telegram.\n\n"
        "*Command utama:*\n"
        "• `/tasks` - Lihat task aktif di topic ini\n"
        "• `/mytasks` - Lihat task aktif yang ditugaskan ke kamu\n"
        "• `/assigned` - Lihat task aktif yang kamu buat\n"
        "• `/help` - Panduan penggunaan\n\n"
        "*Contoh pesan natural language:*\n"
        "• `assign ke @budi kerjain landing page`\n"
        "• `pindahin task 12 ke @andi`\n"
        "• `task 12 selesai`\n"
        "• `batalkan task 12`\n"
    )
    await update.effective_message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(),
    )


async def help_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if not update.effective_message or not update.effective_chat:
        return
    if update.effective_chat.type == "private":
        message = (
            "📖 *Panduan Singkat*\n\n"
            "Bot ini dipakai utama di group/topic untuk assign task.\n"
            "Chat pribadi ini dipakai buat menerima notifikasi dan reminder DM.\n\n"
            "Contoh di group:\n"
            "• `assign ke @budi kerjain landing page`\n"
            "• `task 12 selesai`\n"
            "• `task 12 jam 16:30 ingetin dia`"
        )
        await update.effective_message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        return
    scope = _resolve_scope(update)
    if not scope:
        return
    chat_id, thread_id, _ = scope
    topic_lock_message = _get_topic_lock_message(chat_id, thread_id)
    if topic_lock_message:
        await update.effective_message.reply_text(topic_lock_message, parse_mode=ParseMode.MARKDOWN)
        return

    message = (
        "📖 *Panduan Task Bot*\n\n"
        "*Bikin task:*\n"
        "Kirim pesan seperti `assign ke @budi kerjain landing page`.\n\n"
        "*Update task:*\n"
        "• `pindahin task 12 ke @andi`\n"
        "• `task 12 selesai`\n"
        "• `batalkan task 12`\n"
        "Kamu juga bisa reply ke pesan task bot lalu tulis `selesai` atau `batalkan`.\n\n"
        "*Command:*\n"
        "• `/tasks`\n"
        "• `/mytasks`\n"
        "• `/assigned`\n"
        "• `/initiate` dan `/deinitiate` untuk lock topic\n"
    )
    await update.effective_message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(),
    )


async def tasks_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tasks command."""
    if not update.effective_message or not update.effective_chat:
        return
    scope = _resolve_scope(update)
    if not scope:
        return
    chat_id, thread_id, scoped_chat_id = scope
    topic_lock_message = _get_topic_lock_message(chat_id, thread_id)
    if topic_lock_message:
        await update.effective_message.reply_text(topic_lock_message, parse_mode=ParseMode.MARKDOWN)
        return

    task_service = get_task_service()
    try:
        message = task_service.list_open_tasks(scoped_chat_id, limit=env.TASK_LIST_LIMIT)
        await update.effective_message.reply_text(message, parse_mode=None)
    finally:
        task_service.db.close()


async def mytasks_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mytasks command."""
    if not update.effective_message or not update.effective_chat:
        return
    user = update.effective_user
    if not user:
        return
    scope = _resolve_scope(update)
    if not scope:
        return
    chat_id, thread_id, scoped_chat_id = scope
    topic_lock_message = _get_topic_lock_message(chat_id, thread_id)
    if topic_lock_message:
        await update.effective_message.reply_text(topic_lock_message, parse_mode=ParseMode.MARKDOWN)
        return

    task_service = get_task_service()
    try:
        message = task_service.list_my_tasks(
            scoped_chat_id,
            telegram_id=user.id,
            username=user.username,
            full_name=user.full_name,
            limit=env.TASK_LIST_LIMIT,
        )
        await update.effective_message.reply_text(message, parse_mode=None)
    finally:
        task_service.db.close()


async def assigned_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /assigned command."""
    if not update.effective_message or not update.effective_chat:
        return
    user = update.effective_user
    if not user:
        return
    scope = _resolve_scope(update)
    if not scope:
        return
    chat_id, thread_id, scoped_chat_id = scope
    topic_lock_message = _get_topic_lock_message(chat_id, thread_id)
    if topic_lock_message:
        await update.effective_message.reply_text(topic_lock_message, parse_mode=ParseMode.MARKDOWN)
        return

    task_service = get_task_service()
    try:
        message = task_service.list_assigned_by_me(
            scoped_chat_id,
            telegram_id=user.id,
            username=user.username,
            full_name=user.full_name,
            limit=env.TASK_LIST_LIMIT,
        )
        await update.effective_message.reply_text(message, parse_mode=None)
    finally:
        task_service.db.close()


async def initiate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lock the bot to current topic (admin only)."""
    if not update.effective_message or not update.effective_chat:
        return
    user = update.effective_user
    if not user:
        return

    chat_id = update.effective_chat.id
    thread_id = get_message_thread_id(update)
    if not thread_id:
        await update.effective_message.reply_text(
            "❌ `/initiate` hanya bisa dipakai di dalam topic forum.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    is_admin = await _is_bot_admin(update, context, user.id, user.username)
    if not is_admin:
        await update.effective_message.reply_text(
            "❌ Hanya admin yang bisa lock topic.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    previous_topic = get_bound_topic(chat_id)
    bind_topic(chat_id, thread_id)
    if previous_topic == thread_id:
        message = f"✅ Bot sudah aktif di topic ini (`{thread_id}`)."
    elif previous_topic is None:
        message = f"✅ Bot dikunci ke topic ini (`{thread_id}`)."
    else:
        message = (
            f"✅ Topic lock dipindah dari `{previous_topic}` ke `{thread_id}`.\n"
            "Sekarang bot hanya merespon di topic ini."
        )
    await update.effective_message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


async def deinitiate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove topic lock (admin only)."""
    if not update.effective_message or not update.effective_chat:
        return
    user = update.effective_user
    if not user:
        return

    is_admin = await _is_bot_admin(update, context, user.id, user.username)
    if not is_admin:
        await update.effective_message.reply_text(
            "❌ Hanya admin yang bisa melepas topic lock.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    chat_id = update.effective_chat.id
    was_unbound = unbind_topic(chat_id)
    if was_unbound:
        await update.effective_message.reply_text(
            "✅ Topic lock dilepas. Bot sekarang bisa dipakai di semua topic.",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await update.effective_message.reply_text(
            "ℹ️ Chat ini belum punya topic lock.",
            parse_mode=ParseMode.MARKDOWN,
        )
