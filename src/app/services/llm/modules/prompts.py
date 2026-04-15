"""Prompt templates for task intent parsing."""


class LPrompts:
    """Prompt templates for task parser."""

    @staticmethod
    def get_system_prompt() -> str:
        return (
            "Kamu adalah parser intent untuk bot assignment task Telegram. "
            "Balas JSON valid saja tanpa markdown dan tanpa teks tambahan."
        )

    @staticmethod
    def get_parse_prompt(message_text: str, reply_text: str | None = None) -> str:
        reply_block = f'Reply target: "{reply_text}"\n' if reply_text else ""
        return f"""Analisis pesan Telegram berikut dan ubah menjadi JSON object.

Valid intents:
- create_task
- reassign_task
- mark_done
- cancel_task
- list_member_tasks
- set_task_due
- unknown

Aturan:
- Untuk create_task atau reassign_task, ambil assignee_username tanpa tanda @.
- Untuk list_member_tasks, ambil assignee_username user yang ingin dilihat task aktifnya.
- Untuk mark_done/cancel_task/reassign_task, ambil task_id jika ada di teks. Jika tidak ada, biarkan null.
- Untuk set_task_due, boleh ambil task_id jika ada. Jika tidak ada, biarkan null dan gunakan assignee_username atau description untuk bantu resolusi task.
- description hanya diisi untuk create_task. Untuk intent selain create_task, description JANGAN diisi — biarkan null.
- due_text hanya diisi untuk set_task_due, misalnya: "nanti sore", "besok pagi", "jam 15.00", "jam 12 lewat 10 siang".

PENTING - Cara membedakan set_task_due vs create_task:
- Jika pengguna menyebutkan WAKTU/DEADLINE (jam, nanti sore, besok, lewat, dll) dan sudah ada konteks task sebelumnya, itu set_task_due BUKAN create_task.
- Contoh set_task_due: "task 5 selesaiin jam 3", "iqbal harus selesaiin tasknya jam 12 lewat 7", "mau sekarang jam 12 lewat 10 siang" (merujuk task yang sudah ada).
- Contoh create_task: "kasih task ke iqbal kerjain landing page" (membuat task BARU tanpa menyebut task yang sudah ada).
- Jika pesan menyebut "tasknya" (dengan nya), kemungkinan besar merujuk task yang sudah ada → set_task_due atau mark_done.
- Jika pesan seperti "aku mau [username] selesaiin task [desc] jam [waktu]", itu set_task_due BUKAN create_task.

- Jika pesan tidak jelas terkait assignment task, kembalikan intent unknown.

Skema output:
{{
  "intent": "create_task|reassign_task|mark_done|cancel_task|list_member_tasks|set_task_due|unknown",
  "task_id": 12 atau null,
  "assignee_username": "budi" atau null,
  "description": "kerjain landing page" atau null,
  "due_text": "nanti sore" atau null
}}

Message: "{message_text}"
{reply_block}
Keluarkan JSON valid saja."""
