// Custom EPT authoring: live bank, atomic imports and accessible answer choices.
const questionEditor = { original: null, options: ['', '', '', ''], busy: false, dirty: false };
const questionPagination = { page: 1, pageSize: 15 };
const questionModuleLabels = { listening: 'Listening', grammar: 'Structure', reading: 'Reading', writing: 'Writing riset' };
if (typeof qField === 'undefined') {
  window.qField = id => document.getElementById(id);
}
if (typeof updateAudioPreview === 'undefined') {
  window.updateAudioPreview = function() {
    const audio = qField('questionAudioPreview');
    if (!audio) return;
    const url = (qField('qFormAudio')?.value || '').trim();
    audio.pause();
    const valid = url.startsWith('/media/') || /^https:\/\//i.test(url);
    audio.classList.toggle('hidden', !valid);
    if (valid) audio.src = url; else audio.removeAttribute('src');
  };
}

function questionMessage(message, error = false) {
  const box = qField(error && document.querySelector('.question-bank-layout.is-editing') ? 'questionFormError' : 'questionEditorStatus');
  if (!box) return;
  box.textContent = message;
  box.classList.remove('hidden');
  box.classList.toggle('is-error', error);
  if (error) box.scrollIntoView({ block: 'nearest' });
}

function setQuestionBusy(busy) {
  questionEditor.busy = busy;
  if (qField('saveQuestionButton')) { qField('saveQuestionButton').disabled = busy; qField('saveQuestionButton').textContent = busy ? 'Menyimpan…' : 'Simpan soal'; }
  qField('questionForm')?.querySelectorAll('input, button, select, textarea').forEach(el => el.disabled = busy);
  if (qField('qFormId')) qField('qFormId').readOnly = !!questionEditor.original;
}

function initQuestionEditor() {
  const form = qField('questionForm');
  if (!form || form.dataset.initialized) return;
  form.dataset.initialized = 'true';
  ['input', 'change'].forEach(ev => form.addEventListener(ev, () => questionEditor.dirty = true));
  ['questionSearch', 'questionSectionFilter', 'questionStatusFilter', 'questionTypeFilter'].forEach(id => {
    qField(id)?.addEventListener(id === 'questionSearch' ? 'input' : 'change', () => { questionPagination.page = 1; renderQuestionBank(); });
  });
  qField('qFormSection')?.addEventListener('change', () => updateQuestionFields(true));
  qField('qFormType')?.addEventListener('change', () => updateQuestionFields(false));
  qField('qFormAudio')?.addEventListener('change', updateAudioPreview);
  qField('qFormAudioFile')?.addEventListener('change', uploadQuestionAudio);
  qField('questionImportFile')?.addEventListener('change', importQuestionBank);
  resetQuestionForm();
}

async function loadAdminQuestionsTable() {
  initQuestionEditor();
  questionMessage('Memuat bank soal…');
  try {
    const data = await api('/api/questions');
    if (!qField('adminQuestionsBody')) return;
    appState.adminQuestionsList = data.all_questions || [];
    renderBankKpis(appState.adminQuestionsList);
    renderQuestionBank();
    const urlParams = new URLSearchParams(location.search);
    const targetUuid = urlParams.get('uuid') || urlParams.get('id');
    if (targetUuid) {
      const idx = appState.adminQuestionsList.findIndex(q => q.question_id === targetUuid);
      if (idx !== -1) editQuestionRow(idx);
    }
    questionMessage('Perubahan bank soal berlaku untuk sesi baru.');
  } catch (error) {
    questionMessage(error.message, true);
    qField('adminQuestionsBody').innerHTML = '<tr><td colspan="4">Bank soal belum dapat dimuat. Gunakan tombol Segarkan untuk mencoba kembali.</td></tr>';
  }
}

function renderBankKpis(list) {
  const container = qField('bankKpiGrid');
  if (!container) return;
  const count = sec => list.filter(q => q.section === sec).length;
  const activeCount = list.filter(q => q.is_active).length;
  const pct = list.length ? Math.round((activeCount / list.length) * 100) + '%' : '0%';
  const items = [
    ['Total Soal', list.length, 'book', 'blue', ''],
    ['Listening', count('listening'), 'headphones', 'cyan', ''],
    ['Structure', count('grammar'), 'layers', 'purple', ''],
    ['Reading', count('reading'), 'book', 'green', ''],
    ['Writing', count('writing'), 'pen', 'amber', ''],
    ['Soal Aktif', activeCount, 'check', 'green', pct]
  ];
  container.innerHTML = items.map(([label, val, iconName, color, badge]) =>
    `<div class="kpi-card"><div class="kpi-card-head"><div class="kpi-icon-box kpi-icon-${color}">${icon(iconName)}</div>${badge ? `<span class="kpi-badge kpi-badge-green">${badge}</span>` : ''}</div><strong class="kpi-value">${val}</strong><span class="kpi-label">${label}</span></div>`
  ).join('');
}

function renderQuestionBank() {
  const list = appState.adminQuestionsList || [];
  renderBankKpis(list);
  const search = (qField('questionSearch')?.value || '').trim().toLowerCase();
  const module = qField('questionSectionFilter')?.value || '';
  const status = qField('questionStatusFilter')?.value || '';
  const type = qField('questionTypeFilter')?.value || '';

  const matches = list.map((question, index) => ({ question, index })).filter(({ question: q }) => {
    if (module && q.section !== module) return false;
    if (status === 'active' && !q.is_active) return false;
    if (status === 'inactive' && q.is_active) return false;
    if (type && q.question_type !== type) return false;
    if (search && ![q.question_id, q.title, q.prompt, q.passage].join(' ').toLowerCase().includes(search)) return false;
    return true;
  });

  const activeModule = qField('questionSectionFilter')?.value || '';
  document.querySelectorAll('.bank-module-pills .q-pill').forEach(btn => {
    btn.classList.toggle('active', activeModule ? (btn.getAttribute('onclick') || '').includes(`'${activeModule}'`) : (btn.getAttribute('onclick') || '').includes("''"));
  });

  const total = matches.length;
  const totalPages = Math.max(1, Math.ceil(total / questionPagination.pageSize));
  if (questionPagination.page > totalPages) questionPagination.page = totalPages;
  if (questionPagination.page < 1) questionPagination.page = 1;

  const start = (questionPagination.page - 1) * questionPagination.pageSize;
  const paged = matches.slice(start, start + questionPagination.pageSize);
  const startNum = total === 0 ? 0 : start + 1;
  const endNum = Math.min(start + questionPagination.pageSize, total);

  if (qField('questionBankCount')) {
    qField('questionBankCount').textContent = total ? `Menampilkan ${startNum}–${endNum} dari ${total} soal (Total bank: ${list.length})` : `0 soal ditemukan dari ${list.length} soal`;
  }

  const prevBtn = qField('qPrevPage');
  const nextBtn = qField('qNextPage');
  const pageInfo = qField('qPageInfo');
  if (prevBtn) prevBtn.disabled = questionPagination.page <= 1;
  if (nextBtn) nextBtn.disabled = questionPagination.page >= totalPages;
  if (pageInfo) pageInfo.textContent = `Halaman ${questionPagination.page} / ${totalPages}`;

  qField('adminQuestionsBody').innerHTML = paged.map(({ question: q, index }) => {
    const hasAudio = q.audio_url && (q.audio_url.startsWith('/media/') || /^https?:\/\//i.test(q.audio_url));
    const audioBadge = hasAudio ? `<span class="q-audio-badge" title="Tersedia audio"><svg aria-hidden="true" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>Audio</span>` : '';
    const passageBadge = q.passage && q.passage.trim().length ? '<span class="q-passage-badge">Wacana</span>' : '';
    const typeLabel = { multiple_choice: 'Pilihan ganda', rewrite: 'Perbaikan', essay: 'Esai riset' }[q.question_type] || q.question_type;
    const keyIndex = Number(q.correct_answer);
    const keyLabel = !isNaN(keyIndex) ? String.fromCharCode(65 + keyIndex) : escapeHtml(String(q.correct_answer || '-'));
    const answerSnippet = q.question_type === 'multiple_choice' ? `<div class="q-row-key">Kunci: <strong>${keyLabel}</strong></div>` : '';
    return `<tr class="${questionEditor.original === q.question_id ? 'selected-row' : ''}">
      <td>
        <div class="q-row-meta"><span class="q-id-badge">${escapeHtml(q.question_id)}</span>${audioBadge}${passageBadge}<span class="q-type-badge">${escapeHtml(typeLabel)}</span></div>
        <strong class="q-row-title">${escapeHtml(q.title || q.question_id)}</strong>
        <p class="q-row-prompt">${escapeHtml(q.prompt.slice(0, 110))}</p>
        ${answerSnippet}
      </td>
      <td><span class="q-sec-badge q-sec-${escapeHtml(q.section)}">${escapeHtml(questionModuleLabels[q.section] || q.section)}</span></td>
      <td><button type="button" class="question-status ${q.is_active ? 'is-active' : ''}" onclick="toggleQuestionActive(${index})" aria-label="${q.is_active ? 'Nonaktifkan' : 'Aktifkan'} soal ${escapeHtml(q.question_id)}"><span class="status-dot" aria-hidden="true"></span>${q.is_active ? 'Aktif' : 'Nonaktif'}</button></td>
      <td><div class="bank-row-actions"><button type="button" class="btn-sm" onclick="editQuestionRow(${index})">Edit</button><button type="button" class="btn-sm" onclick="duplicateQuestion(${index})">Salin</button><button type="button" class="btn-sm btn-danger" onclick="deleteQuestionRow(appState.adminQuestionsList[${index}].question_id)">Hapus</button></div></td>
    </tr>`;
  }).join('') || '<tr class="monitor-empty-row"><td colspan="4"><h4>Tidak ada soal yang cocok</h4><p>Ubah kata kunci atau filter untuk menampilkan soal lain.</p></td></tr>';
}

function filterByModule(mod) {
  if (qField('questionSectionFilter')) qField('questionSectionFilter').value = mod;
  questionPagination.page = 1;
  renderQuestionBank();
}

function changeQuestionPage(delta) { questionPagination.page += delta; renderQuestionBank(); }
function changeQuestionPageSize(val) { questionPagination.pageSize = Number(val) || 15; questionPagination.page = 1; renderQuestionBank(); }
function resetQuestionFilters() {
  ['questionSearch', 'questionSectionFilter', 'questionStatusFilter', 'questionTypeFilter'].forEach(id => { if (qField(id)) qField(id).value = ''; });
  questionPagination.page = 1;
  renderQuestionBank();
}

function renderQuestionOptions(selected = qField('qFormCorrect')?.value || '0') {
  const count = questionEditor.options.length;
  qField('questionOptionsEditor').innerHTML = questionEditor.options.map((value, index) => `<div class="question-option-edit"><label for="questionOption${index}">${String.fromCharCode(65 + index)}</label><input type="text" id="questionOption${index}" maxlength="2000" value="${escapeHtml(value)}" aria-label="Teks opsi ${String.fromCharCode(65 + index)}"><button type="button" class="btn-subtle" onclick="removeQuestionOption(${index})" aria-label="Hapus opsi ${String.fromCharCode(65 + index)}" ${count <= 2 ? 'disabled' : ''}>Hapus</button></div>`).join('');
  qField('qFormCorrect').innerHTML = questionEditor.options.map((_, index) => `<option value="${index}">Opsi ${String.fromCharCode(65 + index)}</option>`).join('');
  qField('qFormCorrect').value = Number(selected) < count ? selected : '0';
  qField('addQuestionOption').disabled = count >= 6;
  qField('questionOptionsEditor').querySelectorAll('input').forEach((input, index) => input.addEventListener('input', () => {
    questionEditor.options[index] = input.value;
    qField('qFormOptions').value = questionEditor.options.join('\n');
  }));
  qField('qFormOptions').value = questionEditor.options.join('\n');
}

function addQuestionOption() {
  if (questionEditor.options.length >= 6 || questionEditor.busy) return;
  questionEditor.dirty = true;
  questionEditor.options.push('');
  renderQuestionOptions();
}

function removeQuestionOption(index) {
  if (questionEditor.options.length <= 2 || questionEditor.busy) return;
  questionEditor.dirty = true;
  const correct = Number(qField('qFormCorrect').value);
  questionEditor.options.splice(index, 1);
  renderQuestionOptions(String(correct > index ? correct - 1 : correct === index ? 0 : correct));
}

function updateQuestionFields(resetType = false) {
  const section = qField('qFormSection').value;
  const types = section === 'grammar' ? [['multiple_choice', 'Pilihan ganda'], ['rewrite', 'Perbaikan kalimat']] : section === 'writing' ? [['essay', 'Esai riset']] : [['multiple_choice', 'Pilihan ganda']];
  const previous = qField('qFormType').value;
  qField('qFormType').innerHTML = types.map(([value, label]) => `<option value="${value}">${label}</option>`).join('');
  if (!resetType && types.some(([value]) => value === previous)) qField('qFormType').value = previous;
  const isChoice = qField('qFormType').value === 'multiple_choice';
  qField('questionOptionFields').classList.toggle('hidden', !isChoice);
  qField('questionTextAnswerFields').classList.toggle('hidden', isChoice);
  qField('questionAudioFields').classList.toggle('hidden', section !== 'listening');
  qField('questionPassageFields').classList.toggle('hidden', !['reading', 'listening'].includes(section));
  qField('questionSampleFields').classList.toggle('hidden', section !== 'writing');
  qField('questionPassageLabel').textContent = section === 'listening' ? 'Transkrip untuk pengawas (opsional)' : 'Wacana bacaan';
  qField('questionPassageHelp').textContent = section === 'listening' ? 'Transkrip tidak ditampilkan saat peserta mengerjakan Listening.' : 'Wacana ini ditampilkan bersama pertanyaan Reading.';
  qField('qFormPassage').required = section === 'reading';
}

async function editQuestionRow(index, duplicate = false) {
  if (questionEditor.busy) return;
  const summary = appState.adminQuestionsList[index];
  if (!summary || !await confirmQuestionTransition()) return;
  setQuestionBusy(true);
  let q;
  try {
    const data = await api('/api/admin/questions?id=' + encodeURIComponent(summary.question_id));
    q = data.question;
  } catch (error) { setQuestionBusy(false); return questionMessage(error.message, true); }
  setQuestionBusy(false);
  questionEditor.original = duplicate ? null : q.question_id;
  for (const [id, key] of Object.entries({ qFormId: 'question_id', qFormSection: 'section', qFormTitle: 'title', qFormPrompt: 'prompt', qFormPassage: 'passage', qFormSample: 'sample_ai_reference', qFormAudio: 'audio_url', qFormExplanation: 'explanation' })) qField(id).value = q[key] || '';
  qField('qFormType').innerHTML = `<option value="${escapeHtml(q.question_type)}"></option>`;
  updateQuestionFields();
  if (duplicate) qField('qFormId').value = generateAutoQuestionId();
  qField('qFormId').readOnly = !duplicate;
  questionEditor.options = q.options?.length ? q.options.map(choiceText) : ['', '', '', ''];
  renderQuestionOptions(String(q.correct_answer || '0'));
  qField('qFormTextCorrect').value = q.correct_answer ?? '';
  qField('qFormActive').checked = q.is_active !== 0;
  qField('questionEditorTitle').textContent = duplicate ? 'Salinan soal baru' : 'Edit soal ' + q.question_id;
  qField('questionFormError').classList.add('hidden');
  qField('questionPreview').classList.add('hidden');
  updateAudioPreview(); renderQuestionBank();
  questionEditor.dirty = false;
  const currentUrl = new URL(location.href);
  if (!duplicate) {
    currentUrl.searchParams.set('uuid', q.question_id);
    history.replaceState(null, '', currentUrl.toString());
  }
  openQuestionEditor('qFormTitle');
}

function openQuestionEditor(focusId = 'qFormId') {
  document.querySelector('.question-bank-layout').classList.add('is-editing');
  document.querySelector('.bank-detail').scrollIntoView({ block: 'start' });
  qField(focusId).focus({ preventScroll: true });
}

async function closeQuestionEditor() {
  if (!await confirmQuestionTransition()) return;
  resetQuestionForm();
  qField('questionSearch').focus();
}

async function confirmQuestionTransition() {
  if (questionEditor.busy) { showToast('Tunggu sampai perubahan soal selesai diproses.'); return false; }
  if (!questionEditor.dirty) return true;
  if (!await adminConfirm('Buang perubahan soal?', 'Perubahan yang belum disimpan akan dibuang. Soal yang sudah tersimpan tetap tersedia.', 'Buang perubahan')) return false;
  resetQuestionForm();
  return true;
}

async function requestNewQuestion() { if (await confirmQuestionTransition()) resetQuestionForm(true); }
const duplicateQuestion = index => editQuestionRow(index, true);

function generateAutoQuestionId(section = 'grammar') {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

function resetQuestionForm(focus = false) {
  if (questionEditor.busy || !qField('questionForm')) return;
  questionEditor.original = null;
  const currentUrl = new URL(location.href);
  if (currentUrl.searchParams.has('uuid') || currentUrl.searchParams.has('id')) {
    currentUrl.searchParams.delete('uuid');
    currentUrl.searchParams.delete('id');
    history.replaceState(null, '', currentUrl.toString());
  }
  qField('questionForm').reset();
  const initialSection = qField('qFormSection')?.value || 'grammar';
  qField('qFormId').value = generateAutoQuestionId(initialSection);
  qField('qFormId').readOnly = false;
  questionEditor.options = ['', '', '', ''];
  renderQuestionOptions('0'); updateQuestionFields(true); updateAudioPreview();
  qField('questionEditorTitle').textContent = 'Soal baru';
  qField('questionFormError').classList.add('hidden');
  qField('questionPreview').classList.add('hidden');
  questionEditor.dirty = false;
  document.querySelector('.question-bank-layout').classList.toggle('is-editing', focus);
  if (focus) openQuestionEditor();
}

function questionPayload() {
  const fields = ['qFormId:question_id', 'qFormSection:section', 'qFormType:question_type', 'qFormTitle:title', 'qFormPrompt:prompt', 'qFormPassage:passage', 'qFormSample:sample_ai_reference', 'qFormAudio:audio_url', 'qFormExplanation:explanation', 'qFormCorrect:correct_answer'];
  const payload = Object.fromEntries(fields.map(f => { const [id, key] = f.split(':'); return [key, qField(id).value]; }));
  payload.options = payload.question_type === 'multiple_choice' ? [...questionEditor.options] : [];
  if (payload.question_type !== 'multiple_choice') payload.correct_answer = qField('qFormTextCorrect').value;
  payload.is_active = qField('qFormActive').checked ? 1 : 0;
  payload.mode = questionEditor.original ? 'update' : 'create';
  payload.original_id = questionEditor.original || '';
  return payload;
}

async function saveQuestionCrud(event) {
  event.preventDefault();
  if (questionEditor.busy) return;
  const payload = questionPayload();
  if (payload.prompt) payload.prompt = payload.prompt.replace(/_{2,}/g, '______');
  qField('questionFormError').classList.add('hidden');
  setQuestionBusy(true);
  try {
    await api('/api/admin/questions', { method: 'POST', body: JSON.stringify(payload) });
    setQuestionBusy(false); resetQuestionForm();
    await loadAdminQuestionsTable();
    questionMessage('Soal ' + payload.question_id.toLowerCase() + ' tersimpan dan tersinkron ke bank soal.');
  } catch (error) { questionMessage(error.message, true); }
  finally { setQuestionBusy(false); }
}

async function toggleQuestionActive(index) {
  if (questionEditor.busy) return;
  const q = appState.adminQuestionsList[index];
  setQuestionBusy(true);
  try {
    await api('/api/admin/questions', { method: 'POST', body: JSON.stringify({ question_id: q.question_id, is_active: q.is_active ? 0 : 1, mode: 'toggle' }) });
    await loadAdminQuestionsTable();
  } catch (error) { questionMessage(error.message, true); }
  finally { setQuestionBusy(false); }
}

async function deleteQuestionRow(id) {
  if (questionEditor.busy || !await adminConfirm('Hapus soal ' + id + '?', 'Soal ini tidak tersedia untuk sesi baru setelah dihapus. Soal pada sesi yang telah tersimpan tetap dipertahankan.' + (questionEditor.original === id && questionEditor.dirty ? ' Perubahan editor yang belum disimpan untuk soal ini juga akan dibuang.' : ''), 'Hapus soal')) return;
  setQuestionBusy(true);
  try {
    await api('/api/admin/questions?id=' + encodeURIComponent(id), { method: 'DELETE' });
    setQuestionBusy(false); if (questionEditor.original === id) resetQuestionForm();
    await loadAdminQuestionsTable(); questionMessage('Soal ' + id + ' dihapus.');
  } catch (error) { questionMessage(error.message, true); }
  finally { setQuestionBusy(false); }
}

function previewQuestion() {
  const q = questionPayload();
  const el = qField('questionPreviewBody');
  const sectionName = questionModuleLabels[q.section] || q.section;
  
  let mediaHtml = '';
  if (q.section === 'listening' && (q.audio_url.startsWith('/media/') || /^https:\/\//i.test(q.audio_url))) {
    mediaHtml = `
      <div class="preview-media-box">
        <div class="preview-media-label">Rekaman Audio Soal:</div>
        <audio controls preload="none" src="${escapeHtml(q.audio_url)}" class="preview-audio-player" aria-label="Audio soal pratinjau"></audio>
      </div>`;
  }

  let passageHtml = '';
  if (q.section === 'reading' && q.passage) {
    passageHtml = `
      <div class="preview-passage-card">
        <span class="preview-badge-subtle">Wacana Teks</span>
        <div class="preview-passage-content">${escapeHtml(readablePassage(q.passage))}</div>
      </div>`;
  }

  let answerHtml = '';
  if (q.question_type === 'multiple_choice') {
    answerHtml = `
      <div class="preview-options-container">
        <div class="preview-options-heading">Pilihan Jawaban (A-D):</div>
        <div class="preview-choice-list">
          ${q.options.map((option, index) => {
            const isCorrect = String(index) === String(q.correct_answer);
            const letter = String.fromCharCode(65 + index);
            return `
              <div class="preview-choice-item ${isCorrect ? 'is-correct-key' : ''}">
                <span class="preview-choice-letter">${letter}</span>
                <span class="preview-choice-text">${escapeHtml(choiceText(option) || 'Opsi belum diisi')}</span>
                ${isCorrect ? '<span class="preview-correct-badge">KUNCI JAWABAN</span>' : ''}
              </div>`;
          }).join('')}
        </div>
      </div>`;
  } else {
    answerHtml = `
      <div class="preview-essay-card">
        <span class="preview-badge-subtle">Jawaban Terbuka</span>
        <p class="preview-essay-hint">Peserta akan mengetik esai / teks jawaban pada bidang input respons langsung.</p>
        ${q.correct_answer ? `<div class="preview-ref-answer"><strong>Kunci / Referensi:</strong> ${escapeHtml(q.correct_answer)}</div>` : ''}
      </div>`;
  }

  el.innerHTML = `
    <div class="preview-card-wrapper">
      <div class="preview-header-meta">
        <span class="preview-section-pill preview-pill-${escapeHtml(q.section)}">${escapeHtml(sectionName)}</span>
        <span class="preview-id-pill">${escapeHtml(q.question_id || 'ID Baru')}</span>
      </div>
      <h4 class="preview-question-title">${escapeHtml(q.title || 'Soal EPT')}</h4>
      ${mediaHtml}
      ${passageHtml}
      <div class="preview-prompt-card">
        <div class="preview-prompt-label">Pertanyaan:</div>
        <p class="preview-prompt-text">${escapeHtml(q.prompt || 'Pertanyaan belum diisi.').replace(/_{2,}/g, '<span class="blank-fill-indicator">______</span>')}</p>
      </div>
      ${answerHtml}
      ${q.explanation ? `
        <div class="preview-explanation-box">
          <strong>Pembahasan:</strong>
          <p>${escapeHtml(q.explanation)}</p>
        </div>` : ''}
    </div>`;

  qField('questionPreview').classList.remove('hidden');
  qField('questionPreview').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

