"""WCAG A/AA axe audit and keyboard/reflow checks on a disposable MySQL schema.

Supply a local axe-core 4.10.3 script. No application data is sent to a service.
"""
import argparse
import json
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run(args):
    from backend import config
    from mysql_support import temporary_database
    from backend.database import init_schema
    from backend.seed_data import seed_all
    from backend.router import TOEFLPlatformRouter
    from question_fixtures import seed_test_questions

    output = ROOT / 'docs/qa/test_temp_wcag' / args.output
    output.mkdir(parents=True, exist_ok=True)
    records, errors = [], []
    axe = Path(args.axe).resolve()
    assert axe.is_file(), 'Supply --axe /path/to/axe.min.js (axe-core 4.10.3)'

    def capture(page, name, widths=(1440, 320)):
        for width in widths:
            page.set_viewport_size({'width': width, 'height': 900})
            page.evaluate('scrollTo(0, 0)')
            page.add_script_tag(path=str(axe))
            result = page.evaluate("""async () => {
                const result = await axe.run(document, {runOnly: {type: 'tag',
                  values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']}});
                return {violations: result.violations, incomplete: result.incomplete};
            }""")
            overflow = page.evaluate("""() => [...document.querySelectorAll('main *, header *')]
                .filter(el => { const r = el.getBoundingClientRect(), s = getComputedStyle(el);
                  return r.width && r.height && s.visibility !== 'hidden' &&
                    !el.closest('[inert],.sr-only,.skip-link') &&
                    (r.right > innerWidth + 2 || r.left < -2) &&
                    !el.closest('.table-scroll,.combo-list,.section-stepper'); })
                .slice(0, 12).map(el => el.id || el.className || el.tagName)""")
            records.append({'name': name, 'width': width, 'overflow': overflow, **result})
            page.screenshot(path=str(output / f'{name}-{width}.png'), full_page=True,
                            animations='disabled')
            print(name, width, [(v['id'], len(v['nodes'])) for v in result['violations']],
                  'overflow:', overflow, flush=True)
        page.set_viewport_size({'width': 1440, 'height': 900})

    def visit(page, origin, route, name):
        page.goto(origin + route)
        page.wait_for_load_state('networkidle')
        capture(page, name)

    class QuietRouter(TOEFLPlatformRouter):
        def log_message(self, *_args):
            pass

    with temporary_database(), tempfile.TemporaryDirectory(prefix='linguapulse-a11y-') as tmp:
        config.DATA_DIR = Path(tmp)
        init_schema()
        seed_all()
        seed_test_questions()
        server = ThreadingHTTPServer(('127.0.0.1', 0), QuietRouter)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        origin = f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)

                def context(role=None):
                    ctx = browser.new_context(viewport={'width': 1440, 'height': 900},
                                              reduced_motion='reduce')
                    if role:
                        identifier, password = ('admin', 'admin123') if role == 'admin' else ('nadia_putri', 'student123')
                        assert ctx.request.post(origin + '/api/auth/login', data={
                            'identifier': identifier, 'password': password}).ok
                    page = ctx.new_page()
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('dialog', lambda dialog: dialog.accept())
                    return page

                public = context()
                if args.ui_only:
                    from accessibility_checks import check_keyboard_and_reflow
                    check_keyboard_and_reflow(public, context('student'), context('admin'), origin)
                    browser.close()
                    return
                for route, name in (('/', 'landing'), ('/login', 'login'), ('/register', 'register'),
                                    ('/privacy', 'privacy'), ('/terms', 'terms'), ('/missing', '404')):
                    visit(public, origin, route, name)
                public.goto(origin)
                public.wait_for_load_state('networkidle')
                public.set_viewport_size({'width': 320, 'height': 900})
                public.locator('#siteMenuToggle').click()
                capture(public, 'public-menu', (320,))
                public.goto(origin + '/login')
                public.wait_for_load_state('networkidle')
                public.get_by_role('button', name='Lupa kata sandi?').click()
                capture(public, 'account-help')

                student = context('student')
                for route in ('/dashboard', '/history', '/results', '/exam'):
                    visit(student, origin, route, route[1:])
                for module in ('grammar', 'reading', 'listening'):
                    visit(student, origin, '/practice?module=' + module, 'practice-' + module)
                student.locator('[data-choice="0"]').click()
                student.locator('#practiceCheck').click()
                expect(student.locator('#practiceFeedback')).to_be_visible()
                capture(student, 'practice-feedback')

                admin = context('admin')
                for tab in ('overview', 'proctor', 'questions', 'packages', 'schedules', 'users'):
                    visit(admin, origin, '/admin/' + tab, 'admin-' + tab)
                admin.locator('#adminUserDropdownToggle').click()
                capture(admin, 'admin-account-menu')
                admin.keyboard.press('Escape')
                admin.set_viewport_size({'width': 320, 'height': 900})
                admin.locator('#adminSidebarToggle').click()
                capture(admin, 'admin-drawer', (320,))
                admin.keyboard.press('Escape')
                admin.get_by_role('button', name='Tambah akun', exact=True).click()
                capture(admin, 'user-dialog')
                admin.locator('#editUserRole-combo').focus()
                admin.locator('#editUserRole-combo').press('ArrowDown')
                capture(admin, 'user-role-options')
                admin.keyboard.press('Escape')
                admin.keyboard.press('Escape')
                admin.goto(origin + '/admin/questions')
                admin.wait_for_load_state('networkidle')
                admin.get_by_role('button', name='Tambah soal', exact=True).click()
                capture(admin, 'question-editor')
                for tab, button in (('packages', 'Buat paket'), ('schedules', 'Buat sesi jadwal')):
                    admin.goto(origin + '/admin/' + tab)
                    admin.wait_for_load_state('networkidle')
                    admin.get_by_role('button', name=button, exact=True).click()
                    capture(admin, tab + '-editor')

                student.goto(origin + '/exam')
                student.wait_for_load_state('networkidle')
                student.locator('#examConsent').check()
                student.locator('#beginExamButton').click()
                student.wait_for_url('**/exam/session')
                for index, name in enumerate(('listening', 'structure', 'reading', 'writing')):
                    student.locator('#tabSec' + str(index)).click()
                    capture(student, 'exam-' + name)
                student.locator('#essayEditor').fill('Independent practice helps students understand context.')
                student.locator('#submitExamButton').click()
                student.wait_for_url('**/results?id=*')
                expect(student.locator('.accuracy-value')).to_be_visible()
                capture(student, 'results-populated')
                for route in ('/history', '/dashboard'):
                    visit(student, origin, route, route[1:] + '-populated')
                visit(admin, origin, '/admin/proctor', 'proctor-populated')
                admin.locator('[data-inspect-index]').first.click()
                admin.locator('.monitor-analysis summary').click()
                capture(admin, 'proctor-detail')
                if args.check:
                    from accessibility_checks import check_keyboard_and_reflow
                    check_keyboard_and_reflow(public, student, admin, origin)
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
    (output / 'report.json').write_text(json.dumps({'axeVersion': '4.10.3', 'pages': records,
        'browserErrors': errors}, ensure_ascii=False, indent=2), encoding='utf-8')
    failures = sum(len(row['violations']) for row in records)
    unsupported_names = sum(1 for row in records for issue in row['incomplete']
                            if issue['id'] == 'aria-prohibited-attr')
    print(f'Audit: {len(records)} states/viewports, {failures} rule violations, {len(errors)} JS errors')
    if args.check:
        assert not failures and not unsupported_names and not errors, 'See report.json for audit failures'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--axe', default='docs/qa/test_temp_wcag/axe.min.js')
    parser.add_argument('--output', default='latest')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--ui-only', action='store_true', help='Run keyboard/reflow checks only')
    run(parser.parse_args())
