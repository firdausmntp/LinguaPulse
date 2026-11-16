"""Duration of the currently active exam package."""
from .database import get_connection

DEFAULT_DURATION_MINUTES = 25


def get_exam_settings():
    with get_connection() as conn:
        row = conn.execute("SELECT duration_minutes FROM exam_settings WHERE id = 1").fetchone()
    return {'duration_minutes': row['duration_minutes'] if row else DEFAULT_DURATION_MINUTES}


def save_exam_settings(payload):
    duration = payload.get('duration_minutes')
    if isinstance(duration, bool) or not isinstance(duration, int) or not 1 <= duration <= 240:
        raise ValueError('Durasi harus berupa bilangan bulat 1 sampai 240 menit.')
    with get_connection() as conn:
        conn.execute("""INSERT INTO exam_settings (id, duration_minutes) VALUES (1, %s)
            ON DUPLICATE KEY UPDATE duration_minutes = VALUES(duration_minutes)""", (duration,))
    return {'duration_minutes': duration}
