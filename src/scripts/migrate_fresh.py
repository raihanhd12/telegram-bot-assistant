import os
import subprocess
import sys
from urllib.parse import urlparse, urlunparse

# Tambah root project ke path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import psycopg
from psycopg import sql

import src.config.env as env

DB_URL = env.DATABASE_URL
parsed = urlparse(DB_URL)

DB_NAME = parsed.path.lstrip("/") or "fastapi_db"
DB_HOST = parsed.hostname or "localhost"
DB_PORT = parsed.port or 5432
DB_USER = parsed.username or "postgres"

# Maintenance DB: biasanya "postgres"
MAINT_DB = os.getenv("MAINTENANCE_DB", "postgres")


def _build_db_url(dbname: str) -> str:
    """Build a new DATABASE_URL pointing to a specific database name.

    Normalize the scheme by stripping SQLAlchemy dialect suffix (e.g., '+psycopg')
    so it becomes compatible with libpq-style connection strings used by psycopg.
    """
    new_parsed = parsed._replace(path=f"/{dbname}")
    # Normalize scheme: e.g. 'postgresql+psycopg' -> 'postgresql'
    scheme = new_parsed.scheme.split("+", 1)[0]
    new_parsed = new_parsed._replace(scheme=scheme)
    return urlunparse(new_parsed)


def require_reset_flag():
    """
    Safety guard: prevent accidental resets unless explicitly allowed.
    Run with: ALLOW_DB_RESET=true python src/scripts/migrate_fresh.py
    """
    if os.getenv("ALLOW_DB_RESET", "").lower() != "true":
        print("❌ Refusing to reset DB.")
        print("Set ALLOW_DB_RESET=true to proceed.")
        sys.exit(1)

    # Optional extra safety checks (uncomment if you want stricter rules):
    # banned_keywords = {"prod", "production"}
    # if any(k in DB_NAME.lower() for k in banned_keywords):
    #     print(f"❌ Refusing: DB name '{DB_NAME}' looks like production.")
    #     sys.exit(1)


def terminate_connections(conn, db_name: str):
    print(f"Terminating active connections to database '{db_name}'...")
    conn.execute(
        """
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = %s AND pid <> pg_backend_pid();
        """,
        (db_name,),
    )


def drop_database(conn, db_name: str):
    print(f"Dropping database '{db_name}' if exists...")
    conn.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(db_name)))


def create_database(conn, db_name: str):
    print(f"Creating database '{db_name}'...")
    conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))


def upgrade_migrations():
    print("Upgrading Alembic migrations...")
    subprocess.run(["alembic", "upgrade", "head"], check=True)


def main():

    maint_url = _build_db_url(MAINT_DB)
    print(f"Connecting to maintenance DB '{MAINT_DB}' on {DB_HOST}:{DB_PORT} as {DB_USER}...")

    # autocommit=True diperlukan karena DROP/CREATE DATABASE tidak boleh di dalam transaksi
    with psycopg.connect(maint_url, autocommit=True) as conn:
        terminate_connections(conn, DB_NAME)
        drop_database(conn, DB_NAME)
        create_database(conn, DB_NAME)

    upgrade_migrations()
    print("✅ Database fresh migrated!")


if __name__ == "__main__":
    main()
