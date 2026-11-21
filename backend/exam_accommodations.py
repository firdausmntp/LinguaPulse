"""Per-participant accommodations for scheduled exams."""
from .database import get_connection
from .exam_packages import _read as read_package


ACCOMMODATION_TABLES = {'exam_time_accommodations': """
    schedule_id VARCHAR(40) NOT NULL, user_id BIGINT NOT NULL,
    extra_minutes INT NOT NULL CHECK (extra_minutes BETWEEN 1 AND 240),
    PRIMARY KEY (schedule_id, user_id),
    FOREIGN KEY (schedule_id) REFERENCES exam_schedules(schedule_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
""",
    'exam_listening_accommodations': """
        schedule_id VARCHAR(40) NOT NULL, user_id BIGINT NOT NULL,
        PRIMARY KEY (schedule_id, user_id),
        FOREIGN KEY (schedule_id) REFERENCES exam_schedules(schedule_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    """,
}


def listening_transcripts(bank):
    """Return one equivalent transcript per recording, including shared recordings."""
    questions = bank['listening']['questions']
    if not questions or any(not q.get('audio_url') for q in questions):
        raise ValueError('Lengkapi rekaman Listening pada paket sebelum memberi akses transkrip.')
    recordings = {}
    for question in questions:
        choices = recordings.setdefault(question['audio_url'], set())
        transcript = (question.get('passage') or '').strip()
        if transcript:
            choices.add(transcript)
    if any(len(choices) != 1 for choices in recordings.values()):
        raise ValueError('Isi satu transkrip yang konsisten untuk setiap rekaman Listening pada paket.')
    return {audio: next(iter(choices)) for audio, choices in recordings.items()}


def list_time_accommodations(schedule_id):
    with get_connection() as conn:
        rows = conn.execute('''SELECT u.username, COALESCE(t.extra_minutes,0) AS extra_minutes,
            a.user_id IS NOT NULL AS listening_transcript
            FROM users u LEFT JOIN exam_time_accommodations t ON t.user_id=u.user_id AND t.schedule_id=%s
            LEFT JOIN exam_listening_accommodations a ON a.user_id=u.user_id AND a.schedule_id=%s
            WHERE u.role='student' AND (t.user_id IS NOT NULL OR a.user_id IS NOT NULL) ORDER BY u.username''',
                            (schedule_id, schedule_id)).fetchall()
    return {'accommodations': [
        {**row, 'listening_transcript': bool(row['listening_transcript'])} for row in rows
    ]}


def save_time_accommodation(payload):
    schedule_id = payload.get('schedule_id')
    username = payload.get('username')
    minutes = payload.get('extra_minutes')
    transcript = payload.get('listening_transcript')
    if not isinstance(schedule_id, str) or not 1 <= len(schedule_id) <= 40:
        raise ValueError('Pilih sesi jadwal yang sudah disimpan.')
    if not isinstance(username, str) or not 1 <= len(username.strip()) <= 64:
        raise ValueError('Masukkan username peserta yang terdaftar.')
    if type(minutes) is not int or not 0 <= minutes <= 240:
        raise ValueError('Masukkan tambahan waktu 0 sampai 240 menit.')
    if 'listening_transcript' in payload and not isinstance(transcript, bool):
        raise ValueError('Pilih apakah peserta boleh membuka transkrip Listening.')
    with get_connection() as conn:
        schedule = conn.execute('SELECT package_id FROM exam_schedules WHERE schedule_id=%s FOR UPDATE',
                                (schedule_id,)).fetchone()
        if not schedule:
            raise ValueError('Sesi jadwal tidak ditemukan. Muat ulang daftar jadwal.')
        user = conn.execute("SELECT user_id FROM users WHERE username=%s AND role='student' FOR UPDATE",
                            (username.strip().lower(),)).fetchone()
        if not user:
            raise ValueError('Username peserta tidak ditemukan. Periksa username di menu Akun pengguna.')
        if transcript:
            _, bank = read_package(conn, schedule['package_id'], admin=True)
            listening_transcripts(bank)
            conn.execute('''INSERT INTO exam_listening_accommodations (schedule_id,user_id)
                VALUES (%s,%s) ON DUPLICATE KEY UPDATE user_id=VALUES(user_id)''',
                         (schedule_id, user['user_id']))
        elif transcript is False:
            conn.execute('DELETE FROM exam_listening_accommodations WHERE schedule_id=%s AND user_id=%s',
                         (schedule_id, user['user_id']))
        if minutes:
            conn.execute('''INSERT INTO exam_time_accommodations (schedule_id,user_id,extra_minutes)
                VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE extra_minutes=%s''',
                         (schedule_id, user['user_id'], minutes, minutes))
        else:
            conn.execute('DELETE FROM exam_time_accommodations WHERE schedule_id=%s AND user_id=%s',
                         (schedule_id, user['user_id']))
    return list_time_accommodations(schedule_id)


def accommodation_for(conn, schedule_id, user_id):
    row = conn.execute('''SELECT COALESCE(t.extra_minutes,0) AS extra_minutes,
        a.user_id IS NOT NULL AS listening_transcript
        FROM users u LEFT JOIN exam_time_accommodations t ON t.user_id=u.user_id AND t.schedule_id=%s
        LEFT JOIN exam_listening_accommodations a ON a.user_id=u.user_id AND a.schedule_id=%s
        WHERE u.user_id=%s''', (schedule_id, schedule_id, user_id)).fetchone()
    return {'extra_minutes': row['extra_minutes'] if row else 0,
            'listening_transcript': bool(row and row['listening_transcript'])}
