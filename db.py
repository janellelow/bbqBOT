"""
Tiny SQLite layer for the BBQ RSVP + payment bot.
One row per Telegram user who has ever messaged the bot.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = "bbq.db"


def init_db(path: str = DB_PATH):
    global DB_PATH
    DB_PATH = path
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attendees (
                telegram_id     INTEGER PRIMARY KEY,
                telegram_handle TEXT,
                display_name    TEXT,
                attending       INTEGER DEFAULT NULL,  -- NULL=no response, 1=yes, 0=no
                paid            INTEGER DEFAULT 0,     -- 0=no, 1=yes (auto or manual)
                payment_file_id TEXT,                  -- telegram file_id of the latest screenshot
                screenshot_path TEXT,                  -- local file path, so the web dashboard can show it
                detected_amount TEXT,                  -- best-guess amount/ref OCR pulled out
                needs_review    INTEGER DEFAULT 0,     -- 1 = OCR unsure, organizer should eyeball it
                updated_at      TEXT
            )
            """
        )
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _now():
    return datetime.now(timezone.utc).isoformat()


def upsert_attendee(telegram_id: int, telegram_handle: str, display_name: str):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO attendees (telegram_id, telegram_handle, display_name, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                telegram_handle = excluded.telegram_handle,
                display_name    = excluded.display_name,
                updated_at      = excluded.updated_at
            """,
            (telegram_id, telegram_handle, display_name, _now()),
        )
        conn.commit()


def set_attendance(telegram_id: int, attending: bool):
    with get_conn() as conn:
        conn.execute(
            "UPDATE attendees SET attending = ?, updated_at = ? WHERE telegram_id = ?",
            (1 if attending else 0, _now(), telegram_id),
        )
        conn.commit()


def set_payment(
    telegram_id: int,
    file_id: str,
    screenshot_path: str | None,
    detected_amount: str | None,
    needs_review: bool,
    paid: bool = True,
):
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE attendees
            SET paid = ?, payment_file_id = ?, screenshot_path = ?, detected_amount = ?, needs_review = ?, updated_at = ?
            WHERE telegram_id = ?
            """,
            (1 if paid else 0, file_id, screenshot_path, detected_amount, 1 if needs_review else 0, _now(), telegram_id),
        )
        conn.commit()


def manual_set_paid(telegram_id: int, paid: bool):
    with get_conn() as conn:
        conn.execute(
            "UPDATE attendees SET paid = ?, needs_review = 0, updated_at = ? WHERE telegram_id = ?",
            (1 if paid else 0, _now(), telegram_id),
        )
        conn.commit()


def find_attendees(query: str):
    """Match by @handle or display name (case-insensitive, exact). Returns a list."""
    q = query.strip().lstrip("@").lower()
    return [
        r for r in all_attendees()
        if (r["telegram_handle"] or "").lower() == q or (r["display_name"] or "").strip().lower() == q
    ]


def add_manual_attendee(name: str, paid: bool = True) -> int:
    """
    Add someone who never used the bot (e.g. paid Heidi directly).
    They get a negative placeholder ID so it can't clash with real Telegram IDs.
    """
    with get_conn() as conn:
        row = conn.execute("SELECT MIN(telegram_id) AS m FROM attendees").fetchone()
        new_id = min(row["m"] or 0, 0) - 1
        conn.execute(
            """
            INSERT INTO attendees (telegram_id, telegram_handle, display_name, attending, paid, needs_review, updated_at)
            VALUES (?, '', ?, 1, ?, 0, ?)
            """,
            (new_id, name.strip(), 1 if paid else 0, _now()),
        )
        conn.commit()
    return new_id


def get_attendee(telegram_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM attendees WHERE telegram_id = ?", (telegram_id,)).fetchone()
        return dict(row) if row else None


def all_attendees():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM attendees ORDER BY updated_at").fetchall()
        return [dict(r) for r in rows]
