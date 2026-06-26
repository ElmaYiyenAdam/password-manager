import sqlite3

DB_FILE = "vault.db"


def connect():
    return sqlite3.connect(DB_FILE)


def create_table():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS passwords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            website TEXT NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            note TEXT,
            updated_at TEXT,
            UNIQUE(website, username)
        )
    """)

    conn.commit()
    conn.close()


def add_or_update_password(website, username, password, note, updated_at):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO passwords (website, username, password, note, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(website, username)
        DO UPDATE SET
            password = excluded.password,
            note = excluded.note,
            updated_at = excluded.updated_at
    """, (website, username, password, note, updated_at))

    conn.commit()
    conn.close()


def get_passwords(search_text=""):
    conn = connect()
    cursor = conn.cursor()

    if search_text:
        search = f"%{search_text}%"
        cursor.execute("""
            SELECT id, website, username, password, note, updated_at
            FROM passwords
            WHERE website LIKE ? OR username LIKE ? OR note LIKE ?
            ORDER BY updated_at DESC
        """, (search, search, search))
    else:
        cursor.execute("""
            SELECT id, website, username, password, note, updated_at
            FROM passwords
            ORDER BY updated_at DESC
        """)

    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_password(password_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM passwords
        WHERE id = ?
    """, (password_id,))

    conn.commit()
    conn.close()