const examRenderState = { questions: [], byId: new Map(), answered: new Set(), navigator: new Map(), listeningGroups: [], readingGroups: [], activeId: null };
const examSectionNames = ['Listening', 'Structure', 'Reading', 'Esai riset'];
const examHeaderObserver = new ResizeObserver(([entry]) => {
  if (entry?.target.isConnected) {
    document.documentElement.style.setProperty('--exam-masthead-height', `${entry.borderBoxSize[0].blockSize}px`);
  }
});
const examNavigatorViewport = matchMedia('(max-width: 960px)');
const examReadingViewport = matchMedia('(max-width: 1100px)');

function syncExamDisclosure(selector, viewport) {
  const disclosure = document.querySelector(selector);
  if (!disclosure) return;
  const summary = disclosure.querySelector('summary');
  if (viewport.matches && disclosure.contains(document.activeElement) && document.activeElement !== summary) {
    summary.focus({ preventScroll: true });
    summary.scrollIntoView({ block: 'nearest' });
  }
  disclosure.open = !viewport.matches;
}
examNavigatorViewport.addEventListener('change', () => syncExamDisclosure('.question-navigation', examNavigatorViewport));
examReadingViewport.addEventListener('change', () => syncExamDisclosure('#readingContext', examReadingViewport));

function groupExamQuestions(questions, key) {
  const groups = new Map();
  for (const question of questions) {
    const value = key(question);
    if (!groups.has(value)) groups.set(value, { key: value, title: question.title, items: [] });
    groups.get(value).items.push(question);
  }
  return [...groups.values()];
}

function renderOptions(question) {
  return (question.options || []).map((option, index) => `
    <label class="q-option-label">
      <span class="option-letter" aria-hidden="true">${String.fromCharCode(65 + index)}</span>
      <span class="exam-option-text" lang="en">${escapeHtml(choiceText(option))}</span>
      <input type="radio" name="${escapeHtml(question.id)}" value="${index}" lang="en"
        ${String(appState.selectedAnswers[question.id]) === String(index) ? 'checked' : ''}>
    </label>`).join('');
}

function flagButton(question) {
  return `<button type="button" class="question-flag" data-flag="${escapeHtml(question.id)}" aria-pressed="false" aria-label="Tandai soal ${question.number}">
    <svg aria-hidden="true" class="svg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 22V3m0 0c5-4 9 4 14 0v11c-5 4-9-4-14 0"/></svg>
    <span>Tandai</span>
  </button>`;
}

function questionCard(item, rewrite = false) {
  const question = examRenderState.byId.get(item.id);
  const id = escapeHtml(question.id);
  const response = rewrite
    ? `<p class="essay-purpose">Tulis kalimat perbaikan dengan kata-kata Anda.</p>
       <label class="sr-only" for="rewrite-${id}">Kalimat perbaikan soal ${question.number}</label>
       <textarea id="rewrite-${id}" data-answer="${id}" lang="en" class="telemetry-input" rows="3">${escapeHtml(appState.selectedAnswers[question.id] || '')}</textarea>`
    : `<div class="q-options" role="radiogroup" lang="en" aria-labelledby="prompt-${id}">${renderOptions(question)}</div>
       <div class="exam-choice-tools"><button type="button" class="btn-subtle${isExamAnswered(question) ? '' : ' hidden'}" data-clear-choice="${id}">Hapus pilihan</button></div>`;
  return `<article id="question-${id}" class="q-card hidden" data-question-id="${id}" aria-labelledby="prompt-${id}"><div class="question-card-head">
    <h2 class="q-prompt" id="prompt-${id}" lang="en" tabindex="-1">${escapeHtml(question.prompt)}</h2>${flagButton(question)}</div>${response}</article>`;
}

function renderExamQuestions(data) {
  examHeaderObserver.disconnect();
  examHeaderObserver.observe(document.querySelector('.exam-session-header'));
  syncExamDisclosure('.question-navigation', examNavigatorViewport);
  syncExamDisclosure('#readingContext', examReadingViewport);
  const listening = data.listening?.questions || [];
  const reading = data.reading?.questions || [];
  const writing = data.writing?.id === 'W-NONE' ? null : data.writing;
  const questions = [];
  const add = (items, section) => items.forEach(item => questions.push({ ...item, section, number: questions.length + 1 }));
  add(listening, 0); add(data.grammar_mc || [], 1); add(data.grammar_rewrite || [], 1); add(reading, 2);
  if (writing) add([writing], 3);
  examRenderState.questions = questions;
  examRenderState.byId = new Map(questions.map(question => [question.id, question]));
  examRenderState.answered = new Set(questions.filter(isExamAnswered).map(question => question.id));
  examRenderState.activeId = null;
  appState.exam.marked ||= [];
  document.getElementById('examPackageTitle').textContent = data.package?.name || 'Simulasi TOEFL EPT';

  examRenderState.listeningGroups = groupExamQuestions(listening, item => item.audio_url || '');
  examRenderState.readingGroups = groupExamQuestions(reading, item => `${item.title || ''}\n${item.passage || ''}`);
  const groups = [
    ['listeningGroupSelect', examRenderState.listeningGroups, 'Rekaman'],
    ['readingGroupSelect', examRenderState.readingGroups, 'Bacaan']
  ];
  for (const [id, items, label] of groups) {
    const select = document.getElementById(id);
    select.innerHTML = items.map((group, index) =>
      `<option value="${index}">${label} ${index + 1} · ${escapeHtml(group.title || label)}</option>`).join('');
    select.closest('.exam-context-select').hidden = items.length < 2;
  }
  document.getElementById('listeningMcContainer').innerHTML = listening.map(item => questionCard(item)).join('');
  document.getElementById('grammarMcContainer').innerHTML = (data.grammar_mc || []).map(item => questionCard(item)).join('');
  document.getElementById('grammarRewriteContainer').innerHTML = (data.grammar_rewrite || []).map(item => questionCard(item, true)).join('');
  document.getElementById('readingMcContainer').innerHTML = reading.map(item => questionCard(item)).join('');

  document.getElementById('writingPromptText').textContent = writing?.prompt || '';
  document.getElementById('sampleAiText').textContent = writing?.sample_ai_reference || '';
  document.getElementById('scenarioReference').classList.toggle('hidden', !writing?.sample_ai_reference);
  const editor = document.getElementById('essayEditor');
  editor.value = writing ? appState.selectedAnswers[writing.id] || '' : '';
  editor.dataset.answer = writing?.id || '';
  document.getElementById('essayWordCounter').textContent = `${editor.value.trim() ? editor.value.trim().split(/\s+/).length : 0} kata`;
  document.getElementById('writingFlagControl').innerHTML = writing ? flagButton(examRenderState.byId.get(writing.id)) : '';

  renderExamNavigator();
  questions.forEach(updateExamMarker);
  refreshExamProgress();
  refreshMarkedCount();
  bindExamWorkspace();
  displayExamQuestion(appState.exam.currentQuestionId);
}

function bindExamWorkspace() {
  document.getElementById('viewExam').addEventListener('click', event => {
    const jump = event.target.closest('[data-jump]');
    if (jump) {
      jumpToQuestion(jump.dataset.jump);
      if (examNavigatorViewport.matches) jump.closest('details').open = false;
      return;
    }
    const clear = event.target.closest('[data-clear-choice]');
    if (clear) { clearExamChoice(clear); return; }
    const flag = event.target.closest('[data-flag]');
    if (!flag) return;
    const id = flag.dataset.flag;
    const marked = appState.exam.marked;
    appState.exam.marked = marked.includes(id) ? marked.filter(item => item !== id) : [...marked, id];
    updateExamMarker(examRenderState.byId.get(id));
    refreshMarkedCount();
    saveExamDraft();
  });
  document.getElementById('readingBackToQuestion').addEventListener('click', () => {
    focusExamQuestion(examRenderState.byId.get(examRenderState.activeId), false);
    if (examReadingViewport.matches) document.getElementById('readingContext').open = false;
  });
  const audio = document.getElementById('listeningAudio');
  const status = document.getElementById('listeningAudioStatus');
  audio.addEventListener('error', () => {
    status.textContent = 'Audio belum dapat diputar. Periksa koneksi atau hubungi pengawas.';
  });
  audio.addEventListener('loadedmetadata', () => { status.textContent = ''; });
}

function clearExamChoice(button) {
  const id = button.dataset.clearChoice;
  const radios = button.closest('.q-card').querySelectorAll('input[type="radio"]');
  radios.forEach(input => { input.checked = false; });
  delete appState.selectedAnswers[id];
  recordAnswerChange(id);
  radios[0]?.focus();
  syncExamAnswerState(id);
  saveExamDraft();
}

function renderExamNavigator() {
  const navigator = document.getElementById('questionNavigator');
  navigator.innerHTML = examSectionNames.map((name, section) => {
    const questions = examRenderState.questions.filter(question => question.section === section);
    if (!questions.length) return '';
    const buttons = questions.map(question => `<button type="button" class="question-number" data-jump="${escapeHtml(question.id)}">${question.number}</button>`).join('');
    return `<div class="exam-map-section" role="group" aria-labelledby="exam-map-${section}"><p id="exam-map-${section}"${section < 3 ? ' lang="en"' : ''}>${name}</p><div class="exam-map-items">${buttons}</div></div>`;
  }).join('');
  examRenderState.navigator = new Map([...navigator.querySelectorAll('[data-jump]')].map(button => [button.dataset.jump, button]));
}

function switchListeningGroup(index, jump = true) {
  const group = examRenderState.listeningGroups[index];
  if (jump) return jumpToQuestion(group?.items[0]?.id);
  const audio = document.getElementById('listeningAudio');
  if (audio.getAttribute('src') !== group.key) {
    audio.pause();
    if (group.key) audio.src = group.key;
    else audio.removeAttribute('src');
    document.getElementById('listeningAudioStatus').textContent = group.key ? '' : 'Rekaman belum tersedia.';
    document.getElementById('listeningTranscript').open = false;
  }
  const transcript = group.items.find(item => item.transcript)?.transcript || '';
  const text = document.getElementById('listeningTranscriptText');
  if (text.textContent !== transcript) text.textContent = transcript;
  document.getElementById('listeningTranscript').hidden = !transcript;
  document.getElementById('listeningGroupSelect').value = String(index);
}

function switchReadingGroup(index, jump = true) {
  const group = examRenderState.readingGroups[index];
  if (jump) {
    jumpToQuestion(group?.items[0]?.id, false);
    return;
  }
  document.getElementById('readingGroupSelect').value = String(index);
  document.getElementById('readingTitle').textContent = group?.title || 'Reading passage';
  const passage = document.getElementById('readingPassageText');
  const content = readablePassage(group?.items[0]?.passage || '');
  if (passage.textContent !== content) {
    passage.textContent = content;
    passage.scrollTop = 0;
  }
}

function isExamAnswered(question) {
  const answer = appState.selectedAnswers[question.id];
  return answer !== undefined && answer !== null && String(answer).trim() !== '';
}

function updateExamMarker(question) {
  if (!question) return;
  const button = examRenderState.navigator.get(question.id);
  const answered = examRenderState.answered.has(question.id);
  const marked = appState.exam.marked.includes(question.id);
  const active = examRenderState.activeId === question.id;
  button.classList.toggle('is-answered', answered);
  button.classList.toggle('is-marked', marked);
  button.classList.toggle('is-current', active);
  button.setAttribute('aria-current', active ? 'step' : 'false');
  button.setAttribute('aria-label', `Soal ${question.number}, ${answered ? 'terisi' : 'belum terisi'}${marked ? ', ditandai' : ''}`);
  document.querySelector(`[data-flag="${CSS.escape(question.id)}"]`)?.setAttribute('aria-pressed', String(marked));
}

function refreshMarkedCount() {
  const count = appState.exam.marked.length;
  document.getElementById('markedQuestionCount').textContent = count ? `${count} ditandai` : '';
}

function refreshExamProgress() {
  document.getElementById('examProgressText').textContent = `${examRenderState.answered.size} dari ${examRenderState.questions.length} terisi`;
}

function syncExamAnswerState(id) {
  const question = examRenderState.byId.get(id);
  if (!question) return;
  const answered = isExamAnswered(question);
  if (answered === examRenderState.answered.has(id)) return;
  if (answered) examRenderState.answered.add(id);
  else examRenderState.answered.delete(id);
  const clear = document.querySelector(`[data-clear-choice="${CSS.escape(id)}"]`);
  clear?.classList.toggle('hidden', !answered);
  updateExamMarker(question);
  refreshExamProgress();
}

function showExamSection(section) {
  const current = examRenderState.byId.get(examRenderState.activeId);
  const first = current?.section === section ? current : examRenderState.questions.find(q => q.section === section);
  if (first) jumpToQuestion(first.id);
}

function displayExamQuestion(id, focus = false) {
  const question = examRenderState.byId.get(id) || examRenderState.questions[0];
  if (!question || !appState.exam) return;
  const previous = examRenderState.byId.get(examRenderState.activeId);
  const section = question.section;
  examRenderState.activeId = question.id;
  appState.exam.currentQuestionId = question.id;
  appState.exam.section = section;
  examSectionNames.forEach((_, number) => {
    const active = number === section;
    const tab = document.getElementById(`tabSec${number}`);
    tab.classList.toggle('active', active);
    tab.setAttribute('aria-current', active ? 'step' : 'false');
    tab.disabled = !examRenderState.questions.some(q => q.section === number);
    document.getElementById(`rightSec${number}`).classList.toggle('hidden', !active);
  });
  document.getElementById('readingContext').classList.toggle('hidden', section !== 2);
  document.querySelector('.exam-workspace').classList.toggle('is-reading', section === 2);
  if (section === 0) switchListeningGroup(examRenderState.listeningGroups.findIndex(g => g.items.some(q => q.id === question.id)), false);
  else document.getElementById('listeningAudio').pause();
  if (section === 2) switchReadingGroup(examRenderState.readingGroups.findIndex(g => g.items.some(q => q.id === question.id)), false);
  if (previous) document.getElementById('question-' + previous.id)?.classList.add('hidden');
  document.getElementById('question-' + question.id)?.classList.remove('hidden');
  document.getElementById('examQuestionPosition').textContent = `Soal ${question.number}`;
  document.getElementById('previousQuestion').disabled = question.number === 1;
  document.getElementById('nextQuestion').disabled = question.number === examRenderState.questions.length;
  updateExamMarker(previous);
  updateExamMarker(question);
  saveExamDraft();
  if (focus) focusExamQuestion(question);
}

function focusExamQuestion(question, showPlayer = true) {
  const target = question.section === 3 ? document.getElementById('essayPromptHeading') : document.getElementById('prompt-' + question.id);
  target?.focus({ preventScroll: true });
  const anchor = showPlayer && question.section === 0 ? document.getElementById('examAnswersPane') : target;
  anchor?.scrollIntoView({ block: 'start', behavior: 'instant' });
}

function stepExamQuestion(direction) {
  const question = examRenderState.byId.get(examRenderState.activeId);
  const target = question && examRenderState.questions[question.number - 1 + direction];
  if (target) jumpToQuestion(target.id);
}

function jumpToQuestion(id, focus = true) {
  if (!examRenderState.byId.has(id)) return;
  if (examRenderState.activeId !== id) recordNavSwitch('question_' + id);
  displayExamQuestion(id, focus);
}
