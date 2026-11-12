"""Unit and integration tests for respondent survey and ground-truth labeling."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
import json
from backend.database import init_schema, get_connection
from backend.survey import submit_respondent_survey, get_respondent_survey, update_proctor_label


class TestRespondentSurvey(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_schema()
        cls.test_user = {
            "user_id": 9999,
            "participant_code": "RESP-TEST-001",
            "username": "survey_test_user",
            "role": "student"
        }
        cls.admin_user = {
            "user_id": 1,
            "participant_code": "ADM-001",
            "username": "admin_test",
            "role": "admin"
        }
        cls.session_id = "SES-11111111-2222-3333-4444-555555555555"

        with get_connection() as conn:
            conn.execute("DELETE FROM respondent_surveys WHERE session_id = ?", (cls.session_id,))
            conn.execute("""
                INSERT OR REPLACE INTO exam_submissions
                (session_id, participant_code, display_name, grammar_mc_correct, grammar_mc_total,
                 reading_mc_correct, reading_mc_total, rewrite_count, essay_word_count,
                 estimated_toefl_score, xp_earned, answers_json, submitted_at)
                VALUES (?, ?, 'Test User', 5, 10, 5, 10, 0, 0, 0, 0, '{}', '2026-11-12 12:00:00')
            """, (cls.session_id, cls.test_user["participant_code"]))

            conn.execute("""
                INSERT OR REPLACE INTO telemetry_sessions
                (session_id, participant_code, device_profile, task_condition, duration_sec,
                 features_json, ablation_json, xgboost_score, cnn1d_score, rule_flag,
                 inference_latency_ms, heatmap_points_json, timeline_events_json, created_at, ground_truth_label)
                VALUES (?, ?, 'PC_PHYSICAL', 'MANDIRI', 300.0, '{}', '{}', 0.25, 0.20, 0, 0.5, '[]', '[]', '2026-11-12 12:00:00', 'UNLABELED')
            """, (cls.session_id, cls.test_user["participant_code"]))

    def test_01_initial_status(self):
        status = get_respondent_survey(self.test_user, self.session_id)
        self.assertFalse(status["submitted"])

    def test_02_submit_survey_clean(self):
        payload = {
            "session_id": self.session_id,
            "tab_switched": False,
            "copied_pasted": False,
            "external_resources": False,
            "feedback_note": "Ujian lancar tanpa kendala."
        }
        res = submit_respondent_survey(self.test_user, payload)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["label"], "CLEAN_REPORTED")

        status = get_respondent_survey(self.test_user, self.session_id)
        self.assertTrue(status["submitted"])
        self.assertEqual(status["survey"]["honest_label"], "CLEAN_REPORTED")
        self.assertFalse(status["survey"]["tab_switched"])

        with get_connection() as conn:
            row = conn.execute("SELECT ground_truth_label FROM telemetry_sessions WHERE session_id = ?", (self.session_id,)).fetchone()
            self.assertEqual(row["ground_truth_label"], "CLEAN_REPORTED")

    def test_03_submit_survey_cheating_reported(self):
        payload = {
            "session_id": self.session_id,
            "tab_switched": True,
            "copied_pasted": True,
            "external_resources": False,
            "feedback_note": "Sempat buka kamus di tab lain."
        }
        res = submit_respondent_survey(self.test_user, payload)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["label"], "CHEATING_REPORTED")

        status = get_respondent_survey(self.test_user, self.session_id)
        self.assertTrue(status["submitted"])
        self.assertEqual(status["survey"]["honest_label"], "CHEATING_REPORTED")
        self.assertTrue(status["survey"]["tab_switched"])
        self.assertTrue(status["survey"]["copied_pasted"])

        with get_connection() as conn:
            row = conn.execute("SELECT ground_truth_label FROM telemetry_sessions WHERE session_id = ?", (self.session_id,)).fetchone()
            self.assertEqual(row["ground_truth_label"], "CHEATING_REPORTED")

    def test_04_admin_manual_label_update(self):
        res = update_proctor_label(self.admin_user, {
            "session_id": self.session_id,
            "label": "MANUAL_CHEATING"
        })
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["label"], "MANUAL_CHEATING")

        with get_connection() as conn:
            row = conn.execute("SELECT ground_truth_label FROM telemetry_sessions WHERE session_id = ?", (self.session_id,)).fetchone()
            self.assertEqual(row["ground_truth_label"], "MANUAL_CHEATING")


if __name__ == "__main__":
    unittest.main()
