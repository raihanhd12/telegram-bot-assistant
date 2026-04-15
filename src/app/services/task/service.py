"""Facade service for task assignment operations."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.app.models import Member
from src.app.repositories.member import MemberRepository
from src.app.services.task.modules import (
    TaskCreateService,
    TaskReadService,
    TaskUpdateService,
    TaskValidators,
)

logger = logging.getLogger(__name__)


class TaskService:
    """High-level task orchestration service."""

    def __init__(self, db: Session):
        self.db = db
        self.create = TaskCreateService(db)
        self.read = TaskReadService(db)
        self.update = TaskUpdateService(db)

    def ensure_member(self, telegram_id: int, username: str | None, full_name: str | None) -> Member:
        return self.create.ensure_actor(telegram_id, username, full_name)

    def list_open_tasks(self, scope_chat_id: int, limit: int = 20) -> str:
        return self.read.format_task_list("📋 Open Tasks", self.read.list_open_tasks(scope_chat_id, limit))

    def list_my_tasks(
        self,
        scope_chat_id: int,
        telegram_id: int,
        username: str | None,
        full_name: str | None,
        limit: int = 20,
    ) -> str:
        member = self.ensure_member(telegram_id, username, full_name)
        tasks = self.read.list_tasks_for_assignee(scope_chat_id, member, limit)
        return self.read.format_task_list("🙋 My Tasks", tasks)

    def list_assigned_by_me(
        self,
        scope_chat_id: int,
        telegram_id: int,
        username: str | None,
        full_name: str | None,
        limit: int = 20,
    ) -> str:
        member = self.ensure_member(telegram_id, username, full_name)
        tasks = self.read.list_tasks_from_assigner(scope_chat_id, member, limit)
        return self.read.format_task_list("📤 Assigned By Me", tasks)

    def list_tasks_for_member_handle(
        self,
        scope_chat_id: int,
        member_handle: str,
        limit: int = 20,
    ) -> str:
        member = MemberRepository.find_by_handle(self.db, member_handle)
        if member is None:
            return f"❌ User @{member_handle} belum dikenal bot."
        tasks = self.read.list_tasks_for_assignee(scope_chat_id, member, limit)
        return self.read.format_task_list(
            f"📋 Task Untuk {TaskValidators.display_member(member)}",
            tasks,
        )

    def handle_intent(
        self,
        parsed_intent: dict,
        scope_chat_id: int,
        raw_chat_id: int,
        thread_id: int | None,
        source_message_id: int | None,
        source_text: str,
        reply_text: str | None,
        actor_telegram_id: int,
        actor_username: str | None,
        actor_full_name: str | None,
        is_admin: bool,
    ) -> tuple[bool, str | None]:
        intent_name = parsed_intent.get("intent") or "unknown"
        if intent_name == "unknown":
            logger.info("TaskService ignored unknown intent")
            return False, None

        actor = self.ensure_member(actor_telegram_id, actor_username, actor_full_name)
        task_id = parsed_intent.get("task_id") or TaskValidators.extract_task_id_from_reply(reply_text)
        assignee_username = TaskValidators.normalize_username(parsed_intent.get("assignee_username"))
        description = TaskValidators.ensure_description(parsed_intent.get("description"))
        due_text = TaskValidators.ensure_description(parsed_intent.get("due_text"))
        logger.info(
            "TaskService handling intent=%s actor=%s(%s) scope_chat_id=%s task_id=%s assignee_username=%s due_text=%s",
            intent_name,
            actor.username,
            actor.telegram_id,
            scope_chat_id,
            task_id,
            assignee_username,
            due_text,
        )

        try:
            if intent_name == "list_member_tasks":
                if not assignee_username:
                    logger.info("List member tasks rejected because assignee_username is missing")
                    return False, "❌ Sebutkan username yang mau dilihat task-nya."
                logger.info("Listing tasks for member handle=%s", assignee_username)
                return True, self.list_tasks_for_member_handle(scope_chat_id, assignee_username)

            if intent_name == "create_task":
                if not assignee_username or not description:
                    logger.info("Create task rejected due to incomplete assignee/description")
                    return False, "❌ Format assign belum lengkap. Sertakan @username dan deskripsi task."
                assignee = self.create.ensure_assignee(assignee_username)
                task = self.create.create_task(
                    scope_chat_id=scope_chat_id,
                    raw_chat_id=raw_chat_id,
                    thread_id=thread_id,
                    assigned_by=actor,
                    assigned_to=assignee,
                    description=description,
                    source_message_id=source_message_id,
                    source_text=source_text,
                )
                logger.info("Task created successfully: task_id=%s assigned_to=%s", task.id, assignee.username)
                return True, TaskValidators.format_task(task)

            if task_id is None:
                task = self._resolve_latest_open_task_by_assignee(
                    scope_chat_id=scope_chat_id,
                    actor=actor,
                    assignee_username=assignee_username,
                    description_fragment=description,
                    is_admin=is_admin,
                )
                if task is None and intent_name == "set_task_due":
                    task = self._resolve_latest_open_task_for_assigner(
                        scope_chat_id=scope_chat_id,
                        actor=actor,
                        description_fragment=description,
                    )
                if task is None:
                    logger.info("Task update rejected because task_id is missing and no fallback task was resolved")
                    return False, "❌ Task ID tidak ditemukan. Sebutkan nomor task, mention assignee, atau reply ke pesan task bot."
            else:
                task = self.read.get_task(task_id, scope_chat_id)
                if task is None:
                    logger.info("Task lookup failed: task_id=%s scope_chat_id=%s", task_id, scope_chat_id)
                    return False, f"❌ Task #{task_id} tidak ditemukan di topic ini."

            if intent_name == "reassign_task":
                if not assignee_username:
                    logger.info("Reassign rejected because assignee_username is missing")
                    return False, "❌ Username assignee baru tidak ditemukan."
                new_assignee = self.create.ensure_assignee(assignee_username)
                task = self.update.reassign_task(task, actor, new_assignee, is_admin=is_admin)
                logger.info("Task reassigned: task_id=%s new_assignee=%s", task.id, task.assigned_to.username)
                return True, f"🔁 Task #{task.id} dipindahkan ke {TaskValidators.display_member(task.assigned_to)}."

            if intent_name == "mark_done":
                task = self.update.mark_done(task, actor, is_admin=is_admin)
                logger.info("Task marked done: task_id=%s", task.id)
                return True, f"✅ Task #{task.id} ditandai selesai."

            if intent_name == "cancel_task":
                task = self.update.cancel_task(task, actor, is_admin=is_admin)
                logger.info("Task cancelled: task_id=%s", task.id)
                return True, f"🛑 Task #{task.id} dibatalkan."

            if intent_name == "set_task_due":
                if not due_text:
                    logger.info("Set due rejected because due_text is missing")
                    return False, "❌ Waktu target belum terbaca. Coba pakai format seperti 'nanti sore' atau 'jam 15.00'."
                due_at = TaskValidators.resolve_due_at(due_text)
                task = self.update.set_due(task, actor=actor, due_at=due_at, due_text=due_text, is_admin=is_admin)
                logger.info("Task due updated: task_id=%s due_text=%s due_at=%s", task.id, due_text, due_at)
                return True, f"⏰ Task #{task.id} due di-set ke {TaskValidators.format_due(task)}."

            logger.info("TaskService reached unsupported intent branch: %s", intent_name)
            return False, None
        except PermissionError as exc:
            logger.warning("TaskService permission error: %s", exc)
            return False, f"❌ {exc}"
        except ValueError as exc:
            logger.warning("TaskService validation error: %s", exc)
            return False, f"❌ {exc}"

    def _resolve_latest_open_task_by_assignee(
        self,
        scope_chat_id: int,
        actor: Member,
        assignee_username: str | None,
        description_fragment: str | None,
        is_admin: bool,
    ):
        if not assignee_username:
            return None
        assignee = MemberRepository.find_by_handle(self.db, assignee_username)
        if assignee is None:
            logger.info("Fallback task resolution failed because assignee handle was not found: %s", assignee_username)
            return None

        if description_fragment:
            task = self.read.get_latest_matching_open_task(
                scope_chat_id=scope_chat_id,
                description_fragment=description_fragment,
                assigned_to_member_id=assignee.id,
                assigned_by_member_id=None if is_admin else actor.id,
            )
            if task is not None:
                logger.info(
                    "Fallback task resolution by assignee+description: assignee=%s description=%r resolved_task_id=%s",
                    assignee.username,
                    description_fragment,
                    task.id,
                )
                return task

        task = self.read.get_latest_open_task(
            scope_chat_id=scope_chat_id,
            assigned_to_member_id=assignee.id,
            assigned_by_member_id=None if is_admin else actor.id,
        )
        logger.info(
            "Fallback task resolution by assignee: assignee=%s resolved_task_id=%s",
            assignee.username,
            task.id if task else None,
        )
        return task

    def _resolve_latest_open_task_for_assigner(
        self,
        scope_chat_id: int,
        actor: Member,
        description_fragment: str | None,
    ):
        if description_fragment:
            task = self.read.get_latest_matching_open_task(
                scope_chat_id=scope_chat_id,
                description_fragment=description_fragment,
                assigned_by_member_id=actor.id,
            )
            if task is not None:
                logger.info(
                    "Fallback task resolution by assigner+description: actor=%s description=%r resolved_task_id=%s",
                    actor.username,
                    description_fragment,
                    task.id,
                )
                return task

        task = self.read.get_latest_open_task(
            scope_chat_id=scope_chat_id,
            assigned_by_member_id=actor.id,
        )
        logger.info(
            "Fallback task resolution by assigner: actor=%s resolved_task_id=%s",
            actor.username,
            task.id if task else None,
        )
        return task
