"""Tests for bot command handlers."""

from __future__ import annotations

from types import SimpleNamespace

from src.bot.handlers import commands


class FakeMessage:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append({"text": text, **kwargs})


class FakeTaskService:
    def __init__(self):
        self.calls = []
        self.db = SimpleNamespace(close=lambda: None)

    def ensure_member(self, telegram_id, username, full_name):
        self.calls.append((telegram_id, username, full_name))


async def test_start_command_in_private_registers_member(monkeypatch):
    message = FakeMessage()
    service = FakeTaskService()
    monkeypatch.setattr(commands, "get_task_service", lambda: service)

    update = SimpleNamespace(
        effective_message=message,
        effective_chat=SimpleNamespace(type="private"),
        effective_user=SimpleNamespace(id=2, username="iqbalpurba2610", full_name="M. Iqbal Purba"),
    )

    await commands.start_command(update, None)

    assert service.calls == [(2, "iqbalpurba2610", "M. Iqbal Purba")]
    assert len(message.replies) == 1
    assert "terdaftar untuk notifikasi DM" in message.replies[0]["text"]
