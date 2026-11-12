import sqlite3
from .config import DATA_DIR, DB_PATH


class ManagedConnection(sqlite3.Connection):
    """Commit/rollback and close deterministically, including Windows file handles."""
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, factory=ManagedConnection)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema() -> None:
    conn = get_connection()
    cur = conn.cursor()

    # Legacy reward columns are retained only to preserve existing databases.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_code TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            xp INTEGER NOT NULL DEFAULT 0,
            streak INTEGER NOT NULL DEFAULT 1,
            badges_json TEXT NOT NULL DEFAULT '[]',
            consent_agreed INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    # 2. Tabel Bank Soal TOEFL (Dapat dikelola melalui Panel Admin CRUD)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            question_id TEXT PRIMARY KEY,
            section TEXT NOT NULL,
            question_type TEXT NOT NULL,
            title TEXT,
            passage TEXT,
            prompt TEXT NOT NULL,
            options_json TEXT,
            correct_answer TEXT,
            explanation TEXT,
            sample_ai_reference TEXT,
            points_xp INTEGER NOT NULL DEFAULT 25,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    # 3. Tabel Hasil Jawaban Ujian TOEFL (Terpisah dari tabel telemetri sesuai Batasan Masalah)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exam_submissions (
            session_id TEXT PRIMARY KEY,
            participant_code TEXT NOT NULL,
            display_name TEXT NOT NULL,
            grammar_mc_correct INTEGER NOT NULL,
            grammar_mc_total INTEGER NOT NULL,
            reading_mc_correct INTEGER NOT NULL,
            reading_mc_total INTEGER NOT NULL,
            rewrite_count INTEGER NOT NULL,
            essay_word_count INTEGER NOT NULL,
            estimated_toefl_score INTEGER NOT NULL,
            xp_earned INTEGER NOT NULL,
            answers_json TEXT NOT NULL,
            submitted_at TEXT NOT NULL
        )
    """)

    # 4. Tabel Sesi Telemetri & Prediksi Model (Tanpa menyimpan karakter ketikan mentah / isi clipboard)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_sessions (
            session_id TEXT PRIMARY KEY,
            participant_code TEXT NOT NULL,
            device_profile TEXT NOT NULL,
            task_condition TEXT NOT NULL,
            duration_sec REAL NOT NULL,
            features_json TEXT NOT NULL,
            ablation_json TEXT NOT NULL,
            xgboost_score REAL NOT NULL,
            cnn1d_score REAL NOT NULL,
            rule_flag INTEGER NOT NULL,
            inference_latency_ms REAL NOT NULL,
            heatmap_points_json TEXT NOT NULL,
            timeline_events_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute('''CREATE TABLE IF NOT EXISTS auth_sessions (
        token_hash TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(user_id),
        expires_at REAL NOT NULL
    )''')
    cur.execute("""CREATE TABLE IF NOT EXISTS submission_results (
        session_id TEXT PRIMARY KEY REFERENCES exam_submissions(session_id),
        result_json TEXT NOT NULL
    )""")
    # Additive migrations preserve every existing account, question and result.
    for table, column, definition in (
        ('questions', 'audio_url', "TEXT NOT NULL DEFAULT ''"),
        ('exam_submissions', 'listening_mc_correct', 'INTEGER NOT NULL DEFAULT 0'),
        ('exam_submissions', 'listening_mc_total', 'INTEGER NOT NULL DEFAULT 0'),
        ('telemetry_sessions', 'ground_truth_label', "TEXT NOT NULL DEFAULT 'UNLABELED'"),
    ):
        columns = {row['name'] for row in cur.execute(f'PRAGMA table_info({table})')}
        if column not in columns:
            cur.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')

    cur.execute("""CREATE TABLE IF NOT EXISTS respondent_surveys (
        survey_id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT UNIQUE NOT NULL REFERENCES exam_submissions(session_id),
        participant_code TEXT NOT NULL,
        tab_switched INTEGER NOT NULL DEFAULT 0,
        copied_pasted INTEGER NOT NULL DEFAULT 0,
        external_resources INTEGER NOT NULL DEFAULT 0,
        honest_label TEXT NOT NULL DEFAULT 'UNLABELED',
        feedback_note TEXT NOT NULL DEFAULT '',
        submitted_at TEXT NOT NULL
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS exam_attempts (
        attempt_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
        bank_json TEXT NOT NULL, device_profile TEXT NOT NULL,
        task_condition TEXT NOT NULL, expires_at REAL NOT NULL, created_at REAL NOT NULL
    )""")
    cur.execute('CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY)')
    conn.commit()
    conn.close()

