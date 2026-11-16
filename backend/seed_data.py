import json
import time
from .database import get_connection
from .auth import hash_password


def seed_all() -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        # 1. Seed Users (Admin & Demo Responden Tanpa Emoji)
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            users_seed = [
                (
                    "ADMIN-01",
                    "admin",
                    "admin@toefl.id",
                    hash_password("admin123"),
                    "Firdaus Satrio (Admin & Peneliti)",
                    "admin",
                    0,
                    0,
                    [],
                ),
                (
                    "RESP-1001",
                    "nadia_putri",
                    "nadia@student.id",
                    hash_password("student123"),
                    "Nadia Putri",
                    "student",
                    0,
                    0,
                    [],
                ),
            ]
            for p_code, uname, email, pw, dname, role, xp, streak, badges in users_seed:
                cur.execute(
                    """
                    INSERT INTO users (participant_code, username, email, password_hash, display_name, role, xp, streak, badges_json, consent_agreed, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s)
                """,
                    (
                        p_code,
                        uname,
                        email,
                        pw,
                        dname,
                        role,
                        xp,
                        streak,
                        json.dumps(badges, ensure_ascii=False),
                        now_str,
                    ),
                )
