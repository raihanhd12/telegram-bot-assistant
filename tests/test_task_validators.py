"""Tests for task time parsing heuristics."""

from datetime import datetime
from zoneinfo import ZoneInfo

from src.app.services.task.modules.validators import TaskValidators


def test_resolve_due_at_prefers_same_day_pm_for_bare_hour_in_afternoon():
    now = datetime(2026, 4, 15, 16, 17, tzinfo=ZoneInfo("Asia/Jakarta"))

    due_at = TaskValidators.resolve_due_at("jam 4 lewat 18", now=now)

    assert due_at is not None
    local_due = due_at.astimezone(ZoneInfo("Asia/Jakarta"))
    assert local_due.year == 2026
    assert local_due.month == 4
    assert local_due.day == 15
    assert local_due.hour == 16
    assert local_due.minute == 18


def test_resolve_due_at_keeps_same_day_for_same_minute():
    now = datetime(2026, 4, 15, 16, 20, 22, tzinfo=ZoneInfo("Asia/Jakarta"))

    due_at = TaskValidators.resolve_due_at("jam 16:20", now=now)

    assert due_at is not None
    local_due = due_at.astimezone(ZoneInfo("Asia/Jakarta"))
    assert local_due.year == 2026
    assert local_due.month == 4
    assert local_due.day == 15
    assert local_due.hour == 16
    assert local_due.minute == 20


def test_resolve_due_at_supports_sore_ini_lewat_menit_phrase():
    now = datetime(2026, 4, 15, 16, 30, 7, tzinfo=ZoneInfo("Asia/Jakarta"))

    due_at = TaskValidators.resolve_due_at("jam 4 sore ini lewat 31 menit", now=now)

    assert due_at is not None
    local_due = due_at.astimezone(ZoneInfo("Asia/Jakarta"))
    assert local_due.year == 2026
    assert local_due.month == 4
    assert local_due.day == 15
    assert local_due.hour == 16
    assert local_due.minute == 31
