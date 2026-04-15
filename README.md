# Telegram Task Assignment Bot

Bot Telegram untuk assign task di group atau forum topic. Arsitektur tetap dipisah: `bot` sebagai adaptor Telegram, `services` untuk business logic, `repositories` untuk akses DB, dan `models` untuk skema.

## Fitur
- Natural language assignment: `assign ke @budi kerjain landing page`
- Reassign task: `pindahin task 12 ke @andi`
- Selesai/batal task via teks atau reply ke pesan task bot
- Scope per group/topic menggunakan `scope_chat_id`
- Topic locking dengan `/initiate` dan `/deinitiate`
- Listing task aktif dengan `/tasks`, `/mytasks`, `/assigned`
- Parser intent via direct vLLM / OpenAI-compatible API dengan fallback rule-based lokal
- Persistensi data dengan SQLAlchemy + Alembic

## Struktur
```text
src/
  bot/
  app/
    models/
    repositories/
    services/
      task/
      llm/
  database/
    migrations/
```

## Setup
1. Install dependency
  - Opsi non-Poetry untuk server:
```bash
pip install -r requirements.txt
```
  - Opsi Poetry:
```bash
poetry install
```

2. Siapkan environment
```bash
cp .env.example .env
```

3. Jalankan migrasi
  - Opsi non-Poetry:
```bash
alembic upgrade head
```
  - Opsi Poetry:
```bash
poetry run alembic upgrade head
```

4. Jalankan bot
  - Opsi non-Poetry:
```bash
python main.py
```
  - Opsi Poetry:
```bash
poetry run python main.py
```

## Menjalankan di server dengan PM2
Kalau server kamu tidak pakai Poetry, alurnya biasanya seperti ini:
```bash
pip install -r requirements.txt
alembic upgrade head
pm2 start main.py --name telegram-bot-task-assigned --interpreter python3
```

Kalau kamu ingin tetap pakai Poetry di server, pastikan `poetry` memang terpasang lalu jalankan:
```bash
poetry install --only main
poetry run python main.py
```

## Env Minimum
- `BOT_TOKEN`
- `DATABASE_URL`
- `ADMIN_TELEGRAM_USERNAMES` opsional
- `LLM_URL`
- `LLM_MODEL_NAME`
- `LLM_API_KEY` opsional

`TASK_PARSER_*` dan `CHAT_*` masih punya fallback kompatibilitas, tapi jalur utama sekarang direct LLM via `/v1/chat/completions`.

## Commands
- `/start`
- `/help`
- `/tasks`
- `/mytasks`
- `/assigned`
- `/initiate`
- `/deinitiate`
