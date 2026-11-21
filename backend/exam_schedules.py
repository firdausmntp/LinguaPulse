"""Scheduled exam cohorts/classes with open-close deadlines and 3-tier triage."""
from datetime import datetime, timezone
import re
import secrets
import time
from .database import get_connection
from .exam_packages import _read as read_package, start_package_bank
from .package_schema import DEFAULT_PACKAGE_ID
from .exam_accommodations import accommodation_for

DEFAULT_SCHEDULE_ID = 'SCH-EXPERIMENTAL'
DEFAULT_SESSION_CODE = 'EPT-TERBUKA'
DEFAULT_SCHEDULE_TITLE = 'Simulasi TOEFL EPT Terbuka'
VALID_CONDITIONS = {'MANDIRI', 'COPY_TYPING', 'AI_PARAPHRASE'}
SCHEDULE_TABLES = {
    'exam_schedules': """
        schedule_id VARCHAR(40) NOT NULL PRIMARY KEY,
        session_code VARCHAR(32) NOT NULL UNIQUE,
        title VARCHAR(120) NOT NULL, description TEXT NOT NULL,
        package_id VARCHAR(40) NOT NULL,
        task_condition VARCHAR(32) NOT NULL DEFAULT 'MANDIRI',
        opens_at VARCHAR(32) NULL DEFAULT NULL,
        closes_at VARCHAR(32) NULL DEFAULT NULL,
        is_active TINYINT NOT NULL DEFAULT 1, version INT NOT NULL DEFAULT 1,
        created_at VARCHAR(32) NOT NULL, updated_at VARCHAR(32) NOT NULL,
        INDEX idx_schedules_active (is_active, closes_at),
        FOREIGN KEY (package_id) REFERENCES exam_packages(package_id) ON DELETE CASCADE
    """,
}


def _parse_iso_dt(value):
    if value is None:
        return None, None
    if not isinstance(value, str):
        raise ValueError('Format tanggal/waktu jadwal tidak valid.')
    raw = value.strip()
    if not raw:
        return None, None
    try:
        dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('Gunakan format tanggal ISO (YYYY-MM-DDTHH:MM).') from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return dt.isoformat(timespec='minutes'), dt.timestamp()


def window_state(row, now=None):
    if not row.get('is_active'):
        return 'inactive'
    cur = time.time() if now is None else now
    _, opens_ts = _parse_iso_dt(row.get('opens_at'))
    _, closes_ts = _parse_iso_dt(row.get('closes_at'))
    if opens_ts is not None and cur < opens_ts:
        return 'upcoming'
    if closes_ts is not None and cur >= closes_ts:
        return 'closed'
    return 'open'


def classify_triage_status(xgboost_score, rule_flag):
    score = float(xgboost_score or 0.0)
    flagged = int(rule_flag or 0) == 1
    if score >= 0.70 or (score >= 0.60 and flagged):
        return 'TERDETEKSI'
    if score >= 0.40 or flagged:
        return 'FLAG'
    return 'TIDAK_TERDETEKSI'


def initialize_schedules(conn):
    for tbl in ('exam_attempts', 'telemetry_sessions'):
        cols = {r['Field'] for r in conn.execute(f'SHOW COLUMNS FROM `{tbl}`').fetchall()}
        if 'schedule_id' not in cols:
            conn.execute(f'ALTER TABLE `{tbl}` ADD COLUMN schedule_id VARCHAR(40) NULL DEFAULT NULL')
        if 'session_code' not in cols:
            conn.execute(f'ALTER TABLE `{tbl}` ADD COLUMN session_code VARCHAR(32) NULL DEFAULT NULL')
    marker = 'exam_schedules_v1'
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=%s', (marker,)).fetchone():
        return
    pkg = conn.execute('SELECT is_active FROM exam_packages WHERE package_id=%s', (DEFAULT_PACKAGE_ID,)).fetchone()
    if pkg:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            'INSERT INTO exam_schedules VALUES (%s,%s,%s,%s,%s,%s,NULL,NULL,%s,1,%s,%s)',
            (DEFAULT_SCHEDULE_ID, DEFAULT_SESSION_CODE, DEFAULT_SCHEDULE_TITLE,
             'Sesi jadwal terbuka untuk latihan dan uji fungsi platform.',
             DEFAULT_PACKAGE_ID, 'MANDIRI', int(bool(pkg['is_active'])), now, now),
        )
    conn.execute('INSERT INTO schema_migrations (version) VALUES (%s)', (marker,))


def _hydrate_schedule(conn, row, admin=False):
    pkg, _ = read_package(conn, row['package_id'], admin=True)
    state = window_state(row)
    joinable = state == 'open' and pkg['is_active'] and pkg['ready']
    item = {
        'schedule_id': row['schedule_id'], 'session_code': row['session_code'],
        'title': row['title'], 'description': row['description'],
        'package_id': row['package_id'], 'package_name': pkg['name'],
        'duration_minutes': pkg['duration_minutes'], 'question_count': pkg['question_count'],
        'package_ready': bool(pkg['is_active'] and pkg['ready']),
        'opens_at': row['opens_at'], 'closes_at': row['closes_at'],
        'window_state': state, 'joinable': joinable,
    }
    if admin:
        item.update(is_active=bool(row['is_active']), task_condition=row['task_condition'],
                    version=row['version'], created_at=row['created_at'], updated_at=row['updated_at'])
    return item


def list_schedules(admin=False, user_id=None):
    with get_connection() as conn:
        sql = ('SELECT s.* FROM exam_schedules s JOIN exam_packages p ON p.package_id=s.package_id '
               + ('' if admin else 'WHERE s.is_active=1 AND p.is_active=1 ')
               + 'ORDER BY s.created_at DESC, s.schedule_id')
        rows = conn.execute(sql).fetchall()
        items = [_hydrate_schedule(conn, row, admin=admin) for row in rows]
        if user_id is not None:
            for item in items:
                item.update(accommodation_for(conn, item['schedule_id'], user_id))
        return {'schedules': items}


def resolve_schedule_for_attempt(schedule_id=None, session_code=None, user_id=None):
    sid = str(schedule_id or '').strip()
    code = str(session_code or '').strip().upper()
    if not sid and not code:
        raise ValueError('Pilih sesi jadwal atau masukkan kode sesi.')
    with get_connection() as conn:
        if code:
            row = conn.execute('SELECT * FROM exam_schedules WHERE session_code=%s', (code,)).fetchone()
        else:
            row = conn.execute('SELECT * FROM exam_schedules WHERE schedule_id=%s', (sid,)).fetchone()
        if not row or not row['is_active']:
            raise ValueError('Kode atau sesi jadwal tidak ditemukan atau sedang nonaktif.')
        if sid and row['schedule_id'] != sid:
            raise ValueError('Kode dan jadwal berbeda. Pilih kembali sesi jadwal.')
        state = window_state(row)
        if state == 'upcoming':
            raise ValueError('Sesi ujian belum dibuka sesuai jadwal pengawas.')
        if state == 'closed':
            raise ValueError('Batas waktu (deadline) sesi ujian ini telah berakhir.')
        _, closes_ts = _parse_iso_dt(row['closes_at'])
        info = {
            'schedule_id': row['schedule_id'], 'session_code': row['session_code'],
            'title': row['title'], 'package_id': row['package_id'],
            'task_condition': row['task_condition'], 'opens_at': row['opens_at'],
            'closes_at': row['closes_at'], 'closes_ts': closes_ts,
            **accommodation_for(conn, row['schedule_id'], user_id),
        }
    bank = start_package_bank(info['package_id'])
    return info, bank


def save_schedule(payload):
    title = payload.get('title')
    desc = payload.get('description', '')
    code = payload.get('session_code')
    pkg_id = payload.get('package_id')
    cond = payload.get('task_condition', 'MANDIRI')
    active = payload.get('is_active', True)
    sid = payload.get('schedule_id')
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
        raise ValueError('Judul sesi jadwal harus 1 sampai 120 karakter.')
    if not isinstance(desc, str) or len(desc) > 2000:
        raise ValueError('Deskripsi maksimal 2.000 karakter.')
    if not isinstance(code, str) or not re.fullmatch(r'[A-Z0-9_-]{3,32}', code.strip().upper()):
        raise ValueError('Kode sesi harus 3 sampai 32 karakter huruf, angka, tanda hubung, atau garis bawah.')
    code = code.strip().upper()
    if not isinstance(pkg_id, str) or not 1 <= len(pkg_id.strip()) <= 40:
        raise ValueError('Pilih paket ujian untuk sesi jadwal ini.')
    if cond not in VALID_CONDITIONS:
        raise ValueError('Kondisi penugasan sesi tidak valid.')
    if not isinstance(active, bool):
        raise ValueError('Status aktif sesi jadwal tidak valid.')
    opens_iso, opens_ts = _parse_iso_dt(payload.get('opens_at'))
    closes_iso, closes_ts = _parse_iso_dt(payload.get('closes_at'))
    if opens_ts is not None and closes_ts is not None and closes_ts <= opens_ts:
        raise ValueError('Waktu tutup (deadline) harus lebih lambat dari waktu buka.')
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        pkg_row = conn.execute('SELECT package_id FROM exam_packages WHERE package_id=%s', (pkg_id.strip(),)).fetchone()
        if not pkg_row:
            raise ValueError('Paket ujian yang dirujuk tidak ditemukan.')
        dup = conn.execute('SELECT schedule_id FROM exam_schedules WHERE session_code=%s', (code,)).fetchone()
        if dup and dup['schedule_id'] != sid:
            raise ValueError('Kode sesi sudah digunakan oleh jadwal lain.')
        prev = conn.execute('SELECT * FROM exam_schedules WHERE schedule_id=%s FOR UPDATE', (sid,)).fetchone() if sid else None
        if sid and not prev:
            raise ValueError('Sesi jadwal tidak ditemukan.')
        ver = payload.get('version')
        if prev and (isinstance(ver, bool) or not isinstance(ver, int) or ver != prev['version']):
            raise ValueError('Jadwal telah diubah. Muat ulang sebelum menyimpan kembali.')
        if prev:
            conn.execute(
                'UPDATE exam_schedules SET session_code=%s, title=%s, description=%s, package_id=%s, '
                'task_condition=%s, opens_at=%s, closes_at=%s, is_active=%s, version=version+1, updated_at=%s WHERE schedule_id=%s',
                (code, title.strip(), desc.strip(), pkg_id.strip(), cond, opens_iso, closes_iso, int(active), now, sid),
            )
        else:
            sid = 'SCH-' + secrets.token_hex(10)
            conn.execute(
                'INSERT INTO exam_schedules VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s,%s)',
                (sid, code, title.strip(), desc.strip(), pkg_id.strip(), cond, opens_iso, closes_iso, int(active), now, now),
            )
        row = conn.execute('SELECT * FROM exam_schedules WHERE schedule_id=%s', (sid,)).fetchone()
        return {'schedule': _hydrate_schedule(conn, row, admin=True)}


def delete_schedule(schedule_id):
    sid = str(schedule_id or '').strip()
    if not sid:
        raise ValueError('Identitas sesi jadwal tidak valid.')
    with get_connection() as conn:
        cur = conn.execute('DELETE FROM exam_schedules WHERE schedule_id=%s', (sid,))
        if cur.rowcount == 0:
            raise ValueError('Sesi jadwal tidak ditemukan.')
    return {'status': 'ok', 'deleted': sid}
