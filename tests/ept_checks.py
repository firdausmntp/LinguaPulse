"""EPT-specific integration checks used by the temporary-fixture test runner."""
import base64
import hashlib
import hmac
import json
import time
from pathlib import Path
from urllib.request import build_opener, ProxyHandler, HTTPCookieProcessor
from http.cookiejar import CookieJar
from playwright.sync_api import expect


def check_ept_api(request, origin):
    from backend.security import _keystream_xor
    original = request('/api/admin/questions/export')[1]['questions']
    listening = next(q for q in original if q['question_id'] == 'L1')
    assert listening['audio_url'].endswith('.wav')
    student_client = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()))
    request('/api/auth/login', {'identifier': 'nadia_putri', 'password': 'student123'}, opener=student_client)
    payload = {'device_profile': 'PC_PHYSICAL', 'task_condition': 'MANDIRI', 'consent_agreed': True}
    status, started = request('/api/exam/start', payload, opener=student_client)
    assert status == 200 and len(started['bank']['listening']['questions']) >= 2
    assert not started['bank']['listening']['questions'][0]['passage']
    for item in (
        started['bank']['listening']['questions']
        + started['bank']['grammar_mc']
        + started['bank']['grammar_rewrite']
        + started['bank']['reading']['questions']
        + [started['bank']['writing']]
    ):
        assert not ({'answer', 'correct_answer', 'explanation', 'folder_file'} & set(item))
    resumed = request('/api/exam/resume?id=' + started['attempt_id'], opener=student_client)[1]
    assert not resumed['bank']['listening']['questions'][0]['passage']
    for item in (
        resumed['bank']['listening']['questions']
        + resumed['bank']['grammar_mc']
        + resumed['bank']['grammar_rewrite']
        + resumed['bank']['reading']['questions']
        + [resumed['bank']['writing']]
    ):
        assert not ({'answer', 'correct_answer', 'explanation', 'folder_file'} & set(item))
    # Changing live answer keys must not alter a previously started attempt.
    changed = {**listening, 'correct_answer': str((int(listening['correct_answer']) + 1) % 4), 'mode': 'update', 'original_id': 'L1'}
    assert request('/api/admin/questions', changed)[0] == 200
    plain = {**payload, 'attempt_id': started['attempt_id'], 'duration_sec': 30,
             'answers': {'L1': int(listening['correct_answer'])}, 'participant_code': 'FORGED-OTHER'}
    handshake = request('/api/security/handshake', opener=student_client)[1]
    iv = '11223344556677889900aabb'
    ciphertext = base64.b64encode(_keystream_xor(json.dumps(plain).encode(), handshake['session_key'], iv)).decode()
    stamp = int(time.time())
    message = f"{handshake['handshake_id']}.{iv}.{stamp}.{ciphertext}"
    envelope = {'handshake_id': handshake['handshake_id'], 'iv': iv, 'timestamp': stamp, 'ciphertext': ciphertext,
                'signature': hmac.new(handshake['session_key'].encode(), message.encode(), hashlib.sha256).hexdigest()}
    status, result = request('/api/submit', envelope, opener=student_client)
    assert status == 200, result
    assert result['toefl_practice_result']['listening_mc_correct'] == 1
    reviews = result['toefl_practice_result']['section_reviews']
    assert reviews['listening'][0]['correct_answer'] == int(listening['correct_answer'])
    assert reviews['listening'][0]['status'] == 'correct'
    assert reviews['listening'][1]['status'] == 'unanswered'
    assert reviews['reading'][1]['passage']
    assert result['participant_code'] != 'FORGED-OTHER'
    assert request('/api/submit', envelope, opener=student_client)[1]['already_submitted']
    assert request('/api/admin/questions', {**listening, 'mode': 'update', 'original_id': 'L1'})[0] == 200
    other_client = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()))
    request('/api/auth/login', {'identifier': 'smoke_user', 'password': 'validpassword123'}, opener=other_client)
    assert request('/api/exam/resume?id=' + started['attempt_id'], opener=other_client)[0] == 404
    assert request('/api/admin/questions/export', opener=other_client)[0] == 403
    assert request('/api/admin/audio', {'filename': 'bad.wav', 'data_base64': 'YmFk'}, opener=other_client)[0] == 403
    # Import validates every row before changing any of them.
    reading = {'question_id': 'EPT-READING-CUSTOM', 'section': 'reading', 'question_type': 'multiple_choice',
               'title': 'Independent learning', 'passage': 'A study group meets every Tuesday to discuss assigned research papers.',
               'prompt': 'When does the study group meet?', 'options': ['Tuesday', 'Friday'], 'correct_answer': '0'}
    assert request('/api/admin/questions/import', {'questions': [reading, {**reading, 'question_id': 'INVALID', 'prompt': ''}]})[0] == 400
    assert not any(q['question_id'] == reading['question_id'] for q in request('/api/admin/questions/export')[1]['questions'])
    assert request('/api/admin/questions/import', {'questions': [reading]})[0] == 200
    assert request('/api/admin/questions', reading)[0] == 400  # accidental overwrite rejected
    inactive = {**reading, 'is_active': 0, 'mode': 'update', 'original_id': reading['question_id']}
    assert request('/api/admin/questions', inactive)[0] == 200
    assert not any(q['id'] == reading['question_id'] for q in request('/api/questions', opener=other_client)[1]['reading']['questions'])
    assert request('/api/admin/questions', {**inactive, 'is_active': 1})[0] == 200
    audio = Path(__file__).resolve().parents[1] / 'frontend/media/listening/library-announcement.wav'
    status, uploaded = request('/api/admin/audio', {'filename': 'announcement.wav', 'data_base64': base64.b64encode(audio.read_bytes()).decode()})
    assert status == 200 and uploaded['audio_url'].startswith('/media/uploads/')
    assert request('/api/admin/audio', {'filename': 'fake.wav', 'data_base64': 'bm90IGF1ZGlv'})[0] == 400
    print('PASS: EPT Listening, frozen grading, private attempts, question import/activation, audio upload', flush=True)


def check_ept_browser(admin, context, origin, artifacts):
    admin.goto(origin + '/admin?tab=questions')
    admin.wait_for_load_state('networkidle')
    expect(admin.locator('#adminQuestionsBody')).to_contain_text('Campus library')
    combo = admin.locator('#questionSectionFilter-combo')
    combo.fill('Listening')
    combo.press('ArrowDown')
    combo.press('Enter')
    expect(admin.locator('#questionSectionFilter')).to_have_value('listening')
    combo.fill('Semua')
    combo.press('ArrowDown')
    combo.press('Enter')
    admin.locator('#questionSearch').fill('L1')
    expect(admin.locator('#adminQuestionsBody tr')).to_have_count(1)
    admin.get_by_role('button', name='Edit', exact=True).click()
    expect(admin.locator('#qFormAudio')).to_have_value('/media/listening/library-announcement.wav')
    expect(admin.locator('#qFormPrompt')).not_to_have_value('')
    admin.get_by_role('button', name='Pratinjau', exact=True).click()
    expect(admin.locator('#questionPreview audio')).to_be_visible()
    admin.get_by_role('button', name='Tambah soal', exact=True).click()
    admin.locator('#qFormId').fill('UI-CUSTOM-G')
    admin.locator('#qFormTitle').fill('Custom subject agreement')
    admin.locator('#qFormPrompt').fill('The research team ____ meeting today.')
    for index, value in enumerate(['is', 'are', 'were', 'be']):
        admin.locator('#questionOption' + str(index)).fill(value)
    admin.locator('#qFormCorrect-combo').fill('Opsi A')
    admin.locator('#qFormCorrect-combo').press('ArrowDown')
    admin.locator('#qFormCorrect-combo').press('Enter')
    admin.locator('#qFormExplanation').fill('The collective noun team takes is in this sentence.')
    admin.locator('#saveQuestionButton').click()
    expect(admin.locator('#questionEditorStatus')).to_contain_text('UI-CUSTOM-G tersimpan')
    admin.locator('#questionSearch').fill('UI-CUSTOM-G')
    expect(admin.locator('#adminQuestionsBody tr')).to_have_count(1)
    admin.get_by_role('button', name='Salin', exact=True).click()
    expect(admin.locator('#questionEditorTitle')).to_have_text('Salinan soal baru')
    assert admin.locator('#qFormId').input_value() != 'UI-CUSTOM-G'
    admin.screenshot(path=str(artifacts / 'custom-editor-desktop.png'), full_page=True)
    admin.set_viewport_size({'width': 375, 'height': 812})
    assert admin.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert admin.locator('.bank-detail').bounding_box()['width'] >= 300
    admin.screenshot(path=str(artifacts / 'custom-editor-mobile.png'), full_page=True)
    admin.set_viewport_size({'width': 1440, 'height': 900})
    admin.get_by_role('button', name='Kembali ke daftar soal', exact=True).click()
    admin.locator('#questionSearch').fill('')
    with admin.expect_download() as downloaded:
        admin.get_by_role('button', name='Ekspor JSON', exact=True).click()
    assert downloaded.value.suggested_filename.endswith('.json')
    # Student exercises the real Listening player, flags, per-passage navigation and custom item.
    learner_context = context.browser.new_context(viewport={'width': 1440, 'height': 900})
    learner_context.request.post(origin + '/api/auth/login', data={'identifier': 'nadia_putri', 'password': 'student123'})
    learner = learner_context.new_page()
    learner.on('dialog', lambda dialog: dialog.accept())
    learner.goto(origin + '/exam')
    learner.wait_for_load_state('networkidle')
    learner.locator('#examConsent').check()
    learner.locator('#beginExamButton').click()
    learner.wait_for_url('**/exam/session')
    expect(learner.locator('#listeningAudio')).to_be_visible()
    assert learner.locator('#listeningMcContainer .q-option-label > span:last-child').evaluate_all('(options) => options.every(option => !/^[A-F][.)]\\s/.test(option.textContent))')
    learner.locator('#listeningAudio').evaluate('audio => audio.load()')
    learner.wait_for_function('document.getElementById("listeningAudio").readyState >= 1')
    assert learner.locator('#listeningAudio').evaluate('audio => audio.duration > 10')
    learner.locator('.exam-workspace').screenshot(path=str(Path(__file__).resolve().parents[1] / 'frontend/assets/previews/ept-workspace.png'))
    learner.locator('#listeningAudio').evaluate('audio => audio.play()')
    learner.wait_for_function('!document.getElementById("listeningAudio").paused')
    learner.locator('#listeningMcContainer input').first.check()
    learner.locator('#listeningMcContainer [data-flag]').first.click()
    expect(learner.locator('#markedQuestionCount')).to_contain_text('1 ditandai')
    expect(learner.locator('#examProgressText')).to_contain_text('1 dari')
    learner.locator('#tabSec2').click()
    assert learner.locator('#listeningAudio').evaluate('audio => audio.paused')
    assert learner.locator('#readingGroupSelect option').count() >= 2
    learner.locator('#readingGroupSelect').select_option(index=0)
    first_passage = learner.locator('#readingPassageText').inner_text()
    learner.locator('#readingGroupSelect').select_option(index=1)
    assert learner.locator('#readingPassageText').inner_text() != first_passage
    learner.locator('#tabSec1').click()
    expect(learner.locator('#grammarMcContainer')).to_contain_text('The research team')
    learner.locator('#tabSec0').click()
    # Capture a real, non-private product workspace for the landing hero.
    learner.locator('#listeningAudio').evaluate('audio => { audio.pause(); audio.currentTime = 0; }')

    learner.screenshot(path=str(artifacts / 'listening-desktop.png'), full_page=True)
    learner.set_viewport_size({'width': 375, 'height': 812})
    assert learner.locator('.pane-right').bounding_box()['width'] >= 300
    assert not learner.locator('.question-navigation').evaluate('element => element.open')
    learner.locator('#listeningMcContainer').scroll_into_view_if_needed()
    assert learner.locator('.exam-session-header').bounding_box()['y'] <= 2
    learner.evaluate('window.scrollTo(0, 0)')
    learner.screenshot(path=str(artifacts / 'listening-mobile.png'), full_page=True)
    learner.reload()
    learner.wait_for_load_state('networkidle')
    expect(learner.locator('#markedQuestionCount')).to_contain_text('1 ditandai')
    expect(learner.locator('#examProgressText')).to_contain_text('1 dari')
    learner.close()
    landing = context.new_page()
    landing.route('**/assets/previews/*', lambda route: route.continue_())
    landing.goto(origin)
    landing.wait_for_load_state('networkidle')
    landing.locator('#moduleTab1').click()
    expect(landing.locator('#modulePanel1')).to_be_visible()
    expect(landing.locator('.hero-copy .btn-primary')).to_have_attribute('href', '/admin')
    landing.locator('#moduleTab1').press('ArrowRight')
    expect(landing.locator('#modulePanel2')).to_be_visible()
    landing.locator('#moduleTab0').click()
    expect(landing.locator('.sample-choice')).to_have_count(4)
    assert landing.evaluate('sampleQuestion.answer === undefined && sampleQuestion.explanation === undefined')
    sample_id = landing.evaluate('sampleQuestion.id')
    correct_answer = int(landing.evaluate("""async (id) => {
      for (let i = 0; i < 4; i++) {
        const res = await fetch('/api/sample-question', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id, choice: i }) });
        const data = await res.json();
        if (data.correct) return i;
      }
      return 0;
    }""", sample_id))
    landing.locator('.sample-choice').nth(correct_answer).click()
    expect(landing.locator('#sampleFeedback')).to_have_class(__import__('re').compile('is-correct'))
    assert landing.locator('#sampleFeedback').evaluate('(feedback) => Math.abs(feedback.clientWidth - document.getElementById("sampleOptions").clientWidth) <= 1')
    landing.locator('.sample-question').screenshot(path=str(artifacts / 'sample-feedback-wide.png'))
    for width, height in [(1440, 900), (1280, 800), (1920, 1080), (375, 812), (320, 740)]:
        landing.set_viewport_size({'width': width, 'height': height})
        landing.evaluate('window.scrollTo(0, 0)')
        expect(landing.locator('h1')).to_be_in_viewport()
        assert landing.evaluate('document.documentElement.scrollWidth <= innerWidth')
        landing.screenshot(path=str(artifacts / f'landing-{width}.png'), full_page=True)
        landing.screenshot(path=str(artifacts / f'hero-{width}.png'))
    landing.close()
    print('PASS: custom editor, preview/export, audio playback, flags, multiple passages, real hero capture', flush=True)
