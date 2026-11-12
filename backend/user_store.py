"""Admin account CRUD; historical submissions stay intact after account removal."""
import re
import secrets
import sqlite3
import time
from .auth import hash_password, format_user_row
from .database import get_connection


def save_user(payload, actor):
    fields = {}
    for key in ('display_name', 'username', 'email', 'password', 'role'):
        value = payload.get(key, '')
        if not isinstance(value, str):
            raise ValueError('Kolom akun harus berupa teks.')
        fields[key] = value if key == 'password' else value.strip()
    fields['username'] = fields['username'].lower()
    fields['email'] = fields['email'].lower()
    if not 2 <= len(fields['display_name']) <= 80:
        raise ValueError('Nama lengkap harus 2 hingga 80 karakter.')
    if not re.fullmatch(r'[a-z0-9_]{3,30}', fields['username']):
        raise ValueError('Username harus 3 hingga 30 karakter: huruf, angka, atau garis bawah.')
    if len(fields['email']) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', fields['email']):
        raise ValueError('Alamat email tidak valid.')
    if fields['role'] not in {'admin', 'student'}:
        raise ValueError('Pilih peran admin atau peserta.')
    mode = payload.get('mode')
    if mode not in {'create', 'update'}:
        raise ValueError('Mode perubahan tidak valid.')
    user_id = payload.get('user_id')
    if mode == 'update' and (not isinstance(user_id, int) or isinstance(user_id, bool)):
        raise ValueError('Identitas akun tidak valid.')
    password = fields['password']
    if (mode == 'create' or password) and not 8 <= len(password) <= 128:
        raise ValueError('Kata sandi harus 8 hingga 128 karakter.')
    with get_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        old = None
        if mode == 'update':
            old = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
            if not old:
                raise ValueError('Akun tidak ditemukan. Muat ulang daftar akun.')
            if user_id == actor['user_id'] and fields['role'] != 'admin':
                raise ValueError('Peran akun admin yang sedang digunakan tidak dapat diturunkan.')
            if old['role'] == 'admin' and fields['role'] != 'admin' and conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0] <= 1:
                raise ValueError('Minimal satu akun admin harus tersedia.')
        try:
            values = (fields['display_name'], fields['username'], fields['email'], fields['role'])
            if mode == 'create':
                cursor = conn.execute("""INSERT INTO users
                    (display_name,username,email,role,password_hash,participant_code,xp,streak,badges_json,consent_agreed,created_at)
                    VALUES (?,?,?,?,?,?,0,0,'[]',0,?)""", (*values, hash_password(password),
                        'RESP-' + secrets.token_hex(5).upper(), time.strftime('%Y-%m-%d %H:%M:%S')))
                user_id = cursor.lastrowid
            else:
                conn.execute('UPDATE users SET display_name=?,username=?,email=?,role=? WHERE user_id=?', (*values, user_id))
                if password:
                    conn.execute('UPDATE users SET password_hash=? WHERE user_id=?', (hash_password(password), user_id))
                # Changed credentials and permissions take effect on every existing login.
                if password or old['role'] != fields['role']:
                    conn.execute('DELETE FROM auth_sessions WHERE user_id=?', (user_id,))
        except sqlite3.IntegrityError as error:
            raise ValueError('Username atau email sudah digunakan akun lain.') from error
        user = format_user_row(conn.execute('SELECT * FROM users WHERE user_id=?', (user_id,)).fetchone())
    return {'user': user, 'reauthenticate': bool(mode == 'update' and password and user_id == actor['user_id'])}


def delete_user(user_id, actor):
    if user_id == actor['user_id']:
        raise ValueError('Akun yang sedang Anda gunakan tidak dapat dihapus.')
    with get_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        user = conn.execute('SELECT * FROM users WHERE user_id=?', (user_id,)).fetchone()
        if not user:
            raise ValueError('Akun sudah tidak tersedia.')
        if user['role'] == 'admin' and conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0] <= 1:
            raise ValueError('Akun admin terakhir tidak dapat dihapus.')
        conn.execute('DELETE FROM auth_sessions WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM exam_attempts WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM users WHERE user_id=?', (user_id,))
    return {'status': 'deleted'}
