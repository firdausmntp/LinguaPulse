import json
import random
import re
import time
from .database import get_connection
from .attempts import get_attempt
from .telemetry_engine import extract_features_and_predict
from .security import decrypt_and_verify_payload, verify_cf_challenge
from .ai_tutor import generate_ai_tutor_explanation
from questions.loader import get_structured_questions
from .result_review import build_section_reviews


class ExamRoutes:
    def submit_exam(self, payload, user):
        raw_envelope = payload
        cf_check = verify_cf_challenge(
            raw_envelope.get("cf_turnstile_token", ""),
            self.client_address[0] if self.client_address else "127.0.0.1"
        )
        if not cf_check.get("verified"):
            return self._send_json({"error": "Verifikasi anti-bot Cloudflare Challenge gagal."}, 403)

        try:
            payload, security_meta = decrypt_and_verify_payload(raw_envelope)
        except Exception as exc:
            return self._send_json({"error": f"Dekripsi/verifikasi paket telemetri gagal: {exc}"}, 400)

        if not payload.get('consent_agreed'):
            return self._send_json({'error': 'Persetujuan sesi diperlukan.'}, 400)
        answers = payload.get('answers')
        if not isinstance(answers, dict) or any(not isinstance(v, (str, int)) for v in answers.values()):
            return self._send_json({'error': 'Format jawaban tidak valid.'}, 400)
        if payload.get('device_profile') not in {'PC_PHYSICAL', 'MOBILE_VIRTUAL'} or payload.get('task_condition') not in {'MANDIRI', 'COPY_TYPING', 'AI_PARAPHRASE'}:
            return self._send_json({'error': 'Pengaturan sesi tidak valid.'}, 400)
        p_code = user["participant_code"]
        d_name = user["display_name"]
        dev_prof = payload.get("device_profile", "PC_PHYSICAL")
        cond = payload.get("task_condition", "MANDIRI")
        attempt = payload.get('attempt_id', '')
        if not re.fullmatch(r'[a-f0-9-]{36}', attempt):
            return self._send_json({'error': 'Identitas sesi tidak valid.'}, 400)
        sid = 'SES-' + attempt
        with get_connection() as check:
            existing = check.execute('SELECT participant_code FROM exam_submissions WHERE session_id = ?', (sid,)).fetchone()
        if existing:
            if existing['participant_code'] != p_code:
                return self._send_json({'error': 'Sesi tidak valid.'}, 403)
            return self._send_json({'status': 'ok', 'session_id': sid, 'already_submitted': True})
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        attempt_row = get_attempt(user, attempt)
        if not attempt_row:
            return self._send_json({'error': 'Sesi tidak ditemukan. Mulai ujian dari halaman persiapan.'}, 400)
        payload['device_profile'] = dev_prof = attempt_row['device_profile']
        payload['task_condition'] = cond = attempt_row['task_condition']
        feats, abl, xgb_s, cnn_s, rule_f, lat = extract_features_and_predict(payload)

        q_bank = json.loads(attempt_row['bank_json'])
        ans = payload.get("answers", {})

        g_correct = 0
        g_feedback = []
        for q in q_bank["grammar_mc"]:
            user_choice = ans.get(q["id"])
            is_right = str(user_choice) == str(q["answer"])
            if is_right:
                g_correct += 1
            g_feedback.append({
                "id": q["id"],
                "title": q["title"],
                "is_correct": is_right,
                "explanation": q["explanation"]
            })

        l_questions = q_bank.get('listening', {}).get('questions', [])
        l_correct = sum(str(ans.get(item['id'])) == str(item['answer']) for item in l_questions)
        r_correct = 0
        for q in q_bank["reading"]["questions"]:
            if str(ans.get(q["id"])) == str(q["answer"]):
                r_correct += 1

        rewrite_done = sum(1 for item in q_bank["grammar_rewrite"] if str(ans.get(item["id"]) or "").strip())
        essay_text = str(ans.get(q_bank["writing"]["id"]) or ans.get("W1") or "").strip()
        essay_wc = len(essay_text.split()) if essay_text else 0

        accuracy_percent = round((l_correct + g_correct + r_correct) / max(1, len(l_questions) + len(q_bank['grammar_mc']) + len(q_bank['reading']['questions'])) * 100)
        # Historical schema column retained; no unofficial TOEFL score is generated.
        est_toefl = 0

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO exam_submissions
            (session_id, participant_code, display_name, grammar_mc_correct, grammar_mc_total,
             reading_mc_correct, reading_mc_total, rewrite_count, essay_word_count,
             estimated_toefl_score, xp_earned, answers_json, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sid, p_code, d_name, g_correct, len(q_bank["grammar_mc"]),
            r_correct, len(q_bank["reading"]["questions"]), rewrite_done, essay_wc,
            est_toefl, 0, json.dumps(ans, ensure_ascii=False), now_str
        ))

        cur.execute("""
            INSERT INTO telemetry_sessions
            (session_id, participant_code, device_profile, task_condition, duration_sec,
             features_json, ablation_json, xgboost_score, cnn1d_score, rule_flag,
             inference_latency_ms, heatmap_points_json, timeline_events_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sid, p_code, dev_prof, cond, float(payload.get("duration_sec", 0)),
            json.dumps(feats), json.dumps(abl), xgb_s, cnn_s, rule_f,
            lat, json.dumps(payload.get("heatmap_points", [])[:250]),
            json.dumps(payload.get("timeline_events", [])[:80]), now_str
        ))
        cur.execute('UPDATE exam_submissions SET listening_mc_correct = ?, listening_mc_total = ? WHERE session_id = ?',
                    (l_correct, len(l_questions), sid))
        conn.commit()
        conn.close()


        rewrite_map = {
            item["id"]: (ans.get(item["id"]) or "")
            for item in q_bank["grammar_rewrite"]
        }
        ai_explanation = generate_ai_tutor_explanation({
            "grammar_feedback": g_feedback,
            "essay_text": essay_text,
            "rewrite_answers": rewrite_map,
            "accuracy_percent": accuracy_percent,
        })

        result = {
            "status": "ok",
            "session_id": sid,
            "submitted_at": now_str,
            "participant_code": p_code,
            "security_verification": {
                **security_meta,
                "cf_challenge_mode": cf_check.get("mode", "VERIFIED"),
            },
            "ai_tutor_explanation": ai_explanation,
            "toefl_practice_result": {
                "accuracy_percent": accuracy_percent,
                "listening_mc_correct": l_correct,
                "listening_mc_total": len(l_questions),
                "grammar_mc_correct": g_correct,
                "grammar_mc_total": len(q_bank["grammar_mc"]),
                "reading_mc_correct": r_correct,
                "reading_mc_total": len(q_bank["reading"]["questions"]),
                "rewrite_done": rewrite_done,
                "essay_word_count": essay_wc,
                "grammar_feedback": g_feedback,
                "section_reviews": build_section_reviews(q_bank, ans)
            },
            "telemetry_evaluation": {
                "xgboost_score": xgb_s,
                "cnn1d_score": cnn_s,
                "rule_flag": rule_f,
                "inference_latency_ms": lat,
                "ablation": abl,
                "features": feats
            }
        }
        with get_connection() as conn:
            conn.execute('UPDATE users SET consent_agreed = 1 WHERE user_id = ?', (user['user_id'],))
            conn.execute('INSERT OR REPLACE INTO submission_results VALUES (?, ?)',
                         (sid, json.dumps(result, ensure_ascii=False)))
        public_result = {k: v for k, v in result.items() if k not in {'telemetry_evaluation', 'security_verification'}}
        return self._send_json(public_result)


