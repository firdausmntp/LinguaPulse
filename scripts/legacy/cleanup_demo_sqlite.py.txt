"""Remove only recognized demo records, after a consistent SQLite backup."""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'data/toefl_platform.db'
BACKUP = ROOT / '.workspace-backups/before-demo-cleanup.db'
with sqlite3.connect(DB) as conn:
    if not BACKUP.exists():
        BACKUP.parent.mkdir(exist_ok=True)
        with sqlite3.connect(BACKUP) as backup:
            conn.backup(backup)
    questions_before = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
    conn.execute("DELETE FROM submission_results WHERE session_id IN (SELECT session_id FROM exam_submissions WHERE session_id GLOB 'SES-2026-[0-9][0-9][0-9]')")
    conn.execute("DELETE FROM exam_submissions WHERE session_id GLOB 'SES-2026-[0-9][0-9][0-9]'")
    conn.execute("DELETE FROM telemetry_sessions WHERE session_id GLOB 'SES-2026-[0-9][0-9][0-9]'")
    demo = "SELECT user_id FROM users WHERE username IN ('rizky_pratama','alya_mobile') OR (username LIKE 'guest_%' AND email LIKE '%@public.toefl.id')"
    conn.execute('DELETE FROM auth_sessions WHERE user_id IN (' + demo + ')')
    conn.execute('DELETE FROM exam_attempts WHERE user_id IN (' + demo + ')')
    conn.execute("DELETE FROM users WHERE user_id IN (" + demo + ')')
    assert conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0] == questions_before
    print('Questions preserved:', questions_before)
    print('Accounts remaining:', conn.execute('SELECT COUNT(*) FROM users').fetchone()[0])
    print('Telemetry sessions remaining:', conn.execute('SELECT COUNT(*) FROM telemetry_sessions').fetchone()[0])
    print('Submissions remaining:', conn.execute('SELECT COUNT(*) FROM exam_submissions').fetchone()[0])
print('Backup:', BACKUP)
