"""One-time original Listening examples, never repopulated after deliberate deletion."""
import json
import time
from .config import ROOT_DIR
from .database import get_connection


def seed_listening():
    with get_connection() as conn:
        if conn.execute("SELECT 1 FROM schema_migrations WHERE version = 'ept_listening_examples'").fetchone():
            return
        examples = json.loads((ROOT_DIR / 'questions/listening/questions.json').read_text(encoding='utf-8'))
        for item in examples:
            conn.execute("""INSERT OR IGNORE INTO questions
                (question_id,section,question_type,title,passage,prompt,options_json,
                 correct_answer,explanation,sample_ai_reference,points_xp,is_active,created_at,audio_url)
                VALUES (?,?,?,?,?,?,?,?,?,?,0,1,?,?)""", (
                    item['question_id'], 'listening', 'multiple_choice', item['title'], item['passage'],
                    item['prompt'], json.dumps(item['options']), item['correct_answer'], item['explanation'],
                    '', time.strftime('%Y-%m-%d %H:%M:%S'), item['audio_url']))
            conn.execute("UPDATE questions SET audio_url = ? WHERE question_id = ? AND audio_url = ''",
                         (item['audio_url'], item['question_id']))
        conn.execute("INSERT INTO schema_migrations VALUES ('ept_listening_examples')")
