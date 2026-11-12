from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "toefl_platform.db"

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

