// Shared state, safe rendering helpers and API errors.
const appState = {
  currentUser: null, questionsBank: null, selectedAnswers: {},
  proctorSessions: [], adminQuestionsList: [], exam: null, submitting: false,
  latestResult: null, route: '/', routeVersion: 0
};

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[ch]));
}

function choiceText(value) { return String(value ?? '').replace(/^\s*[A-F][.)]\s+/i, ''); }
function readablePassage(value) { return String(value ?? '').replace(/\\n/g, '\n'); }
function formatDateTime(value, options = {}) {
  const date = new Date(String(value || '').replace(' ', 'T'));
  if (Number.isNaN(date.getTime())) return String(value || 'Waktu tidak tersedia');
  return new Intl.DateTimeFormat('id-ID', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', ...options }).format(date);
}

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, { ...options, headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers
    }});
  } catch (_) { throw new Error('Koneksi terputus. Periksa jaringan lalu coba lagi.'); }
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/api/auth/')) {
      updateProfileUI(null);
      appState.submitting = false;
      navigate('/login?next=' + encodeURIComponent(location.pathname));
    }
    throw new Error(data.error || 'Permintaan gagal. Silakan coba lagi.');
  }
  return data;
}

function showToast(message) {
  const el = document.getElementById('toastBox');
  el.textContent = message;
  el.classList.remove('hidden');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => el.classList.add('hidden'), 5000);
}

function renderError(el, message, retry) {
  if (!el) return;
  el.innerHTML = `<div class="empty-state"><h2>Data belum dapat dimuat</h2><p>${escapeHtml(message)}</p><button type="button" class="btn-secondary">Coba lagi</button></div>`;
  el.querySelector('button').addEventListener('click', retry);
}

function switchView(view) {
  navigate({ hub: '/dashboard', exam: '/exam', admin: '/admin' }[view] || '/');
}
