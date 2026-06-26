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
            UNIQUE(website, username)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


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


def create_crypto(master_password):
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


def add_or_update_password(website, username, password, note, updated_at, crypto):
    encrypted_password = encrypt_password(crypto, password)

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
    """, (website, username, encrypted_password, note, updated_at))

    conn.commit()
    conn.close()


def get_passwords(search_text="", crypto=None):
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

    decrypted_rows = []

    for row in rows:
        password_id, website, username, encrypted_password, note, updated_at = row

        if crypto is None:
            password = "[locked]"
        else:
            password = decrypt_password(crypto, encrypted_password)

        decrypted_rows.append(
            (password_id, website, username, password, note, updated_at)
        )

    return decrypted_rows


def delete_password(password_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM passwords WHERE id = ?", (password_id,))

    conn.commit()
    conn.close()