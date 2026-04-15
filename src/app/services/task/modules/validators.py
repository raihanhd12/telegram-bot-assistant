"""Validation and formatting helpers for task services."""

from __future__ import annotations

from datetime import datetime, timedelta
import re
from zoneinfo import ZoneInfo

import src.config.env as env
from src.app.models import Member, Task, TaskStatus


class TaskValidators:
    """Validators for task operations."""

    TASK_ID_PATTERN = re.compile(r"(?:\btask\s*#?|\B#)(\d+)\b", flags=re.IGNORECASE)
    USERNAME_PATTERN = re.compile(r"@([A-Za-z0-9_]{3,32})")
    DUE_TEXT_PATTERN = re.compile(
        r"(nanti\s+(?:pagi|siang|sore|malam)|besok\s+(?:pagi|siang|sore|malam)|jam\s+\d{1,2}(?:\s*(?:pagi|siang|sore|malam))?(?:\s*(?:ini|hari\s+ini))?(?:(?:\s*lewat\s*\d{1,2}(?:\s*menit)?)|(?:(?::|\.)\s*\d{1,2}))?(?:\s*(?:pagi|siang|sore|malam))?)",
        flags=re.IGNORECASE,
    )

    @staticmethod
    def normalize_username(username: str | None) -> str | None:
        if not username:
            return None
        cleaned = username.strip().lstrip("@").lower()
        return cleaned or None

    @staticmethod
    def sanitize_text(text: str | None) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def extract_task_id(text: str | None) -> int | None:
        if not text:
            return None
        match = TaskValidators.TASK_ID_PATTERN.search(text)
        return int(match.group(1)) if match else None

    @staticmethod
    def extract_task_id_from_reply(reply_text: str | None) -> int | None:
        return TaskValidators.extract_task_id(reply_text)

    @staticmethod
    def extract_usernames(text: str | None) -> list[str]:
        if not text:
            return []
        seen: list[str] = []
        for match in TaskValidators.USERNAME_PATTERN.findall(text):
            normalized = TaskValidators.normalize_username(match)
            if normalized and normalized not in seen:
                seen.append(normalized)
        return seen

    @staticmethod
    def extract_due_text(text: str | None) -> str | None:
        if not text:
            return None
        match = TaskValidators.DUE_TEXT_PATTERN.search(text)
        return TaskValidators.sanitize_text(match.group(1)) if match else None

    @staticmethod
    def ensure_description(description: str | None) -> str | None:
        cleaned = TaskValidators.sanitize_text(description)
        return cleaned or None

    @staticmethod
    def can_reassign(task: Task, actor: Member, is_admin: bool) -> bool:
        return is_admin or actor.id == task.assigned_by_member_id

    @staticmethod
    def can_cancel(task: Task, actor: Member, is_admin: bool) -> bool:
        return is_admin or actor.id == task.assigned_by_member_id

    @staticmethod
    def can_mark_done(task: Task, actor: Member, is_admin: bool) -> bool:
        return is_admin or actor.id in {task.assigned_by_member_id, task.assigned_to_member_id}

    @staticmethod
    def is_open(task: Task) -> bool:
        return task.status == TaskStatus.ASSIGNED

    @staticmethod
    def display_member(member: Member | None) -> str:
        if member is None:
            return "-"
        if member.username:
            return f"@{member.username}"
        if member.full_name:
            return member.full_name
        if member.telegram_id:
            return str(member.telegram_id)
        return f"member:{member.id}"

    @staticmethod
    def format_task(task: Task) -> str:
        lines = [
            f"📌 Task #{task.id}\n"
            f"Status: {task.status.value}\n"
            f"To: {TaskValidators.display_member(task.assigned_to)}\n"
            f"By: {TaskValidators.display_member(task.assigned_by)}\n"
            f"Desc: {task.description}"
        ]
        if task.due_at or task.due_text:
            lines.append(f"\nDue: {TaskValidators.format_due(task)}")
        return "".join(lines)

    @staticmethod
    def format_due(task: Task) -> str:
        if task.due_at is not None:
            tz = ZoneInfo(env.TASK_TIMEZONE)
            localized = task.due_at.astimezone(tz)
            if task.due_text:
                return f"{task.due_text} ({localized.strftime('%Y-%m-%d %H:%M %Z')})"
            return localized.strftime("%Y-%m-%d %H:%M %Z")
        return task.due_text or "-"

    @staticmethod
    def resolve_due_at(due_text: str | None, now: datetime | None = None) -> datetime | None:
        if not due_text:
            return None

        tz = ZoneInfo(env.TASK_TIMEZONE)
        now_local = now.astimezone(tz) if now is not None else datetime.now(tz)
        text = TaskValidators.sanitize_text(due_text).lower()
        period_hours = {
            "pagi": 9,
            "siang": 13,
            "sore": 17,
            "malam": 20,
        }

        for prefix, day_offset in {"nanti": 0, "besok": 1}.items():
            for period, hour in period_hours.items():
                if text == f"{prefix} {period}":
                    candidate = datetime(
                        now_local.year,
                        now_local.month,
                        now_local.day,
                        hour,
                        0,
                        tzinfo=tz,
                    ) + timedelta(days=day_offset)
                    if prefix == "nanti" and candidate <= now_local:
                        candidate += timedelta(days=1)
                    return candidate.astimezone(ZoneInfo("UTC"))

        jam_match = re.search(
            r"jam\s+(?P<hour>\d{1,2})"
            r"(?:\s*(?P<period1>pagi|siang|sore|malam))?"
            r"(?:\s*(?P<today>ini|hari\s+ini))?"
            r"(?:(?:\s*(?P<sep>lewat)\s*(?P<lewat_min>\d{1,2})(?:\s*menit)?)|(?:(?::|\.)\s*(?P<minute>\d{1,2})))?"
            r"(?:\s*(?P<period2>pagi|siang|sore|malam))?",
            text,
        )
        if jam_match:
            raw_hour = int(jam_match.group("hour"))
            hour = raw_hour
            lewat_min = jam_match.group("lewat_min")
            if lewat_min:
                minute = int(lewat_min)
            else:
                minute = int(jam_match.group("minute") or 0)
            period = jam_match.group("period1") or jam_match.group("period2")
            if period == "siang" and hour < 12:
                hour += 12
            elif period == "sore" and hour < 12:
                hour += 12
            elif period == "malam" and hour < 12:
                hour += 12

            # For phrases like "jam 4" said in the afternoon, prefer the same-day PM
            # interpretation if it is still upcoming.
            if period is None and 1 <= raw_hour < 12 and now_local.hour >= 12:
                pm_candidate = datetime(
                    now_local.year,
                    now_local.month,
                    now_local.day,
                    raw_hour + 12,
                    minute,
                    tzinfo=tz,
                )
                if pm_candidate > now_local:
                    hour = raw_hour + 12

            candidate = datetime(
                now_local.year,
                now_local.month,
                now_local.day,
                hour % 24,
                minute,
                tzinfo=tz,
            )
            force_today = "hari ini" in text or re.search(r"\bjam\b.*\bini\b", text) is not None
            same_minute = candidate.strftime("%Y-%m-%d %H:%M") == now_local.strftime("%Y-%m-%d %H:%M")
            if candidate <= now_local and not force_today and not same_minute:
                candidate += timedelta(days=1)
            return candidate.astimezone(ZoneInfo("UTC"))

        return None
