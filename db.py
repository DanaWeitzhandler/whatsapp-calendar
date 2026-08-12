import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "./app.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL,
                title TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_state (
                phone TEXT PRIMARY KEY,
                last_event_id INTEGER
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_event(phone, title, start_time, end_time):
    conn = _connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO events (phone, title, start_time, end_time, status)
            VALUES (?, ?, ?, ?, 'active')
            """,
            (phone, title, start_time, end_time),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_event(event_id):
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_event(event_id, phone, title=None, start_time=None, end_time=None):
    fields = []
    values = []
    if title is not None:
        fields.append("title = ?")
        values.append(title)
    if start_time is not None:
        fields.append("start_time = ?")
        values.append(start_time)
    if end_time is not None:
        fields.append("end_time = ?")
        values.append(end_time)

    if not fields:
        return False

    values.append(event_id)
    values.append(phone)
    conn = _connect()
    try:
        cursor = conn.execute(
            f"UPDATE events SET {', '.join(fields)} WHERE id = ? AND phone = ?",
            values,
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def cancel_event(event_id, phone):
    conn = _connect()
    try:
        cursor = conn.execute(
            "UPDATE events SET status = 'cancelled' WHERE id = ? AND phone = ?",
            (event_id, phone),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_events_for_phone(phone, active_only=False):
    conn = _connect()
    try:
        if active_only:
            rows = conn.execute(
                "SELECT * FROM events WHERE phone = ? AND status = 'active' ORDER BY start_time ASC",
                (phone,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events WHERE phone = ? ORDER BY start_time ASC",
                (phone,),
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_last_event_id(phone):
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT last_event_id FROM conversation_state WHERE phone = ?",
            (phone,),
        ).fetchone()
        return row["last_event_id"] if row else None
    finally:
        conn.close()


def set_last_event_id(phone, event_id):
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO conversation_state (phone, last_event_id)
            VALUES (?, ?)
            ON CONFLICT(phone) DO UPDATE SET last_event_id = excluded.last_event_id
            """,
            (phone, event_id),
        )
        conn.commit()
    finally:
        conn.close()
