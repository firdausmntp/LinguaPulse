"""Render every page/state for a visual audit without modifying the real database."""
import json
import sys
import tempfile
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'docs/qa' / (sys.argv[1] if len(sys.argv) > 1 else 'audit-2026-11-11')
OUT.mkdir(parents=True, exist_ok=True)
METRICS = (ROOT / 'tests/audit_metrics.js').read_text(encoding='utf-8')
records = []
errors = []


def capture(page, name):
    for width, height in ((1440, 900), (375, 812), (320, 812)):
        page.set_viewport_size({'width': width, 'height': height})
        page.evaluate('scrollTo(0,0)')
        page.screenshot(path=str(OUT / f'{name}-{width}-full.png'), full_page=True, animations='disabled')
        page.screenshot(path=str(OUT / f'{name}-{width}.png'), animations='disabled')
        records.append({'name': name, **page.evaluate(METRICS)})
    page.set_viewport_size({'width': 1440, 'height': 900})
    print('Captured:', name, flush=True)


def visit(page, origin, route, name):
    page.goto(origin + route)
    page.wait_for_load_state('networkidle')
    capture(page, name)


def montage():
    from PIL import Image, ImageOps, ImageDraw
    names = list(dict.fromkeys(row['name'] for row in records))
    for start in range(0, len(names), 6):
        batch = names[start:start+6]
        canvas = Image.new('RGB', (1440, 1452), 'white')
        draw = ImageDraw.Draw(canvas)
        for index, name in enumerate(batch):
            x, y = (index % 2)*720, (index//2)*484
            draw.text((x+12, y+8), name, fill='black')
            im = Image.open(OUT / f'{name}-1440.png').convert('RGB')
            im.thumbnail((720,450))
            canvas.paste(im,(x,y+28))
        canvas.save(OUT/f'desktop-sheet-{start//6+1}.png')
    for start in range(0, len(names), 6):
        batch=names[start:start+6]
        canvas=Image.new('RGB',(1125,1684),'white')
        draw=ImageDraw.Draw(canvas)
        for index,name in enumerate(batch):
            x,y=(index%3)*375,(index//3)*842
            draw.text((x+8,y+6),name,fill='black')
            canvas.paste(Image.open(OUT/f'{name}-375.png').convert('RGB'),(x,y+26))
        canvas.save(OUT/f'mobile-sheet-{start//6+1}.png')


def run():
    from backend import config
    with tempfile.TemporaryDirectory(prefix='linguapulse-audit-') as tmp:
        config.DATA_DIR=Path(tmp)
        config.DB_PATH=Path(tmp)/'audit.db'
        from backend.database import init_schema
        from backend.seed_data import seed_all
        from backend.router import TOEFLPlatformRouter
        import questions.loader as loader
        loader.SECTION_FILES={key:Path(tmp)/path.name for key,path in loader.SECTION_FILES.items()}
        init_schema()
        seed_all()
        class QuietRouter(TOEFLPlatformRouter):
            def log_message(self,*args):
                pass
        server=ThreadingHTTPServer(('127.0.0.1',0),QuietRouter)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        origin=f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True)
                def context():
                    c=browser.new_context(viewport={'width':1440,'height':900})
                    c.on('page',lambda page: page.on('pageerror',lambda error: errors.append(str(error))))
                    return c
                public=context()
                page=public.new_page()
                for route,name in (('/', 'landing'),('/login','login'),('/register','register'),('/privacy','privacy'),('/terms','terms'),('/missing-page','not-found')):
                    visit(page,origin,route,name)
                student=context()
                student.request.post(origin+'/api/auth/login',data={'identifier':'nadia_putri','password':'student123'})
                learner=student.new_page()
                learner.on('dialog',lambda dialog:dialog.accept())
                for route,name in (('/dashboard','dashboard-empty'),('/history','history-empty'),('/results','results-empty'),('/exam','prepare')):
                    visit(learner,origin,route,name)
                for module in ('grammar','listening','reading'):
                    visit(learner,origin,'/practice?module='+module,'practice-'+module)
                learner.locator('[data-choice="0"]').click()
                learner.locator('#practiceCheck').click()
                capture(learner,'practice-feedback')
                admin=context()
                admin.request.post(origin+'/api/auth/login',data={'identifier':'admin','password':'admin123'})
                manager=admin.new_page()
                for route,name in (('/admin','admin-overview-empty'),('/admin?tab=proctor','admin-proctor-empty'),('/admin?tab=questions','admin-questions'),('/admin?tab=users','admin-users')):
                    visit(manager,origin,route,name)
                manager.get_by_role('button',name='Tambah akun',exact=True).click()
                capture(manager,'admin-user-editor')
                manager.get_by_role('button',name='Tutup editor akun',exact=True).click()
                learner.goto(origin+'/exam')
                learner.wait_for_load_state('networkidle')
                learner.locator('#examConsent').check()
                learner.locator('#beginExamButton').click()
                learner.wait_for_url('**/exam/session')
                expect(learner.locator('#listeningMcContainer input').first).to_be_visible()
                for index,name in enumerate(('exam-listening','exam-structure','exam-reading','exam-writing')):
                    learner.locator('#tabSec'+str(index)).click()
                    capture(learner,name)
                learner.locator('#essayEditor').fill('Independent practice helps students identify recurring mistakes and improve comprehension. Careful review connects the correct answer to its explanation.')
                learner.locator('#tabSec1').click()
                learner.locator('#grammarMcContainer input').first.check()
                learner.locator('#submitExamButton').click()
                learner.wait_for_url('**/results?id=*')
                expect(learner.locator('.accuracy-value')).to_be_visible()
                capture(learner,'results-populated')
                visit(learner,origin,'/history','history-populated')
                visit(learner,origin,'/dashboard','dashboard-populated')
                visit(manager,origin,'/admin','admin-overview-populated')
                visit(manager,origin,'/admin?tab=proctor','admin-proctor-populated')
                manager.locator('[data-inspect-index]').first.click()
                manager.locator('.monitor-analysis summary').click()
                capture(manager,'admin-proctor-detail')
                manager.goto(origin+'/admin?tab=questions')
                manager.wait_for_load_state('networkidle')
                manager.get_by_role('button',name='Tambah soal',exact=True).click()
                capture(manager,'admin-question-editor')
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
    (OUT/'metrics.json').write_text(json.dumps({'pages':records,'browserErrors':errors},indent=2,ensure_ascii=False),encoding='utf-8')
    montage()
    print('Audit complete:',len(records),'renders; browser errors:',len(errors),flush=True)


if __name__=='__main__':
    run()
