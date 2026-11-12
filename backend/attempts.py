"""Freeze the active question bank per attempt so author edits cannot alter grading."""
import json
import secrets
import time
from .database import get_connection
from questions.loader import get_structured_questions, public_bank


def start_attempt(user, payload):
    device = payload.get('device_profile')
    condition = payload.get('task_condition')
    if payload.get('consent_agreed') is not True:
        raise ValueError('Persetujuan diperlukan sebelum memulai sesi.')
    if device not in {'PC_PHYSICAL', 'MOBILE_VIRTUAL'} or condition not in {'MANDIRI', 'COPY_TYPING', 'AI_PARAPHRASE'}:
        raise ValueError('Pengaturan sesi tidak valid.')
    bank = get_structured_questions()
    if not bank['listening']['questions'] or not bank['grammar_mc'] or not bank['reading']['questions']:
        raise ValueError('Paket EPT belum lengkap. Pengawas perlu mengaktifkan soal Listening, Structure, dan Reading.')
    writing_id = payload.get('writing_id')
    if writing_id:
        selected = next((item for item in bank['writing_tasks'] if item['id'] == writing_id), None)
        if not selected:
            raise ValueError('Tugas Writing tidak tersedia. Muat ulang persiapan sesi.')
        bank['writing'] = selected
    attempt_id = secrets.token_hex(4) + '-' + secrets.token_hex(2) + '-' + secrets.token_hex(2) + '-' + secrets.token_hex(2) + '-' + secrets.token_hex(6)
    now = time.time()
    deadline = now + 25 * 60
    with get_connection() as conn:
        conn.execute('INSERT INTO exam_attempts VALUES (?,?,?,?,?,?,?)',
                     (attempt_id, user['user_id'], json.dumps(bank), device, condition, deadline, now))
    return {'attempt_id': attempt_id, 'deadline': round(deadline * 1000), 'bank': public_bank(bank, condition=condition)}


def get_attempt(user, attempt_id):
    with get_connection() as conn:
        row = conn.execute('SELECT * FROM exam_attempts WHERE attempt_id = ? AND user_id = ?',
                           (attempt_id, user['user_id'])).fetchone()
    return dict(row) if row else None


def resume_attempt(user, attempt_id):
    row = get_attempt(user, attempt_id)
    if not row:
        raise ValueError('Sesi tidak ditemukan. Mulai sesi baru dari halaman persiapan.')
    return {'attempt_id': attempt_id, 'deadline': round(row['expires_at'] * 1000),
            'bank': public_bank(json.loads(row['bank_json']), condition=row['task_condition'])}
