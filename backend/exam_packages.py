"""Package authoring and public previews. Answer keys remain server-side."""
from datetime import datetime, timezone
import secrets
from .database import get_connection
from .package_schema import DEFAULT_PACKAGE_ID
from questions.loader import get_structured_questions, public_bank


def readiness(bank):
    counts = {'listening': len(bank['listening']['questions']), 'grammar': len(bank['grammar_mc']),
              'reading': len(bank['reading']['questions']), 'rewrite': len(bank['grammar_rewrite']),
              'writing': len(bank['writing_tasks'])}
    problems = []
    for key, label in [('listening', 'Listening'), ('grammar', 'Structure'), ('reading', 'Reading')]:
        if not counts[key]:
            problems.append(f'Belum ada soal pilihan ganda {label}.')
    if any(not q.get('passage', '').strip() for q in bank['reading']['questions']):
        problems.append('Ada soal Reading tanpa bacaan.')
    if any(not q.get('audio_url', '').strip() for q in bank['listening']['questions']):
        problems.append('Ada soal Listening tanpa audio.')
    return counts, problems


def _read(conn, package_id, admin=False):
    row = conn.execute('SELECT * FROM exam_packages WHERE package_id=%s', (package_id,)).fetchone()
    if not row or (not admin and not row['is_active']):
        raise ValueError('Paket tidak tersedia. Pilih paket lain atau hubungi admin.')
    ids = [r['question_id'] for r in conn.execute('SELECT question_id FROM exam_package_questions '
           'WHERE package_id=%s ORDER BY position', (package_id,)).fetchall()]
    bank = get_structured_questions(question_ids=ids, conn=conn)
    counts, problems = readiness(bank)
    if len(bank['all_questions']) != len(ids):
        problems.append('Ada soal nonaktif atau tidak tersedia dalam paket.')
    item = dict(row)
    item.update(is_active=bool(row['is_active']), question_ids=ids, counts=counts,
                question_count=sum(counts.values())-max(0, counts['writing']-1),
                ready=not problems, problems=problems)
    bank['package'] = {k: item[k] for k in ['package_id', 'name', 'description', 'duration_minutes', 'version']}
    return item, bank


def get_package(package_id, admin=False):
    with get_connection() as conn:
        item, bank = _read(conn, package_id, admin)
    return item if admin else {'package': _public(item), 'bank': public_bank(bank)}


def _public(item):
    return {k: item[k] for k in ['package_id', 'name', 'description', 'duration_minutes',
                                'version', 'counts', 'question_count', 'ready', 'problems']}


def list_packages(admin=False):
    with get_connection() as conn:
        ids = conn.execute('SELECT package_id FROM exam_packages' +
                           ('' if admin else ' WHERE is_active=1') + ' ORDER BY created_at, package_id').fetchall()
        items = [_read(conn, row['package_id'], admin)[0] for row in ids]
    return {'packages': items if admin else [_public(item) for item in items]}


def start_package_bank(package_id=None):
    if package_id is not None and (not isinstance(package_id, str) or not 1 <= len(package_id) <= 40):
        raise ValueError('Identitas paket tidak valid.')
    with get_connection() as conn:
        item, bank = _read(conn, package_id or DEFAULT_PACKAGE_ID)
        if not item['ready']:
            raise ValueError('Paket belum siap. ' + ' '.join(item['problems']))
    return bank


def save_package(payload):
    name = payload.get('name')
    description = payload.get('description', '')
    duration = payload.get('duration_minutes')
    active = payload.get('is_active', False)
    ids = payload.get('question_ids')
    package_id = payload.get('package_id')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
        raise ValueError('Nama paket harus 1 sampai 100 karakter.')
    if not isinstance(description, str) or len(description) > 2000:
        raise ValueError('Deskripsi maksimal 2.000 karakter.')
    if isinstance(duration, bool) or not isinstance(duration, int) or not 1 <= duration <= 240:
        raise ValueError('Durasi harus berupa bilangan bulat 1 sampai 240 menit.')
    if not isinstance(active, bool):
        raise ValueError('Status paket tidak valid.')
    if not isinstance(ids, list) or len(ids) > 3000 or any(not isinstance(x, str) or not x or len(x) > 40 for x in ids):
        raise ValueError('Daftar soal paket tidak valid.')
    if len(set(ids)) != len(ids):
        raise ValueError('Soal yang sama tidak boleh dimasukkan dua kali.')
    if package_id is not None and (not isinstance(package_id, str) or not 1 <= len(package_id) <= 40):
        raise ValueError('Identitas paket tidak valid.')
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        previous = conn.execute('SELECT * FROM exam_packages WHERE package_id=%s FOR UPDATE',
                                (package_id,)).fetchone() if package_id else None
        if package_id and not previous:
            raise ValueError('Paket tidak ditemukan.')
        version = payload.get('version')
        if previous and (isinstance(version, bool) or not isinstance(version, int) or version != previous['version']):
            raise ValueError('Paket sudah diubah. Muat ulang sebelum menyimpan kembali.')
        bank = get_structured_questions(include_inactive=True, question_ids=ids, conn=conn)
        if len(bank['all_questions']) != len(ids):
            raise ValueError('Ada soal yang sudah dihapus. Periksa kembali pilihan soal.')
        _, problems = readiness(bank)
        if any(not q['is_active'] for q in bank['all_questions']):
            problems.append('Paket memuat soal nonaktif.')
        if active and problems:
            raise ValueError('Paket belum dapat dipublikasikan. ' + ' '.join(problems))
        if previous:
            conn.execute('UPDATE exam_packages SET name=%s, description=%s, duration_minutes=%s, '
                         'is_active=%s, version=version+1, updated_at=%s WHERE package_id=%s',
                         (name.strip(), description.strip(), duration, int(active), now, package_id))
        else:
            package_id = 'PKG-' + secrets.token_hex(12)
            conn.execute('INSERT INTO exam_packages VALUES (%s,%s,%s,%s,%s,1,%s,%s)',
                         (package_id, name.strip(), description.strip(), duration, int(active), now, now))
        conn.execute('DELETE FROM exam_package_questions WHERE package_id=%s', (package_id,))
        if ids:
            conn.executemany('INSERT INTO exam_package_questions VALUES (%s,%s,%s)',
                             [(package_id, question_id, i) for i, question_id in enumerate(ids)])
        item, _ = _read(conn, package_id, admin=True)
    return {'package': item}
