"""Read models for the administrator overview and untimed practice."""
import json
import random
import time
from .database import get_connection


def admin_overview():
    with get_connection() as conn:
        students = conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
        users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        modules = [dict(row) for row in conn.execute("""SELECT section, COUNT(*) AS total,
            SUM(is_active) AS active,
            SUM(CASE WHEN is_active = 1 AND question_type = 'multiple_choice' THEN 1 ELSE 0 END) AS active_mc
            FROM questions GROUP BY section""")]
        completed = conn.execute('SELECT COUNT(*) FROM exam_submissions').fetchone()[0]
        ongoing = conn.execute("""SELECT COUNT(*) FROM exam_attempts a WHERE expires_at > ?
            AND NOT EXISTS (SELECT 1 FROM exam_submissions s WHERE s.session_id = 'SES-' || a.attempt_id)""",
            (time.time(),)).fetchone()[0]
        sessions = [dict(row) for row in conn.execute("""SELECT session_id, display_name,
            participant_code, submitted_at FROM exam_submissions ORDER BY submitted_at DESC, rowid DESC LIMIT 5""")]
    return {'students': students, 'users': users, 'modules': modules,
            'completed': completed, 'ongoing': ongoing, 'recent': sessions}


def practice_question(section, excluded):
    if section not in {'listening', 'grammar', 'reading'}:
        raise ValueError('Modul latihan tidak tersedia.')
    with get_connection() as conn:
        rows = conn.execute("""SELECT question_id, title, prompt, passage, audio_url,
            correct_answer FROM questions WHERE section=?
            AND question_type='multiple_choice' AND is_active=1""", (section,)).fetchall()
        opt_rows = conn.execute("""SELECT q.question_id, o.option_text 
            FROM question_options o JOIN questions q ON q.question_id = o.question_id
            WHERE q.section=? AND q.question_type='multiple_choice' AND q.is_active=1
            ORDER BY o.question_id, o.option_index""", (section,)).fetchall()
    opts_by_qid = {}
    for r in opt_rows:
        opts_by_qid.setdefault(r['question_id'], []).append(r['option_text'])
    valid = []
    for row in rows:
        options = opts_by_qid.get(row['question_id'], [])
        answer = str(row['correct_answer'])
        passage = (row['passage'] or '') if section == 'reading' else ''
        if section == 'reading' and not passage.strip():
            # Legacy rows share a passage by title; never attach an unrelated text.
            shared = {item['passage'] for item in rows if item['title'] == row['title'] and (item['passage'] or '').strip()}
            passage = shared.pop() if len(shared) == 1 else ''
        if section == 'reading' and not passage.strip():
            continue
        if section == 'listening' and not row['audio_url']:
            continue
        if isinstance(options, list) and len(options) >= 2 and answer.isdigit() and 0 <= int(answer) < len(options):
            valid.append({
                'question_id': row['question_id'],
                'title': row['title'] or '',
                'prompt': row['prompt'] or '',
                'passage': passage,
                'audio_url': (row['audio_url'] or '') if section == 'listening' else '',
                'options': options,
            })
    candidates = [row for row in valid if row['question_id'] != excluded] or valid
    if not candidates:
        return {'question': None, 'total': 0}
    item = dict(random.choice(candidates))
    item['id'] = item.pop('question_id')
    return {'question': item, 'total': len(valid)}


def check_practice_answer(payload):
    qid = str(payload.get('id') or '').strip().lower()
    choice = payload.get('choice')
    if not qid or not isinstance(choice, int) or isinstance(choice, bool) or choice < 0:
        raise ValueError('Pilihan jawaban tidak valid.')
    with get_connection() as conn:
        row = conn.execute("""SELECT question_id, correct_answer, explanation
            FROM questions WHERE question_id=? AND question_type='multiple_choice' AND is_active=1""", (qid,)).fetchone()
        if not row:
            raise ValueError('Soal latihan tidak ditemukan.')
        opt_rows = conn.execute("SELECT option_text FROM question_options WHERE question_id=? ORDER BY option_index", (qid,)).fetchall()
        options = [r['option_text'] for r in opt_rows]
    answer = str(row['correct_answer'])
    if not answer.isdigit() or not 0 <= int(answer) < len(options) or choice >= len(options):
        raise ValueError('Pilihan jawaban tidak valid.')
    correct_idx = int(answer)
    return {
        'id': row['question_id'],
        'correct': choice == correct_idx,
        'answer': correct_idx,
        'explanation': row['explanation'] or '',
    }


def sample_question(excluded=''):
    with get_connection() as conn:
        rows = conn.execute("""SELECT question_id, title, prompt, correct_answer
            FROM questions WHERE section = 'grammar' AND question_type = 'multiple_choice'
            AND is_active = 1""").fetchall()
        opt_rows = conn.execute("""SELECT q.question_id, o.option_text 
            FROM question_options o JOIN questions q ON q.question_id = o.question_id
            WHERE q.section='grammar' AND q.question_type='multiple_choice' AND q.is_active=1
            ORDER BY o.question_id, o.option_index""").fetchall()
    opts_by_qid = {}
    for r in opt_rows:
        opts_by_qid.setdefault(r['question_id'], []).append(r['option_text'])
    valid = []
    for row in rows:
        options = opts_by_qid.get(row['question_id'], [])
        answer = str(row['correct_answer'])
        if isinstance(options, list) and len(options) >= 2 and answer.isdigit() and 0 <= int(answer) < len(options):
            valid.append({'id': row['question_id'], 'title': row['title'] or '', 'prompt': row['prompt'] or '', 'options': options})
    candidates = [row for row in valid if row['id'] != excluded] or valid
    return {'question': random.choice(candidates) if candidates else None}


def check_sample_answer(payload):
    qid = str(payload.get('id') or '').strip().lower()
    choice = payload.get('choice')
    if not qid or not isinstance(choice, int) or isinstance(choice, bool) or choice < 0:
        raise ValueError('Pilihan jawaban tidak valid.')
    with get_connection() as conn:
        row = conn.execute("""SELECT question_id, correct_answer, explanation
            FROM questions WHERE question_id=? AND section='grammar'
            AND question_type='multiple_choice' AND is_active=1""", (qid,)).fetchone()
        if not row:
            raise ValueError('Contoh soal tidak ditemukan.')
        opt_rows = conn.execute("SELECT option_text FROM question_options WHERE question_id=? ORDER BY option_index", (qid,)).fetchall()
        options = [r['option_text'] for r in opt_rows]
    answer = str(row['correct_answer'])
    if not answer.isdigit() or not 0 <= int(answer) < len(options) or choice >= len(options):
        raise ValueError('Pilihan jawaban tidak valid.')
    correct = choice == int(answer)
    return {
        'id': row['question_id'],
        'correct': correct,
        'explanation': (row['explanation'] or '') if correct else '',
    }
