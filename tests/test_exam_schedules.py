"""Scheduled cohort CRUD, deadline enforcement, scenario hiding, and triage checks."""
from datetime import datetime, timedelta
from http.server import ThreadingHTTPServer
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright, expect
from mysql_support import temporary_database
from question_fixtures import seed_test_questions
from backend import config
from backend.database import init_schema
from backend.database import get_connection
from backend.seed_data import seed_all
from backend.router import TOEFLPlatformRouter
from backend.exam_schedules import classify_triage_status, delete_schedule, list_schedules, save_schedule
from backend.attempts import resume_attempt, start_attempt


def _iso_offset(hours=0, minutes=0):
    dt = datetime.now().astimezone() + timedelta(hours=hours, minutes=minutes)
    return dt.isoformat(timespec='minutes')


class ExamScheduleTests(unittest.TestCase):
    def setUp(self):
        self.db = temporary_database()
        self.db.__enter__()
        self.addCleanup(self.db.__exit__, None, None, None)
        init_schema()
        seed_all()
        seed_test_questions()
        with get_connection() as conn:
            self.user = dict(conn.execute("SELECT * FROM users WHERE username='nadia_putri'").fetchone())

    def test_schedule_validation_and_privacy(self):
        created = save_schedule({
            'title': 'Gelombang Kelas A',
            'session_code': 'kelas-a1',
            'description': 'Kelas eksperimen',
            'package_id': 'PKG-EXPERIMENTAL',
            'task_condition': 'AI_PARAPHRASE',
            'opens_at': _iso_offset(hours=-1),
            'closes_at': _iso_offset(hours=2),
            'is_active': True,
        })['schedule']
        self.assertEqual(created['session_code'], 'KELAS-A1')
        self.assertEqual(created['window_state'], 'open')

        for bad in (
            {'session_code': 'KELAS-A1'},
            {'session_code': 'X', 'title': 'Pendek'},
            {'session_code': 'BAD-TIME', 'opens_at': _iso_offset(hours=3), 'closes_at': _iso_offset(hours=1)},
            {'session_code': 'BAD-PKG', 'package_id': 'PKG-MISSING'},
            {'session_code': 'BAD-COND', 'task_condition': 'INVALID'},
        ):
            with self.assertRaises(ValueError, msg=str(bad)):
                save_schedule({
                    'title': 'Uji Validasi', 'package_id': 'PKG-EXPERIMENTAL',
                    'task_condition': 'MANDIRI', 'is_active': True, **bad,
                })

        public_list = list_schedules(admin=False)['schedules']
        mine = next(item for item in public_list if item['schedule_id'] == created['schedule_id'])
        self.assertNotIn('task_condition', mine)
        self.assertNotIn('version', mine)
        self.assertTrue(mine['joinable'])

        with self.assertRaises(ValueError):
            save_schedule({
                'schedule_id': created['schedule_id'], 'version': 99, 'title': 'Stale',
                'session_code': 'KELAS-A1', 'package_id': 'PKG-EXPERIMENTAL',
                'task_condition': 'MANDIRI', 'is_active': True,
            })

    def test_window_enforcement_deadline_cap_and_delete(self):
        upcoming = save_schedule({
            'title': 'Gelombang Besok', 'session_code': 'BESOK-01', 'package_id': 'PKG-EXPERIMENTAL',
            'task_condition': 'MANDIRI', 'opens_at': _iso_offset(hours=2), 'closes_at': _iso_offset(hours=5), 'is_active': True,
        })['schedule']
        closed = save_schedule({
            'title': 'Gelombang Tutup', 'session_code': 'TUTUP-01', 'package_id': 'PKG-EXPERIMENTAL',
            'task_condition': 'MANDIRI', 'opens_at': _iso_offset(hours=-5), 'closes_at': _iso_offset(minutes=-5), 'is_active': True,
        })['schedule']
        for blocked in (upcoming['session_code'], closed['session_code'], 'TIDAK-ADA'):
            with self.assertRaises(ValueError):
                start_attempt(self.user, {'session_code': blocked, 'device_profile': 'PC_PHYSICAL', 'consent_agreed': True})

        closing_soon = save_schedule({
            'title': 'Gelombang Ketat', 'session_code': 'KETAT-01', 'package_id': 'PKG-EXPERIMENTAL',
            'task_condition': 'COPY_TYPING', 'opens_at': _iso_offset(minutes=-5), 'closes_at': _iso_offset(minutes=10), 'is_active': True,
        })['schedule']
        started = start_attempt(self.user, {
            'session_code': 'ketat-01', 'device_profile': 'PC_PHYSICAL', 'consent_agreed': True,
        })
        self.assertLessEqual(started['deadline'] / 1000 - time.time(), 10 * 60 + 65)
        self.assertEqual(started['bank']['schedule']['session_code'], 'KETAT-01')
        self.assertNotIn('task_condition', started['bank']['schedule'])
        resumed = resume_attempt(self.user, started['attempt_id'])
        self.assertEqual(resumed, started)
        with get_connection() as conn:
            row = conn.execute('SELECT task_condition, schedule_id, session_code FROM exam_attempts WHERE attempt_id=%s',
                               (started['attempt_id'],)).fetchone()
        self.assertEqual((row['task_condition'], row['schedule_id'], row['session_code']),
                         ('COPY_TYPING', closing_soon['schedule_id'], 'KETAT-01'))
        deleted = delete_schedule(closing_soon['schedule_id'])
        self.assertEqual(deleted['status'], 'ok')

    def test_triage_thresholds(self):
        self.assertEqual(classify_triage_status(0.15, 0), 'TIDAK_TERDETEKSI')
        self.assertEqual(classify_triage_status(0.45, 0), 'FLAG')
        self.assertEqual(classify_triage_status(0.20, 1), 'FLAG')
        self.assertEqual(classify_triage_status(0.62, 1), 'TERDETEKSI')
        self.assertEqual(classify_triage_status(0.75, 0), 'TERDETEKSI')

    def test_browser_schedule_flow_and_proctor_triage(self):
        class QuietRouter(TOEFLPlatformRouter):
            def log_message(self, *_args):
                pass
        with tempfile.TemporaryDirectory(prefix='sched-e2e-') as tmp:
            config.DATA_DIR = Path(tmp)
            server = ThreadingHTTPServer(('127.0.0.1', 0), QuietRouter)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            origin = f'http://127.0.0.1:{server.server_port}'
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    admin_ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
                    student_ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
                    errors = []
                    assert admin_ctx.request.post(origin + '/api/auth/login', data={'identifier': 'admin', 'password': 'admin123'}).ok
                    assert student_ctx.request.post(origin + '/api/auth/login', data={'identifier': 'nadia_putri', 'password': 'student123'}).ok
                    admin = admin_ctx.new_page()
                    learner = student_ctx.new_page()
                    admin.on('pageerror', lambda e: errors.append(str(e)))
                    learner.on('pageerror', lambda e: errors.append(str(e)))
                    admin.goto(origin + '/admin/schedules')
                    admin.wait_for_load_state('networkidle')
                    admin.locator('#newScheduleButton').click()
                    admin.locator('#scheduleTitle').fill('Gelombang Simulasi E2E')
                    admin.locator('#scheduleCode').fill('GEL-E2E-01')
                    admin.locator('#schedulePackage').select_option('PKG-EXPERIMENTAL')
                    admin.locator('#scheduleCondition').select_option('AI_PARAPHRASE')
                    admin.locator('#saveScheduleButton').click()
                    expect(admin.locator('#scheduleSaveStatus')).to_contain_text('aktif')
                    for w in (375, 320):
                        admin.set_viewport_size({'width': w, 'height': 812})
                        self.assertTrue(admin.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    learner.goto(origin + '/exam')
                    learner.wait_for_load_state('networkidle')
                    self.assertEqual(learner.locator('#taskCondition').count(), 0)
                    learner.locator('#sessionCodeInput').fill('gel-e2e-01')
                    learner.locator('#applySessionCodeButton').click()
                    expect(learner.locator('#sessionCodeFeedback')).to_contain_text('GEL-E2E-01')
                    learner.locator('#examConsent').check()
                    learner.locator('#beginExamButton').click()
                    learner.wait_for_url('**/exam/session')
                    expect(learner.locator('.q-card:visible')).to_have_count(1)
                    learner.on('dialog', lambda d: d.accept())
                    learner.locator('#submitExamButton').click()
                    learner.wait_for_url('**/results?id=*')
                    admin.set_viewport_size({'width': 1440, 'height': 900})
                    admin.goto(origin + '/admin/proctor')
                    admin.wait_for_load_state('networkidle')
                    expect(admin.locator('#proctorSessionsBody')).to_contain_text('GEL-E2E-01')
                    expect(admin.locator('#proctorSessionsBody')).to_contain_text('Tidak terdeteksi')
                    csv_resp = admin_ctx.request.get(origin + '/api/export/csv')
                    self.assertTrue(csv_resp.ok)
                    csv_head = csv_resp.text().splitlines()[0]
                    self.assertIn('session_code', csv_head)
                    self.assertIn('triage_status', csv_head)
                    self.assertFalse(errors, errors)
                    browser.close()
            finally:
                server.shutdown()
                server.server_close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
