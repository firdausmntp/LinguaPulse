// Untimed practice is separate from exam attempts, scores, drafts and sensors.
const practiceState = { section: 'grammar', question: null, choice: null, checked: false, request: 0, previous: {}, completed: 0 };
const practiceLabels = { grammar: 'Structure', listening: 'Listening', reading: 'Reading' };
const practiceNarrow = matchMedia('(max-width: 900px)');
practiceNarrow.addEventListener('change', () => syncPracticePane());
function initPractice() {
  practiceState.completed = 0;
  const section = new URLSearchParams(location.search).get('module');
  return selectPracticeModule(practiceLabels[section] ? section : 'grammar');
}
async function selectPracticeModule(section, focusQuestion = false) {
  if (!practiceLabels[section]) return;
  document.querySelectorAll('.practice-page audio').forEach(audio => audio.pause());
  practiceState.section = section; practiceState.choice = null; practiceState.checked = false; practiceState.question = null;
  document.querySelectorAll('.practice-modules button').forEach(button => button.setAttribute('aria-pressed', String(button.id.toLowerCase().endsWith(section))));
  history.replaceState({}, '', '/practice?module=' + section);
  const el = document.getElementById('practiceContent');
  const request = ++practiceState.request;
  el.innerHTML = '<div class="practice-loading">Menyiapkan soal ' + practiceLabels[section] + '…</div>';
  el.setAttribute('aria-busy', 'true');
  try {
    const data = await api('/api/practice/question?section=' + section + '&exclude=' + encodeURIComponent(practiceState.previous[section] || ''));
    if (!el.isConnected || request !== practiceState.request) return;
    practiceState.question = data.question;
    if (!data.question) {
      el.innerHTML = '<div class="empty-state"><h2>Materi ini belum tersedia</h2><p>Pilih modul lain untuk melanjutkan latihan.</p></div>';
      return;
    }
    practiceState.previous[section] = data.question.id;
    renderPracticeQuestion(data.total);
    if (focusQuestion) {
      const prompt = document.getElementById('practicePrompt');
      prompt.focus({ preventScroll: true });
      prompt.scrollIntoView({ block: 'start', behavior: 'instant' });
    }
  } catch (error) { if (el.isConnected && request === practiceState.request) renderError(el, error.message, () => selectPracticeModule(section)); }
  finally { if (request === practiceState.request) el.removeAttribute('aria-busy'); }
}
function renderPracticeQuestion(total) {
  const { question: q, section } = practiceState;
  const context = section === 'reading' ? `<aside class="practice-context"><h2>Bacaan</h2><h3>${escapeHtml(q.title || 'Reading passage')}</h3><div class="practice-passage">${escapeHtml(readablePassage(q.passage))}</div></aside>` : section === 'listening' ? `<aside class="practice-context"><span class="practice-context-icon">${icon('headphones')}</span><h2>Dengarkan rekamannya</h2><p>Putar audio sebelum menjawab. Anda boleh memutarnya kembali.</p><audio controls preload="metadata" src="${escapeHtml(q.audio_url || '')}" aria-label="Audio soal Listening"></audio><p class="practice-audio-status" role="status"></p></aside>` : '';
  const switcher = context ? `<nav class="practice-pane-switch" aria-label="Materi dan soal"><button type="button" id="practicePaneQuestion" aria-pressed="true" onclick="showPracticePane('question')">Soal &amp; jawaban</button><button type="button" id="practicePaneContext" aria-pressed="false" onclick="showPracticePane('context')">${section === 'reading' ? 'Bacaan' : 'Audio Listening'}</button></nav>` : '';
  document.getElementById('practiceContent').innerHTML = `${switcher}<div class="practice-grid ${section === 'grammar' ? 'practice-single' : ''}" data-pane="question">${context}<section class="practice-question" aria-labelledby="practicePrompt"><div class="practice-question-meta"><span>${practiceLabels[section]}</span><span>${total} soal tersedia</span></div><h2 id="practicePrompt" tabindex="-1">${escapeHtml(q.prompt.replace(/\s*\[[A-F]\]\s*/gi, ' '))}</h2><fieldset class="practice-options"><legend class="sr-only">Pilih satu jawaban</legend>${q.options.map((option, index) => `<label class="practice-option" data-choice="${index}"><input type="radio" name="practiceAnswer" value="${index}"><span class="practice-letter">${String.fromCharCode(65 + index)}</span><span>${escapeHtml(choiceText(option))}</span><span class="practice-option-status"></span></label>`).join('')}</fieldset><div id="practiceFeedback" class="practice-feedback hidden" role="status" tabindex="-1"></div><div class="practice-question-actions"><p id="practiceHint">Pilih jawaban yang paling tepat.</p><div class="practice-action-buttons"><button type="button" id="practiceSkip" class="btn-secondary" onclick="selectPracticeModule(practiceState.section, true)">Lewati</button><button type="button" id="practiceCheck" class="btn-primary" disabled onclick="checkPracticeAnswer()">Periksa jawaban</button><button type="button" id="practiceNext" class="btn-primary hidden" onclick="selectPracticeModule(practiceState.section, true)">Soal berikutnya ${icon('chevronRight')}</button></div></div></section></div>`;
  document.querySelectorAll('[name="practiceAnswer"]').forEach(input => input.addEventListener('change', () => {
    practiceState.choice = Number(input.value);
    document.querySelectorAll('.practice-option').forEach(option => option.classList.toggle('is-selected', Number(option.dataset.choice) === practiceState.choice));
    document.getElementById('practiceCheck').disabled = false;
  }));
  const audio = document.querySelector('.practice-context audio');
  audio?.addEventListener('error', () => { document.querySelector('.practice-audio-status').textContent = 'Audio belum dapat diputar. Periksa koneksi atau coba soal berikutnya.'; });
  syncPracticePane();
}
function showPracticePane(pane) {
  const grid = document.querySelector('.practice-grid');
  if (!grid) return;
  grid.dataset.pane = pane;
  syncPracticePane();
  if (practiceNarrow.matches) grid.scrollIntoView({ block: 'start', behavior: 'instant' });
}
function syncPracticePane() {
  const grid = document.querySelector('.practice-grid');
  if (!grid) return;
  const context = grid.querySelector('.practice-context');
  const question = grid.querySelector('.practice-question');
  const showContext = grid.dataset.pane === 'context';
  document.getElementById('practicePaneQuestion')?.setAttribute('aria-pressed', String(!showContext));
  document.getElementById('practicePaneContext')?.setAttribute('aria-pressed', String(showContext));
  if (context) { context.inert = practiceNarrow.matches && !showContext; context.setAttribute('aria-hidden', String(context.inert)); }
  question.inert = practiceNarrow.matches && !!context && showContext;
  question.setAttribute('aria-hidden', String(question.inert));
}
async function checkPracticeAnswer() {
  const { question, choice } = practiceState;
  if (!question || choice === null || practiceState.checked) return;
  const checkBtn = document.getElementById('practiceCheck');
  checkBtn.disabled = true;
  try {
    const result = await api('/api/practice/question', { method: 'POST', body: JSON.stringify({ id: question.id, choice }) });
    if (practiceState.question?.id !== question.id || practiceState.checked) return;
    practiceState.checked = true; practiceState.completed++;
    const correct = !!result.correct;
    const answer = Number(result.answer);
    document.querySelectorAll('.practice-option').forEach(option => {
      const index = Number(option.dataset.choice);
      option.querySelector('input').disabled = true;
      option.classList.toggle('is-correct', index === answer);
      option.classList.toggle('is-incorrect', index === choice && !correct);
      option.querySelector('.practice-option-status').textContent = index === answer ? 'Benar' : index === choice ? 'Pilihan Anda' : '';
    });
    const feedback = document.getElementById('practiceFeedback');
    feedback.className = 'practice-feedback ' + (correct ? 'is-correct' : 'is-incorrect');
    feedback.innerHTML = `<strong>${icon(correct ? 'check' : 'alert')}${correct ? 'Tepat, Anda memahami polanya.' : 'Belum tepat. Mari lihat alasannya.'}</strong><p>Jawaban benar: <b>${String.fromCharCode(65 + answer)}. ${escapeHtml(choiceText(question.options[answer]))}</b></p><p>${escapeHtml(result.explanation || 'Perhatikan konteks pertanyaan dan bandingkan kembali setiap pilihan jawaban.')}</p>`;
    checkBtn.classList.add('hidden');
    document.getElementById('practiceSkip').classList.add('hidden');
    document.getElementById('practiceNext').classList.remove('hidden');
    document.getElementById('practiceHint').textContent = 'Baca pembahasannya sebelum beralih.';
    document.getElementById('practiceSessionCount').textContent = practiceState.completed + ' soal diperiksa selama kunjungan ini.';
    feedback.focus({ preventScroll: true });
  } catch (error) {
    checkBtn.disabled = false;
    showToast(error.message || 'Jawaban belum dapat diperiksa.');
  }
}
