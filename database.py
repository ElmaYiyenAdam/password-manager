import sqlite3
import os
import hashlib
import binascii
import base64
from cryptography.fernet import Fernet, InvalidToken

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
            favorite INTEGER NOT NULL DEFAULT 0,
            UNIQUE(website, username)
        )
    """)

    migrate_passwords_table(cursor)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def migrate_passwords_table(cursor):
    cursor.execute("PRAGMA table_info(passwords)")
    columns = {row[1] for row in cursor.fetchall()}

    if "favorite" not in columns:
        cursor.execute(
            "ALTER TABLE passwords ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0"
        )


def set_setting(key, value):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO settings (key, value)
        VALUES (?, ?)
    """, (key, value))

    conn.commit()
    conn.close()


def get_setting(key, default=None):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = cursor.fetchone()

    conn.close()

    if result is None:
        return default

    return result[0]


def hash_master_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100000
    )

    return (
        binascii.hexlify(salt).decode("utf-8"),
        binascii.hexlify(password_hash).decode("utf-8")
    )


def has_master_password():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM settings WHERE key = ?", ("master_password",))
    result = cursor.fetchone()

    conn.close()
    return result is not None


def set_master_password(password):
    salt, password_hash = hash_master_password(password)
    value = f"{salt}:{password_hash}"

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO settings (key, value)
        VALUES (?, ?)
    """, ("master_password", value))

    conn.commit()
    conn.close()


def create_master_password_value_and_crypto(password):
    salt_hex, password_hash = hash_master_password(password)
    salt = binascii.unhexlify(salt_hex)

    return f"{salt_hex}:{password_hash}", create_crypto(password, salt)


def get_master_salt():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM settings WHERE key = ?", ("master_password",))
    result = cursor.fetchone()

    conn.close()

    if result is None:
        return None

    salt_hex, _ = result[0].split(":")
    return binascii.unhexlify(salt_hex)


def verify_master_password(password):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT value FROM settings WHERE key = ?", ("master_password",))
    result = cursor.fetchone()

    conn.close()

    if result is None:
        return False

    stored_value = result[0]
    salt_hex, stored_hash = stored_value.split(":")

    salt = binascii.unhexlify(salt_hex)
    _, entered_hash = hash_master_password(password, salt)

    return entered_hash == stored_hash


def create_crypto(master_password, salt=None):
    if salt is None:
        salt = get_master_salt()

    if salt is None:
        raise ValueError("Master password salt not found.")

    key = hashlib.pbkdf2_hmac(
        "sha256",
        master_password.encode("utf-8"),
        salt,
        100000
    )

    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)


def encrypt_password(crypto, password):
    return crypto.encrypt(password.encode("utf-8")).decode("utf-8")


def decrypt_password(crypto, encrypted_password):
    try:
        return crypto.decrypt(encrypted_password.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return "[decryption failed]"


def decrypt_password_strict(crypto, encrypted_password):
    return crypto.decrypt(encrypted_password.encode("utf-8")).decode("utf-8")


def add_or_update_password(
    website,
    username,
    password,
    note,
    updated_at,
    crypto,
    favorite=0
):
    encrypted_password = encrypt_password(crypto, password)
    favorite = 1 if favorite else 0

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO passwords (website, username, password, note, updated_at, favorite)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(website, username)
        DO UPDATE SET
            password = excluded.password,
            note = excluded.note,
            updated_at = excluded.updated_at
    """, (website, username, encrypted_password, note, updated_at, favorite))

    conn.commit()
    conn.close()


def decrypt_password_rows(rows, crypto=None):
    decrypted_rows = []

    for row in rows:
        password_id, website, username, encrypted_password, note, updated_at, favorite = row

        if crypto is None:
            password = "[locked]"
        else:
            password = decrypt_password(crypto, encrypted_password)

        decrypted_rows.append(
            (password_id, website, username, password, note, updated_at, int(favorite or 0))
        )

    return decrypted_rows


def get_passwords(search_text="", crypto=None):
    conn = connect()
    cursor = conn.cursor()

    if search_text:
        search = f"%{search_text}%"
        cursor.execute("""
            SELECT id, website, username, password, note, updated_at, favorite
            FROM passwords
            WHERE website LIKE ? OR username LIKE ? OR note LIKE ?
            ORDER BY favorite DESC, updated_at DESC
        """, (search, search, search))
    else:
        cursor.execute("""
            SELECT id, website, username, password, note, updated_at, favorite
            FROM passwords
            ORDER BY favorite DESC, updated_at DESC
        """)

    rows = cursor.fetchall()
    conn.close()

    return decrypt_password_rows(rows, crypto)


def get_favorites(crypto=None):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, website, username, password, note, updated_at, favorite
        FROM passwords
        WHERE favorite = 1
        ORDER BY updated_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return decrypt_password_rows(rows, crypto)


def get_encrypted_password_rows():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, website, username, password, note, updated_at, favorite
        FROM passwords
        ORDER BY id
    """)

    rows = cursor.fetchall()
    conn.close()
    return rows


def replace_master_password_and_password_rows(master_password_value, rows):
    conn = connect()
    cursor = conn.cursor()
    normalized_rows = []

    for row in rows:
        if len(row) == 6:
            normalized_rows.append((*row, 0))
        else:
            normalized_rows.append(row)

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        """, ("master_password", master_password_value))

        cursor.execute("DELETE FROM passwords")
        cursor.executemany("""
            INSERT INTO passwords (id, website, username, password, note, updated_at, favorite)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, normalized_rows)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_password(password_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM passwords WHERE id = ?", (password_id,))

    conn.commit()
    conn.close()


def get_password_favorite(password_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT favorite FROM passwords WHERE id = ?", (password_id,))
    result = cursor.fetchone()

    conn.close()

    if result is None:
        return 0

    return int(result[0] or 0)


def toggle_favorite(password_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE passwords
        SET favorite = CASE WHEN COALESCE(favorite, 0) = 1 THEN 0 ELSE 1 END
        WHERE id = ?
    """, (password_id,))

    if cursor.rowcount == 0:
        conn.rollback()
        conn.close()
        return None

    cursor.execute("SELECT favorite FROM passwords WHERE id = ?", (password_id,))
    result = cursor.fetchone()

    conn.commit()
    conn.close()

    return int(result[0] or 0)
