"""Additive package schema and one-time grouping of the existing active bank."""
DEFAULT_PACKAGE_ID = 'PKG-EXPERIMENTAL'
DEFAULT_PACKAGE_NAME = 'Simulasi TOEFL EPT'
PACKAGE_TABLES = {
    'exam_packages': """
        package_id VARCHAR(40) NOT NULL PRIMARY KEY, name VARCHAR(100) NOT NULL,
        description TEXT NOT NULL, duration_minutes INT NOT NULL,
        is_active TINYINT NOT NULL DEFAULT 0, version INT NOT NULL DEFAULT 1,
        created_at VARCHAR(32) NOT NULL, updated_at VARCHAR(32) NOT NULL,
        CHECK (duration_minutes BETWEEN 1 AND 240)
    """,
    'exam_package_questions': """
        package_id VARCHAR(40) NOT NULL, question_id VARCHAR(40) NOT NULL,
        position INT NOT NULL, PRIMARY KEY (package_id, question_id),
        UNIQUE KEY uq_package_position (package_id, position),
        FOREIGN KEY (package_id) REFERENCES exam_packages(package_id) ON DELETE CASCADE,
        FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE
    """,
}


def initialize_packages(conn):
    from datetime import datetime, timezone
    marker = 'exam_packages_v1'
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=%s', (marker,)).fetchone():
        return
    rows = conn.execute('SELECT question_id, section, question_type FROM questions '
                        'WHERE is_active=1 ORDER BY question_id').fetchall()
    sections = {r['section'] for r in rows if r['question_type'] == 'multiple_choice'}
    settings = conn.execute('SELECT duration_minutes FROM exam_settings WHERE id=1').fetchone()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute('INSERT INTO exam_packages VALUES (%s,%s,%s,%s,%s,1,%s,%s)',
                 (DEFAULT_PACKAGE_ID, DEFAULT_PACKAGE_NAME, 'Listening, Structure, dan Reading dalam satu sesi.',
                  settings['duration_minutes'] if settings else 25,
                  int({'listening', 'grammar', 'reading'} <= sections), now, now))
    if rows:
        conn.executemany('INSERT INTO exam_package_questions VALUES (%s,%s,%s)',
                         [(DEFAULT_PACKAGE_ID, r['question_id'], i) for i, r in enumerate(rows)])
    conn.execute('INSERT INTO schema_migrations (version) VALUES (%s)', (marker,))
