"""Validated custom-question writes shared by editor and JSON import."""
import json
import re
import time
from urllib.parse import urlparse, unquote
from .database import get_connection
from questions.loader import sync_db_questions_to_disk

VALID_TYPES = {
    ('listening', 'multiple_choice'), ('grammar', 'multiple_choice'),
    ('grammar', 'rewrite'), ('reading', 'multiple_choice'), ('writing', 'essay')
}
FIELDS = ('question_id', 'section', 'question_type', 'title', 'passage', 'prompt',
          'correct_answer', 'explanation', 'sample_ai_reference', 'audio_url')


def text_field(payload, field, maximum=20000):
    value = payload.get(field, '')
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError(f'Kolom {field} harus berupa teks maksimal {maximum} karakter.')
    return value.strip()


def valid_audio_url(value):
    if not value:
        return False
    parsed = urlparse(value)
    if parsed.scheme == 'https' and parsed.netloc and not parsed.username and not parsed.password:
        return True
    decoded = unquote(parsed.path)
    return (not parsed.scheme and not parsed.netloc and decoded.startswith('/media/')
            and '\\' not in decoded and '..' not in decoded.split('/')
            and not parsed.query and not parsed.fragment)


def validate_question(payload):
    if not isinstance(payload, dict):
        raise ValueError('Setiap soal harus berupa objek JSON.')
    payload = dict(payload)
    if isinstance(payload.get('correct_answer'), int) and not isinstance(payload.get('correct_answer'), bool):
        payload['correct_answer'] = str(payload['correct_answer'])
    item = {field: text_field(payload, field) for field in FIELDS}
    item['question_id'] = item['question_id'].upper()
    if not re.fullmatch(r'[A-Z0-9_-]{1,40}', item['question_id']):
        raise ValueError('Kode soal harus 1 hingga 40 karakter: huruf, angka, garis bawah, atau tanda hubung.')
    if (item['section'], item['question_type']) not in VALID_TYPES:
        raise ValueError('Kombinasi modul dan tipe soal tidak valid.')
    if not item['prompt']:
        raise ValueError('Pertanyaan wajib diisi.')
    if len(item['title']) > 160:
        raise ValueError('Topik soal maksimal 160 karakter.')
    options = payload.get('options', [])
    if not isinstance(options, list) or any(not isinstance(x, str) for x in options):
        raise ValueError('Opsi harus berupa daftar teks.')
    item['options'] = [x.strip() for x in options]
    if item['question_type'] == 'multiple_choice':
        answer = str(payload.get('correct_answer', ''))
        if not 2 <= len(options) <= 6 or any(not x or len(x) > 2000 for x in item['options']):
            raise ValueError('Pilihan ganda memerlukan 2 hingga 6 opsi yang terisi.')
        if not answer.isdigit() or int(answer) >= len(options):
            raise ValueError('Pilih satu jawaban benar dari opsi yang tersedia.')
        item['correct_answer'] = answer
    else:
        item['options'] = []
    if item['section'] == 'reading' and not item['passage']:
        raise ValueError('Soal Reading memerlukan wacana bacaan.')
    if item['section'] == 'listening' and not valid_audio_url(item['audio_url']):
        raise ValueError('Soal Listening memerlukan audio lokal /media/ atau URL HTTPS yang valid.')
    if item['audio_url'] and not valid_audio_url(item['audio_url']):
        raise ValueError('Alamat audio tidak valid. Gunakan unggahan lokal atau URL HTTPS.')
    active = payload.get('is_active', 1)
    if active not in (0, 1, False, True):
        raise ValueError('Status aktif harus bernilai 0 atau 1.')
    item['is_active'] = int(active)
    return item


def write_question(conn, item):
    values = [item[field] for field in FIELDS]
    # Keep the original creation time and preserve the historical reward column at zero.
    conn.execute("""INSERT INTO questions
        (question_id, section, question_type, title, passage, prompt, correct_answer,
         explanation, sample_ai_reference, audio_url, options_json, is_active, points_xp, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        ON CONFLICT(question_id) DO UPDATE SET section=excluded.section,
          question_type=excluded.question_type, title=excluded.title, passage=excluded.passage,
          prompt=excluded.prompt, correct_answer=excluded.correct_answer,
          explanation=excluded.explanation, sample_ai_reference=excluded.sample_ai_reference,
          audio_url=excluded.audio_url, options_json=excluded.options_json,
          is_active=excluded.is_active, points_xp=0""",
        (*values, json.dumps(item['options'], ensure_ascii=False), item['is_active'],
         time.strftime('%Y-%m-%d %H:%M:%S')))


def get_question_detail(question_id):
    qid = str(question_id or '').strip().upper()
    if not re.fullmatch(r'[A-Z0-9_-]{1,40}', qid):
        raise ValueError('Kode soal tidak valid.')
    with get_connection() as conn:
        row = conn.execute('SELECT * FROM questions WHERE question_id = ?', (qid,)).fetchone()
    if not row:
        raise ValueError('Soal tidak ditemukan. Muat ulang bank soal.')
    item = {field: row[field] or '' for field in FIELDS}
    item['options'] = json.loads(row['options_json'] or '[]')
    item['is_active'] = int(row['is_active'])
    return {'question': item}


def save_question(payload):
    if isinstance(payload, dict) and payload.get('mode') == 'toggle':
        qid = text_field(payload, 'question_id', 40).upper()
        active = payload.get('is_active', 1)
        if not re.fullmatch(r'[A-Z0-9_-]{1,40}', qid) or active not in (0, 1, False, True):
            raise ValueError('Status aktif soal tidak valid.')
        with get_connection() as conn:
            cursor = conn.execute('UPDATE questions SET is_active = ? WHERE question_id = ?', (int(active), qid))
            if not cursor.rowcount:
                raise ValueError('Soal tidak ditemukan. Muat ulang bank soal.')
        sync_db_questions_to_disk()
        return {'status': 'ok', 'question_id': qid, 'is_active': int(active)}
    item = validate_question(payload)
    mode = payload.get('mode', 'create')
    original = str(payload.get('original_id', '')).strip().upper()
    if mode not in {'create', 'update'}:
        raise ValueError('Mode penyimpanan soal tidak valid.')
    with get_connection() as conn:
        exists = conn.execute('SELECT 1 FROM questions WHERE question_id = ?', (item['question_id'],)).fetchone()
        if mode == 'create' and exists:
            raise ValueError('Kode soal sudah digunakan. Pilih kode baru atau buka soal untuk diedit.')
        if mode == 'update':
            if not original or original != item['question_id'] or not exists:
                raise ValueError('Soal yang diedit tidak ditemukan. Muat ulang bank soal; kode soal tidak dapat diganti saat mengedit.')
        write_question(conn, item)
    sync_db_questions_to_disk()
    return {'status': 'ok', 'question_id': item['question_id']}


def import_questions(payload):
    items = payload.get('questions') if isinstance(payload, dict) else None
    if not isinstance(items, list) or not 1 <= len(items) <= 200:
        raise ValueError('Impor memerlukan 1 hingga 200 soal dalam properti questions.')
    validated = []
    seen = set()
    for number, value in enumerate(items, 1):
        try:
            item = validate_question(value)
        except ValueError as error:
            raise ValueError(f'Soal ke-{number}: {error}') from error
        if item['question_id'] in seen:
            raise ValueError(f'Kode {item["question_id"]} muncul lebih dari sekali dalam berkas impor.')
        seen.add(item['question_id'])
        validated.append(item)
    with get_connection() as conn:
        for item in validated:
            write_question(conn, item)
    sync_db_questions_to_disk()
    return {'status': 'ok', 'imported': len(validated)}


def export_questions():
    with get_connection() as conn:
        rows = conn.execute('SELECT * FROM questions ORDER BY section, question_id').fetchall()
    output = []
    for row in rows:
        item = {field: row[field] or '' for field in FIELDS}
        item['options'] = json.loads(row['options_json'] or '[]')
        item['is_active'] = row['is_active']
        output.append(item)
    return {'format': 'linguapulse-ept-questions-v1', 'questions': output}


def delete_question(question_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', question_id):
        raise ValueError('Kode soal tidak valid.')
    with get_connection() as conn:
        cursor = conn.execute('DELETE FROM questions WHERE question_id = ?', (question_id,))
        if not cursor.rowcount:
            raise ValueError('Soal sudah tidak tersedia. Muat ulang bank soal.')
    sync_db_questions_to_disk()
    return {'status': 'deleted', 'question_id': question_id}
