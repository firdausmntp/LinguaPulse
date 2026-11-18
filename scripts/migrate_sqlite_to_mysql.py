"""One-way, lossless import. SQLite is read only; a populated target is refused."""
import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.database import get_connection, init_schema
from backend.mysql_schema import TABLES
from backend.package_schema import DEFAULT_PACKAGE_ID, initialize_packages
from backend.exam_schedules import DEFAULT_SCHEDULE_ID, initialize_schedules
from backend import config

MARKER = 'mysql_from_sqlite_v1'


def fingerprint(rows):
    """Compare every value, including duplicate rows, without logging user data."""
    def value(item):
        if isinstance(item, (int, float, Decimal)):
            return ['number', str(Decimal(str(item)).normalize())]
        return item
    return Counter(hashlib.sha256(json.dumps([value(v) for v in row],
                   ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
                   for row in rows)


def source_tables(source):
    names = [r[0] for r in source.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    unknown = set(names) - TABLES.keys()
    if unknown:
        raise ValueError(f'Tabel sumber belum didukung: {sorted(unknown)}')
    return names


def migrate(source_path, backup_dir, apply=False):
    source_path = Path(source_path).resolve(strict=True)
    if source_path.suffix.lower() not in {'.db', '.sqlite', '.sqlite3'}:
        raise ValueError('Sumber harus berupa berkas SQLite.')
    with closing(sqlite3.connect(source_path.as_uri() + '?mode=ro', uri=True)) as original:
        integrity = original.execute('PRAGMA integrity_check').fetchone()[0]
        if integrity != 'ok':
            raise ValueError('Integritas SQLite tidak valid; impor dihentikan.')
        tables = source_tables(original)
        counts = {t: original.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}
        if not apply:
            return {'mode': 'dry-run', 'source_counts': counts,
                    'target': f'{config.MYSQL_HOST}:{config.MYSQL_PORT}/{config.MYSQL_DATABASE}'}
        backup_dir = Path(backup_dir).resolve()
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
        backup = backup_dir / f'sqlite-before-mysql-{stamp}.sqlite3'
        with closing(sqlite3.connect(backup)) as snapshot:
            original.backup(snapshot)

    init_schema()
    report = {}
    with closing(sqlite3.connect(backup.as_uri() + '?mode=ro', uri=True)) as source, get_connection() as target:
        # Serializes two importers, including when the destination is still empty.
        locked = target.execute("SELECT GET_LOCK('linguapulse_sqlite_import', 10)").fetchone()[0]
        if locked != 1:
            raise ValueError('Migrasi lain sedang berjalan.')
        for table in TABLES:
            if table == 'schema_migrations':
                markers = {r['version'] for r in target.execute('SELECT version FROM schema_migrations')}
                if markers - {'options_relational_v1', 'exam_packages_v1', 'exam_schedules_v1'}:
                    raise ValueError('Target sudah berisi data migrasi; tidak ditimpa.')
            elif target.execute(f'SELECT COUNT(*) FROM `{table}`').fetchone()[0]:
                raise ValueError(f'Target sudah berisi data ({table}); tidak ditimpa.')
        # Only the untouched empty draft created by startup may be replaced.
        packages = target.execute('SELECT * FROM exam_packages').fetchall()
        if (len(packages) != 1 or packages[0]['package_id'] != DEFAULT_PACKAGE_ID
                or packages[0]['version'] != 1 or packages[0]['is_active']
                or target.execute('SELECT COUNT(*) FROM exam_package_questions').fetchone()[0]):
            raise ValueError('Target sudah berisi paket ujian; tidak ditimpa.')
        schedules = target.execute('SELECT * FROM exam_schedules').fetchall()
        if len(schedules) > 1 or (len(schedules) == 1 and (schedules[0]['schedule_id'] != DEFAULT_SCHEDULE_ID or schedules[0]['version'] != 1)):
            raise ValueError('Target sudah berisi sesi jadwal; tidak ditimpa.')
        target.execute('DELETE FROM exam_schedules')
        target.execute('DELETE FROM exam_packages WHERE package_id=%s', (DEFAULT_PACKAGE_ID,))
        target.execute('DELETE FROM schema_migrations')
        for table in TABLES:
            if table not in tables:
                continue
            columns = [r[1] for r in source.execute(f'PRAGMA table_info("{table}")')]
            destination = {r['Field'] for r in target.execute(f'SHOW COLUMNS FROM `{table}`')}
            if set(columns) - destination:
                raise ValueError(f'Kolom sumber belum didukung pada tabel {table}.')
            names = ','.join(f'`{name}`' for name in columns)
            rows = source.execute(f'SELECT {names} FROM "{table}" ORDER BY rowid').fetchall()
            if rows:
                target.executemany(f'INSERT INTO `{table}` ({names}) VALUES '
                                   f'({",".join(["%s"] * len(columns))})', rows)
            copied = [tuple(row.values()) for row in target.execute(f'SELECT {names} FROM `{table}`')]
            if fingerprint(rows) != fingerprint(copied):
                raise ValueError(f'Verifikasi nilai gagal pada {table}; transaksi dibatalkan.')
            report[table] = len(rows)
        initialize_packages(target)
        initialize_schedules(target)
        target.execute('INSERT INTO schema_migrations (version) VALUES (%s)', (MARKER,))
    result = {'mode': 'applied', 'backup': str(backup), 'verified_rows': report,
              'verification': 'all original columns and row counts match', 'marker': MARKER}
    backup.with_suffix('.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'data/toefl_platform.db')
    parser.add_argument('--backup-dir', type=Path, default=ROOT / '.workspace-backups')
    parser.add_argument('--apply', action='store_true', help='Import into an empty MySQL database')
    args = parser.parse_args()
    print(json.dumps(migrate(args.source, args.backup_dir, args.apply), indent=2))


if __name__ == '__main__':
    main()
