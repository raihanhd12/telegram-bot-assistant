"""Repository tests for task domain."""

from src.app.models import Member, TaskEventType, TaskStatus
from src.app.repositories.member import MemberRepository
from src.app.repositories.task import TaskRepository
from src.app.repositories.task_event import TaskEventRepository


def test_task_repository_lists_by_scope_and_actor(db_session):
    assigner = MemberRepository.create_member(db_session, telegram_id=1, username="alice")
    assignee = MemberRepository.create_member(db_session, telegram_id=2, username="budi")
    other = MemberRepository.create_member(db_session, telegram_id=3, username="andi")

    open_task = TaskRepository.create_task(
        db_session,
        scope_chat_id=1001,
        raw_chat_id=-10,
        thread_id=7,
        description="Kerjain landing page",
        status=TaskStatus.ASSIGNED,
        assigned_by_member_id=assigner.id,
        assigned_to_member_id=assignee.id,
    )
    TaskRepository.create_task(
        db_session,
        scope_chat_id=1002,
        raw_chat_id=-10,
        thread_id=8,
        description="Task lain",
        status=TaskStatus.ASSIGNED,
        assigned_by_member_id=assigner.id,
        assigned_to_member_id=other.id,
    )

    listed = TaskRepository.list_tasks(
        db_session,
        scope_chat_id=1001,
        status=TaskStatus.ASSIGNED,
        assigned_to_member_id=assignee.id,
    )

    assert [task.id for task in listed] == [open_task.id]


def test_task_event_repository_stores_audit_events(db_session):
    assigner = MemberRepository.create_member(db_session, telegram_id=10, username="alice")
    assignee = MemberRepository.create_member(db_session, telegram_id=11, username="budi")
    task = TaskRepository.create_task(
        db_session,
        scope_chat_id=2001,
        raw_chat_id=-20,
        thread_id=None,
        description="Review PR",
        status=TaskStatus.ASSIGNED,
        assigned_by_member_id=assigner.id,
        assigned_to_member_id=assignee.id,
    )

    TaskEventRepository.create_event(
        db_session,
        task_id=task.id,
        event_type=TaskEventType.ASSIGNED,
        actor_member_id=assigner.id,
        previous_assignee_member_id=None,
        new_assignee_member_id=assignee.id,
    )

    events = TaskEventRepository.list_by_task(db_session, task.id)
    assert len(events) == 1
    assert events[0].event_type == TaskEventType.ASSIGNED
    assert events[0].new_assignee_member_id == assignee.id
