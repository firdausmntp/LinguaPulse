"""End-to-end checks against a temporary database and temporary question files."""
import json
import sys
import tempfile
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import build_opener, ProxyHandler, HTTPCookieProcessor, Request
from urllib.error import HTTPError
from http.cookiejar import CookieJar

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend import config
from playwright.sync_api import sync_playwright, expect


def run():
    with tempfile.TemporaryDirectory(prefix='linguapulse-test-') as tmp:
        config.DATA_DIR = Path(tmp)
        config.DB_PATH = Path(tmp) / 'test.db'
        from backend.database import init_schema, get_connection
        from backend.seed_data import seed_all
        from backend.router import TOEFLPlatformRouter
        import questions.loader as loader
        loader.SECTION_FILES = {key: Path(tmp) / path.name for key, path in loader.SECTION_FILES.items()}
        import backend.audio_upload as audio_upload
        audio_upload.MEDIA_DIR = Path(tmp) / 'uploads'
        init_schema()
        seed_all()
        class QuietRouter(TOEFLPlatformRouter):
            def log_message(self, *_args):
                pass
            def translate_path(self, path):
                from urllib.parse import urlparse
                route = urlparse(path).path
                if route.startswith('/media/uploads/'):
                    return str(audio_upload.MEDIA_DIR / Path(route).name)
                return super().translate_path(path)
        server = ThreadingHTTPServer(('127.0.0.1', 0), QuietRouter)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        origin = f'http://127.0.0.1:{server.server_port}'
        from finish_checks import check_branded_404, check_finished_browser
        check_branded_404(origin)
        client = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()))

        def request(path, payload=None, method=None, headers=None, opener=client):
            data = None if payload is None else json.dumps(payload).encode()
            req = Request(origin + path, data=data, method=method,
                          headers={'Content-Type': 'application/json', **(headers or {})})
            try:
                response = opener.open(req, timeout=10)
                body = response.read()
                return response.status, json.loads(body) if response.headers.get_content_type() == 'application/json' else body.decode()
            except HTTPError as error:
                return error.code, json.loads(error.read())

        for path in ('/', '/login', '/register', '/exam', '/exam/session', '/dashboard', '/results', '/history', '/admin', '/privacy'):
            assert request(path)[0] == 200, path
        for path in ('/api/admin/users', '/api/proctor/sessions', '/api/export/csv', '/api/questions', '/pages/admin.html'):
            assert request(path)[0] == 401, path
        assert request('/api/auth/register', {'username': 'x', 'password': 'short'})[0] == 400
        assert request('/api/auth/register', {'username': 'valid_user', 'email': 'valid@example.test', 'password': 'validpassword', 'display_name': 'Valid User'})[0] == 400
        assert request('/api/auth/login', {'identifier': 'admin', 'password': 'bad'})[0] == 401
        assert request('/api/auth/login', {'identifier': 'admin', 'password': 'admin123'}, headers={'Origin': 'https://elsewhere.example'})[0] == 403
        status, account = request('/api/auth/register', {'username': 'smoke_user', 'email': 'smoke@example.test', 'password': 'validpassword123', 'display_name': '<script>alert(1)</script>', 'role': 'admin', 'terms_accepted': True})
        assert status == 200 and account['user']['role'] == 'student'
        assert not {'xp', 'badges', 'level_title', 'streak'} & set(account['user'])
        assert request('/api/admin/users')[0] == 403
        assert request('/api/questions')[1].get('all_questions') is None
        student_q = request('/api/questions')[1]['grammar_mc'][0]
        assert not ({'answer', 'correct_answer', 'explanation', 'folder_file'} & set(student_q))
        sample_q = request('/api/sample-question')[1]['question']
        assert sample_q and not ({'answer', 'correct_answer', 'explanation'} & set(sample_q))
        request('/api/auth/logout', {})
        assert request('/api/admin/users')[0] == 401
        assert request('/api/auth/login', {'identifier': 'admin', 'password': 'admin123'})[0] == 200
        assert request('/api/admin/users')[0] == 200
        admin_bank = request('/api/questions')[1]
        assert admin_bank.get('all_questions')
        for listed in admin_bank['all_questions']:
            assert not ({'answer', 'correct_answer', 'explanation', 'folder_file', 'sample_ai_reference'} & set(listed))
        question = {'question_id': 'TEST-Q', 'section': 'grammar', 'question_type': 'multiple_choice', 'title': 'Test', 'prompt': 'Choose one.', 'options': ['A', 'B'], 'correct_answer': '0'}
        assert request('/api/admin/questions', question)[0] == 200
        assert request('/api/admin/questions?id=TEST-Q', method='DELETE')[0] == 200
        assert request('/api/admin/questions', {**question, 'question_id': "invalid'id"})[0] == 400
        from ept_checks import check_ept_api, check_ept_browser
        check_ept_api(request, origin)
        from users_checks import check_user_api, check_user_browser
        check_user_api(request)
        from workspace_checks import check_workspace_api, check_workspace_browser, capture_overview
        check_workspace_api(request)
        print('PASS: HTTP routes, validation, session/logout, CSRF, admin authorization and CRUD', flush=True)

        artifacts = ROOT / 'docs' / 'qa'
        artifacts.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 900})
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('dialog', lambda dialog: dialog.accept())
            page.goto(origin)
            page.wait_for_load_state('networkidle')
            expect(page.locator('h1')).to_contain_text('Lebih siap EPT')
            assert page.locator('#viewExam').count() == 0
            assert page.locator('#authModal').count() == 0
            expect(page.locator('.sample-choice').first).to_be_visible()
            assert page.evaluate('sampleQuestion.answer === undefined && sampleQuestion.explanation === undefined')
            first_id = page.evaluate('sampleQuestion.id')
            exported_items = request('/api/admin/questions/export')[1]['questions']
            correct = int(next(q['correct_answer'] for q in exported_items if q['question_id'] == first_id))
            wrong = (correct + 1) % page.locator('.sample-choice').count()
            page.locator('.sample-choice').nth(wrong).click()
            expect(page.locator('.sample-choice.is-incorrect')).to_have_count(1)
            expect(page.locator('#sampleFeedback')).to_contain_text('Belum tepat')
            page.locator('.sample-choice').nth(correct).click()
            expect(page.locator('.sample-choice.is-correct')).to_have_count(1)
            expect(page.locator('.sample-choice.is-incorrect')).to_have_count(0)
            expect(page.locator('#sampleFeedback')).to_contain_text('Tepat')
            assert page.locator('#sampleRefresh').count() == 0
            page.reload()
            page.wait_for_load_state('networkidle')
            page.wait_for_function('previous => sampleQuestion && sampleQuestion.id !== previous', arg=first_id)
            assert page.locator('#sampleOptions button').count() >= 2
            page.evaluate('window.scrollTo(0, 0)')
            assert page.evaluate('telemetryState.totalKeydowns + telemetryState.focusLossEpisodes + telemetryState.heatmapPoints.length') == 0
            for width, height in [(1440, 900), (1280, 800), (1920, 1080), (375, 812), (320, 740)]:
                page.set_viewport_size({'width': width, 'height': height})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
                page.screenshot(path=str(artifacts / f'landing-{width}.png'), full_page=True)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(origin + '/exam/session')
            page.wait_for_url('**/login?next=*')
            expect(page.locator('#loginForm')).to_be_visible()
            expect(page.locator('.auth-home')).to_have_attribute('href', '/')
            page.screenshot(path=str(artifacts / 'login-desktop.png'), full_page=True)
            page.set_viewport_size({'width': 375, 'height': 812})
            page.screenshot(path=str(artifacts / 'login-mobile.png'), full_page=True)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.locator('#loginIdentifier').fill('nadia_putri')
            page.locator('#loginPassword').fill('bad')
            page.get_by_role('button', name='Masuk', exact=True).click()
            expect(page.locator('#authErrorMsg')).to_contain_text('salah')
            page.locator('#loginPassword').fill('student123')
            page.get_by_role('button', name='Masuk', exact=True).click()
            page.wait_for_url('**/exam')
            expect(page.locator('#beginExamButton')).to_be_visible()
            assert page.evaluate('examTimerId') is None
            assert page.evaluate('telemetryState.totalKeydowns + telemetryState.focusLossEpisodes') == 0
            page.screenshot(path=str(artifacts / 'prepare-desktop.png'), full_page=True)
            page.locator('#examConsent').check()
            page.locator('#beginExamButton').click()
            page.wait_for_url('**/exam/session')
            expect(page.locator('#listeningMcContainer input').first).to_be_visible()
            page.locator('#tabSec1').click()
            expect(page.locator('#grammarMcContainer input').first).to_be_visible()
            page.locator('#grammarMcContainer input').first.check()
            page.locator('#tabSec3').click()
            page.locator('#essayEditor').press_sequentially('First, education benefits from thoughtful technology. However, students need practice and independent analysis.', delay=5)
            expect(page.locator('#essayWordCounter')).not_to_have_text('0 kata')
            assert page.evaluate('telemetryState.totalKeydowns') > 0
            before_deadline = page.evaluate('appState.exam.deadline')
            page.reload()
            page.wait_for_load_state('networkidle')
            expect(page.locator('#essayEditor')).to_have_value('First, education benefits from thoughtful technology. However, students need practice and independent analysis.')
            assert page.evaluate('appState.exam.deadline') == before_deadline
            page.screenshot(path=str(artifacts / 'exam-desktop.png'), full_page=True)
            page.set_viewport_size({'width': 375, 'height': 812})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert page.locator('.pane-right').bounding_box()['width'] >= 300
            page.screenshot(path=str(artifacts / 'exam-mobile.png'), full_page=True)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.locator('#submitExamButton').click()
            page.wait_for_url('**/results?id=*')
            expect(page.locator('.accuracy-value')).to_be_visible()
            result_url = page.url
            page.reload()
            page.wait_for_load_state('networkidle')
            expect(page.locator('.accuracy-value')).to_be_visible()
            page.screenshot(path=str(artifacts / 'results-desktop.png'), full_page=True)
            assert page.evaluate('appState.exam') is None
            assert page.evaluate('telemetryActive') is False
            page.goto(origin + '/history')
            page.wait_for_load_state('networkidle')
            expect(page.locator('.history-table')).to_be_visible()
            # A different account cannot inspect the first account's result.
            new_context = browser.new_context()
            other = new_context.new_page()
            other.on('pageerror', lambda error: errors.append(str(error)))
            other.goto(origin + '/register')
            other.wait_for_load_state('networkidle')
            other.screenshot(path=str(artifacts / 'register-desktop.png'), full_page=True)
            other.set_viewport_size({'width': 375, 'height': 812})
            other.screenshot(path=str(artifacts / 'register-mobile.png'), full_page=True)
            other.set_viewport_size({'width': 1440, 'height': 900})
            other.locator('#regDisplayName').fill('Peserta Browser')
            other.locator('#regUsername').fill('browser_user')
            other.locator('#regEmail').fill('browser@example.test')
            other.locator('#regPassword').fill('browserpassword123')
            other.locator('#regTerms').check()
            other.locator('#regConfirm').fill('notmatching')
            other.get_by_role('button', name='Buat akun peserta', exact=True).click()
            expect(other.locator('#authErrorMsg')).to_contain_text('belum sama')
            other.locator('#regConfirm').fill('browserpassword123')
            other.get_by_role('button', name='Buat akun peserta', exact=True).click()
            other.wait_for_url('**/dashboard')
            expect(other.locator('.empty-state')).to_contain_text('Belum ada sesi')
            other.goto(result_url)
            other.wait_for_load_state('networkidle')
            expect(other.locator('#resultsContent')).to_contain_text('tidak ditemukan')
            # Deadline expiry sends once; failed network preserves draft and retry reuses ID.
            other.goto(origin + '/exam')
            other.wait_for_load_state('networkidle')
            other.locator('#examConsent').check()
            other.locator('#beginExamButton').click()
            other.wait_for_url('**/exam/session')
            expect(other.locator('#listeningMcContainer input').first).to_be_visible()
            other.route('**/api/submit', lambda route: route.abort())
            other.evaluate('appState.exam.deadline = Date.now() - 1; startExamCountdown()')
            expect(other.locator('#submitExamButton')).to_have_text('Coba kirim kembali')
            assert other.evaluate('!!localStorage.getItem(draftKey())')
            assert other.evaluate('telemetryActive') is False
            other.unroute('**/api/submit')
            other.on('dialog', lambda dialog: dialog.accept())
            other.locator('#retryExamButton').click()
            other.wait_for_url('**/results?id=*')
            expect(other.locator('.accuracy-value')).to_be_visible()
            # Leaving the exam pauses all sensors, while the wall clock remains fixed.
            other.goto(origin + '/exam')
            other.wait_for_load_state('networkidle')
            other.locator('#examConsent').check()
            other.locator('#beginExamButton').click()
            other.wait_for_url('**/exam/session')
            expect(other.locator('#listeningMcContainer input').first).to_be_visible()
            other.locator('.nav-account').click()
            other.wait_for_url('**/dashboard')
            other.locator('.participant-identity summary').click()
            expect(other.locator('#participantDetails')).to_be_visible()
            before = other.evaluate('telemetryState.totalKeydowns + telemetryState.focusLossEpisodes + telemetryState.heatmapPoints.length')
            other.mouse.move(100, 200)
            other.evaluate("window.dispatchEvent(new Event('blur')); window.dispatchEvent(new Event('focus'))")
            assert other.evaluate('telemetryState.totalKeydowns + telemetryState.focusLossEpisodes + telemetryState.heatmapPoints.length') == before
            other.screenshot(path=str(artifacts / 'dashboard-desktop.png'), full_page=True)
            # Expired server sessions redirect and isolate the previous account's draft.
            other.request.post(origin + '/api/auth/logout', data={})
            other.goto(origin + '/history')
            other.wait_for_url('**/login?next=*')
            expect(other.locator('#loginForm')).to_be_visible()
            assert other.evaluate('appState.currentUser') is None
            assert other.evaluate('appState.exam') is None
            print('PASS: automatic expiry, network retry/draft retention, sensors inactive outside exam', flush=True)
            page.get_by_role('button', name='Keluar', exact=True).click()
            page.wait_for_url('**/login')
            page.locator('#loginIdentifier').fill('admin')
            page.locator('#loginPassword').fill('admin123')
            page.get_by_role('button', name='Masuk', exact=True).click()
            page.wait_for_url(lambda u: '/admin' in u)
            expect(page.locator('.overview-stats')).to_be_visible()
            page.get_by_role('button', name='Pengawasan', exact=True).click()
            expect(page.locator('#proctorSessionsBody tr').first).to_be_visible()
            page.get_by_role('button', name='Bank soal').click()
            expect(page.locator('#adminQuestionsBody tr').first).to_be_visible()
            page.locator('#adminQuestionsBody .btn-sm').first.click()
            expect(page.locator('#qFormId')).not_to_have_value('')
            page.get_by_role('button', name='Akun pengguna').click()
            expect(page.locator('#adminUsersBody')).to_contain_text('<script>alert(1)</script>')
            # Real text must remain escaped, never execute or become markup.
            assert page.locator('#adminUsersBody script').count() == 0
            page.screenshot(path=str(artifacts / 'admin-desktop.png'), full_page=True)
            check_user_browser(page, origin, artifacts)
            capture_overview(page, origin, artifacts)
            check_workspace_browser(browser, origin, artifacts)
            check_ept_browser(page, context, origin, artifacts)
            check_finished_browser(browser, origin, artifacts)
            assert not errors, errors
            browser.close()
            print('PASS: browser login/register, route guards, no landing sensors, exam draft/refresh, submission, results/history, private results and admin tabs', flush=True)
        server.shutdown()
        server.server_close()
        print('Screenshots: docs/qa/', flush=True)


if __name__ == '__main__':
    run()

