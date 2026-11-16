"""InnoDB schema. Parents precede their foreign-key dependants."""
import json

TABLES = {
    'users': """
        user_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        participant_code VARCHAR(64) NOT NULL UNIQUE,
        username VARCHAR(64) NOT NULL UNIQUE, email VARCHAR(254) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL, display_name VARCHAR(255) NOT NULL,
        role VARCHAR(16) NOT NULL DEFAULT 'student',
        xp INT NOT NULL DEFAULT 0, streak INT NOT NULL DEFAULT 0,
        badges_json LONGTEXT NOT NULL, consent_agreed TINYINT NOT NULL DEFAULT 1,
        created_at VARCHAR(32) NOT NULL, INDEX idx_users_role (role)
    """,
    'questions': """
        question_id VARCHAR(40) NOT NULL PRIMARY KEY,
        section VARCHAR(32) NOT NULL, question_type VARCHAR(32) NOT NULL,
        title TEXT, passage LONGTEXT, prompt LONGTEXT NOT NULL,
        options_json LONGTEXT, correct_answer LONGTEXT, explanation LONGTEXT,
        sample_ai_reference LONGTEXT, points_xp INT NOT NULL DEFAULT 25,
        is_active TINYINT NOT NULL DEFAULT 1, created_at VARCHAR(32) NOT NULL,
        audio_url TEXT, INDEX idx_questions_active (is_active, section, question_type)
    """,
    'exam_submissions': """
        session_id VARCHAR(64) NOT NULL PRIMARY KEY,
        participant_code VARCHAR(64) NOT NULL, display_name VARCHAR(255) NOT NULL,
        grammar_mc_correct INT NOT NULL, grammar_mc_total INT NOT NULL,
        reading_mc_correct INT NOT NULL, reading_mc_total INT NOT NULL,
        rewrite_count INT NOT NULL, essay_word_count INT NOT NULL,
        estimated_toefl_score INT NOT NULL, xp_earned INT NOT NULL,
        answers_json LONGTEXT NOT NULL, submitted_at VARCHAR(32) NOT NULL,
        listening_mc_correct INT NOT NULL DEFAULT 0,
        listening_mc_total INT NOT NULL DEFAULT 0,
        submission_order BIGINT NOT NULL AUTO_INCREMENT UNIQUE,
        INDEX idx_submissions_participant (participant_code, submitted_at)
    """,
    'telemetry_sessions': """
        session_id VARCHAR(64) NOT NULL PRIMARY KEY,
        participant_code VARCHAR(64) NOT NULL, device_profile VARCHAR(32) NOT NULL,
        task_condition VARCHAR(32) NOT NULL, duration_sec DOUBLE NOT NULL,
        features_json LONGTEXT NOT NULL, ablation_json LONGTEXT NOT NULL,
        xgboost_score DOUBLE NOT NULL, cnn1d_score DOUBLE NOT NULL,
        rule_flag INT NOT NULL, inference_latency_ms DOUBLE NOT NULL,
        heatmap_points_json LONGTEXT NOT NULL, timeline_events_json LONGTEXT NOT NULL,
        created_at VARCHAR(32) NOT NULL,
        ground_truth_label VARCHAR(32) NOT NULL DEFAULT 'UNLABELED',
        INDEX idx_telemetry_participant (participant_code),
        INDEX idx_telemetry_created (created_at)
    """,
    'question_options': """
        option_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        question_id VARCHAR(40) NOT NULL, option_index INT NOT NULL,
        option_text TEXT NOT NULL, UNIQUE KEY uq_question_option (question_id, option_index),
        FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE
    """,
    'exam_submission_answers': """
        answer_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        session_id VARCHAR(64) NOT NULL, question_id VARCHAR(40) NOT NULL,
        answer_text LONGTEXT NOT NULL, UNIQUE KEY uq_submission_answer (session_id, question_id),
        FOREIGN KEY (session_id) REFERENCES exam_submissions(session_id) ON DELETE CASCADE
    """,
    'user_badges': """
        badge_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT NOT NULL, badge_key VARCHAR(64) NOT NULL,
        awarded_at VARCHAR(32) NOT NULL, UNIQUE KEY uq_user_badge (user_id, badge_key),
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    """,
    'auth_sessions': """
        token_hash VARCHAR(64) NOT NULL PRIMARY KEY, user_id BIGINT NOT NULL,
        expires_at DOUBLE NOT NULL, INDEX idx_auth_expiry (expires_at),
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    """,
    'submission_results': """
        session_id VARCHAR(64) NOT NULL PRIMARY KEY, result_json LONGTEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES exam_submissions(session_id) ON DELETE CASCADE
    """,
    'respondent_surveys': """
        survey_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        session_id VARCHAR(64) NOT NULL UNIQUE, participant_code VARCHAR(64) NOT NULL,
        tab_switched TINYINT NOT NULL DEFAULT 0, copied_pasted TINYINT NOT NULL DEFAULT 0,
        external_resources TINYINT NOT NULL DEFAULT 0,
        honest_label VARCHAR(32) NOT NULL DEFAULT 'UNLABELED',
        feedback_note TEXT, submitted_at VARCHAR(32) NOT NULL,
        FOREIGN KEY (session_id) REFERENCES exam_submissions(session_id) ON DELETE CASCADE
    """,
    'exam_settings': """
        id INT NOT NULL PRIMARY KEY, duration_minutes INT NOT NULL,
        CHECK (id = 1), CHECK (duration_minutes BETWEEN 1 AND 240)
    """,
    'exam_attempts': """
        attempt_id VARCHAR(36) NOT NULL PRIMARY KEY, user_id BIGINT NOT NULL,
        bank_json LONGTEXT NOT NULL, device_profile VARCHAR(32) NOT NULL,
        task_condition VARCHAR(32) NOT NULL, expires_at DOUBLE NOT NULL,
        created_at DOUBLE NOT NULL, INDEX idx_attempts_user (user_id)
    """,
    'schema_migrations': 'version VARCHAR(100) NOT NULL PRIMARY KEY',
}


def initialize_schema(conn):
    for name, definition in TABLES.items():
        conn.execute(f'CREATE TABLE IF NOT EXISTS `{name}` ({definition}) '
                     'ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin')
    # Retain legacy options_json for lossless import; reads use question_options.
    marker = 'options_relational_v1'
    if not conn.execute('SELECT 1 FROM schema_migrations WHERE version=%s', (marker,)).fetchone():
        rows = conn.execute("""SELECT q.question_id, q.options_json FROM questions q
            WHERE q.options_json IS NOT NULL AND q.options_json NOT IN ('','[]')
            AND NOT EXISTS (SELECT 1 FROM question_options o WHERE o.question_id=q.question_id)""").fetchall()
        for row in rows:
            try:
                options = json.loads(row['options_json'])
            except (ValueError, TypeError):
                continue
            if isinstance(options, list):
                conn.executemany('INSERT INTO question_options '
                                 '(question_id,option_index,option_text) VALUES (%s,%s,%s)',
                                 [(row['question_id'], i, str(v)) for i, v in enumerate(options)])
        conn.execute('INSERT INTO schema_migrations (version) VALUES (%s)', (marker,))
