"""Browser coverage of admin packages and the focused question workspace."""
import sys
from pathlib import Path
from playwright.sync_api import expect


def check_package_browser(browser, origin, artifacts):
    errors = []
    admin_ctx = browser.new_context(viewport={'width': 1440, 'height': 1000})
    student_ctx = browser.new_context(viewport={'width': 1440, 'height': 1000})
    try:
        assert student_ctx.request.get(origin + '/api/exam/packages').status == 401
        assert admin_ctx.request.post(origin + '/api/auth/login', data={'identifier': 'admin', 'password': 'admin123'}).ok
        assert student_ctx.request.post(origin + '/api/auth/login', data={'identifier': 'nadia_putri', 'password': 'student123'}).ok
        assert student_ctx.request.get(origin + '/api/admin/packages').status == 403
        assert student_ctx.request.post(origin + '/api/admin/packages', data={}).status == 403
        admin = admin_ctx.new_page()
        learner = student_ctx.new_page()
        for page in (admin, learner):
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('dialog', lambda dialog: dialog.accept())
        admin.goto(origin + '/admin/packages')
        admin.wait_for_load_state('networkidle')
        admin.locator('#newPackageButton').click()
        admin.locator('#packageName').fill('Experimental ringkas')
        admin.locator('#packageDescription').fill('Paket uji antarmuka, bukan data penelitian.')
        admin.locator('#packageDuration').fill('7')
        admin.locator('#savePackageButton').click()
        expect(admin.locator('#packageSaveStatus')).to_contain_text('Draf tersimpan')
        package_id = admin.evaluate('packageEditor.current.package_id')
        assert all(p['package_id'] != package_id for p in student_ctx.request.get(origin + '/api/exam/packages').json()['packages'])
        admin.locator('#packagePublished').check()
        admin.locator('#savePackageButton').click()
        expect(admin.locator('#packageError')).to_contain_text('belum dapat dipublikasikan')
        exported = admin_ctx.request.get(origin + '/api/admin/questions/export').json()['questions']
        selected = [next(q['question_id'] for q in exported if q['section'] == section and q['is_active']
                         and (section != 'grammar' or q['question_type'] == 'multiple_choice')
                         and (section != 'reading' or q['passage'])) for section in ('listening', 'grammar', 'reading', 'writing')]
        for qid in selected:
            admin.locator(f'[data-package-question="{qid}"]').check()
        admin.locator('#savePackageButton').click()
        expect(admin.locator('#packageError')).not_to_be_visible()
        expect(admin.locator('#packageSaveStatus')).to_contain_text('tersedia untuk peserta')
        admin.reload()
        admin.wait_for_load_state('networkidle')
        admin.locator(f'[data-edit-package="{package_id}"]').click()
        expect(admin.locator('#packageDuration')).to_have_value('7')
        assert admin.locator('[data-package-question]:checked').count() == 4
        admin.screenshot(path=str(artifacts / 'packages-admin-desktop.png'), full_page=True)
        for width in (375, 320):
            admin.set_viewport_size({'width': width, 'height': 812})
            expect(admin.locator('#adminSidebar')).to_be_hidden()
            assert admin.evaluate('document.documentElement.scrollWidth <= innerWidth'), ('admin', width)
        admin.screenshot(path=str(artifacts / 'packages-admin-mobile.png'), full_page=True)
        admin.set_viewport_size({'width': 1440, 'height': 1000})
        learner.goto(origin + '/exam')
        learner.wait_for_load_state('networkidle')
        learner.locator(f'[data-package="{package_id}"]').click()
        expect(learner.locator('#preparePackageName')).to_have_text('Experimental ringkas')
        expect(learner.locator('#prepareDuration')).to_contain_text('7 menit')
        assert learner.evaluate('telemetryActive') is False
        learner.screenshot(path=str(artifacts / 'packages-prepare-desktop.png'), full_page=True)
        learner.locator('#examConsent').check()
        learner.locator('#beginExamButton').click()
        learner.wait_for_url('**/exam/session')
        expect(learner.locator('#examPackageTitle')).to_have_text('Experimental ringkas')
        expect(learner.locator('.q-card:visible')).to_have_count(1)
        expect(learner.locator('#questionNavigator button')).to_have_count(4)
        expect(learner.locator('#previousQuestion')).to_be_disabled()
        first_id = learner.evaluate('appState.exam.currentQuestionId')
        learner.locator('.q-card:visible input').first.check()
        learner.locator('.q-card:visible [data-clear-choice]').press('Enter')
        expect(learner.locator('.q-card:visible input:checked')).to_have_count(0)
        expect(learner.locator('.q-card:visible [data-clear-choice]')).to_be_hidden()
        expect(learner.locator('#examProgressText')).to_contain_text('0 dari 4')
        learner.locator('.q-card:visible input').first.check()
        learner.locator('.q-card:visible [data-flag]').click()
        expect(learner.locator(f'[data-jump="{first_id}"]')).to_have_class(__import__('re').compile('is-marked'))
        learner.screenshot(path=str(artifacts / 'packages-session-desktop.png'), full_page=True)
        learner.locator('#nextQuestion').click()
        expect(learner.locator('.q-card:visible')).to_have_count(1)
        second_id = learner.evaluate('appState.exam.currentQuestionId')
        assert second_id != first_id
        learner.locator('.q-card:visible input').first.check()
        deadline = learner.evaluate('appState.exam.deadline')
        learner.reload()
        learner.wait_for_load_state('networkidle')
        assert learner.evaluate('appState.exam.currentQuestionId') == second_id
        assert learner.evaluate('appState.exam.deadline') == deadline
        expect(learner.locator('.q-card:visible input:checked')).to_have_count(1)
        expect(learner.locator('#examProgressText')).to_contain_text('2 dari 4')
        learner.locator('#previousQuestion').click()
        expect(learner.locator('.q-card:visible input:checked')).to_have_count(1)
        expect(learner.locator('.q-card:visible [data-flag]')).to_have_attribute('aria-pressed', 'true')
        # A package can be withdrawn while an existing frozen attempt stays usable.
        admin.locator('#packageName').fill('Paket dihentikan')
        admin.locator('#packageDuration').fill('19')
        admin.locator('#packagePublished').uncheck()
        admin.locator('#savePackageButton').click()
        expect(admin.locator('#packageSaveStatus')).to_contain_text('Draf tersimpan')
        learner.reload()
        learner.wait_for_load_state('networkidle')
        expect(learner.locator('#examPackageTitle')).to_have_text('Experimental ringkas')
        assert learner.evaluate('appState.exam.deadline') == deadline
        assert student_ctx.request.get(origin + '/api/exam/packages?id=' + package_id).status == 404
        learner.locator('#questionNavigator button').first.focus()
        learner.set_viewport_size({'width': 768, 'height': 812})
        expect(learner.locator('.question-navigation summary')).to_be_focused()
        for width in (1100, 768, 375, 320):
            learner.set_viewport_size({'width': width, 'height': 812})
            assert learner.evaluate('document.documentElement.scrollWidth <= innerWidth'), ('session', width)
            expect(learner.locator('.q-card:visible')).to_have_count(1)
            if width <= 960:
                learner.locator('.question-navigation').evaluate('(el) => el.open = true')
            learner.locator('#questionNavigator [data-jump]').nth(2).click()
            reading_summary = learner.locator('#readingContext summary')
            expect(reading_summary).to_have_text('Baca teks')
            assert reading_summary.evaluate('el => el.getBoundingClientRect().height >= 44')
            reading_summary.click()
            expect(learner.locator('#readingPassageText')).to_be_visible()
            expect(learner.locator('.q-card:visible')).to_have_count(1)
            learner.locator('#readingBackToQuestion').press('Enter')
            expect(learner.locator('#readingContext')).not_to_have_attribute('open', '')
            expect(learner.locator('.q-card:visible .q-prompt')).to_be_focused()
            learner.screenshot(path=str(artifacts / f'packages-session-{width}.png'), full_page=True)
            learner.screenshot(path=str(artifacts / f'packages-session-viewport-{width}.png'))
        learner.locator('#nextQuestion').click()
        expect(learner.locator('#writingPromptText')).to_be_visible()
        expect(learner.locator('#essayEditor')).to_be_visible()
        expect(learner.locator('#nextQuestion')).to_be_disabled()
        learner.locator('#essayEditor').fill('Jawaban uji Writing, bukan data responden penelitian.')
        expect(learner.locator('#examProgressText')).to_contain_text('3 dari 4')
        learner.locator('#submitExamButton').click()
        learner.wait_for_url('**/results?id=*')
        expect(learner.locator('.accuracy-value')).to_be_visible()
        assert learner.evaluate('telemetryActive') is False
        current = admin_ctx.request.get(origin + '/api/admin/packages?id=' + package_id).json()
        assert admin_ctx.request.post(origin + '/api/admin/packages', data={**current,
            'is_active': True, 'question_ids': selected[:3]}).ok
        learner.goto(origin + '/exam')
        learner.locator(f'[data-package="{package_id}"]').click()
        expect(learner.locator('#prepareDuration')).to_contain_text('19 menit')
        learner.locator('#examConsent').check()
        learner.locator('#beginExamButton').click()
        learner.wait_for_url('**/exam/session')
        expect(learner.locator('#tabSec3')).to_be_disabled()
        expect(learner.locator('#questionNavigator button')).to_have_count(3)
        learner.evaluate("appState.selectedAnswers.W1 = 'Foreign essay data must never be counted as an assigned Writing task in this package.'")
        learner.locator('#submitExamButton').click()
        learner.wait_for_url('**/results?id=*')
        expect(learner.locator('.accuracy-value')).to_be_visible()
        result_id = learner.url.split('?id=')[1]
        result = student_ctx.request.get(origin + '/api/results?id=' + result_id).json()
        assert result['toefl_practice_result']['essay_word_count'] == 0
        assert not errors, errors
        print('PASS: admin draft/publish, package choice/duration, 1 visible question, navigation/flags/reload, frozen package, responsive context, submit', flush=True)
    finally:
        admin_ctx.close()
        student_ctx.close()


def run():
    import tempfile
    import threading
    from http.server import ThreadingHTTPServer
    from playwright.sync_api import sync_playwright
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from mysql_support import temporary_database
    from backend.database import init_schema
    from backend.seed_data import seed_all
    from question_fixtures import seed_test_questions
    from backend.router import TOEFLPlatformRouter
    from backend import config
    artifacts = Path(__file__).resolve().parents[1] / 'docs/qa/polish-packages-2026-11-18'
    artifacts.mkdir(parents=True, exist_ok=True)
    with temporary_database(), tempfile.TemporaryDirectory(prefix='package-qa-') as tmp:
        config.DATA_DIR = Path(tmp)
        init_schema()
        seed_all()
        seed_test_questions()
        class QuietRouter(TOEFLPlatformRouter):
            def log_message(self, *_args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), QuietRouter)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                try:
                    check_package_browser(browser, f'http://127.0.0.1:{server.server_port}', artifacts)
                finally:
                    browser.close()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    run()
