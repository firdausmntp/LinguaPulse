"""Admin authoring through participant review using browser UI and disposable data."""
import json
import os
import re
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mysql_support import temporary_database

TRANSCRIPT = ('Attention students. The university library will close at six p.m. this Friday for scheduled '
              'maintenance. If you need to borrow a book, please visit the circulation desk before five thirty. '
              'The library will reopen at nine a.m. on Saturday. Study rooms in the student center will remain '
              'available during the closure.')


def visit(page, base, route):
    if os.environ.get('LINGUAPULSE_NVDA_TEST') == '1':
        page.bring_to_front()
    page.goto(base + route)
    page.wait_for_load_state('networkidle')


def login(page, base, username, password):
    visit(page, base, '/login')
    page.locator('#loginIdentifier').fill(username)
    page.locator('#loginPassword').fill(password)
    page.locator('#loginPassword').press('Enter')
    expect(page.locator('#loginForm')).to_have_count(0)
    page.wait_for_load_state('networkidle')


def create_question(page, base, module, qid, prompt):
    visit(page, base, '/admin/questions')
    page.get_by_role('button', name='Tambah soal', exact=True).click()
    module_combo = page.locator('#qFormSection-combo')
    module_combo.fill({'listening': 'Listening', 'grammar': 'Structure', 'reading': 'Reading'}[module])
    module_combo.press('ArrowDown')
    module_combo.press('Enter')
    expect(page.locator('#qFormSection')).to_have_value(module)
    page.locator('#qFormId').fill(qid)
    page.locator('#qFormTitle').fill(f'Materi uji {module}')
    page.locator('#qFormPrompt').fill(prompt)
    if module == 'listening':
        page.locator('#saveQuestionButton').click()
        expect(page.locator('#qFormAudio')).to_be_focused()
        expect(page.locator('#qFormAudio')).to_have_attribute('aria-invalid', 'true')
        expect(page.locator('#qFormPrompt')).to_have_value(prompt)
        audio = ROOT / 'frontend/media/listening/library-announcement.wav'
        page.locator('#qFormAudioFile').set_input_files(audio)
        expect(page.locator('#qFormAudio')).to_have_value(re.compile(r'^/media/uploads/'))
        page.locator('#qFormPassage').fill(TRANSCRIPT)
    elif module == 'reading':
        page.locator('#qFormPassage').fill('Many birds migrate to a warmer region in winter.')
    options = ('Before five thirty', 'Before noon', 'After closing', 'Saturday')
    if module == 'grammar':
        options = ('studies', 'study', 'studying', 'studied')
    elif module == 'reading':
        options = ('A warmer region', 'A city library', 'A computer lab', 'A classroom')
    for index, value in enumerate(options):
        page.locator(f'#questionOption{index}').fill(value)
    page.locator('#qFormExplanation').fill('The first choice matches the material.')
    page.locator('#saveQuestionButton').click()
    expect(page.locator('#questionEditorStatus')).to_contain_text(f'{qid} tersimpan')


def publish_package(admin, base):
    visit(admin, base, '/admin/packages')
    admin.locator('#newPackageButton').click()
    admin.locator('#packageName').fill('Simulasi aksesibilitas')
    admin.locator('#packageDuration').fill('0')
    admin.locator('#savePackageButton').click()
    expect(admin.locator('#packageDuration')).to_be_focused()
    expect(admin.locator('#packageDuration-error')).to_contain_text('1 sampai 240')
    admin.locator('#packageDuration').fill('20')
    admin.locator('#packagePublished').check()
    for qid in ('qa-listening', 'qa-structure', 'qa-reading'):
        admin.locator(f'[data-package-question="{qid}"]').check()
    admin.locator('#savePackageButton').click()
    expect(admin.locator('#packageSaveStatus')).to_contain_text('tersedia untuk peserta')
    return admin.locator('[data-edit-package]').filter(has_text='Simulasi aksesibilitas').get_attribute('data-edit-package')


def register(learner, base):
    visit(learner, base, '/register')
    learner.locator('#regDisplayName').fill('Peserta Pengujian')
    learner.locator('#regUsername').fill('qa_peserta')
    learner.locator('#regEmail').fill('qa@example.test')
    learner.locator('#regPassword').fill('testpassword123')
    learner.locator('#regConfirm').fill('mismatch678')
    learner.locator('#regTerms').check()
    learner.get_by_role('button', name='Buat akun peserta', exact=True).click()
    expect(learner.locator('#regConfirm')).to_be_focused()
    expect(learner.locator('#regConfirm-error')).to_have_text('Masukkan kembali kata sandi yang sama.')
    expect(learner.locator('#regConfirm')).to_have_accessible_description(re.compile('kata sandi yang sama'))
    expect(learner.locator('#regEmail')).to_have_value('qa@example.test')
    learner.locator('#regConfirm').fill('testpassword123')
    learner.locator('#regConfirm').press('Enter')
    learner.wait_for_url('**/dashboard')


def create_schedule(admin, base, package_id):
    visit(admin, base, '/admin/schedules')
    admin.locator('#newScheduleButton').click()
    admin.locator('#scheduleTitle').fill('Gelombang pengujian aksesibilitas')
    admin.locator('#scheduleCode').fill('AKSES-01')
    admin.locator('#schedulePackage').select_option(package_id)
    admin.locator('#saveScheduleButton').click()
    expect(admin.locator('#scheduleSaveStatus')).to_contain_text('aktif')
    return admin.locator('[data-edit-schedule]').filter(has_text='AKSES-01').get_attribute('data-edit-schedule')


def set_accommodation(admin, minutes, transcript):
    if os.environ.get('LINGUAPULSE_NVDA_TEST') == '1':
        admin.bring_to_front()
    admin.locator('#accommodationUser').fill('qa_peserta')
    admin.locator('#accommodationMinutes').fill(str(minutes))
    admin.locator('#accommodationTranscript').set_checked(transcript)
    admin.get_by_role('button', name='Simpan akomodasi').click()
    expect(admin.locator('#accommodationStatus')).to_contain_text('tersimpan' if minutes or transcript else 'dihapus')


def check_exam(admin, learner, other, base, schedule_id):
    visit(learner, base, '/exam')
    learner.locator('#sessionCodeInput').fill('SALAH')
    learner.locator('#sessionCodeInput').press('Enter')
    expect(learner.locator('#sessionCodeInput-error')).to_contain_text('Kode tidak ditemukan')
    learner.locator('#sessionCodeInput').fill('akses-01')
    learner.locator('#sessionCodeInput').press('Enter')
    expect(learner.locator('#prepareDuration')).to_contain_text('35 menit (20 menit paket + 15 menit tambahan)')
    expect(learner.locator('#prepareListeningAccommodation')).to_be_visible()
    learner.locator('#beginExamButton').click()
    expect(learner.locator('#examConsent')).to_be_focused()
    learner.locator('#examConsent').press('Space')
    with learner.expect_response(lambda r: r.url.endswith('/api/exam/start')) as start_response:
        learner.locator('#beginExamButton').click()
    started = start_response.value.json()
    learner.wait_for_url('**/exam/session')
    expect(learner.locator('#listeningAudio')).to_be_visible()
    expect(learner.locator('.q-card:visible')).to_be_visible()
    learner.wait_for_function('document.querySelector("#listeningAudio").duration > 0')
    learner.locator('#listeningAudio').evaluate('async audio => { await audio.play(); audio.pause(); }')
    learner.locator('#listeningTranscript summary').press('Enter')
    expect(learner.locator('#listeningTranscriptText')).to_have_text(TRANSCRIPT)
    assert 34.8 < (started['deadline'] / 1000 - time.time()) / 60 <= 35.1
    assert started['bank']['schedule']['extra_minutes'] == 15
    assert started['bank']['listening']['questions'][0]['transcript'] == TRANSCRIPT
    assert other.request.get(base + '/api/admin/time-accommodations?schedule_id=' + schedule_id).status == 403
    other_schedule = next(s for s in other.request.get(base + '/api/exam/schedules').json()['schedules']
                          if s['schedule_id'] == schedule_id)
    assert other_schedule['extra_minutes'] == 0
    assert not other_schedule['listening_transcript']
    assert TRANSCRIPT not in other.request.get(base + '/api/exam/packages?id=' + other_schedule['package_id']).text()
    other_start = other.request.post(base + '/api/exam/start', data={'schedule_id': schedule_id,
        'device_profile': 'PC_PHYSICAL', 'consent_agreed': True, 'extra_minutes': 240,
        'listening_transcript': True}).json()
    assert 19.8 < (other_start['deadline'] / 1000 - time.time()) / 60 <= 20.1
    assert 'transcript' not in other_start['bank']['listening']['questions'][0]
    assert not other.request.get(base + '/api/exam/resume?id=' + started['attempt_id']).ok
    set_accommodation(admin, 0, False)
    expect(admin.locator('#accommodationList li')).to_have_count(0)
    resumed = learner.request.get(base + '/api/exam/resume?id=' + started['attempt_id'])
    assert resumed.json()['deadline'] == started['deadline'] and TRANSCRIPT in resumed.text()
    if os.environ.get('LINGUAPULSE_NVDA_TEST') == '1':
        learner.bring_to_front()
    learner.get_by_role('radio', name='Before five thirty').press('Space')
    expect(learner.get_by_role('radio', name='Before five thirty')).to_be_checked()
    learner.locator('#nextQuestion').press('Enter')
    learner.get_by_role('radio', name='studies', exact=True).press('Space')
    learner.locator('#nextQuestion').press('Enter')
    learner.get_by_role('radio', name='A warmer region').press('Space')
    learner.on('dialog', lambda dialog: dialog.accept())
    learner.locator('#submitExamButton').click()
    learner.wait_for_url('**/results?id=*')
    expect(learner.locator('.accuracy-value')).to_have_text('100%')
    expect(learner.get_by_text('Akses transkrip Listening diberikan pada sesi ini.')).to_be_visible()
    assert TRANSCRIPT not in learner.request.get(base + '/api/exam/resume?id=' + started['attempt_id']).text()
    learner.get_by_text('Transkrip audio', exact=True).click()
    expect(learner.locator('.audio-transcript')).to_have_text(TRANSCRIPT)
    learner.get_by_label('Audio soal yang ditinjau').evaluate('async audio => { await audio.play(); audio.pause(); }')
    result_path = learner.url.removeprefix(base)
    # Reproduce a result saved before transcript support, then reload through the API.
    from backend.database import get_connection
    session_id = 'SES-' + started['attempt_id']
    with get_connection() as conn:
        saved = conn.execute('SELECT result_json FROM submission_results WHERE session_id=%s', (session_id,)).fetchone()
        result = json.loads(saved['result_json'])
        for item in result['toefl_practice_result']['section_reviews']['listening']:
            item.pop('transcript')
        conn.execute('UPDATE submission_results SET result_json=%s WHERE session_id=%s', (json.dumps(result), session_id))
    old_review = learner.request.get(base + '/api/results?id=' + session_id).json()
    assert old_review['toefl_practice_result']['section_reviews']['listening'][0]['transcript'] == TRANSCRIPT
    visit(learner, base, '/history')
    expect(learner.locator(f'.history-cards a[href="{result_path}"]')).to_be_visible()


def run():
    from backend import config, audio_upload
    from backend.database import init_schema
    from backend.router import TOEFLPlatformRouter
    from backend.seed_data import seed_all
    from question_fixtures import seed_test_questions

    class QuietRouter(TOEFLPlatformRouter):
        def log_message(self, *_args):
            pass

        def translate_path(self, path):
            if path.startswith('/media/uploads/'):
                return str(audio_upload.MEDIA_DIR / Path(path).name)
            return super().translate_path(path)

    with temporary_database(), tempfile.TemporaryDirectory(prefix='accessible-workflow-') as directory:
        config.DATA_DIR = Path(directory)
        audio_upload.MEDIA_DIR = config.DATA_DIR / 'uploads'
        init_schema()
        seed_all()
        seed_test_questions()
        server = ThreadingHTTPServer(('127.0.0.1', 0), QuietRouter)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as playwright:
                headed = os.environ.get('LINGUAPULSE_NVDA_TEST') == '1'
                browser = playwright.chromium.launch(headless=not headed, args=['--force-renderer-accessibility'])
                admin = browser.new_page(viewport={'width': 1280, 'height': 900})
                learner = browser.new_page(viewport={'width': 375, 'height': 812})
                other = browser.new_context()
                errors = []
                for page in (admin, learner):
                    page.on('pageerror', lambda error: errors.append(str(error)))
                login(admin, base, 'admin', 'admin123')
                create_question(admin, base, 'listening', 'qa-listening', 'When should borrowers visit the desk?')
                create_question(admin, base, 'grammar', 'qa-structure', 'She ______ every evening.')
                create_question(admin, base, 'reading', 'qa-reading', 'Where do many birds go?')
                package_id = publish_package(admin, base)
                register(learner, base)
                schedule_id = create_schedule(admin, base, package_id)
                set_accommodation(admin, 15, True)
                assert other.request.post(base + '/api/auth/login', data={'identifier': 'nadia_putri', 'password': 'student123'}).ok
                visit(learner, base, '/practice?module=listening')
                learner.locator('#practiceListeningFormat').select_option('transcript')
                learner.get_by_role('button', name='Transkrip', exact=True).click()
                expect(learner.get_by_role('region', name='Teks transkrip')).to_be_visible()
                assert not learner.evaluate('telemetryActive')
                assert 'region "Teks transkrip"' in learner.get_by_role('region', name='Teks transkrip').aria_snapshot()
                check_exam(admin, learner, other, base, schedule_id)
                visit(admin, base, '/admin/proctor')
                expect(admin.get_by_role('table')).to_contain_text('AKSES-01')
                admin.get_by_role('region', name='Tabel sesi peserta', exact=True).focus()
                expect(admin.get_by_role('region', name='Tabel sesi peserta', exact=True)).to_be_focused()
                assert not errors, errors
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
    print('PASS: authoring, upload, publishing, text practice, individual grants, active transcript, exam and review')


if __name__ == '__main__':
    run()
