"""Логирование диалогов в SQLite."""
import json
import sqlite3
from datetime import datetime

import config


def _conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT,
                user_id INTEGER,
                username TEXT,
                first_name TEXT,
                question TEXT,
                answer TEXT,
                sources TEXT,
                found INTEGER
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                lang TEXT
            )"""
        )


def get_lang(user_id, default=None):
    """Возвращает сохранённый язык пользователя или default, если не задан."""
    with _conn() as c:
        row = c.execute("SELECT lang FROM users WHERE user_id=?", (user_id,)).fetchone()
    return row["lang"] if row else default


def set_lang(user_id, lang):
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO users (user_id, lang) VALUES (?, ?)",
            (user_id, lang),
        )


def log_message(user_id, username, first_name, question, answer, sources, found):
    with _conn() as c:
        c.execute(
            """INSERT INTO messages
               (ts, user_id, username, first_name, question, answer, sources, found)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().isoformat(timespec="seconds"),
                user_id, username, first_name, question, answer,
                json.dumps(sources, ensure_ascii=False), int(found),
            ),
        )


def fetch_messages(limit=1000, search=None):
    query = "SELECT * FROM messages"
    params = []
    if search:
        query += " WHERE question LIKE ? OR answer LIKE ?"
        params += [f"%{search}%", f"%{search}%"]
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with _conn() as c:
        return [dict(row) for row in c.execute(query, params).fetchall()]


def stats():
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        users = c.execute("SELECT COUNT(DISTINCT user_id) FROM messages").fetchone()[0]
        not_found = c.execute("SELECT COUNT(*) FROM messages WHERE found=0").fetchone()[0]
        today = c.execute(
            "SELECT COUNT(*) FROM messages WHERE substr(ts,1,10)=?",
            (datetime.now().date().isoformat(),),
        ).fetchone()[0]
    return {"total": total, "users": users, "not_found": not_found, "today": today}
