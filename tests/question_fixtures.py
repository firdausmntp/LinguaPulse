"""Load archived examples into the temporary databases used by integration tests."""
import json
from pathlib import Path

from backend.database import get_connection
from backend.question_store import write_question


def seed_test_questions():
    question_dir = Path(__file__).resolve().parents[1] / 'questions'
    with get_connection() as conn:
        for path in sorted(question_dir.glob('*/*.json')):
            for item in json.loads(path.read_text(encoding='utf-8')):
                item = {**item, 'audio_url': item.get('audio_url', ''),
                        'is_active': 1, 'options': item.get('options', [])}
                write_question(conn, item)
    # Populate the migrated default package explicitly in disposable test data.
    with get_connection() as conn:
        ids = [r['question_id'] for r in conn.execute('SELECT question_id FROM questions WHERE is_active=1 ORDER BY question_id')]
        conn.execute('DELETE FROM exam_package_questions WHERE package_id=%s', ('PKG-EXPERIMENTAL',))
        conn.executemany('INSERT INTO exam_package_questions VALUES (%s,%s,%s)',
                         [('PKG-EXPERIMENTAL', qid, i) for i, qid in enumerate(ids)])
        conn.execute("UPDATE exam_packages SET is_active=1 WHERE package_id='PKG-EXPERIMENTAL'")
        conn.execute("UPDATE exam_schedules SET is_active=1 WHERE schedule_id='SCH-EXPERIMENTAL'")
