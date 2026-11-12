import csv
import io
import json
from urllib.parse import urlparse, parse_qs
from .database import get_connection
from .auth import format_user_row
from .question_store import get_question_detail, save_question, import_questions, export_questions, delete_question
from .audio_upload import upload_audio
from .survey import update_proctor_label


class AdminRoutes:
    def admin_get(self, parsed):
        if parsed.path == "/api/admin/questions":
            question_id = parse_qs(parsed.query).get("id", [""])[0]
            try:
                return self._send_json(get_question_detail(question_id))
            except ValueError as error:
                return self._send_json({"error": str(error)}, 404)
        if parsed.path == "/api/admin/questions/export":
            return self._send_json(export_questions())
        if parsed.path == "/api/admin/users":
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users ORDER BY user_id DESC")
            users = [format_user_row(r) for r in cur.fetchall()]
            conn.close()
            return self._send_json({"users": users})

        if parsed.path == "/api/proctor/sessions":
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""SELECT t.*, u.display_name,
                s.tab_switched AS survey_tab_switched,
                s.copied_pasted AS survey_copied_pasted,
                s.external_resources AS survey_external_resources,
                s.honest_label AS survey_label,
                s.feedback_note AS survey_note,
                s.submitted_at AS survey_submitted_at
                FROM telemetry_sessions t
                LEFT JOIN users u ON u.participant_code=t.participant_code
                LEFT JOIN respondent_surveys s ON s.session_id=t.session_id
                ORDER BY t.created_at DESC, t.session_id DESC""")
            sessions = []
            for r in cur.fetchall():
                d = dict(r)
                d["features"] = json.loads(d.pop("features_json"))
                d["ablation"] = json.loads(d.pop("ablation_json"))
                d["heatmap_points"] = json.loads(d.pop("heatmap_points_json") or "[]")
                d["timeline_events"] = json.loads(d.pop("timeline_events_json") or "[]")
                sessions.append(d)
            conn.close()
            return self._send_json({"sessions": sessions})

        if parsed.path == "/api/export/csv":
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""SELECT t.*,
                s.tab_switched AS survey_tab_switched,
                s.copied_pasted AS survey_copied_pasted,
                s.honest_label AS survey_label
                FROM telemetry_sessions t
                LEFT JOIN respondent_surveys s ON s.session_id=t.session_id
                ORDER BY t.session_id ASC""")
            all_rows = cur.fetchall()
            conn.close()

            output = io.StringIO()
            fieldnames = [
                "session_id", "participant_code", "device_profile", "task_condition",
                "ground_truth_label", "survey_tab_switched", "survey_copied_pasted",
                "xgboost_score", "cnn1d_score", "rule_flag", "inference_latency_ms",
                "answer_change_count", "answer_change_ratio", "nav_switch_count",
                "mean_item_time_sec", "rapid_answer_count", "rapid_answer_ratio",
                "dwell_median_ms", "dwell_iqr_ms", "flight_median_ms", "flight_iqr_ms",
                "interkey_median_ms", "long_pause_ratio", "backspace_ratio", "burst_input_ratio",
                "typing_cpm", "focus_loss_episodes", "hidden_duration_ms", "hidden_duration_ratio",
                "paste_count", "zone_passage_prop", "zone_answer_prop", "zone_nav_prop", "spatial_entropy_H"
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for r in all_rows:
                feats = json.loads(r["features_json"])
                row_dict = {
                    "session_id": r["session_id"],
                    "participant_code": r["participant_code"],
                    "device_profile": r["device_profile"],
                    "task_condition": r["task_condition"],
                    "ground_truth_label": r["ground_truth_label"] if "ground_truth_label" in r.keys() else "UNLABELED",
                    "survey_tab_switched": r["survey_tab_switched"] if r["survey_tab_switched"] is not None else "",
                    "survey_copied_pasted": r["survey_copied_pasted"] if r["survey_copied_pasted"] is not None else "",
                    "xgboost_score": r["xgboost_score"],
                    "cnn1d_score": r["cnn1d_score"],
                    "rule_flag": r["rule_flag"],
                    "inference_latency_ms": r["inference_latency_ms"],
                }
                for k in fieldnames[11:]:
                    row_dict[k] = feats.get(k, 0)
                writer.writerow(row_dict)

            csv_bytes = output.getvalue().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="dataset_telemetri_toefl.csv"')
            self.send_header("Content-Length", str(len(csv_bytes)))
            self.end_headers()
            self.wfile.write(csv_bytes)
            return

        return self._send_json({"error": "Endpoint tidak ditemukan."}, 404)

    def admin_post(self, parsed, payload):
        if parsed.path == '/api/proctor/label':
            actor = self._authorize(admin=True)
            if not actor:
                return
            try:
                return self._send_json(update_proctor_label(actor, payload))
            except ValueError as error:
                return self._send_json({'error': str(error)}, 400)

        handlers = {
            '/api/admin/questions': save_question,
            '/api/admin/questions/import': import_questions,
            '/api/admin/audio': upload_audio,
        }
        if parsed.path not in handlers:
            return self._send_json({'error': 'Endpoint tidak ditemukan.'}, 404)
        try:
            return self._send_json(handlers[parsed.path](payload))
        except ValueError as error:
            return self._send_json({'error': str(error)}, 400)

    def admin_delete(self):
        parsed = urlparse(self.path)
        if parsed.path != '/api/admin/questions':
            return self._send_json({'error': 'Endpoint tidak ditemukan.'}, 404)
        question_id = parse_qs(parsed.query).get('id', [''])[0]
        try:
            return self._send_json(delete_question(question_id))
        except ValueError as error:
            return self._send_json({'error': str(error)}, 400)
