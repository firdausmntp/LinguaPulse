import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database import init_schema, get_connection
from backend.seed_data import seed_all


def run_summary():
    init_schema()
    seed_all()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM telemetry_sessions ORDER BY session_id ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    print(f"=== RINGKASAN DATASET TELEMETRI TOEFL ({len(rows)} Sesi) ===")
    for r in rows:
        print(
            f"[{r['session_id']}] {r['participant_code']} | {r['device_profile']:14s} | "
            f"{r['task_condition']:13s} | XGBoost={r['xgboost_score']:.3f} | "
            f"1D-CNN={r['cnn1d_score']:.3f} | Rule={r['rule_flag']}"
        )


if __name__ == "__main__":
    run_summary()

