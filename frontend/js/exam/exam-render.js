// Render the four EPT/research sections without exposing answer keys.
const examRenderState = { questions: [], listeningGroups: [], readingGroups: [], listeningIndex: 0, readingIndex: 0 };
const examSectionNames = ['Listening', 'Structure', 'Reading', 'Writing riset'];
const examHeaderObserver = new ResizeObserver(entries => {
  for (const entry of entries) if (entry.target.isConnected) {
    document.documentElement.style.setProperty('--exam-status-height', entry.target.getBoundingClientRect().height + 'px');
  }
});

const examMobileViewport = matchMedia('(max-width: 1100px)');
const examNavigatorViewport = matchMedia('(max-width: 760px)');
examNavigatorViewport.addEventListener('change', () => {
  const navigation = document.querySelector('.question-navigation');
  if (navigation) navigation.open = !examNavigatorViewport.matches;
});
examMobileViewport.addEventListener('change', syncExamPane);

function groupExamQuestions(questions, key) {
  const groups = [];
  for (const question of questions) {
    const value = key(question);
    let group = groups.find(item => item.key === value);
    if (!group) { group = { key: value, title: question.title, items: [] }; groups.push(group); }
    group.items.push(question);
  }
  return groups;
}

function renderOptions(question) {
  return (question.options || []).map((option, index) => `<label class="q-option-label"><input type="radio" name="${escapeHtml(question.id)}" value="${index}" ${String(appState.selectedAnswers[question.id]) === String(index) ? 'checked' : ''}><span class="option-letter" aria-hidden="true">${String.fromCharCode(65 + index)}</span><span>${escapeHtml(choiceText(option))}</span></label>`).join('');
}

function flagIcon() {
  return '<svg aria-hidden="true" class="svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M5 22V3m0 0c5-4 9 4 14 0v11c-5 4-9-4-14 0"/></svg>';
}

function flagButton(question) {
  const marked = (appState.exam.marked || []).includes(question.id);
  return `<button type="button" class="question-flag" data-flag="${escapeHtml(question.id)}" aria-pressed="${marked}" aria-label="${marked ? 'Hapus tanda' : 'Tandai'} soal ${escapeHtml(question.number)}">${flagIcon()}<span>${marked ? 'Ditandai' : 'Tandai'}</span></button>`;
}

function questionCard(question, rewrite = false, group = null) {
  const record = examRenderState.questions.find(item => item.id === question.id);
  const groupAttribute = group === null ? '' : ` data-question-group="${group}"`;
  return `<article id="question-${escapeHtml(question.id)}" class="q-card" data-question-id="${escapeHtml(question.id)}"${groupAttribute} tabindex="-1"><div class="question-card-head"><h3 class="q-prompt" id="prompt-${escapeHtml(question.id)}">${record.number}. ${escapeHtml(question.prompt)}</h3>${flagButton(record)}</div>${rewrite ? `<label class="sr-only" for="rewrite-${escapeHtml(question.id)}">Kalimat perbaikan soal ${record.number}</label><textarea id="rewrite-${escapeHtml(question.id)}" data-answer="${escapeHtml(question.id)}" class="telemetry-input" rows="3" placeholder="Tulis perbaikan kalimat.">${escapeHtml(appState.selectedAnswers[question.id] || '')}</textarea>` : `<div class="q-options" role="radiogroup" aria-labelledby="prompt-${escapeHtml(question.id)}">${renderOptions(question)}</div>`}</article>`;
}

function renderExamQuestions(data) {
  examHeaderObserver.disconnect();
  examHeaderObserver.observe(document.querySelector('.exam-session-header'));
  document.querySelector('.question-navigation').open = !matchMedia('(max-width: 760px)').matches;
  const listening = data.listening?.questions || [];
  const reading = data.reading?.questions || [];
  const writing = data.writing?.id === 'W-NONE' ? null : data.writing;
  examRenderState.questions = [];
  const add = (items, section) => items.forEach(item => examRenderState.questions.push({ ...item, section, number: examRenderState.questions.length + 1 }));
  add(listening, 0); add(data.grammar_mc || [], 1); add(data.grammar_rewrite || [], 1); add(reading, 2);
  if (writing) add([writing], 3);
  appState.exam.marked ||= [];
  examRenderState.listeningGroups = groupExamQuestions(listening, item => item.audio_url || '');
  examRenderState.readingGroups = groupExamQuestions(reading, item => `${item.title || ''}\n${item.passage || ''}`);
  document.getElementById('grammarMcContainer').innerHTML = (data.grammar_mc || []).map(item => questionCard(item)).join('') || '<p>Belum ada soal Structure pada paket ini.</p>';
  document.getElementById('grammarRewriteContainer').innerHTML = (data.grammar_rewrite || []).map(item => questionCard(item, true)).join('') || '<p>Tidak ada tugas perbaikan kalimat pada paket ini.</p>';
  document.getElementById('listeningMcContainer').innerHTML = examRenderState.listeningGroups.map((group, index) => group.items.map(item => questionCard(item, false, index)).join('')).join('') || '<p>Belum ada soal Listening. Hubungi pengawas untuk melengkapi paket.</p>';
  document.getElementById('readingMcContainer').innerHTML = examRenderState.readingGroups.map((group, index) => group.items.map(item => questionCard(item, false, index)).join('')).join('') || '<p>Belum ada soal Reading pada paket ini.</p>';
  for (const [id, groups, label] of [['listeningGroupSelect', examRenderState.listeningGroups, 'Rekaman'], ['readingGroupSelect', examRenderState.readingGroups, 'Bacaan']]) {
    const select = document.getElementById(id);
    select.innerHTML = groups.map((group, index) => `<option value="${index}">${label} ${index + 1}: ${escapeHtml(group.title || label)}</option>`).join('') || `<option>${label} belum tersedia</option>`;
    select.disabled = !groups.length;
  }
  switchListeningGroup(Math.min(appState.exam.listeningGroup || 0, Math.max(0, examRenderState.listeningGroups.length - 1)), false);
  switchReadingGroup(Math.min(appState.exam.readingGroup || 0, Math.max(0, examRenderState.readingGroups.length - 1)), false);
  document.getElementById('writingPromptText').textContent = writing?.prompt || 'Tidak ada tugas Writing untuk sesi ini.';
  document.getElementById('sampleAiText').textContent = writing?.sample_ai_reference || '';
  document.getElementById('scenarioReference').classList.toggle('hidden', appState.exam.condition === 'MANDIRI' || !writing?.sample_ai_reference);
  const editor = document.getElementById('essayEditor');
  editor.value = writing ? appState.selectedAnswers[writing.id] || '' : '';
  editor.dataset.answer = writing?.id || '';
  editor.disabled = !writing;
  const writingRecord = examRenderState.questions.find(item => item.section === 3);
  document.getElementById('writingFlagControl').innerHTML = writingRecord ? flagButton(writingRecord) : '';
  document.getElementById('rightSec3').dataset.questionId = writing?.id || '';
  document.getElementById('essayWordCounter').textContent = `${editor.value.trim() ? editor.value.trim().split(/\s+/).length : 0} kata`;
  const view = document.getElementById('viewExam');
  view.addEventListener('click', event => {
    const button = event.target.closest('[data-flag]');
    if (!button) return;
    const id = button.dataset.flag;
    const marked = appState.exam.marked;
    appState.exam.marked = marked.includes(id) ? marked.filter(item => item !== id) : [...marked, id];
    saveExamDraft(); refreshExamProgress();
  });
  view.addEventListener('input', () => queueMicrotask(refreshExamProgress));
  const audio = document.getElementById('listeningAudio');
  audio.addEventListener('error', () => { document.getElementById('listeningAudioStatus').textContent = 'Audio belum dapat diputar. Periksa koneksi atau hubungi pengawas.'; });
  audio.addEventListener('play', () => { document.getElementById('listeningAudioStatus').textContent = 'Rekaman sedang diputar.'; });
  audio.addEventListener('pause', () => { document.getElementById('listeningAudioStatus').textContent = audio.currentTime ? 'Rekaman dijeda. Tekan putar untuk melanjutkan.' : 'Tekan putar untuk mulai mendengarkan.'; });
  audio.addEventListener('ended', () => { document.getElementById('listeningAudioStatus').textContent = 'Rekaman selesai. Tinjau jawaban Anda sebelum berpindah bagian.'; });
  displayExamQuestion(appState.exam.currentQuestionId || examRenderState.questions[0]?.id);
}

function switchListeningGroup(index, jump = true) {
  if (jump) return jumpToQuestion(examRenderState.listeningGroups[index]?.items[0]?.id);
  examRenderState.listeningIndex = index;
  const group = examRenderState.listeningGroups[index];
  const audio = document.getElementById('listeningAudio');
  if (audio.getAttribute('src') !== group?.key) {
    audio.pause();
    if (group?.key) audio.src = group.key;
    else audio.removeAttribute('src');
    document.getElementById('listeningAudioStatus').textContent = group?.key ? 'Tekan putar untuk mulai mendengarkan.' : 'Rekaman belum tersedia pada paket ini.';
  }
  document.getElementById('listeningGroupSelect').value = String(index);
  document.querySelectorAll('#listeningMcContainer [data-question-group]').forEach(card => card.classList.toggle('hidden', Number(card.dataset.questionGroup) !== index));
  if (appState.exam) { appState.exam.listeningGroup = index; saveExamDraft(); }
}

function switchReadingGroup(index, jump = true) {
  if (jump) return jumpToQuestion(examRenderState.readingGroups[index]?.items[0]?.id);
  examRenderState.readingIndex = index;
  const group = examRenderState.readingGroups[index];
  document.getElementById('readingGroupSelect').value = String(index);
  document.getElementById('readingTitle').textContent = group?.title || 'Reading comprehension';
  document.getElementById('readingPassageText').textContent = readablePassage(group?.items[0]?.passage || 'Bacaan belum tersedia.');
  document.querySelectorAll('#readingMcContainer [data-question-group]').forEach(card => card.classList.toggle('hidden', Number(card.dataset.questionGroup) !== index));
  if (appState.exam) { appState.exam.readingGroup = index; saveExamDraft(); }
}

function isExamAnswered(question) {
  const answer = appState.selectedAnswers[question.id];
  return answer !== undefined && answer !== null && String(answer).trim() !== '';
}

function refreshExamProgress() {
  const questions = examRenderState.questions;
  const answered = questions.filter(isExamAnswered).length;
  const progress = document.getElementById('examProgress');
  if (!progress || !appState.exam) return;
  progress.max = Math.max(1, questions.length); progress.value = answered;
  progress.textContent = `${Math.round(answered / Math.max(1, questions.length) * 100)}%`;
  document.getElementById('examProgressText').textContent = `${answered} dari ${questions.length} jawaban terisi`;
  document.getElementById('markedQuestionCount').textContent = appState.exam.marked.length ? `${appState.exam.marked.length} ditandai` : '';
  const section = appState.exam.section ?? 0;
  const current = questions.filter(item => item.section === section);
  document.getElementById('examSectionCount').textContent = `${current.filter(isExamAnswered).length} / ${current.length} terisi`;
  document.getElementById('questionNavigator').innerHTML = questions.map(question => `<button type="button" class="question-number${isExamAnswered(question) ? ' is-answered' : ''}${appState.exam.marked.includes(question.id) ? ' is-marked' : ''}${appState.exam.currentQuestionId === question.id ? ' is-current' : ''}" aria-current="${appState.exam.currentQuestionId === question.id ? 'step' : 'false'}" data-jump="${escapeHtml(question.id)}" aria-label="Soal ${question.number}, ${examSectionNames[question.section]}${isExamAnswered(question) ? ', terisi' : ', belum terisi'}${appState.exam.marked.includes(question.id) ? ', ditandai' : ''}">${question.number}</button>`).join('');
  document.getElementById('questionNavigator').querySelectorAll('[data-jump]').forEach(button => button.addEventListener('click', () => jumpToQuestion(button.dataset.jump)));
  document.querySelectorAll('[data-flag]').forEach(button => {
    const marked = appState.exam.marked.includes(button.dataset.flag);
    button.setAttribute('aria-pressed', String(marked));
    button.querySelector('span').textContent = marked ? 'Ditandai' : 'Tandai';
    const record = questions.find(item => item.id === button.dataset.flag);
    button.setAttribute('aria-label', `${marked ? 'Hapus tanda' : 'Tandai'} soal ${record?.number || ''}`);
  });
}

function showExamSection(section) {
  const current = examRenderState.questions.find(q => q.id === appState.exam?.currentQuestionId && q.section === section);
  const first = current || examRenderState.questions.find(q => q.section === section);
  if (first) jumpToQuestion(first.id);
}

function displayExamQuestion(id, focus = false) {
  const question = examRenderState.questions.find(q => q.id === id) || examRenderState.questions[0];
  if (!question || !appState.exam) return;
  const section = question.section;
  appState.exam.currentQuestionId = question.id;
  appState.exam.section = section;
  [0, 1, 2, 3].forEach(number => {
    const active = number === section;
    const tab = document.getElementById(`tabSec${number}`);
    tab.classList.toggle('active', active);
    tab.setAttribute('aria-current', active ? 'step' : 'false');
    tab.disabled = !examRenderState.questions.some(q => q.section === number);
    document.getElementById(`leftSec${number}`).classList.toggle('hidden', !active);
    document.getElementById(`rightSec${number}`).classList.toggle('hidden', !active);
  });
  if (section === 0) switchListeningGroup(examRenderState.listeningGroups.findIndex(g => g.items.some(q => q.id === question.id)), false);
  else document.getElementById('listeningAudio').pause();
  if (section === 2) switchReadingGroup(examRenderState.readingGroups.findIndex(g => g.items.some(q => q.id === question.id)), false);
  document.querySelectorAll('.q-card').forEach(card => card.classList.toggle('hidden', card.dataset.questionId !== question.id));
  const workspace = document.querySelector('.exam-workspace');
  workspace.classList.toggle('is-structure', section === 1);
  document.getElementById('examPaneContext').textContent = ['Audio Listening', 'Petunjuk', 'Bacaan', 'Instruksi Writing'][section];
  document.getElementById('examQuestionPosition').textContent = `Soal ${question.number} dari ${examRenderState.questions.length}`;
  document.getElementById('previousQuestion').disabled = question.number === 1;
  document.getElementById('nextQuestion').disabled = question.number === examRenderState.questions.length;
  document.getElementById('examPackageTitle').textContent = appState.questionsBank.package?.name || 'Sesi ujian EPT';
  showExamPane('answers');
  saveExamDraft(); refreshExamProgress();
  if (focus) {
    const target = section === 3 ? document.getElementById('essayEditor') : document.getElementById('question-' + question.id);
    target?.focus({ preventScroll: true });
    document.querySelector('.exam-task-area').scrollIntoView({ block: 'start', behavior: 'instant' });
  }
}

function stepExamQuestion(direction) {
  const current = examRenderState.questions.findIndex(q => q.id === appState.exam?.currentQuestionId);
  const target = examRenderState.questions[current + direction];
  if (target) jumpToQuestion(target.id);
}

function showExamPane(pane, moveFocus = false) {
  const workspace = document.querySelector('.exam-workspace');
  if (!workspace) return;
  workspace.dataset.pane = pane;
  syncExamPane();
  if (moveFocus && examMobileViewport.matches) {
    const panel = workspace.querySelector(pane === 'context' ? '.pane-left' : '.pane-right');
    panel.focus({ preventScroll: true });
    panel.scrollIntoView({ block: 'start', behavior: 'instant' });
  }
}

function syncExamPane() {
  const workspace = document.querySelector('.exam-workspace');
  if (!workspace) return;
  const context = workspace.dataset.pane === 'context';
  document.getElementById('examPaneAnswers').setAttribute('aria-pressed', String(!context));
  document.getElementById('examPaneContext').setAttribute('aria-pressed', String(context));
  const left = workspace.querySelector('.pane-left'), right = workspace.querySelector('.pane-right');
  left.inert = examMobileViewport.matches && !context;
  right.inert = examMobileViewport.matches && context;
  left.setAttribute('aria-hidden', String(left.inert));
  right.setAttribute('aria-hidden', String(right.inert));
}

function jumpToQuestion(id, focus = true) {
  if (!examRenderState.questions.some(q => q.id === id)) return;
  if (appState.exam?.currentQuestionId !== id && typeof recordNavSwitch === 'function') recordNavSwitch('question_' + id);
  displayExamQuestion(id, focus);
}
