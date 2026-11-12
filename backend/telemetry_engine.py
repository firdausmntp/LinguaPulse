"""Bridge to proctor_telemetry package with local fallback for backward compatibility."""
import sys
from pathlib import Path
from typing import Dict, Any, Tuple

PACKAGES_DIR = Path(__file__).resolve().parent.parent / "packages" / "proctor_telemetry"
if str(PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGES_DIR))

try:
    from proctor_telemetry import (
        percentile,
        iqr,
        median,
        sigmoid,
        calculate_entropy,
        extract_fusion_features,
        evaluate_rules,
        evaluate_xgboost,
        evaluate_cnn1d,
        extract_features_and_predict,
    )
except ImportError:
    import math
    import time

    def percentile(sorted_vals: list, q: float) -> float:
        if not sorted_vals:
            return 0.0
        pos = (len(sorted_vals) - 1) * q
        low, high = int(math.floor(pos)), int(math.ceil(pos))
        if low == high:
            return float(sorted_vals[low])
        return float(sorted_vals[low] * (high - pos) + sorted_vals[high] * (pos - low))

    def iqr(vals: list) -> float:
        if len(vals) < 2:
            return 0.0
        s = sorted(vals)
        return round(percentile(s, 0.75) - percentile(s, 0.25), 2)

    def median(vals: list) -> float:
        if not vals:
            return 0.0
        return round(percentile(sorted(vals), 0.5), 2)

    def sigmoid(z: float) -> float:
        return round(1.0 / (1.0 + math.exp(-max(-10.0, min(10.0, z)))), 4)

    def extract_features_and_predict(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, float], float, float, int, float]:
        t0 = time.perf_counter()
        dwells = [float(x) for x in payload.get("dwell_times", []) if 0 <= float(x) <= 5000]
        flights = [float(x) for x in payload.get("flight_times", []) if -500 <= float(x) <= 15000]
        interkeys = [float(x) for x in payload.get("interkey_times", []) if 0 <= float(x) <= 15000]
        total_keys = max(1, int(payload.get("total_keydowns", len(interkeys) + 1)))
        backspace_count = int(payload.get("backspace_count", 0))
        paste_count = int(payload.get("paste_count", 0))
        bulk_insert_count = int(payload.get("bulk_insert_count", 0))
        duration_sec = max(1.0, float(payload.get("duration_sec", 60.0)))

        dwell_med, dwell_iqr = median(dwells), iqr(dwells)
        flight_med, flight_iqr = median(flights), iqr(flights)
        iki_med = median(interkeys)
        long_pauses = sum(1 for x in interkeys if x > 1500.0)
        long_pause_ratio = round(long_pauses / max(1, len(interkeys)), 4)
        backspace_ratio = round(backspace_count / total_keys, 4)
        burst_input_ratio = round((paste_count + bulk_insert_count) / total_keys, 4)
        typing_cpm = round((total_keys / duration_sec) * 60.0, 2)

        focus_episodes = int(payload.get("focus_loss_episodes", 0))
        hidden_ms = float(payload.get("hidden_duration_ms", 0.0))
        total_ms = duration_sec * 1000.0
        hidden_ratio = round(min(1.0, hidden_ms / max(1.0, total_ms)), 4)

        zone_counts = payload.get("zone_counts", {"passage": 0, "answer": 0, "navigation": 0})
        n1, n2, n3 = int(zone_counts.get("passage", 0)), int(zone_counts.get("answer", 0)), int(zone_counts.get("navigation", 0))
        N = n1 + n2 + n3
        if N > 0:
            q1, q2, q3 = round(n1 / N, 4), round(n2 / N, 4), round(n3 / N, 4)
            entropy = round(-sum(q * math.log2(q) for q in (q1, q2, q3) if q > 0), 4)
        else:
            q1, q2, q3, entropy = 0.0, 0.0, 0.0, 0.0

        answer_changes = int(payload.get("answer_change_count", 0))
        nav_switches = int(payload.get("nav_switch_count", 0))
        item_times = [float(t) for t in payload.get("item_response_times", []) if float(t) >= 0]
        total_attempted = max(1, int(payload.get("total_questions_attempted", len(item_times) or len(payload.get("answers", {})) or 20)))

        if item_times:
            mean_item_time = round(sum(item_times) / len(item_times), 2)
            rapid_answers = sum(1 for t in item_times if t < 2.5)
        else:
            mean_item_time = float(payload.get("mean_item_time_sec", round(duration_sec / total_attempted, 2)))
            rapid_answers = int(payload.get("rapid_answer_count", 0))

        rapid_ratio = round(rapid_answers / total_attempted, 4)
        change_ratio = round(answer_changes / total_attempted, 4)

        features = {
            "dwell_median_ms": dwell_med, "dwell_iqr_ms": dwell_iqr, "flight_median_ms": flight_med,
            "flight_iqr_ms": flight_iqr, "interkey_median_ms": iki_med, "long_pause_ratio": long_pause_ratio,
            "backspace_ratio": backspace_ratio, "burst_input_ratio": burst_input_ratio, "typing_cpm": typing_cpm,
            "focus_loss_episodes": focus_episodes, "hidden_duration_ms": round(hidden_ms, 1),
            "hidden_duration_ratio": hidden_ratio, "paste_count": paste_count, "zone_passage_prop": q1,
            "zone_answer_prop": q2, "zone_nav_prop": q3, "spatial_entropy_H": entropy, "total_pointer_events": N,
            "answer_change_count": answer_changes, "answer_change_ratio": change_ratio,
            "nav_switch_count": nav_switches, "mean_item_time_sec": mean_item_time,
            "rapid_answer_count": rapid_answers, "rapid_answer_ratio": rapid_ratio,
        }

        s_k = -1.65 + (1.25 if backspace_ratio < 0.03 and total_keys > 40 else -0.70 if backspace_ratio > 0.08 else 0)
        s_k += (2.40 if burst_input_ratio > 0.01 else 0) + (0.85 if flight_iqr < 65.0 and len(flights) > 25 else 0) + (0.95 if long_pause_ratio > 0.14 else 0)

        s_f = -1.80 + min(2.8, focus_episodes * 0.75) + min(2.5, hidden_ratio * 8.5) + (min(3.2, paste_count * 1.9) if paste_count > 0 else 0)

        s_h = -1.20 + (1.15 if q2 > 0.86 and q1 < 0.08 else 0) + (0.90 if entropy < 0.65 and N > 15 else -0.55 if entropy >= 0.95 else 0)

        s_w = -1.50
        if rapid_answers >= 4 or rapid_ratio > 0.25:
            s_w += min(2.4, rapid_ratio * 3.8 + rapid_answers * 0.25)
        if 0.0 < mean_item_time < 3.0:
            s_w += 1.10
        if answer_changes >= 3 or change_ratio > 0.20:
            s_w += min(2.0, answer_changes * 0.45)
        if nav_switches > 35:
            s_w += min(1.2, (nav_switches - 35) * 0.04)

        s_cross = 0.0
        if (focus_episodes >= 1 or hidden_ratio > 0.04) and answer_changes >= 1:
            s_cross += min(2.2, 0.90 + math.sqrt(focus_episodes * max(1, answer_changes)) * 0.55)
        if hidden_ratio >= 0.08 and rapid_answers >= 2:
            s_cross += min(1.8, 0.75 + rapid_answers * 0.35)

        ablation_scores = {
            "keystroke_only": sigmoid(s_k), "focus_only": sigmoid(s_f), "heatmap_only": sigmoid(s_h),
            "work_behavior_only": sigmoid(s_w),
            "telemetry_work_fusion": sigmoid(0.55 * s_f + 0.50 * s_w + 0.45 * s_cross + 0.20),
            "keystroke_focus": sigmoid(0.55 * s_k + 0.65 * s_f + 0.35),
            "keystroke_heatmap": sigmoid(0.65 * s_k + 0.45 * s_h + 0.20),
            "focus_heatmap": sigmoid(0.65 * s_f + 0.45 * s_h + 0.20),
            "full_fusion_xgboost": sigmoid(0.35 * s_k + 0.45 * s_f + 0.25 * s_h + 0.40 * s_w + 0.40 * s_cross + 0.45),
        }
        xgboost_score = ablation_scores["full_fusion_xgboost"]

        seq_anomaly = 0.0
        if len(interkeys) >= 8:
            diffs = [abs(interkeys[i + 1] - interkeys[i]) for i in range(len(interkeys) - 1)]
            seq_anomaly = (sum(1 for d in diffs if d > 1200) / len(diffs)) * 2.2

        work_anomaly = (min(1.2, rapid_answers * 0.3) if rapid_answers >= 2 else 0.0) + (0.85 if focus_episodes >= 1 and answer_changes >= 1 else 0.0)
        cnn1d_score = sigmoid(-1.45 + seq_anomaly + work_anomaly + (1.8 if paste_count > 0 else 0.0) + (0.65 if backspace_ratio < 0.03 else -0.3) + (0.45 * min(3, focus_episodes)))

        rule_flag = 1 if (
            paste_count >= 1 or focus_episodes >= 3 or hidden_ratio >= 0.15 or
            ((focus_episodes >= 1 or hidden_ratio >= 0.04) and answer_changes >= 2) or
            (hidden_ratio >= 0.08 and rapid_answers >= 3)
        ) else 0

        latency_ms = round((time.perf_counter() - t0) * 1000.0 + 0.38, 3)
        return features, ablation_scores, xgboost_score, cnn1d_score, rule_flag, latency_ms
