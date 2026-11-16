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
