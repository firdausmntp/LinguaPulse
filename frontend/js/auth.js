// Account pages use server-validated HttpOnly cookie sessions.
function getInitials(name) {
  return String(name || '').trim().split(/\s+/).slice(0, 2).map(s => s[0] || '').join('').toUpperCase();
}

function updateProfileUI(user) {
  const previous = appState.currentUser;
  if (previous && previous.user_id !== user?.user_id) {
    setTelemetryActive(false);
    saveExamDraft();
    stopExamCountdown();
    appState.exam = null;
    appState.selectedAnswers = {};
    appState.latestResult = null;
  }
  appState.currentUser = user;
  // Retire the old editable identity cookies and local storage.
  localStorage.removeItem('toefl_active_user');
  document.cookie = 'toefl_user=; path=/; max-age=0; SameSite=Lax';
  const el = document.getElementById('accountNav');
  el.innerHTML = user
    ? `<a href="${user.role === 'admin' ? '/admin/overview' : '/dashboard'}" class="nav-account"><span class="avatar" aria-hidden="true">${escapeHtml(getInitials(user.display_name))}</span><span>${user.role === 'admin' ? 'Panel admin' : 'Dasbor'}</span></a><button type="button" class="btn-secondary" onclick="handleLogout()">Keluar</button>`
    : '<a href="/login" class="nav-login">Masuk</a><a href="/register" class="btn-primary">Daftar</a>';
}

async function initAuthSession() {
  const data = await api('/api/auth/me');
  updateProfileUI(data.user);
}

function showAuthPage(path) {
  const register = path === '/register';
  document.getElementById('loginForm').classList.toggle('hidden', register);
  document.getElementById('registerForm').classList.toggle('hidden', !register);
  document.getElementById('tabLogin').setAttribute('aria-current', register ? 'false' : 'page');
  document.getElementById('tabRegister').setAttribute('aria-current', register ? 'page' : 'false');
  document.getElementById('authTitle').textContent = register ? 'Buat akun peserta' : 'Masuk ke akun Anda';
  document.getElementById('authDescription').textContent = register ? 'Simpan hasil latihan dalam akun pribadi Anda.' : 'Lanjutkan latihan dan tinjau hasil sebelumnya.';
  const panel = document.querySelector('.auth-workspace');
  panel.classList.toggle('auth-register', register);
  panel.querySelectorAll('input').forEach(input => input.addEventListener('input', () => {
    document.getElementById('authErrorMsg').classList.add('hidden');
  }));
  document.getElementById('regPassword').addEventListener('input', updatePasswordMatch);
  document.getElementById('regConfirm').addEventListener('input', updatePasswordMatch);
}

function updatePasswordMatch() {
  const password = document.getElementById('regPassword');
  const confirm = document.getElementById('regConfirm');
  const hint = document.getElementById('passwordMatch');
  if (!confirm.value) {
    hint.className = 'hidden'; confirm.removeAttribute('aria-invalid'); return;
  }
  const same = password.value === confirm.value;
  confirm.setAttribute('aria-invalid', String(!same));
  hint.className = same ? 'is-valid' : 'is-invalid';
  hint.textContent = same ? 'Kedua kata sandi sudah sama.' : 'Kedua kata sandi belum sama.';
}

function openAccountHelp() { document.getElementById('accountHelpDialog').showModal(); }

function togglePassword(id, button) {
  const input = document.getElementById(id);
  input.type = input.type === 'password' ? 'text' : 'password';
  button.textContent = input.type === 'password' ? 'Tampilkan' : 'Sembunyikan';
  button.setAttribute('aria-label', button.textContent + ' kata sandi');
  button.setAttribute('aria-pressed', String(input.type === 'text'));
}

function authDestination() {
  if (appState.currentUser?.role === 'admin') return '/admin/overview';
  const next = new URLSearchParams(location.search).get('next');
  return ['/dashboard', '/practice', '/exam', '/exam/session', '/history', '/results', '/admin', '/admin/overview', '/admin/questions', '/admin/proctor', '/admin/users'].includes(next)
    ? next : '/dashboard';
}

async function submitAuth(event, path, payload) {
  event.preventDefault();
  const form = event.currentTarget;
  const error = document.getElementById('authErrorMsg');
  const button = form.querySelector('[type="submit"]');
  if (button.disabled) return;
  const label = button.textContent;
  button.disabled = true;
  button.textContent = 'Memproses…';
  error.classList.add('hidden');
  form.setAttribute('aria-busy', 'true');
  try {
    const data = await api(path, { method: 'POST', body: JSON.stringify(payload) });
    updateProfileUI(data.user);
    await navigate(authDestination());
  } catch (err) {
    error.textContent = err.message;
    error.classList.remove('hidden');
    error.focus();
  } finally {
    button.disabled = false;
    button.textContent = label;
    form.removeAttribute('aria-busy');
  }
}

function handleLogin(event) {
  return submitAuth(event, '/api/auth/login', {
    identifier: document.getElementById('loginIdentifier').value,
    password: document.getElementById('loginPassword').value
  });
}

function handleRegister(event) {
  event.preventDefault();
  const password = document.getElementById('regPassword').value;
  if (password !== document.getElementById('regConfirm').value) {
    const error = document.getElementById('authErrorMsg');
    error.textContent = 'Kedua kata sandi belum sama. Periksa kembali.';
    error.classList.remove('hidden');
    document.getElementById('regConfirm').setAttribute('aria-invalid', 'true');
    error.focus();
    return;
  }
  return submitAuth(event, '/api/auth/register', {
    display_name: document.getElementById('regDisplayName').value,
    username: document.getElementById('regUsername').value,
    email: document.getElementById('regEmail').value, password, terms_accepted: document.getElementById('regTerms').checked
  });
}

async function handleLogout() {
  if (appState.submitting) return showToast('Tunggu sampai jawaban selesai dikirim.');
  if (appState.route === '/admin' && !await confirmQuestionTransition()) return;
  if (appState.exam && !confirm('Keluar dari akun? Sesi aktif akan dihentikan dan draf di perangkat ini dihapus.')) return;
  try {
    await api('/api/auth/logout', { method: 'POST', body: '{}' });
    clearExamDraft();
    appState.latestResult = null;
    updateProfileUI(null);
    navigate('/login');
  } catch (err) { showToast(err.message); }
}
