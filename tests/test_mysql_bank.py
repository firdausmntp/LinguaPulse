"""The live question bank is MySQL, including across server initialization."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.database import get_connection, init_schema
from backend.question_store import save_question, delete_question, export_questions, import_questions
from backend.seed_data import seed_all
from mysql_support import temporary_database


class MySQLBankTests(unittest.TestCase):
    def test_restart_never_seeds_or_restores_questions_from_json(self):
        with temporary_database():
            init_schema()
            seed_all()
            self.assertEqual(export_questions()['questions'], [])
            question = {'question_id': 'db-question', 'section': 'grammar',
                        'question_type': 'multiple_choice', 'prompt': 'Choose one',
                        'options': ['A', 'B'], 'correct_answer': '0'}
            reading = {**question, 'question_id': 'reading-a', 'section': 'reading',
                       'title': 'Shared passage', 'passage': 'A reading passage.'}
            import_questions({'questions': [reading, {**reading, 'question_id': 'reading-b', 'passage': ''}]})
            exported = export_questions()['questions']
            self.assertEqual([q['passage'] for q in exported], ['A reading passage.'] * 2)
            delete_question('reading-a')
            delete_question('reading-b')
            save_question(question)
            seed_all()
            self.assertEqual(export_questions()['questions'][0]['question_id'], 'db-question')
            delete_question('db-question')
            seed_all()
            self.assertEqual(export_questions()['questions'], [])
            with get_connection() as conn:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM question_options').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
