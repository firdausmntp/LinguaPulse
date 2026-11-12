function decoratePageIcons() {
  const primary = document.querySelector('.hero-copy .btn-primary');
  if (primary) {
    primary.href = appState.currentUser ? (appState.currentUser.role === 'admin' ? '/admin' : '/practice') : '/register';
    if (appState.currentUser) primary.innerHTML = (appState.currentUser.role === 'admin' ? 'Buka panel admin ' : 'Mulai latihan bebas ') + icon('chevronRight');
  }
  document.querySelectorAll('[data-icon]').forEach(el => { el.innerHTML = icon(el.dataset.icon); });
}

function toggleSiteMenu() {
  const open = document.querySelector('.site-header').classList.toggle('menu-open');
  const button = document.getElementById('siteMenuToggle');
  button.setAttribute('aria-expanded', String(open));
  button.setAttribute('aria-label', open ? 'Tutup navigasi' : 'Buka navigasi');
}
function closeSiteMenu() {
  document.querySelector('.site-header').classList.remove('menu-open');
  const button = document.getElementById('siteMenuToggle');
  button?.setAttribute('aria-expanded', 'false');
  button?.setAttribute('aria-label', 'Buka navigasi');
}
document.addEventListener('click', event => { if (!event.target.closest('.site-header') || event.target.closest('#sitePublicNav a')) closeSiteMenu(); });
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && document.querySelector('.site-header.menu-open')) { closeSiteMenu(); document.getElementById('siteMenuToggle').focus(); }
});

function selectLandingModule(index, moveFocus = false) {
  [0, 1, 2].forEach(number => {
    const tab = document.getElementById('moduleTab' + number);
    const active = number === index;
    tab.setAttribute('aria-selected', String(active));
    tab.tabIndex = active ? 0 : -1;
    document.getElementById('modulePanel' + number).classList.toggle('hidden', !active);
    if (active && moveFocus) tab.focus();
  });
}

document.addEventListener('keydown', event => {
  const tab = event.target.closest('.module-tabs [role="tab"]');
  if (!tab || !['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  const current = Number(tab.id.replace('moduleTab', ''));
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? 2 : (current + (event.key === 'ArrowRight' ? 1 : 2)) % 3;
  selectLandingModule(next, true);
});

let sampleQuestion = null;
let sampleRequest = 0;
async function loadSampleQuestion() {
  const prompt = document.getElementById('samplePrompt');
  const options = document.getElementById('sampleOptions');
  const feedback = document.getElementById('sampleFeedback');
  if (!prompt) return;
  const requestId = ++sampleRequest;
  prompt.textContent = 'Memuat contoh soal…';
  options.replaceChildren();
  feedback.textContent = '';
  feedback.classList.remove('is-correct', 'is-incorrect');
  document.getElementById('sampleContinue')?.classList.add('hidden');
  try {
    let previous = sampleQuestion?.id;
    try { previous ||= sessionStorage.getItem('linguapulse_sample_id'); } catch (_) {}
    const url = '/api/sample-question' + (previous ? '?exclude=' + encodeURIComponent(previous) : '');
    const data = await api(url);
    if (requestId !== sampleRequest || !prompt.isConnected) return;
    sampleQuestion = data.question;
    if (!sampleQuestion) { prompt.textContent = 'Contoh soal belum tersedia.'; feedback.textContent = 'Silakan kembali lagi nanti.'; return; }
    try { sessionStorage.setItem('linguapulse_sample_id', sampleQuestion.id); } catch (_) {}
    prompt.textContent = sampleQuestion.prompt.replace(/\s*\[[A-F]\]\s*/gi, ' ');
    sampleQuestion.options.forEach((option, index) => {
      const button = document.createElement('button');
      const letter = document.createElement('span');
      const text = document.createElement('span');
      button.type = 'button'; button.className = 'sample-choice';
      letter.className = 'sample-letter'; letter.textContent = String.fromCharCode(65 + index);
      text.textContent = choiceText(option); button.append(letter, text);
      button.addEventListener('click', () => answerSample(button, index));
      options.append(button);
    });
    feedback.textContent = 'Pilih jawaban untuk melihat pembahasan.';
  } catch (_) {
    if (prompt.isConnected) { prompt.textContent = 'Contoh soal belum dapat dimuat.'; feedback.textContent = 'Periksa koneksi lalu muat ulang halaman untuk mencoba kembali.'; }
  }
}

async function answerSample(button, index) {
  if (!sampleQuestion?.id) return;
  const questionId = sampleQuestion.id;
  document.querySelectorAll('.sample-choice').forEach(item => {
    item.classList.remove('is-selected', 'is-correct', 'is-incorrect'); item.setAttribute('aria-pressed', 'false');
  });
  button.classList.add('is-selected'); button.setAttribute('aria-pressed', 'true');
  const feedback = document.getElementById('sampleFeedback');
  try {
    const result = await api('/api/sample-question', { method: 'POST', body: JSON.stringify({ id: questionId, choice: index }) });
    if (!button.isConnected || sampleQuestion?.id !== questionId) return;
    const correct = !!result.correct;
    button.classList.add(correct ? 'is-correct' : 'is-incorrect');
    feedback.classList.toggle('is-correct', correct);
    feedback.classList.toggle('is-incorrect', !correct);
    document.getElementById('sampleContinue')?.classList.remove('hidden');
    feedback.textContent = correct ? 'Tepat. ' + (result.explanation || 'Jawaban Anda benar.') : 'Belum tepat. Coba pilihan lain.';
    if (!matchMedia('(prefers-reduced-motion: reduce)').matches && feedback.animate) {
      feedback.animate([{ opacity: 0.35, transform: 'translateY(4px)' }, { opacity: 1, transform: 'translateY(0)' }], { duration: 240, easing: 'ease-out' });
    }
  } catch (error) {
    if (feedback?.isConnected) feedback.textContent = error.message || 'Jawaban belum dapat diperiksa.';
  }
}
