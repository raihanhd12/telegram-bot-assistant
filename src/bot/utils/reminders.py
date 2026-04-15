"""Task reminder helpers."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

import src.config.env as env
from src.app.models import TaskStatus
from src.app.repositories.task import TaskRepository
from src.app.services.task import TaskService
from src.app.services.task.modules.validators import TaskValidators
from src.database.session import SessionLocal

logger = logging.getLogger(__name__)

_TASK_DUE_JOB_PREFIX = "task-due-reminder:"
_IMMEDIATE_DUE_GRACE_SECONDS = 300


def daily_reminder_time() -> time:
    """Configured daily reminder time in local task timezone."""
    return time(
        hour=env.TASK_DAILY_REMINDER_HOUR,
        minute=env.TASK_DAILY_REMINDER_MINUTE,
        tzinfo=ZoneInfo(env.TASK_TIMEZONE),
    )


async def restore_due_task_reminders(application) -> None:
    """Re-register one-off due reminders for open tasks after bot startup."""
    if application.job_queue is None:
        logger.warning("Job queue is unavailable; due reminders will not run.")
        return

    db = SessionLocal()
    service = TaskService(db)
    scheduled = 0
    try:
        for task in service.read.list_all_open_tasks():
            if schedule_task_due_reminder(application.job_queue, task):
                scheduled += 1
    finally:
        db.close()

    logger.info("Restored %s due reminder job(s) on startup", scheduled)


async def send_daily_task_reminders(context) -> None:
    """Send daily DM summaries for all assignees with open tasks."""
    db = SessionLocal()
    service = TaskService(db)
    try:
        tasks = service.read.list_all_open_tasks()
        tasks_by_member = defaultdict(list)
        for task in tasks:
            if task.assigned_to and task.assigned_to.telegram_id:
                tasks_by_member[task.assigned_to.telegram_id].append(task)

        logger.info("Preparing daily task reminders for %s assignees", len(tasks_by_member))
        for telegram_id, member_tasks in tasks_by_member.items():
            member = member_tasks[0].assigned_to
            text = _format_dm_summary(member_tasks, member_display=TaskValidators.display_member(member))
            try:
                await context.bot.send_message(chat_id=telegram_id, text=text, parse_mode=None)
                logger.info("Daily reminder sent to telegram_id=%s task_count=%s", telegram_id, len(member_tasks))
            except Exception:
                logger.exception(
                    "Failed to send daily reminder DM to telegram_id=%s. User may need to start the bot privately first.",
                    telegram_id,
                )
    finally:
        db.close()


async def send_task_due_reminder(context) -> None:
    """Send a one-off DM when a task reaches its due time."""
    payload = getattr(context.job, "data", None) or {}
    task_id = payload.get("task_id")
    if task_id is None:
        logger.warning("Due reminder job skipped because task_id is missing")
        return

    db = SessionLocal()
    try:
        task = TaskRepository.get_by_id(db, int(task_id))
        if task is None:
            logger.info("Due reminder skipped because task #%s no longer exists", task_id)
            return
        if task.status != TaskStatus.ASSIGNED or task.due_at is None:
            logger.info("Due reminder skipped because task #%s is no longer active/due", task_id)
            return
        if not task.assigned_to:
            logger.info("Due reminder skipped because task #%s has no assignee relation", task_id)
            return

        expected_due_at = payload.get("due_at")
        current_due_at = _ensure_utc(task.due_at).isoformat()
        if expected_due_at and expected_due_at != current_due_at:
            logger.info(
                "Due reminder skipped because task #%s due_at changed from %s to %s",
                task_id,
                expected_due_at,
                current_due_at,
            )
            return

        text = (
            f"⏰ Reminder Task #{task.id}\n\n"
            f"Task: {task.description}\n"
            f"Due: {TaskValidators.format_due(task)}\n"
            f"By: {TaskValidators.display_member(task.assigned_by)}"
        )
        if not task.assigned_to.telegram_id:
            logger.info("Due reminder skipped because task #%s assignee has no telegram_id", task_id)
            await _send_group_reminder_status(
                context,
                task,
                success=False,
                reason="Assignee belum pernah chat bot secara pribadi. Minta dia `/start` bot dulu.",
            )
            return

        try:
            await context.bot.send_message(
                chat_id=task.assigned_to.telegram_id,
                text=text,
                parse_mode=None,
            )
            logger.info(
                "Due reminder DM sent for task_id=%s telegram_id=%s",
                task.id,
                task.assigned_to.telegram_id,
            )
            await _send_group_reminder_status(context, task, success=True)
        except Exception:
            logger.exception("Failed to send due reminder DM for task_id=%s", task_id)
            await _send_group_reminder_status(
                context,
                task,
                success=False,
                reason="Gagal kirim DM. Bisa jadi user belum `/start` bot atau DM diblokir.",
            )
    except Exception:
        logger.exception("Failed to send due reminder for task_id=%s", task_id)
    finally:
        db.close()


def schedule_task_due_reminder(job_queue, task) -> bool:
    """Schedule or reschedule a one-off due reminder for a task."""
    if job_queue is None:
        return False

    cancel_task_due_reminder(job_queue, task.id)

    if (
        task.status != TaskStatus.ASSIGNED
        or task.due_at is None
        or task.assigned_to is None
    ):
        return False

    due_at = _ensure_utc(task.due_at)
    now_utc = datetime.now(timezone.utc)
    if due_at <= now_utc:
        delay_seconds = (now_utc - due_at).total_seconds()
        if delay_seconds > _IMMEDIATE_DUE_GRACE_SECONDS:
            logger.info("Due reminder not scheduled for task #%s because due time already passed", task.id)
            return False
        when = 0
    else:
        when = due_at

    job_queue.run_once(
        send_task_due_reminder,
        when=when,
        data={
            "task_id": task.id,
            "due_at": due_at.isoformat(),
        },
        name=task_due_job_name(task.id),
    )
    logger.info(
        "Scheduled due reminder for task_id=%s telegram_id=%s at %s",
        task.id,
        task.assigned_to.telegram_id,
        due_at.isoformat(),
    )
    return True


def cancel_task_due_reminder(job_queue, task_id: int) -> int:
    """Cancel any scheduled one-off due reminder for a task."""
    if job_queue is None:
        return 0

    removed = 0
    for job in list(job_queue.get_jobs_by_name(task_due_job_name(task_id))):
        job.schedule_removal()
        removed += 1
    if removed:
        logger.info("Cancelled %s due reminder job(s) for task_id=%s", removed, task_id)
    return removed


def task_due_job_name(task_id: int) -> str:
    """Stable job name for a task due reminder."""
    return f"{_TASK_DUE_JOB_PREFIX}{task_id}"


def _ensure_utc(value: datetime) -> datetime:
    """Treat naive datetimes from DB as UTC and normalize aware ones to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_dm_summary(tasks, member_display: str) -> str:
    lines = [f"⏰ Reminder Task Untuk {member_display}", "", "Kamu masih punya task aktif:"]
    for task in tasks:
        lines.append(f"- #{task.id}: {task.description}")
        if task.due_at or task.due_text:
            lines.append(f"  Due: {TaskValidators.format_due(task)}")
    lines.append("")
    lines.append("Jangan lupa dikerjakan ya.")
    return "\n".join(lines)


async def _send_group_reminder_status(context, task, *, success: bool, reason: str | None = None) -> None:
    """Post reminder delivery status back to the source group/topic."""
    if not task.raw_chat_id:
        return

    member_display = TaskValidators.display_member(task.assigned_to)
    if success:
        text = f"📨 Reminder untuk {member_display} sudah dikirim via DM untuk Task #{task.id}."
    else:
        detail = f"\nAlasan: {reason}" if reason else ""
        text = f"⚠️ Reminder untuk {member_display} gagal dikirim via DM untuk Task #{task.id}.{detail}"

    kwargs = {
        "chat_id": task.raw_chat_id,
        "text": text,
        "parse_mode": None,
    }
    if task.thread_id is not None:
        kwargs["message_thread_id"] = task.thread_id

    try:
        await context.bot.send_message(**kwargs)
    except Exception:
        logger.exception("Failed to send group reminder status for task_id=%s", task.id)
