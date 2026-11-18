"""Package validation and immutable attempts against a disposable MySQL schema."""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mysql_support import temporary_database
from question_fixtures import seed_test_questions
from backend.database import init_schema, get_connection
from backend.exam_packages import save_package, get_package, list_packages
from backend.attempts import start_attempt, resume_attempt
from questions.loader import get_structured_questions


class ExamPackagesTests(unittest.TestCase):
    def setUp(self):
        self.db = temporary_database()
        self.db.__enter__()
        self.addCleanup(self.db.__exit__, None, None, None)
        init_schema()
        from backend.seed_data import seed_all
        seed_all()
        seed_test_questions()
        bank = get_structured_questions()
        self.ids = [bank['listening']['questions'][0]['id'], bank['grammar_mc'][0]['id'],
                    bank['reading']['questions'][0]['id']]
        with get_connection() as conn:
            self.ids[2] = conn.execute("SELECT question_id FROM questions WHERE section='reading' "
                                      "AND TRIM(passage)<>'' ORDER BY question_id LIMIT 1").fetchone()[0]
        self.payload = dict(name='Experimental mini', description='Paket uji', duration_minutes=17,
                            is_active=True, question_ids=self.ids)
        with get_connection() as conn:
            self.user = dict(conn.execute("SELECT * FROM users WHERE username='nadia_putri'").fetchone())

    def test_selection_duration_privacy_and_snapshot(self):
        package = save_package(self.payload)['package']
        preview = get_package(package['package_id'])
        self.assertIsNone(preview['bank']['writing'])
        self.assertEqual(preview['package']['question_count'], 3)
        started = start_attempt(self.user, dict(package_id=package['package_id'], consent_agreed=True,
                               device_profile='MOBILE_VIRTUAL', task_condition='MANDIRI'))
        self.assertAlmostEqual(started['deadline'] / 1000 - time.time(), 17 * 60, delta=3)
        bank = started['bank']
        questions = bank['listening']['questions'] + bank['grammar_mc'] + bank['reading']['questions']
        self.assertEqual({q['id'] for q in questions}, set(self.ids))
        self.assertTrue(all(not {'answer', 'correct_answer', 'explanation'} & q.keys() for q in questions))
        with get_connection() as conn:
            frozen = json.loads(conn.execute('SELECT bank_json FROM exam_attempts WHERE attempt_id=%s',
                                (started['attempt_id'],)).fetchone()['bank_json'])
        self.assertIn('answer', frozen['grammar_mc'][0])
        changed = save_package({**self.payload, 'package_id': package['package_id'],
                                'version': package['version'], 'name': 'Diarsipkan',
                                'duration_minutes': 5, 'is_active': False, 'question_ids': []})
        self.assertEqual(changed['package']['version'], 2)
        resumed = resume_attempt(self.user, started['attempt_id'])
        self.assertEqual(resumed, started)
        with self.assertRaises(ValueError):
            start_attempt(self.user, dict(package_id=package['package_id'], consent_agreed=True,
                          device_profile='PC_PHYSICAL', task_condition='MANDIRI'))

    def test_draft_validation_and_atomic_stale_edit(self):
        draft = save_package({**self.payload, 'is_active': False, 'question_ids': []})['package']
        self.assertFalse(draft['ready'])
        self.assertNotIn(draft['package_id'], [p['package_id'] for p in list_packages()['packages']])
        with self.assertRaises(ValueError):
            get_package(draft['package_id'])
        edit = {**self.payload, 'package_id': draft['package_id'], 'version': draft['version']}
        for invalid in ({'question_ids': [*self.ids, 'MISSING']}, {'question_ids': self.ids * 2},
                        {'question_ids': self.ids[:1]}, {'duration_minutes': True},
                        {'duration_minutes': 0}, {'is_active': 'true'}, {'version': 0},
                        {'version': True}, {'package_id': ''}):
            with self.assertRaises(ValueError, msg=str(invalid)):
                save_package({**edit, **invalid})
            self.assertEqual(get_package(draft['package_id'], admin=True), draft)
        published = save_package(edit)['package']
        with self.assertRaises(ValueError):
            save_package(edit)
        self.assertEqual(get_package(draft['package_id'], admin=True), published)

    def test_inactive_question_block_and_idempotent_schema(self):
        package = save_package(self.payload)['package']
        with get_connection() as conn:
            conn.execute('UPDATE questions SET is_active=0 WHERE question_id=%s', (self.ids[0],))
        self.assertFalse(get_package(package['package_id'])['package']['ready'])
        with self.assertRaises(ValueError):
            save_package({**self.payload, 'package_id': package['package_id'], 'version': package['version']})
        init_schema()
        self.assertEqual(get_package(package['package_id'], admin=True)['question_ids'], self.ids)
        with get_connection() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM exam_packages').fetchone()[0], 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
