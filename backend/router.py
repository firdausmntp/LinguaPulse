"""HTTP entry point: SPA routes, account sessions, protected exam/admin APIs."""
import json
import logging
import random
from http.server import SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from .config import FRONTEND_DIR
from .database import get_connection
from .auth import login_user, register_user
from .sessions import session_user, create_session, logout_session
from .security import create_security_handshake
from .routes_admin import AdminRoutes
from .routes_exam import ExamRoutes
from questions.loader import get_structured_questions, public_bank
from .attempts import start_attempt, resume_attempt
from .user_store import save_user, delete_user
from .workspace_reads import (
    admin_overview, practice_question, check_practice_answer,
    sample_question, check_sample_answer,
)
from .result_review import enrich_saved_review
from .survey import submit_respondent_survey, get_respondent_survey

PAGE_ROUTES = {'/', '/login', '/register', '/dashboard', '/exam', '/exam/session',
               '/results', '/history', '/admin', '/admin/overview', '/admin/proctor',
               '/admin/questions', '/admin/users', '/privacy', '/terms', '/practice'}
ADMIN_PATHS = {'/api/admin/users', '/api/admin/questions', '/api/proctor/sessions', '/api/export/csv', '/api/admin/questions/export', '/api/admin/overview'}


class TOEFLPlatformRouter(AdminRoutes, ExamRoutes, SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def _read_json(self):
        length = int(self.headers.get('Content-Length', 0))
        if not 0 < length <= (12_000_000 if urlparse(self.path).path == '/api/admin/audio' else 2_000_000):
            raise ValueError('Ukuran permintaan tidak valid.')
        payload = json.loads(self.rfile.read(length).decode('utf-8'))
        if not isinstance(payload, dict):
            raise ValueError('Permintaan harus berupa objek JSON.')
        return payload

    def _send_json(self, data, status=200, cookie=None):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(body)

    def _authorize(self, admin=False):
        user = session_user(self)
        if not user:
            self._send_json({'error': 'Sesi berakhir. Silakan masuk kembali.'}, 401)
        elif admin and user['role'] != 'admin':
            self._send_json({'error': 'Halaman ini hanya untuk pengawas.'}, 403)
            return None
        return user

    def do_HEAD(self):
        path = urlparse(self.path).path.rstrip('/') or '/'
        if path in PAGE_ROUTES or path.startswith('/admin/'):
            self.path = '/index.html'
        else:
            target = (FRONTEND_DIR / path.lstrip('/')).resolve()
            if target.is_relative_to(FRONTEND_DIR.resolve()) and not target.is_file() and not path.startswith(('/api/', '/pages/', '/js/', '/css/', '/media/', '/assets/')):
                return self._send_app_not_found()
        return super().do_HEAD()

    def do_GET(self):
        try:
            return self._get()
        except Exception:
            logging.exception('GET failed')
            return self._send_json({'error': 'Data belum dapat dimuat. Coba kembali.'}, 500)

    def _get(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'
        if path in PAGE_ROUTES or path.startswith('/admin/'):
            self.path = '/index.html'
            return super().do_GET()
        if path == '/api/sample-question':
            excluded = parse_qs(parsed.query).get('exclude', [''])[0]
            return self._send_json(sample_question(excluded))
        if path == '/api/auth/me':
            return self._send_json({'user': session_user(self)})
        if path in ADMIN_PATHS:
            if not self._authorize(admin=True):
                return
            if path == '/api/admin/overview':
                return self._send_json(admin_overview())
            return self.admin_get(parsed)
        if path == '/api/practice/question':
            user = self._authorize()
            if not user:
                return
            if user['role'] == 'admin':
                return self._send_json({'error': 'Gunakan akun peserta untuk latihan bebas.'}, 403)
            query = parse_qs(parsed.query)
            try:
                return self._send_json(practice_question(query.get('section', ['grammar'])[0], query.get('exclude', [''])[0]))
            except ValueError as error:
                return self._send_json({'error': str(error)}, 400)
        if path == '/api/survey':
            user = self._authorize()
            if not user:
                return
            sid = parse_qs(parsed.query).get('session_id', [''])[0]
            return self._send_json(get_respondent_survey(user, sid))
        if path in {'/api/questions', '/api/security/handshake', '/api/history', '/api/results', '/api/exam/resume'}:
            user = self._authorize()
            if not user:
                return
            if path == '/api/security/handshake':
                return self._send_json(create_security_handshake())
            if path == '/api/questions':
                is_admin = user['role'] == 'admin'
                bank = get_structured_questions(include_inactive=is_admin)
                return self._send_json(public_bank(bank, include_list=is_admin))
            if path == '/api/exam/resume':
                try:
                    return self._send_json(resume_attempt(user, parse_qs(parsed.query).get('id', [''])[0]))
                except ValueError as error:
                    return self._send_json({'error': str(error)}, 404)
            if path == '/api/results':
                sid = parse_qs(parsed.query).get('id', [''])[0]
                with get_connection() as conn:
                    result = conn.execute('SELECT result_json FROM submission_results JOIN exam_submissions USING (session_id) WHERE session_id = ? AND participant_code = ?', (sid, user['participant_code'])).fetchone()
                if result:
                    data = json.loads(result['result_json'])
                    data.pop('telemetry_evaluation', None)
                    data.pop('security_verification', None)
                    data['participant_code'] = user['participant_code']
                    return self._send_json(enrich_saved_review(data, sid, user))
                row = next((r for r in self._history(user) if r['session_id'] == sid), None)
                if row:
                    row['rewrite_done'] = row['rewrite_count']
                    return self._send_json({'session_id': sid, 'toefl_practice_result': row})
                return self._send_json({'error': 'Hasil sesi tidak ditemukan pada akun Anda.'}, 404)
            return self._send_json({'submissions': self._history(user)})
        if path.startswith('/api/'):
            return self._send_json({'error': 'Endpoint tidak ditemukan.'}, 404)
        if path.startswith('/pages/') and path not in {'/pages/landing.html', '/pages/auth.html', '/pages/privacy.html', '/pages/terms.html'}:
            if not self._authorize(admin=path == '/pages/admin.html'):
                return
        if path.endswith('/') or not (FRONTEND_DIR / path.lstrip('/')).resolve().is_relative_to(FRONTEND_DIR.resolve()):
            self.send_error(404)
            return
        target = (FRONTEND_DIR / path.lstrip('/')).resolve()
        if not target.is_file() and not path.startswith(('/pages/', '/js/', '/css/', '/media/', '/assets/')):
            return self._send_app_not_found()
        return super().do_GET()

    def end_headers(self):
        if not self.path.startswith('/media/'):
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
        super().end_headers()


    def _send_app_not_found(self):
        body = (FRONTEND_DIR / 'index.html').read_bytes()
        self.send_response(404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def _history(self, user):
        with get_connection() as conn:
            rows = conn.execute("""SELECT session_id, grammar_mc_correct, grammar_mc_total,
                reading_mc_correct, reading_mc_total, listening_mc_correct, listening_mc_total, rewrite_count, essay_word_count, submitted_at
                FROM exam_submissions WHERE participant_code = ? ORDER BY submitted_at DESC, rowid DESC""",
                (user['participant_code'],)).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            total = item['grammar_mc_total'] + item['reading_mc_total'] + item['listening_mc_total']
            item['accuracy_percent'] = round((item['grammar_mc_correct'] + item['reading_mc_correct'] + item['listening_mc_correct']) / max(1, total) * 100)
            output.append(item)
        return output

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            origin = self.headers.get('Origin')
            if origin and urlparse(origin).netloc != self.headers.get('Host'):
                if length > 0:
                    self.rfile.read(min(length, 2_000_000))
                return self._send_json({'error': 'Asal permintaan tidak diizinkan.'}, 403)
            if 'application/json' not in self.headers.get('Content-Type', ''):
                if length > 0:
                    self.rfile.read(min(length, 2_000_000))
                return self._send_json({'error': 'Gunakan application/json.'}, 415)
            return self._post(urlparse(self.path), self._read_json())
        except (ValueError, TypeError, KeyError):
            return self._send_json({'error': 'Data permintaan tidak valid.'}, 400)
        except Exception:
            logging.exception('POST failed')
            return self._send_json({'error': 'Permintaan belum dapat diproses. Coba kembali.'}, 500)

    def _post(self, parsed, payload):
        if parsed.path == '/api/sample-question':
            try:
                return self._send_json(check_sample_answer(payload))
            except ValueError as error:
                return self._send_json({'error': str(error)}, 400)
        if parsed.path == '/api/practice/question':
            user = self._authorize()
            if not user:
                return
            if user['role'] == 'admin':
                return self._send_json({'error': 'Gunakan akun peserta untuk latihan bebas.'}, 403)
            try:
                return self._send_json(check_practice_answer(payload))
            except ValueError as error:
                return self._send_json({'error': str(error)}, 400)
        if parsed.path in {'/api/auth/login', '/api/auth/register'}:
            if parsed.path.endswith('login'):
                result = login_user(payload.get('identifier', ''), payload.get('password', ''))
            else:
                if payload.get('terms_accepted') is not True:
                    return self._send_json({'error': 'Setujui syarat dan ketentuan untuk membuat akun.'}, 400)
                result = register_user(payload.get('username', ''), payload.get('email', ''),
                                       payload.get('password', ''), payload.get('display_name', ''))
            if 'user' not in result:
                return self._send_json(result, 400 if parsed.path.endswith('register') else 401)
            return self._send_json(result, cookie=create_session(self, result['user']))
        if parsed.path == '/api/auth/logout':
            return self._send_json({'status': 'ok'}, cookie=logout_session(self))
        if parsed.path == '/api/admin/users':
            actor = self._authorize(admin=True)
            if not actor:
                return
            try:
                return self._send_json(save_user(payload, actor))
            except ValueError as error:
                return self._send_json({'error': str(error)}, 400)
        if parsed.path in {'/api/admin/questions', '/api/admin/questions/import', '/api/admin/audio', '/api/proctor/label'}:
            if not self._authorize(admin=True):
                return
            return self.admin_post(parsed, payload)
        if parsed.path == '/api/survey':
            user = self._authorize()
            if not user:
                return
            try:
                return self._send_json(submit_respondent_survey(user, payload))
            except ValueError as error:
                return self._send_json({'error': str(error)}, 400)
        if parsed.path == '/api/exam/start':
            user = self._authorize()
            if not user:
                return
            if user['role'] == 'admin':
                return self._send_json({'error': 'Gunakan akun peserta untuk mengerjakan ujian.'}, 403)
            try:
                return self._send_json(start_attempt(user, payload))
            except ValueError as error:
                return self._send_json({'error': str(error)}, 400)
        if parsed.path == '/api/submit':
            user = self._authorize()
            if not user:
                return
            if user['role'] == 'admin':
                return self._send_json({'error': 'Akun admin hanya untuk pengelolaan dan pengawasan.'}, 403)
            return self.submit_exam(payload, user)
        return self._send_json({'error': 'Endpoint tidak ditemukan.'}, 404)

    def do_DELETE(self):
        origin = self.headers.get('Origin')
        if origin and urlparse(origin).netloc != self.headers.get('Host'):
            return self._send_json({'error': 'Asal permintaan tidak diizinkan.'}, 403)
        actor = self._authorize(admin=True)
        if not actor:
            return
        if urlparse(self.path).path == '/api/admin/users':
            try:
                user_id = int(parse_qs(urlparse(self.path).query).get('id', [''])[0])
                return self._send_json(delete_user(user_id, actor))
            except ValueError as error:
                return self._send_json({'error': str(error)}, 400)
        return self.admin_delete()
