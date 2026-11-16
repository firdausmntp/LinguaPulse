"""Real MySQL regression tests for data import, rollback, and schema constraints."""
import hashlib
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.database import get_connection, init_schema, IntegrityError
from backend.mysql_schema import TABLES
from backend.question_store import save_question
from mysql_support import temporary_database
from scripts.migrate_sqlite_to_mysql import migrate, MARKER


def fixture(path, invalid=False):
    sid = 'SES-migration'
    data = {
        'users': dict(user_id=7, participant_code='RESP-007', username='example',
                      email='migration@example.test', password_hash='unchanged-hash',
                      display_name="Pengguna é 日本 100% 'tes'", role='student',
                      badges_json='[]', created_at='2026-11-16 12:00:00'),
        'questions': dict(question_id='legacy-q', section='grammar',
                          question_type='multiple_choice', prompt='Unicode é',
                          options_json='["A", "B"]', correct_answer='0',
                          created_at='2026-11-16 12:00:00'),
        'exam_submissions': dict(session_id=sid, participant_code='RESP-007',
                                 display_name='Nama historis', grammar_mc_correct=1,
                                 grammar_mc_total=2, reading_mc_correct=0, reading_mc_total=1,
                                 rewrite_count=0, essay_word_count=30, estimated_toefl_score=0,
                                 xp_earned=0, answers_json='{"legacy-q": 0}',
                                 submitted_at='2026-11-16 12:00:00'),
        'question_options': dict(option_id=9, question_id='missing' if invalid else 'legacy-q',
                                 option_index=0, option_text='Opsi é'),
        'auth_sessions': dict(token_hash='a' * 64, user_id=7, expires_at=1900000000.5),
        'exam_submission_answers': dict(answer_id=11, session_id=sid,
                                        question_id='legacy-q', answer_text='0'),
        'submission_results': dict(session_id=sid, result_json='{"status": "ok"}'),
        'respondent_surveys': dict(survey_id=3, session_id=sid, participant_code='RESP-007',
                                   tab_switched=1, copied_pasted=0, external_resources=0,
                                   honest_label='CHEATING_REPORTED', feedback_note='Catatan é',
                                   submitted_at='2026-11-16 12:00:00'),
        'telemetry_sessions': dict(session_id=sid, participant_code='RESP-007',
                                   device_profile='MOBILE_VIRTUAL', task_condition='MANDIRI',
                                   duration_sec=120.5, features_json='{}', ablation_json='{}',
                                   xgboost_score=0.25, cnn1d_score=0.5, rule_flag=1,
                                   inference_latency_ms=0.125, heatmap_points_json='[]',
                                   timeline_events_json='[]', created_at='2026-11-16 12:00:00',
                                   ground_truth_label='CHEATING_REPORTED'),
        'exam_attempts': dict(attempt_id='00000000-1111-2222-3333-444444444444',
                              user_id=7, bank_json='{}', device_profile='MOBILE_VIRTUAL',
                              task_condition='MANDIRI', expires_at=1900000000.5, created_at=1800000000.0),
        'user_badges': dict(badge_id=1, user_id=7, badge_key='legacy', awarded_at='2025-01-01'),
        'exam_settings': dict(id=1, duration_minutes=17),
        'schema_migrations': dict(version='historical_marker'),
    }
    with closing(sqlite3.connect(path)) as conn, conn:
        for name, fields in data.items():
            definitions = ','.join(f'"{key}" ' + ('REAL' if isinstance(value, float) else
                                   'INTEGER' if isinstance(value, int) else 'TEXT')
                                   for key, value in fields.items())
            conn.execute(f'CREATE TABLE "{name}" ({definitions})')
            conn.execute(f'INSERT INTO "{name}" VALUES ({",".join("?" for _ in fields)})', tuple(fields.values()))
    return data


class MySQLMigrationTests(unittest.TestCase):
    def test_lossless_import_all_tables_and_refuse_second_import(self):
        with temporary_database(), tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'source.db'
            data = fixture(path)
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(migrate(path, tmp)['mode'], 'dry-run')
            result = migrate(path, tmp, apply=True)
            self.assertEqual(result['verified_rows'], {name: 1 for name in data})
            self.assertTrue(Path(result['backup']).exists())
            with get_connection() as conn:
                self.assertEqual(conn.execute('SELECT display_name FROM users').fetchone()[0], data['users']['display_name'])
                self.assertEqual(conn.execute('SELECT password_hash FROM users').fetchone()[0], 'unchanged-hash')
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM schema_migrations WHERE version=%s', (MARKER,)).fetchone()[0], 1)
            with self.assertRaisesRegex(ValueError, 'Target sudah berisi'):
                migrate(path, tmp, apply=True)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)

    def test_invalid_foreign_key_rolls_back_entire_import(self):
        with temporary_database(), tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'invalid.db'
            fixture(path, invalid=True)
            with self.assertRaises(IntegrityError):
                migrate(path, tmp, apply=True)
            with get_connection() as conn:
                for table in TABLES:
                    if table != 'schema_migrations':
                        self.assertEqual(conn.execute(f'SELECT COUNT(*) FROM `{table}`').fetchone()[0], 0, table)

    def test_unknown_source_column_is_refused_without_partial_data(self):
        with temporary_database(), tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'extra.db'
            fixture(path)
            with closing(sqlite3.connect(path)) as conn, conn:
                conn.execute('ALTER TABLE users ADD COLUMN unknown_data TEXT')
            with self.assertRaisesRegex(ValueError, 'Kolom sumber'):
                migrate(path, tmp, apply=True)
            with get_connection() as conn:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM users').fetchone()[0], 0)

    def test_real_innodb_transactions_and_unchanged_update(self):
        with temporary_database():
            init_schema()
            with get_connection() as conn:
                version = conn.execute('SELECT VERSION()').fetchone()[0]
                self.assertNotIn('MariaDB', version)
                engines = {r[0] for r in conn.execute('SELECT ENGINE FROM information_schema.tables WHERE table_schema=DATABASE()')}
                self.assertEqual(engines, {'InnoDB'})
            with self.assertRaisesRegex(RuntimeError, 'rollback'):
                with get_connection() as conn:
                    conn.execute('INSERT INTO exam_settings VALUES (1,17)')
                    raise RuntimeError('rollback')
            with get_connection() as conn:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM exam_settings').fetchone()[0], 0)
            save_question(dict(question_id='same', section='grammar', question_type='multiple_choice',
                               prompt='Pick', options=['A', 'B'], correct_answer='0'))
            with get_connection() as conn:
                matched = conn.execute('UPDATE questions SET is_active=1 WHERE question_id=%s', ('same',))
                self.assertEqual(matched.rowcount, 1)


if __name__ == '__main__':
    unittest.main()
