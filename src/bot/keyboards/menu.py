"""Reply keyboard menu for Telegram bot commands."""

from telegram import ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Build the main command keyboard shown to users."""
    return ReplyKeyboardMarkup(
        keyboard=[
            ["/tasks", "/mytasks"],
            ["/assigned", "/help"],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Ketik assign task atau pilih menu...",
    )
