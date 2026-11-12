import json
import random
import time
from .database import get_connection
from .auth import hash_password
from .telemetry_engine import extract_features_and_predict
from questions.loader import load_all_questions_from_folders


def seed_all() -> None:
    conn = get_connection()
    cur = conn.cursor()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    # 1. Seed Users (Admin & Demo Responden Tanpa Emoji)
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        users_seed = [
            ("ADMIN-01", "admin", "admin@toefl.id", hash_password("admin123"), "Firdaus Satrio (Admin & Peneliti)", "admin", 0, 0, []),
            ("RESP-1001", "nadia_putri", "nadia@student.id", hash_password("student123"), "Nadia Putri", "student", 0, 0, []),
        ]
        for p_code, uname, email, pw, dname, role, xp, streak, badges in users_seed:
            cur.execute("""
                INSERT INTO users (participant_code, username, email, password_hash, display_name, role, xp, streak, badges_json, consent_agreed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """, (p_code, uname, email, pw, dname, role, xp, streak, json.dumps(badges, ensure_ascii=False), now_str))

    # 2. Seed Questions dari Folder questions/{grammar,reading,writing}/
    cur.execute("SELECT COUNT(*) FROM questions")
    if cur.fetchone()[0] == 0:
        folder_questions = load_all_questions_from_folders()
        for q in folder_questions:
            cur.execute("""
                INSERT INTO questions
                (question_id, section, question_type, title, passage, prompt, options_json, correct_answer, explanation, sample_ai_reference, points_xp, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """, (
                q["question_id"], q["section"], q["question_type"], q.get("title", ""), q.get("passage", ""),
                q["prompt"], json.dumps(q.get("options", []), ensure_ascii=False), str(q.get("correct_answer", "")),
                q.get("explanation", ""), q.get("sample_ai_reference", ""), 0, now_str
            ))

    conn.commit()
    conn.close()
    from .seed_listening import seed_listening
    seed_listening()
