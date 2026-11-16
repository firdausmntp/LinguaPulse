"""Reading passages must follow their questions into the exam snapshot."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.attempts import start_attempt
from backend.database import get_connection, init_schema
from backend.question_store import save_question
from mysql_support import temporary_database


class ReadingBankTests(unittest.TestCase):
    def test_shared_passage_and_ambiguous_passage(self):
        with temporary_database():
            init_schema()
            common = {'question_type': 'multiple_choice', 'prompt': 'Choose',
                      'options': ['A', 'B'], 'correct_answer': '0'}
            save_question({**common, 'question_id': 'l', 'section': 'listening', 'audio_url': '/media/a.wav'})
            save_question({**common, 'question_id': 'g', 'section': 'grammar'})
            save_question({**common, 'question_id': 'r1', 'section': 'reading', 'title': 'Shared', 'passage': 'Passage one'})
            save_question({**common, 'question_id': 'r2', 'section': 'reading', 'title': 'Shared', 'passage': 'Passage one'})
            save_question({**common, 'question_id': 'r3', 'section': 'reading', 'title': 'Other', 'passage': 'Passage two'})
            with get_connection() as conn:
                conn.execute("UPDATE questions SET passage='' WHERE question_id='r2'")
            payload = {'device_profile': 'PC_PHYSICAL', 'task_condition': 'MANDIRI', 'consent_agreed': True}
            attempt = start_attempt({'user_id': 1}, payload)
            passages = {q['id']: q['passage'] for q in attempt['bank']['reading']['questions']}
            self.assertEqual(passages, {'r1': 'Passage one', 'r2': 'Passage one', 'r3': 'Passage two'})
            with get_connection() as conn:
                conn.execute("UPDATE questions SET title='Missing', passage='' WHERE question_id='r2'")
            with self.assertRaisesRegex(ValueError, 'tanpa bacaan'):
                start_attempt({'user_id': 1}, payload)


if __name__ == '__main__':
    unittest.main()
