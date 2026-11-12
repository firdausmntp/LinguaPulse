"""Respondent self-report survey and ground-truth labeling for academic integrity evaluation."""
import time
from .database import get_connection


def submit_respondent_survey(user, payload):
    if not isinstance(payload, dict):
        raise ValueError("Format data survei tidak valid.")

    session_id = str(payload.get("session_id", "")).strip()
    if not session_id.startswith("SES-"):
        raise ValueError("Kode sesi tidak valid.")

    p_code = user["participant_code"]
    with get_connection() as conn:
        sub = conn.execute(
            "SELECT session_id FROM exam_submissions WHERE session_id = ? AND participant_code = ?",
            (session_id, p_code)
        ).fetchone()
        if not sub:
            raise ValueError("Sesi ujian tidak ditemukan untuk akun ini.")

        tab_switched = 1 if payload.get("tab_switched") else 0
        copied_pasted = 1 if payload.get("copied_pasted") else 0
        external_resources = 1 if payload.get("external_resources") else 0
        feedback_note = str(payload.get("feedback_note", "")).strip()[:500]

        if tab_switched or copied_pasted or external_resources:
            honest_label = "CHEATING_REPORTED"
        else:
            honest_label = "CLEAN_REPORTED"

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        conn.execute("""
            INSERT INTO respondent_surveys
            (session_id, participant_code, tab_switched, copied_pasted, external_resources, honest_label, feedback_note, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                tab_switched=excluded.tab_switched,
                copied_pasted=excluded.copied_pasted,
                external_resources=excluded.external_resources,
                honest_label=excluded.honest_label,
                feedback_note=excluded.feedback_note,
                submitted_at=excluded.submitted_at
        """, (session_id, p_code, tab_switched, copied_pasted, external_resources, honest_label, feedback_note, now_str))

        conn.execute(
            "UPDATE telemetry_sessions SET ground_truth_label = ? WHERE session_id = ?",
            (honest_label, session_id)
        )

    return {
        "status": "ok",
        "session_id": session_id,
        "label": honest_label,
        "message": "Survei validasi responden berhasil disimpan untuk dataset penelitian skripsi."
    }


def get_respondent_survey(user, session_id):
    if not session_id or not session_id.startswith("SES-"):
        return {"submitted": False}
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM respondent_surveys WHERE session_id = ? AND participant_code = ?",
            (session_id, user["participant_code"])
        ).fetchone()
        if not row:
            return {"submitted": False}
        return {
            "submitted": True,
            "survey": {
                "session_id": row["session_id"],
                "tab_switched": bool(row["tab_switched"]),
                "copied_pasted": bool(row["copied_pasted"]),
                "external_resources": bool(row["external_resources"]),
                "honest_label": row["honest_label"],
                "feedback_note": row["feedback_note"],
                "submitted_at": row["submitted_at"]
            }
        }


def update_proctor_label(actor, payload):
    if not isinstance(payload, dict):
        raise ValueError("Format data label tidak valid.")
    session_id = str(payload.get("session_id", "")).strip()
    label = str(payload.get("label", "")).strip().upper()
    valid_labels = {"UNLABELED", "CLEAN_REPORTED", "CHEATING_REPORTED", "MANUAL_CLEAN", "MANUAL_CHEATING"}
    if label not in valid_labels:
        raise ValueError("Pilihan label tidak valid.")

    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE telemetry_sessions SET ground_truth_label = ? WHERE session_id = ?",
            (label, session_id)
        )
        if cur.rowcount == 0:
            raise ValueError("Sesi tidak ditemukan.")
    return {"status": "ok", "session_id": session_id, "label": label}

