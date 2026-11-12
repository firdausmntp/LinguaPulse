"""Account validation and password storage, with legacy password migration."""
import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from .database import get_connection


def hash_password(raw):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', raw.encode(), salt.encode(), 260000).hex()
    return f'pbkdf2_sha256${salt}${digest}'


def verify_password(raw, stored):
    if stored.startswith('pbkdf2_sha256$'):
        _, salt, expected = stored.split('$')
        actual = hashlib.pbkdf2_hmac('sha256', raw.encode(), salt.encode(), 260000).hex()
    else:
        expected = stored
        actual = hashlib.sha256(raw.encode()).hexdigest()
    return hmac.compare_digest(actual, expected)


def format_user_row(row):
    return {key: row[key] for key in (
        'user_id', 'participant_code', 'username', 'email', 'display_name',
        'role', 'consent_agreed', 'created_at'
    )}


def register_user(username, email, password, display_name, role='student'):
    if not all(isinstance(value, str) for value in (username, email, password, display_name)):
        return {'error': 'Kolom pendaftaran harus berupa teks.'}
    username = username.strip().lower()
    email = email.strip().lower()
    display_name = display_name.strip()
    if not re.fullmatch(r'[a-z0-9_]{3,30}', username):
        return {'error': 'Username harus 3–30 karakter: huruf, angka, atau garis bawah.'}
    if len(email) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        return {'error': 'Masukkan alamat email yang valid.'}
    if not 8 <= len(password) <= 128:
        return {'error': 'Kata sandi harus 8–128 karakter.'}
    if not 2 <= len(display_name) <= 80:
        return {'error': 'Nama lengkap harus 2–80 karakter.'}
    with get_connection() as conn:
        try:
            conn.execute('''INSERT INTO users
                (participant_code, username, email, password_hash, display_name, role,
                 xp, streak, badges_json, consent_agreed, created_at)
                VALUES (?, ?, ?, ?, ?, 'student', 0, 0, '[]', 0, ?)''', (
                    'RESP-' + secrets.token_hex(5).upper(), username, email,
                    hash_password(password), display_name, time.strftime('%Y-%m-%d %H:%M:%S')
                ))
        except sqlite3.IntegrityError:
            return {'error': 'Username atau email sudah terdaftar.'}
        row = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    return {'status': 'ok', 'user': format_user_row(row)}


def login_user(identifier, password):
    if not isinstance(identifier, str) or not isinstance(password, str):
        return {'error': 'Username/email dan kata sandi harus berupa teks.'}
    with get_connection() as conn:
        ident = identifier.strip().lower()
        row = conn.execute('SELECT * FROM users WHERE username = ? OR email = ?', (ident, ident)).fetchone()
        if not row or not verify_password(password, row['password_hash']):
            return {'error': 'Username/email atau kata sandi salah.'}
        if not row['password_hash'].startswith('pbkdf2_sha256$'):
            conn.execute('UPDATE users SET password_hash = ? WHERE user_id = ?',
                         (hash_password(password), row['user_id']))
    return {'status': 'ok', 'user': format_user_row(row)}
