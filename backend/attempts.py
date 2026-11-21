"""Freeze the active question bank and assigned schedule per attempt."""
import json
import secrets
import time
from .database import get_connection
from .exam_accommodations import listening_transcripts
from .exam_packages import start_package_bank
from .exam_schedules import VALID_CONDITIONS, resolve_schedule_for_attempt
from questions.loader import public_bank


def start_attempt(user, payload):
    device = payload.get('device_profile')
    if payload.get('consent_agreed') is not True:
        raise ValueError('Persetujuan diperlukan sebelum memulai sesi.')
    if device not in {'PC_PHYSICAL', 'MOBILE_VIRTUAL'}:
        raise ValueError('Profil perangkat tidak valid.')

    schedule_id = payload.get('schedule_id')
    session_code = payload.get('session_code')
    now = time.time()
    if schedule_id or session_code:
        sched, bank = resolve_schedule_for_attempt(schedule_id, session_code, user['user_id'])
        condition = sched['task_condition']
        sid = sched['schedule_id']
        scode = sched['session_code']
        bank['schedule'] = {
            k: sched[k] for k in ('schedule_id', 'session_code', 'title', 'opens_at', 'closes_at',
                                  'extra_minutes', 'listening_transcript')
        }
        if sched['listening_transcript']:
            bank['listening_transcripts'] = listening_transcripts(bank)
        deadline = now + (bank['package']['duration_minutes'] + sched['extra_minutes']) * 60
        if sched['closes_ts'] is not None:
            deadline = min(deadline, sched['closes_ts'])
        if deadline <= now:
            raise ValueError('Batas waktu (deadline) sesi ujian ini telah berakhir.')
    else:
        condition = payload.get('task_condition') or 'MANDIRI'
        if condition not in VALID_CONDITIONS:
            raise ValueError('Pengaturan sesi tidak valid.')
        bank = start_package_bank(payload.get('package_id'))
        sid, scode = None, None
        deadline = now + bank['package']['duration_minutes'] * 60

    if not bank['listening']['questions'] or not bank['grammar_mc'] or not bank['reading']['questions']:
        raise ValueError('Paket EPT belum lengkap. Pengawas perlu mengaktifkan soal Listening, Structure, dan Reading.')
    if any(not item.get('passage', '').strip() for item in bank['reading']['questions']):
        raise ValueError('Ada soal Reading tanpa bacaan yang jelas. Pengawas perlu memperbaiki bank soal.')

    writing_id = payload.get('writing_id')
    if writing_id:
        selected = next((item for item in bank['writing_tasks'] if item['id'] == writing_id), None)
        if not selected:
            raise ValueError('Tugas Writing tidak tersedia. Muat ulang persiapan sesi.')
        bank['writing'] = selected

    attempt_id = (
        f"{secrets.token_hex(4)}-{secrets.token_hex(2)}-{secrets.token_hex(2)}-"
        f"{secrets.token_hex(2)}-{secrets.token_hex(6)}"
    )
    with get_connection() as conn:
        conn.execute(
            'INSERT INTO exam_attempts (attempt_id, user_id, bank_json, device_profile, '
            'task_condition, expires_at, created_at, schedule_id, session_code) '
            'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (attempt_id, user['user_id'], json.dumps(bank), device, condition, deadline, now, sid, scode),
        )
    return {'attempt_id': attempt_id, 'deadline': round(deadline * 1000),
            'bank': public_bank(bank, condition=condition, transcripts=bank.get('listening_transcripts'))}


def get_attempt(user, attempt_id):
    with get_connection() as conn:
        row = conn.execute('SELECT * FROM exam_attempts WHERE attempt_id = %s AND user_id = %s',
                           (attempt_id, user['user_id'])).fetchone()
    return dict(row) if row else None


def resume_attempt(user, attempt_id):
    row = get_attempt(user, attempt_id)
    if not row:
        raise ValueError('Sesi tidak ditemukan. Mulai sesi baru dari halaman persiapan.')
    bank = json.loads(row['bank_json'])
    transcripts = bank.get('listening_transcripts') if row['expires_at'] > time.time() else None
    if transcripts:
        with get_connection() as conn:
            if conn.execute('SELECT 1 FROM exam_submissions WHERE session_id=%s', ('SES-' + attempt_id,)).fetchone():
                transcripts = None
    return {'attempt_id': attempt_id, 'deadline': round(row['expires_at'] * 1000),
            'bank': public_bank(bank, condition=row['task_condition'], transcripts=transcripts)}
