"""Regression checks for the findings in the complete page audit."""
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError
from playwright.sync_api import expect


def check_branded_404(origin):
    opener = build_opener(ProxyHandler({}))
    for method in ('GET', 'HEAD'):
        try:
            opener.open(Request(origin + '/page-that-does-not-exist', method=method))
            raise AssertionError('Unknown route should have status 404')
        except HTTPError as error:
            assert error.code == 404
            assert error.headers.get_content_type() == 'text/html'
            body = error.read()
            assert (b'LinguaPulse' in body) if method == 'GET' else not body
    print('PASS: branded HTML 404 and correct GET/HEAD status', flush=True)


def check_finished_browser(browser, origin, artifacts):
    context = browser.new_context(viewport={'width': 320, 'height': 812})
    errors = []
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(origin + '/page-that-does-not-exist')
    page.wait_for_load_state('networkidle')
    expect(page.locator('h1')).to_have_text('Halaman tidak ditemukan')
    page.locator('#siteMenuToggle').click()
    expect(page.locator('#sitePublicNav')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#siteMenuToggle')).to_be_focused()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(artifacts / 'finish-404-320.png'), full_page=True)
    page.goto(origin + '/login')
    page.wait_for_load_state('networkidle')
    page.get_by_role('button', name='Lupa kata sandi?', exact=True).click()
    expect(page.locator('#accountHelpDialog')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.get_by_role('button', name='Lupa kata sandi?', exact=True)).to_be_focused()
    assert context.request.post(origin + '/api/auth/login', data={'identifier': 'nadia_putri', 'password': 'student123'}).ok
    page.goto(origin + '/history')
    page.wait_for_load_state('networkidle')
    expect(page.locator('.history-cards')).to_be_visible()
    assert page.locator('.history-cards').evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
    page.screenshot(path=str(artifacts / 'finish-history-320.png'), full_page=True)
    page.locator('.history-cards a').first.click()
    page.wait_for_url('**/results?id=*')
    expect(page.locator('.accuracy-value')).to_be_visible()
    for module in ('listening', 'grammar', 'reading'):
        page.locator('[data-result-module="' + module + '"]').click()
        expect(page.locator('.review-question').first).to_be_visible()
        expect(page.locator('.review-question[open] .review-options .is-correct')).to_have_count(1)
    expect(page.locator('.review-question[open] .review-context')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(artifacts / 'finish-results-320.png'), full_page=True)
    page.goto(origin + '/practice?module=reading')
    page.wait_for_load_state('networkidle')
    assert page.locator('#practicePrompt').bounding_box()['y'] < 650
    page.locator('[data-choice="0"]').click()
    page.locator('#practicePaneContext').click()
    expect(page.locator('.practice-passage')).to_be_visible()
    page.locator('#practicePaneQuestion').click()
    expect(page.locator('[name="practiceAnswer"][value="0"]')).to_be_checked()
    page.locator('#practiceSkip').click()
    expect(page.locator('#practicePrompt')).to_be_focused()
    assert page.evaluate('telemetryActive') is False
    page.goto(origin + '/exam')
    page.wait_for_load_state('networkidle')
    assert page.evaluate('document.querySelector(".prep-duration").getBoundingClientRect().top - document.querySelector(".prep-module-counts").getBoundingClientRect().bottom') >= 16
    expect(page.locator('#deviceProfile-combo')).to_be_visible()
    context.close()

    admin = browser.new_context(viewport={'width': 375, 'height': 812})
    admin.request.post(origin + '/api/auth/login', data={'identifier': 'admin', 'password': 'admin123'})
    manager = admin.new_page()
    manager.on('pageerror', lambda error: errors.append(str(error)))
    manager.goto(origin + '/admin?tab=proctor')
    manager.wait_for_load_state('networkidle')
    first = manager.locator('[data-inspect-index]').first
    first.focus()
    first.press('Enter')
    expect(manager.locator('#inspectTitle')).to_be_focused()
    expect(manager.locator('.monitor-analysis')).not_to_have_attribute('open', '')
    assert '0 (Aman)' not in manager.locator('#adminTabProctor').inner_text()
    manager.locator('.monitor-analysis summary').click()
    expect(manager.locator('#heatmapCanvas')).to_be_visible()
    manager.screenshot(path=str(artifacts / 'finish-proctor-detail-375.png'), full_page=True)
    manager.goto(origin + '/admin?tab=questions')
    manager.wait_for_load_state('networkidle')
    expect(manager.locator('.bank-detail')).to_be_hidden()
    manager.locator('#adminQuestionsBody').get_by_role('button', name='Edit', exact=True).first.click()
    expect(manager.locator('#qFormTitle')).to_be_focused()
    expect(manager.locator('#qFormPrompt')).not_to_have_value('')
    manager.locator('#qFormPrompt').fill('Unsaved audit edit')
    manager.get_by_role('button', name='Tambah soal', exact=True).click()
    expect(manager.locator('#adminConfirmDialog')).to_be_visible()
    manager.locator('#adminConfirmDialog').get_by_role('button', name='Batal', exact=True).click()
    expect(manager.locator('#qFormPrompt')).to_have_value('Unsaved audit edit')
    manager.locator('#adminSidebarToggle').click()
    manager.get_by_role('button', name='Akun pengguna', exact=True).click()
    expect(manager.locator('#adminConfirmDialog')).to_be_visible()
    manager.locator('#adminConfirmAccept').click()
    expect(manager.locator('#adminTabUsers')).to_be_visible()
    assert not errors, errors
    admin.close()
    print('PASS: mobile history/results, full module review, context retention, compact question, prep spacing, keyboard proctor and dirty-edit cancellation', flush=True)
