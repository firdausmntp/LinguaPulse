import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env", override=False)
FRONTEND_DIR = ROOT_DIR / "frontend"
DATA_DIR = ROOT_DIR / "data"
MYSQL_HOST = os.environ.get('TOEFL_MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = int(os.environ.get('TOEFL_MYSQL_PORT', '3306'))
MYSQL_DATABASE = os.environ.get('TOEFL_MYSQL_DATABASE', 'linguapulse')
MYSQL_USER = os.environ.get('TOEFL_MYSQL_USER', 'linguapulse_app')
MYSQL_PASSWORD = os.environ.get('TOEFL_MYSQL_PASSWORD', '')
MYSQL_CONNECT_TIMEOUT = int(os.environ.get('TOEFL_MYSQL_CONNECT_TIMEOUT', '10'))
MYSQL_SSL_CA = os.environ.get('TOEFL_MYSQL_SSL_CA', '')

SERVER_HOST = os.environ.get("TOEFL_SERVER_HOST", "127.0.0.1")
SERVER_PORT = 8878

