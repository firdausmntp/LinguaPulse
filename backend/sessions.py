"""Server-validated sessions; account identity never comes from browser storage."""
import hashlib
import secrets
import time
from http.cookies import SimpleCookie
from .database import get_connection
from .auth import format_user_row

COOKIE_NAME = 'linguapulse_session'
SESSION_AGE = 60 * 60 * 24 * 7


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def read_token(request):
    cookie = SimpleCookie()
    try:
        cookie.load(request.headers.get('Cookie', ''))
        return cookie[COOKIE_NAME].value if COOKIE_NAME in cookie else ''
    except Exception:
        return ''


def session_user(request):
    token = read_token(request)
    if not token:
        return None
    with get_connection() as conn:
        row = conn.execute('''SELECT users.* FROM auth_sessions
            JOIN users ON users.user_id = auth_sessions.user_id
            WHERE token_hash = ? AND expires_at > ?''', (token_hash(token), time.time())).fetchone()
    return format_user_row(row) if row else None


def create_session(request, user):
    token = secrets.token_urlsafe(32)
    with get_connection() as conn:
        conn.execute('DELETE FROM auth_sessions WHERE expires_at < ? OR token_hash = ?',
                     (time.time(), token_hash(read_token(request))))
        conn.execute('INSERT INTO auth_sessions VALUES (?, ?, ?)',
                     (token_hash(token), user['user_id'], time.time() + SESSION_AGE))
    return f'{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_AGE}'


def logout_session(request):
    with get_connection() as conn:
        conn.execute('DELETE FROM auth_sessions WHERE token_hash = ?', (token_hash(read_token(request)),))
    return f'{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0'
