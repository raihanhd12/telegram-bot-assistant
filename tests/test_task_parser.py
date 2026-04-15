"""Tests for task intent parser fallback and normalization."""

import asyncio

from src.app.services.llm.service import TaskIntentParserService


def build_parser() -> TaskIntentParserService:
    return TaskIntentParserService(
        llm_url="",
        llm_header_api_key="",
        llm_model_api_key="",
        llm_agent_id="",
        llm_output_type="json",
    )


def test_parser_create_task_from_natural_language():
    parser = build_parser()
    parsed = asyncio.run(parser.parse_intent("assign ke @budi kerjain landing page"))

    assert parsed["intent"] == "create_task"
    assert parsed["assignee_username"] == "budi"
    assert parsed["description"] == "kerjain landing page"


def test_parser_create_task_from_casual_language():
    parser = build_parser()
    parsed = asyncio.run(
        parser.parse_intent(
            "kasih task ke @iqbalpurba2610 biar dia kerja dong aku capek dia gak mau kerja terus. malah ngerokok"
        )
    )

    assert parsed["intent"] == "create_task"
    assert parsed["assignee_username"] == "iqbalpurba2610"
    assert parsed["description"] == (
        "biar dia kerja dong aku capek dia gak mau kerja terus. malah ngerokok"
    )


def test_parser_create_task_without_at_symbol():
    parser = build_parser()
    parsed = asyncio.run(parser.parse_intent("kasih lah task ke iqbal biar dia kerja dong"))

    assert parsed["intent"] == "create_task"
    assert parsed["assignee_username"] == "iqbal"
    assert parsed["description"] == "biar dia kerja dong"


def test_parser_create_task_with_filler_word_before_explicit_mention():
    parser = build_parser()
    parsed = asyncio.run(
        parser.parse_intent(
            "aku mau kasih task dong ke @iqbalpurba2610 suruh dia bersihin pantat kucing"
        )
    )

    assert parsed["intent"] == "create_task"
    assert parsed["assignee_username"] == "iqbalpurba2610"
    assert parsed["description"] == "suruh dia bersihin pantat kucing"


def test_parser_create_task_with_pronoun_assignee_stays_incomplete():
    parser = build_parser()
    parsed = asyncio.run(parser.parse_intent("iya aku mau kasih task ke dia"))

    assert parsed["intent"] == "create_task"
    assert parsed["assignee_username"] is None
    assert parsed["description"] is None


def test_parser_reassign_task():
    parser = build_parser()
    parsed = asyncio.run(parser.parse_intent("pindahin task 12 ke @andi"))

    assert parsed == {
        "intent": "reassign_task",
        "task_id": 12,
        "assignee_username": "andi",
        "description": None,
        "due_text": None,
    }


def test_parser_done_uses_reply_task_reference():
    parser = build_parser()
    parsed = asyncio.run(
        parser.parse_intent(
            "selesai",
            reply_text="📌 Task #42\nStatus: assigned\nTo: @budi\nBy: @alice\nDesc: review PR",
        )
    )

    assert parsed["intent"] == "mark_done"
    assert parsed["task_id"] == 42


def test_parser_cancel_task_from_gak_jadi_phrase():
    parser = build_parser()
    parsed = asyncio.run(parser.parse_intent("gak jadi dah si @iqbalpurba2610 ngerjain kucing loncat aja"))

    assert parsed["intent"] == "cancel_task"
    assert parsed["task_id"] is None
    assert parsed["assignee_username"] == "iqbalpurba2610"


def test_parser_list_member_tasks_from_reminder_phrase():
    parser = build_parser()
    parsed = asyncio.run(parser.parse_intent("reminder iqbal dong task nya apa aja"))

    assert parsed["intent"] == "list_member_tasks"
    assert parsed["assignee_username"] == "iqbal"
    assert parsed["description"] is None
    assert parsed["due_text"] is None


def test_parser_set_task_due_from_natural_language():
    parser = build_parser()
    parsed = asyncio.run(
        parser.parse_intent("aku mau @iqbalpurba2610 ini selesain task yang kucing loncat nanti sore")
    )

    assert parsed["intent"] == "set_task_due"
    assert parsed["assignee_username"] == "iqbalpurba2610"
    assert parsed["description"] == "kucing loncat"
    assert parsed["due_text"] == "nanti sore"


def test_parser_ignores_non_task_messages():
    parser = build_parser()
    parsed = asyncio.run(parser.parse_intent("halo semua, nanti standup jam 10 ya"))

    assert parsed["intent"] == "unknown"


def test_parser_set_task_due_with_lewat_expression():
    parser = build_parser()
    parsed = asyncio.run(
        parser.parse_intent("aku mau @iqbalpurba2610 selesain tasknya jam 12 lewat 7 siang")
    )

    assert parsed["intent"] == "set_task_due"
    assert parsed["assignee_username"] == "iqbalpurba2610"
    assert parsed["due_text"] is not None
    assert "jam 12 lewat 7" in parsed["due_text"]


def test_parser_set_task_due_short_with_lewat():
    parser = build_parser()
    parsed = asyncio.run(
        parser.parse_intent("aku mau sekarang jam 12 lewat 10 siang")
    )

    assert parsed["intent"] == "set_task_due"
    assert parsed["due_text"] is not None
    assert "jam 12 lewat 10" in parsed["due_text"]


def test_parser_set_task_due_from_reminder_phrase():
    parser = build_parser()
    parsed = asyncio.run(
        parser.parse_intent("jam 4 sore lewat 10 menit ingetin ke dia nya kali aja dia lupa")
    )

    assert parsed["intent"] == "set_task_due"
    assert parsed["due_text"] is not None
    assert "jam 4 sore lewat 10" in parsed["due_text"]


def test_parser_set_task_due_supports_sore_ini_lewat_menit_phrase():
    parser = build_parser()
    parsed = asyncio.run(
        parser.parse_intent("ingetin si iqbal jam 4 sore ini lewat 31 menit la ya ingetin dia")
    )

    assert parsed["intent"] == "set_task_due"
    assert parsed["due_text"] is not None
    assert "jam 4 sore ini lewat 31 menit" in parsed["due_text"]


def test_parser_set_task_due_uses_explicit_task_reference_not_due_hour():
    parser = build_parser()
    parsed = asyncio.run(
        parser.parse_intent("task 1 jam 4 sore lewat 20 ya ingetin ke dia")
    )

    assert parsed["intent"] == "set_task_due"
    assert parsed["task_id"] == 1
    assert parsed["due_text"] is not None
    assert "jam 4 sore lewat 20" in parsed["due_text"]


def test_parser_set_task_due_does_not_create_new_task():
    parser = build_parser()
    parsed = asyncio.run(
        parser.parse_intent("aku mau iqbal nyelesaiin task kasih makan kucing jam 12 lewat 10 siang hari ini")
    )

    assert parsed["intent"] == "set_task_due"
    assert parsed["assignee_username"] is not None or parsed["description"] is not None
    assert parsed["due_text"] is not None
