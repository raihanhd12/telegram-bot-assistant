"""Tests for bot reminder scheduling."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.app.repositories.member import MemberRepository
from src.app.repositories.task import TaskRepository
from src.app.services.task.service import TaskService
from src.bot.utils import reminders


class FakeBot:
    def __init__(self, fail_chat_ids=None):
        self.messages = []
        self.fail_chat_ids = set(fail_chat_ids or [])

    async def send_message(self, **kwargs):
        if kwargs.get("chat_id") in self.fail_chat_ids:
            raise RuntimeError("send failed")
        self.messages.append(kwargs)


class FakeJob:
    def __init__(self, name, data=None, when=None):
        self.name = name
        self.data = data
        self.when = when
        self.removed = False

    def schedule_removal(self):
        self.removed = True


class FakeJobQueue:
    def __init__(self):
        self.jobs = {}

    def get_jobs_by_name(self, name):
        jobs = self.jobs.get(name, [])
        return [job for job in jobs if not job.removed]

    def run_once(self, callback, when, data=None, name=None):
        job = FakeJob(name=name, data=data, when=when)
        job.callback = callback
        self.jobs.setdefault(name, []).append(job)
        return job


def test_schedule_task_due_reminder_registers_job(db_session):
    service = TaskService(db_session)
    task = service.create.create_task(
        scope_chat_id=1,
        raw_chat_id=-100,
        thread_id=None,
        assigned_by=MemberRepository.create_member(db_session, telegram_id=1, username="alice"),
        assigned_to=MemberRepository.create_member(db_session, telegram_id=2, username="iqbalpurba2610"),
        description="kasih makan ayam",
        source_message_id=10,
        source_text="assign ke @iqbalpurba2610 kasih makan ayam",
    )
    task = TaskRepository.update_task(
        db_session,
        task,
        {
            "due_at": datetime.now(timezone.utc) + timedelta(minutes=30),
            "due_text": "jam 4 sore lewat 10",
        },
    )

    job_queue = FakeJobQueue()
    scheduled = reminders.schedule_task_due_reminder(job_queue, task)

    assert scheduled is True
    jobs = job_queue.get_jobs_by_name(reminders.task_due_job_name(task.id))
    assert len(jobs) == 1
    assert jobs[0].data["task_id"] == task.id


def test_schedule_task_due_reminder_registers_job_without_telegram_id(db_session):
    service = TaskService(db_session)
    task = service.create.create_task(
        scope_chat_id=10,
        raw_chat_id=-100,
        thread_id=24,
        assigned_by=MemberRepository.create_member(db_session, telegram_id=1, username="alice"),
        assigned_to=MemberRepository.create_member(db_session, username="iqbalpurba2610"),
        description="mandiin kucing",
        source_message_id=14,
        source_text="assign ke @iqbalpurba2610 mandiin kucing",
    )
    task = TaskRepository.update_task(
        db_session,
        task,
        {
            "due_at": datetime.now(timezone.utc) + timedelta(minutes=2),
            "due_text": "jam 16:39",
        },
    )

    job_queue = FakeJobQueue()
    scheduled = reminders.schedule_task_due_reminder(job_queue, task)

    assert scheduled is True
    jobs = job_queue.get_jobs_by_name(reminders.task_due_job_name(task.id))
    assert len(jobs) == 1


async def test_send_task_due_reminder_sends_private_dm(monkeypatch, db_session):
    service = TaskService(db_session)
    task = service.create.create_task(
        scope_chat_id=2,
        raw_chat_id=-100,
        thread_id=None,
        assigned_by=MemberRepository.create_member(db_session, telegram_id=1, username="alice"),
        assigned_to=MemberRepository.create_member(db_session, telegram_id=2, username="iqbalpurba2610"),
        description="kasih makan ayam",
        source_message_id=11,
        source_text="assign ke @iqbalpurba2610 kasih makan ayam",
    )
    due_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    task = TaskRepository.update_task(
        db_session,
        task,
        {
            "due_at": due_at,
            "due_text": "jam 4 sore lewat 10",
        },
    )

    bot = FakeBot()
    monkeypatch.setattr(reminders, "SessionLocal", lambda: db_session)

    context = SimpleNamespace(
        bot=bot,
        job=SimpleNamespace(
            data={
                "task_id": task.id,
                "due_at": due_at.isoformat(),
            }
        ),
    )

    await reminders.send_task_due_reminder(context)

    assert len(bot.messages) == 2
    assert bot.messages[0]["chat_id"] == 2
    assert "Reminder Task" in bot.messages[0]["text"]
    assert "kasih makan ayam" in bot.messages[0]["text"]
    assert bot.messages[1]["chat_id"] == -100
    assert "sudah dikirim via DM" in bot.messages[1]["text"]


def test_schedule_task_due_reminder_runs_immediately_for_recent_same_minute_due(db_session):
    service = TaskService(db_session)
    task = service.create.create_task(
        scope_chat_id=3,
        raw_chat_id=-100,
        thread_id=None,
        assigned_by=MemberRepository.create_member(db_session, telegram_id=1, username="alice"),
        assigned_to=MemberRepository.create_member(db_session, telegram_id=2, username="iqbalpurba2610"),
        description="bersihin kuping kucing",
        source_message_id=12,
        source_text="assign ke @iqbalpurba2610 bersihin kuping kucing",
    )
    task = TaskRepository.update_task(
        db_session,
        task,
        {
            "due_at": datetime.now(timezone.utc) - timedelta(seconds=20),
            "due_text": "jam 16:20",
        },
    )

    job_queue = FakeJobQueue()
    scheduled = reminders.schedule_task_due_reminder(job_queue, task)

    assert scheduled is True
    jobs = job_queue.get_jobs_by_name(reminders.task_due_job_name(task.id))
    assert len(jobs) == 1
    assert jobs[0].when == 0


async def test_send_task_due_reminder_reports_group_when_dm_fails(monkeypatch, db_session):
    service = TaskService(db_session)
    task = service.create.create_task(
        scope_chat_id=4,
        raw_chat_id=-100,
        thread_id=24,
        assigned_by=MemberRepository.create_member(db_session, telegram_id=1, username="alice"),
        assigned_to=MemberRepository.create_member(db_session, telegram_id=2, username="iqbalpurba2610"),
        description="mandiin kucing",
        source_message_id=13,
        source_text="assign ke @iqbalpurba2610 mandiin kucing",
    )
    due_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    task = TaskRepository.update_task(
        db_session,
        task,
        {
            "due_at": due_at,
            "due_text": "jam 16:34",
        },
    )

    bot = FakeBot(fail_chat_ids={2})
    monkeypatch.setattr(reminders, "SessionLocal", lambda: db_session)

    context = SimpleNamespace(
        bot=bot,
        job=SimpleNamespace(
            data={
                "task_id": task.id,
                "due_at": due_at.isoformat(),
            }
        ),
    )

    await reminders.send_task_due_reminder(context)

    assert len(bot.messages) == 1
    assert bot.messages[0]["chat_id"] == -100
    assert bot.messages[0]["message_thread_id"] == 24
    assert "gagal dikirim via DM" in bot.messages[0]["text"]
