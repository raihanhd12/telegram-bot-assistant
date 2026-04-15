"""Repository helpers for Member model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.app.models import Member


class MemberRepository:
    """CRUD helpers for task members."""

    @staticmethod
    def normalize_username(username: str | None) -> str | None:
        if not username:
            return None
        cleaned = username.strip().lstrip("@").lower()
        return cleaned or None

    @staticmethod
    def get_by_id(db: Session, member_id: int) -> Member | None:
        return db.query(Member).filter(Member.id == member_id).first()

    @staticmethod
    def get_by_telegram_id(db: Session, telegram_id: int) -> Member | None:
        return db.query(Member).filter(Member.telegram_id == telegram_id).first()

    @staticmethod
    def get_by_username(db: Session, username: str | None) -> Member | None:
        normalized = MemberRepository.normalize_username(username)
        if not normalized:
            return None
        return db.query(Member).filter(func.lower(Member.username) == normalized).first()

    @staticmethod
    def find_by_handle(db: Session, handle: str | None) -> Member | None:
        """Find member by exact or partial handle/full_name match."""
        normalized = MemberRepository.normalize_username(handle)
        if not normalized:
            return None

        exact = MemberRepository.get_by_username(db, normalized)
        if exact is not None:
            return exact

        prefix = (
            db.query(Member)
            .filter(Member.username.is_not(None), func.lower(Member.username).like(f"{normalized}%"))
            .order_by(func.length(Member.username).asc(), Member.id.asc())
            .first()
        )
        if prefix is not None:
            return prefix

        full_name_match = (
            db.query(Member)
            .filter(Member.full_name.is_not(None), func.lower(Member.full_name).like(f"%{normalized}%"))
            .order_by(func.length(Member.full_name).asc(), Member.id.asc())
            .first()
        )
        return full_name_match

    @staticmethod
    def create_member(db: Session, **kwargs: Any) -> Member:
        member = Member(**kwargs)
        db.add(member)
        db.commit()
        db.refresh(member)
        return member

    @staticmethod
    def update_member(db: Session, member: Member, update_data: dict[str, Any]) -> Member:
        for key, value in update_data.items():
            setattr(member, key, value)
        db.add(member)
        db.commit()
        db.refresh(member)
        return member

    @staticmethod
    def get_or_create_from_telegram(
        db: Session,
        telegram_id: int,
        username: str | None = None,
        full_name: str | None = None,
    ) -> Member:
        member = MemberRepository.get_by_telegram_id(db, telegram_id)
        normalized_username = MemberRepository.normalize_username(username)

        if member is None and normalized_username:
            member = MemberRepository.get_by_username(db, normalized_username)

        if member is None:
            return MemberRepository.create_member(
                db,
                telegram_id=telegram_id,
                username=normalized_username,
                full_name=full_name,
                is_active=True,
            )

        update_data: dict[str, Any] = {}
        if member.telegram_id != telegram_id:
            update_data["telegram_id"] = telegram_id
        if normalized_username and member.username != normalized_username:
            update_data["username"] = normalized_username
        if full_name and member.full_name != full_name:
            update_data["full_name"] = full_name
        if update_data:
            member = MemberRepository.update_member(db, member, update_data)
        return member

    @staticmethod
    def get_or_create_by_username(db: Session, username: str) -> Member:
        normalized = MemberRepository.normalize_username(username)
        if not normalized:
            raise ValueError("username is required")
        member = MemberRepository.find_by_handle(db, normalized)
        if member is not None:
            return member
        return MemberRepository.create_member(db, username=normalized, is_active=True)
