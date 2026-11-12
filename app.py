from http.server import ThreadingHTTPServer
from backend.config import SERVER_HOST, SERVER_PORT
from backend.database import init_schema
from backend.seed_data import seed_all
from backend.router import TOEFLPlatformRouter


def main():
    init_schema()
    seed_all()
    server = ThreadingHTTPServer((SERVER_HOST, SERVER_PORT), TOEFLPlatformRouter)
    print(f"============================================================")
    print(f" LinguaPulse TOEFL EPT Berjalan!")
    print(f" URL Akses  : http://localhost:{SERVER_PORT}")
    print(f" Akun Admin : admin / admin123")
    print(f" Akun Siswa : nadia_putri / student123")
    print(f"============================================================")
    server.serve_forever()


if __name__ == "__main__":
    main()

