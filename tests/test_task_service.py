"""Service tests for task orchestration."""

from src.app.models import TaskEventType, TaskStatus
from src.app.repositories.member import MemberRepository
from src.app.repositories.task import TaskRepository
from src.app.repositories.task_event import TaskEventRepository
from src.app.services.task.service import TaskService


def test_create_task_from_intent(db_session):
    service = TaskService(db_session)

    handled, response = service.handle_intent(
        parsed_intent={
            "intent": "create_task",
            "task_id": None,
            "assignee_username": "budi",
            "description": "Kerjain landing page",
        },
        scope_chat_id=12345,
        raw_chat_id=-100,
        thread_id=10,
        source_message_id=99,
        source_text="assign ke @budi kerjain landing page",
        reply_text=None,
        actor_telegram_id=1,
        actor_username="alice",
        actor_full_name="Alice",
        is_admin=False,
    )

    assert handled is True
    assert response is not None
    task = TaskRepository.list_tasks(db_session, scope_chat_id=12345)[0]
    assert task.description == "Kerjain landing page"
    assert task.status == TaskStatus.ASSIGNED
    assert task.assigned_to.username == "budi"
    assert f"Task #{task.id}" in response


def test_reassign_task_updates_same_row_and_logs_event(db_session):
    service = TaskService(db_session)
    service.handle_intent(
        parsed_intent={
            "intent": "create_task",
            "task_id": None,
            "assignee_username": "budi",
            "description": "Deploy staging",
        },
        scope_chat_id=555,
        raw_chat_id=-100,
        thread_id=None,
        source_message_id=10,
        source_text="assign ke @budi deploy staging",
        reply_text=None,
        actor_telegram_id=1,
        actor_username="alice",
        actor_full_name="Alice",
        is_admin=False,
    )
    task = TaskRepository.list_tasks(db_session, scope_chat_id=555)[0]

    handled, response = service.handle_intent(
        parsed_intent={
            "intent": "reassign_task",
            "task_id": task.id,
            "assignee_username": "andi",
            "description": None,
        },
        scope_chat_id=555,
        raw_chat_id=-100,
        thread_id=None,
        source_message_id=11,
        source_text=f"pindahin task {task.id} ke @andi",
        reply_text=None,
        actor_telegram_id=1,
        actor_username="alice",
        actor_full_name="Alice",
        is_admin=False,
    )

    assert handled is True
    assert response == f"🔁 Task #{task.id} dipindahkan ke @andi."
    updated = TaskRepository.get_by_id_in_scope(db_session, task.id, 555)
    assert updated is not None
    assert updated.assigned_to.username == "andi"
    events = TaskEventRepository.list_by_task(db_session, task.id)
    assert [event.event_type for event in events] == [
        TaskEventType.ASSIGNED,
        TaskEventType.REASSIGNED,
    ]


def test_mark_done_via_reply_task_reference(db_session):
    service = TaskService(db_session)
    service.handle_intent(
        parsed_intent={
            "intent": "create_task",
            "task_id": None,
            "assignee_username": "budi",
            "description": "QA smoke test",
        },
        scope_chat_id=777,
        raw_chat_id=-100,
        thread_id=None,
        source_message_id=20,
        source_text="assign ke @budi QA smoke test",
        reply_text=None,
        actor_telegram_id=1,
        actor_username="alice",
        actor_full_name="Alice",
        is_admin=False,
    )
    task = TaskRepository.list_tasks(db_session, scope_chat_id=777)[0]
    bot_summary = (
        f"📌 Task #{task.id}\n"
        "Status: assigned\n"
        "To: @budi\n"
        "By: @alice\n"
        "Desc: QA smoke test"
    )

    handled, response = service.handle_intent(
        parsed_intent={
            "intent": "mark_done",
            "task_id": None,
            "assignee_username": None,
            "description": None,
        },
        scope_chat_id=777,
        raw_chat_id=-100,
        thread_id=None,
        source_message_id=21,
        source_text="selesai",
        reply_text=bot_summary,
        actor_telegram_id=2,
        actor_username="budi",
        actor_full_name="Budi",
        is_admin=False,
    )

    assert handled is True
    assert response == f"✅ Task #{task.id} ditandai selesai."
    updated = TaskRepository.get_by_id_in_scope(db_session, task.id, 777)
    assert updated is not None
    assert updated.status == TaskStatus.DONE


def test_cancel_requires_assigner_or_admin(db_session):
    service = TaskService(db_session)
    service.handle_intent(
        parsed_intent={
            "intent": "create_task",
            "task_id": None,
            "assignee_username": "budi",
            "description": "Prepare report",
        },
        scope_chat_id=888,
        raw_chat_id=-100,
        thread_id=None,
        source_message_id=30,
        source_text="assign ke @budi prepare report",
        reply_text=None,
        actor_telegram_id=1,
        actor_username="alice",
        actor_full_name="Alice",
        is_admin=False,
    )
    task = TaskRepository.list_tasks(db_session, scope_chat_id=888)[0]

    handled, response = service.handle_intent(
        parsed_intent={
            "intent": "cancel_task",
            "task_id": task.id,
            "assignee_username": None,
            "description": None,
        },
        scope_chat_id=888,
        raw_chat_id=-100,
        thread_id=None,
        source_message_id=31,
        source_text=f"batalkan task {task.id}",
        reply_text=None,
        actor_telegram_id=3,
        actor_username="charlie",
        actor_full_name="Charlie",
        is_admin=False,
    )

    assert handled is False
    assert response == "❌ Hanya assigner atau admin yang bisa membatalkan task ini."


def test_create_task_resolves_partial_member_handle(db_session):
    service = TaskService(db_session)
    MemberRepository.create_member(
        db_session,
        telegram_id=2,
        username="iqbalpurba2610",
        full_name="Iqbal Purba",
    )

    handled, response = service.handle_intent(
        parsed_intent={
            "intent": "create_task",
            "task_id": None,
            "assignee_username": "iqbal",
            "description": "tolong review laporan",
        },
        scope_chat_id=999,
        raw_chat_id=-100,
        thread_id=None,
        source_message_id=40,
        source_text="kasih lah task ke iqbal tolong review laporan",
        reply_text=None,
        actor_telegram_id=1,
        actor_username="alice",
        actor_full_name="Alice",
        is_admin=False,
    )

    assert handled is True
    assert response is not None
    task = TaskRepository.list_tasks(db_session, scope_chat_id=999)[0]
    assert task.assigned_to.username == "iqbalpurba2610"


def test_cancel_latest_open_task_by_assignee_without_task_id(db_session):
    service = TaskService(db_session)
    service.handle_intent(
        parsed_intent={
            "intent": "create_task",
            "task_id": None,
            "assignee_username": "iqbalpurba2610",
            "description": "kerjain landing page",
        },
        scope_chat_id=321,
        raw_chat_id=-100,
        thread_id=None,
        source_message_id=50,
        source_text="assign ke @iqbalpurba2610 kerjain landing page",
        reply_text=None,
        actor_telegram_id=1,
        actor_username="alice",
        actor_full_name="Alice",
        is_admin=False,
    )
    task = TaskRepository.list_tasks(db_session, scope_chat_id=321)[0]

    handled, response = service.handle_intent(
        parsed_intent={
            "intent": "cancel_task",
            "task_id": None,
            "assignee_username": "iqbalpurba2610",
            "description": None,
        },
        scope_chat_id=321,
        raw_chat_id=-100,
        thread_id=None,
        source_message_id=51,
        source_text="gak jadi dah si @iqbalpurba2610 ngerjain itu",
        reply_text=None,
        actor_telegram_id=1,
        actor_username="alice",
        actor_full_name="Alice",
        is_admin=False,
    )

    assert handled is True
    assert response == f"🛑 Task #{task.id} dibatalkan."
    updated = TaskRepository.get_by_id_in_scope(db_session, task.id, 321)
    assert updated is not None
    assert updated.status == TaskStatus.CANCELLED


def test_list_member_tasks_from_natural_language_intent(db_session):
    service = TaskService(db_session)
    service.handle_intent(
        parsed_intent={
            "intent": "create_task",
            "task_id": None,
            "assignee_username": "iqbalpurba2610",
            "description": "kerjain kucing loncat",
            "due_text": None,
        },
        scope_chat_id=654,
        raw_chat_id=-100,
        thread_id=None,
        source_message_id=60,
        source_text="assign ke @iqbalpurba2610 kerjain kucing loncat",
        reply_text=None,
        actor_telegram_id=1,
        actor_username="alice",
        actor_full_name="Alice",
        is_admin=False,
    )

    handled, response = service.handle_intent(
        parsed_intent={
            "intent": "list_member_tasks",
            "task_id": None,
            "assignee_username": "iqbal",
            "description": None,
            "due_text": None,
        },
        scope_chat_id=654,
        raw_chat_id=-100,
        thread_id=None,
        source_message_id=61,
        source_text="reminder iqbal dong task nya apa aja",
        reply_text=None,
        actor_telegram_id=1,
        actor_username="alice",
        actor_full_name="Alice",
        is_admin=False,
    )

    assert handled is True
    assert response is not None
    assert "Task Untuk @iqbalpurba2610" in response
    assert "kerjain kucing loncat" in response


def test_set_due_updates_existing_task_by_assignee_and_description(db_session):
    service = TaskService(db_session)
    service.handle_intent(
        parsed_intent={
            "intent": "create_task",
            "task_id": None,
            "assignee_username": "iqbalpurba2610",
            "description": "kucing loncat",
            "due_text": None,
        },
        scope_chat_id=7777,
        raw_chat_id=-100,
        thread_id=None,
        source_message_id=70,
        source_text="assign ke @iqbalpurba2610 kucing loncat",
        reply_text=None,
        actor_telegram_id=1,
        actor_username="alice",
        actor_full_name="Alice",
        is_admin=False,
    )
    task = TaskRepository.list_tasks(db_session, scope_chat_id=7777)[0]

    handled, response = service.handle_intent(
        parsed_intent={
            "intent": "set_task_due",
            "task_id": None,
            "assignee_username": "iqbalpurba2610",
            "description": "kucing loncat",
            "due_text": "nanti sore",
        },
        scope_chat_id=7777,
        raw_chat_id=-100,
        thread_id=None,
        source_message_id=71,
        source_text="aku mau @iqbalpurba2610 ini selesain task yang kucing loncat nanti sore",
        reply_text=None,
        actor_telegram_id=1,
        actor_username="alice",
        actor_full_name="Alice",
        is_admin=False,
    )

    assert handled is True
    assert response is not None
    assert f"Task #{task.id}" in response
    updated = TaskRepository.get_by_id_in_scope(db_session, task.id, 7777)
    assert updated is not None
    assert updated.due_text == "nanti sore"
    assert updated.due_at is not None


def test_set_due_uses_latest_task_from_same_assigner_as_follow_up(db_session):
    service = TaskService(db_session)
    service.handle_intent(
        parsed_intent={
            "intent": "create_task",
            "task_id": None,
            "assignee_username": "iqbalpurba2610",
            "description": "kasih makan ayam",
            "due_text": None,
        },
        scope_chat_id=8800,
        raw_chat_id=-100,
        thread_id=None,
        source_message_id=80,
        source_text="assign ke @iqbalpurba2610 kasih makan ayam",
        reply_text=None,
        actor_telegram_id=1,
        actor_username="alice",
        actor_full_name="Alice",
        is_admin=False,
    )
    task = TaskRepository.list_tasks(db_session, scope_chat_id=8800)[0]

    handled, response = service.handle_intent(
        parsed_intent={
            "intent": "set_task_due",
            "task_id": None,
            "assignee_username": None,
            "description": None,
            "due_text": "jam 4 sore lewat 10",
        },
        scope_chat_id=8800,
        raw_chat_id=-100,
        thread_id=None,
        source_message_id=81,
        source_text="jam 4 sore lewat 10 menit ingetin ke dia nya kali aja dia lupa",
        reply_text=None,
        actor_telegram_id=1,
        actor_username="alice",
        actor_full_name="Alice",
        is_admin=False,
    )

    assert handled is True
    assert response is not None
    assert f"Task #{task.id}" in response
    updated = TaskRepository.get_by_id_in_scope(db_session, task.id, 8800)
    assert updated is not None
    assert updated.due_text == "jam 4 sore lewat 10"
    assert updated.due_at is not None
