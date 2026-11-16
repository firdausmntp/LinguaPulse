// History API routing with protected pages and direct-URL refresh support.
const routes = {
  '/': ['landing', 'Persiapan TOEFL EPT'],
  '/login': ['auth', 'Masuk'], '/register': ['auth', 'Daftar'],
  '/dashboard': ['dashboard', 'Dasbor peserta'], '/exam': ['prepare', 'Persiapan ujian'],
  '/practice': ['practice', 'Latihan bebas'],
  '/exam/session': ['exam', 'Ruang ujian'], '/results': ['results', 'Hasil latihan'],
  '/history': ['history', 'Riwayat latihan'], '/admin': ['admin', 'Panel pengawas'],
  '/admin/overview': ['admin', 'Panel pengawas - Ringkasan'],
  '/admin/proctor': ['admin', 'Panel pengawas - Pengawasan'],
  '/admin/questions': ['admin', 'Panel pengawas - Bank soal'],
  '/admin/users': ['admin', 'Panel pengawas - Akun pengguna'],
  '/privacy': ['privacy', 'Privasi & riset'], '/terms': ['terms', 'Syarat dan ketentuan']
};
const publicRoutes = new Set(['/', '/login', '/register', '/privacy', '/terms']);

async function navigate(url, replace = false) {
  if (appState.submitting) {
    showToast('Tunggu sampai jawaban selesai dikirim.');
    return;
  }
  const target = new URL(url, location.origin);
  if (target.origin !== location.origin) return;
  if (appState.route?.startsWith('/admin') && !target.pathname.startsWith('/admin') && !await confirmQuestionTransition()) return;
  if (appState.route === '/exam/session' && target.pathname !== '/exam/session' && appState.exam) {
    if (!confirm('Tinggalkan ruang ujian? Pengamatan dihentikan, tetapi waktu sesi tetap berjalan dan draf dapat dilanjutkan.')) return;
    saveExamDraft();
  }
  history[replace ? 'replaceState' : 'pushState']({}, '', target.pathname + target.search + target.hash);
  await renderRoute();
}

async function renderRoute() {
  const version = ++appState.routeVersion;
  let path = location.pathname.replace(/\/$/, '') || '/';
  const app = document.getElementById('app');
  if (!publicRoutes.has(path) && routes[path] && !appState.currentUser) {
    history.replaceState({}, '', '/login?next=' + encodeURIComponent(path));
    path = '/login';
  }
  if (['/login', '/register'].includes(path) && appState.currentUser) {
    history.replaceState({}, '', authDestination());
    return renderRoute();
  }
  if (appState.currentUser?.role === 'admin' && ['/dashboard', '/practice', '/exam', '/exam/session', '/history', '/results'].includes(path)) {
    history.replaceState({}, '', '/admin/overview');
    return renderRoute();
  }
  stopExamCountdown();
  setTelemetryActive(false);
  document.querySelectorAll('audio').forEach(audio => audio.pause());
  appState.route = path;
  const isAuthPage = path === '/login' || path === '/register';
  const isAdminRoute = path === '/admin' || path.startsWith('/admin/');
  const publicShell = publicRoutes.has(path) || !routes[path];
  closeSiteMenu();
  document.getElementById('siteMenuToggle').classList.toggle('hidden', !publicShell || isAuthPage);
  document.body.classList.toggle('is-exam', path === '/exam/session');
  document.body.classList.toggle('is-admin', isAdminRoute);
  document.querySelector('.site-header').classList.toggle('hidden', isAuthPage || isAdminRoute);
  document.getElementById('siteFooter').classList.toggle('hidden', isAuthPage || !publicShell);
  document.querySelector('.main-nav').classList.toggle('hidden', !publicShell);
  if (!routes[path]) {
    app.innerHTML = '<main id="mainContent" class="view-container not-found-page" tabindex="-1"><div class="not-found-code" aria-hidden="true">404</div><h1>Halaman tidak ditemukan</h1><p>Alamat mungkin berubah atau belum tersedia. Kembali ke beranda untuk menemukan materi dan latihan Anda.</p><div class="action-row"><a href="/" class="btn-primary">Kembali ke beranda</a><a href="/dashboard" class="btn-secondary">Buka ruang peserta</a></div></main>';
    document.title = 'Halaman tidak ditemukan | LinguaPulse';
    document.getElementById('mainContent').focus({ preventScroll: true });
    window.scrollTo(0, 0);
    return;
  }
  if (isAdminRoute && appState.currentUser.role !== 'admin') {
    app.innerHTML = '<main id="mainContent" class="view-container empty-state" tabindex="-1"><h1>Akses terbatas</h1><p>Halaman ini hanya dapat dibuka oleh pengawas.</p><a href="/dashboard" class="btn-primary">Ke dasbor peserta</a></main>';
    return;
  }
  const [page, title] = routes[path];
  document.title = title + ' | LinguaPulse';
  app.setAttribute('aria-busy', 'true');
  try {
    const response = await fetch('/pages/' + page + '.html');
    if (!response.ok) throw new Error('Halaman belum dapat dimuat. Silakan muat ulang.');
    const html = await response.text();
    if (version !== appState.routeVersion) return;
    app.innerHTML = html;
    decoratePageIcons();
    if (path === '/') loadSampleQuestion();
    if (path === '/login' || path === '/register') showAuthPage(path);
    if (path === '/dashboard') await initDashboard();
    if (path === '/practice') await initPractice();
    if (path === '/history') await loadHistory();
    if (path === '/results') await loadResults();
    if (path === '/exam') await initExamPreparation();
    if (path === '/exam/session') await initExamPage();
    if (isAdminRoute) {
      initAdminShell();
      initUserManagement();
      initQuestionEditor();
      initAdminComboboxes();
      const sub = path.replace(/^\/admin\/?/, '');
      const queryTab = new URLSearchParams(location.search).get('tab');
      const initialTab = sub || queryTab || 'overview';
      if (queryTab || path === '/admin') {
        history.replaceState({}, '', '/admin/' + initialTab);
        appState.route = '/admin/' + initialTab;
      }
      await switchAdminTab(initialTab, false);
    }
    const main = document.getElementById('mainContent') || document.querySelector('main');
    if (main && !location.hash) {
      main.setAttribute('tabindex', '-1');
      main.focus({ preventScroll: true });
    }
    if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
    else window.scrollTo(0, 0);
  } catch (error) {
    if (version === appState.routeVersion) renderError(app, error.message, renderRoute);
  } finally {
    if (version === appState.routeVersion) app.removeAttribute('aria-busy');
  }
}

document.addEventListener('click', event => {
  const link = event.target.closest('a[href]');
  if (!link || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || link.target || link.hasAttribute('download') || link.hasAttribute('data-download')) return;
  const url = new URL(link.href, location.origin);
  if (url.origin !== location.origin || url.pathname.startsWith('/api/')) return;
  event.preventDefault();
  if (url.pathname === location.pathname && url.search === location.search && url.hash) {
    history.pushState({}, '', url.hash);
    document.getElementById(url.hash.slice(1))?.scrollIntoView();
  } else navigate(url.href);
});
window.addEventListener('popstate', () => { saveExamDraft(); renderRoute(); });
window.addEventListener('beforeunload', event => {
  if (appState.route?.startsWith('/admin') && typeof questionEditor !== 'undefined' && questionEditor.dirty) {
    event.preventDefault(); event.returnValue = '';
  }
  if (appState.exam && appState.route === '/exam/session') {
    saveExamDraft();
    event.preventDefault();
    event.returnValue = '';
  }
});
window.addEventListener('DOMContentLoaded', async () => {
  initTelemetrySensors();
  try { await initAuthSession(); }
  catch (error) { showToast(error.message); }
  await renderRoute();
});
