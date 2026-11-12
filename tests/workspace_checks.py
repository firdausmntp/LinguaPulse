"""Overview and untimed practice checks, always against the temporary database."""
from http.cookiejar import CookieJar
from urllib.request import build_opener, ProxyHandler, HTTPCookieProcessor
from playwright.sync_api import expect


def check_workspace_api(request):
    status, overview = request('/api/admin/overview')
    assert status == 200 and overview['students'] >= 1
    assert overview['completed'] >= 0 and 'modules' in overview
    assert overview['completed'] == 1 and overview['ongoing'] == 0  # The submitted fixture must not count as ongoing.
    assert request('/api/practice/question')[0] == 403
    client = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()))
    assert request('/api/practice/question', opener=client)[0] == 401
    assert request('/api/auth/login', {'identifier': 'nadia_putri', 'password': 'student123'}, opener=client)[0] == 200
    assert request('/api/admin/overview', opener=client)[0] == 403
    before = request('/api/history', opener=client)[1]
    for section in ('grammar', 'listening', 'reading'):
        status, data = request('/api/practice/question?section=' + section, opener=client)
        assert status == 200 and data['total'] > 0 and data['question']
        question = data['question']
        assert len(question['options']) >= 2
        assert not ({'answer', 'correct_answer', 'explanation', 'sample_ai_reference', 'folder_file'} & set(question))
        checked_status, checked = request('/api/practice/question', {'id': question['id'], 'choice': 0}, opener=client)
        assert checked_status == 200 and 0 <= checked['answer'] < len(question['options']) and 'explanation' in checked
        if section == 'reading':
            assert question['passage'].strip()
        else:
            assert not question['passage']
        if data['total'] > 1:
            another = request('/api/practice/question?section=' + section + '&exclude=' + question['id'], opener=client)[1]
            assert another['question']['id'] != question['id']
    assert request('/api/practice/question?section=invalid', opener=client)[0] == 400
    from unittest.mock import patch
    with patch('backend.workspace_reads.random.choice', side_effect=lambda items: next(item for item in items if item['question_id'] == 'R2')):
        inherited = request('/api/practice/question?section=reading', opener=client)[1]['question']
        assert inherited['id'] == 'R2' and 'bioluminescence' in inherited['passage'].lower()
    assert request('/api/history', opener=client)[1] == before
    print('PASS: role-protected overview, practice modules/random exclusion and unchanged exam history', flush=True)


def check_workspace_browser(browser, origin, artifacts):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    errors = []
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(origin + '/login')
    page.wait_for_load_state('networkidle')
    page.locator('#loginIdentifier').fill('nadia_putri')
    page.locator('#loginPassword').fill('student123')
    page.get_by_role('button', name='Masuk', exact=True).click()
    page.wait_for_url('**/dashboard')
    expect(page.locator('.learning-start')).to_contain_text('Mulai latihan bebas')
    page.screenshot(path=str(artifacts / 'learning-dashboard.png'), full_page=True)
    for width in (375, 320):
        page.set_viewport_size({'width': width, 'height': 812})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert page.locator('.learning-start').evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
        page.screenshot(path=str(artifacts / f'learning-dashboard-{width}.png'), full_page=True)
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.locator('.learning-start a').click()
    page.wait_for_url('**/practice?module=grammar')
    expect(page.locator('#practiceCheck')).to_be_disabled()
    assert page.evaluate('practiceState.question.answer === undefined && practiceState.question.explanation === undefined')
    correct = int(page.evaluate("""async () => {
      const res = await fetch('/api/practice/question', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: practiceState.question.id, choice: 0 }) });
      const data = await res.json();
      return data.answer;
    }"""))
    wrong = (correct + 1) % page.evaluate('practiceState.question.options.length')
    page.locator('[data-choice="' + str(wrong) + '"]').click()
    page.locator('#practiceCheck').click()
    expect(page.locator('#practiceFeedback')).to_contain_text('Belum tepat')
    expect(page.locator('.practice-option.is-correct')).to_have_count(1)
    expect(page.locator('.practice-option.is-incorrect')).to_have_count(1)
    assert page.evaluate('telemetryActive') is False
    page.screenshot(path=str(artifacts / 'practice-feedback-desktop.png'), full_page=True)
    old_id = page.evaluate('practiceState.question.id')
    page.locator('#practiceNext').click()
    page.wait_for_function('old => practiceState.question && practiceState.question.id !== old', arg=old_id)
    assert page.evaluate('practiceState.question.answer === undefined && practiceState.question.explanation === undefined')
    correct = int(page.evaluate("""async () => {
      const res = await fetch('/api/practice/question', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: practiceState.question.id, choice: 0 }) });
      const data = await res.json();
      return data.answer;
    }"""))
    page.locator('[data-choice="' + str(correct) + '"]').click()
    page.locator('#practiceCheck').click()
    expect(page.locator('#practiceFeedback')).to_contain_text('Tepat')
    expect(page.locator('.practice-option.is-incorrect')).to_have_count(0)
    expect(page.locator('#practiceSessionCount')).to_contain_text('2 soal')
    for width in (375, 320):
        page.set_viewport_size({'width': width, 'height': 812})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert page.locator('.practice-question').evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
        page.screenshot(path=str(artifacts / f'practice-{width}.png'), full_page=True)
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.locator('#practiceModuleReading').click()
    expect(page.locator('.practice-passage')).not_to_be_empty()
    assert '\\n' not in page.locator('.practice-passage').inner_text()
    page.screenshot(path=str(artifacts / 'practice-reading.png'), full_page=True)
    page.locator('#practiceModuleListening').click()
    expect(page.locator('.practice-context audio')).to_be_visible()
    assert page.evaluate('telemetryActive') is False
    for width in (375, 320):
        page.set_viewport_size({'width': width, 'height': 812})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.reload()
    page.wait_for_load_state('networkidle')
    expect(page.locator('#practiceModuleListening')).to_have_attribute('aria-pressed', 'true')
    page.route('**/api/practice/question?section=reading*', lambda route: route.fulfill(json={'question': None, 'total': 0}))
    page.locator('#practiceModuleReading').click()
    expect(page.locator('#practiceContent')).to_contain_text('Materi ini belum tersedia')
    page.unroute('**/api/practice/question?section=reading*')
    page.route('**/api/practice/question?section=grammar*', lambda route: route.abort())
    page.locator('#practiceModuleGrammar').click()
    expect(page.locator('#practiceContent')).to_contain_text('Koneksi terputus')
    page.unroute('**/api/practice/question?section=grammar*')
    page.get_by_role('button', name='Coba lagi', exact=True).click()
    expect(page.locator('#practicePrompt')).to_be_visible()
    assert not errors, errors
    context.close()
    print('PASS: practice correct/incorrect feedback, next question, module switching, refresh, mobile and no sensors', flush=True)


def capture_overview(page, origin, artifacts):
    page.goto(origin + '/admin')
    page.wait_for_url(lambda u: '/admin' in u)
    page.wait_for_load_state('networkidle')
    expect(page.locator('.overview-stats')).to_be_visible()
    expect(page.locator('#adminPageTitle')).to_have_text('Ringkasan')
    page.screenshot(path=str(artifacts / 'admin-overview.png'), full_page=True)
    page.locator('#adminSidebarToggle').click()
    expect(page.locator('#adminSidebar')).to_have_css('width', '80px')
    page.screenshot(path=str(artifacts / 'admin-overview-collapsed.png'), full_page=True)
    page.locator('#adminSidebarToggle').click()
    for width in (375, 320):
        page.set_viewport_size({'width': width, 'height': 812})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert page.locator('.overview-stats').evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
        page.screenshot(path=str(artifacts / f'admin-overview-{width}.png'), full_page=True)
    page.set_viewport_size({'width': 1440, 'height': 900})
