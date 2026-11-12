// Custom EPT authoring: live bank, atomic imports and accessible answer choices.
const questionEditor = { original: null, options: ['', '', '', ''], busy: false, dirty: false };
const questionPagination = { page: 1, pageSize: 15 };
const questionModuleLabels = { listening: 'Listening', grammar: 'Structure', reading: 'Reading', writing: 'Writing riset' };
const qField = id => document.getElementById(id);

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
  if (duplicate) qField('qFormId').value = q.question_id.slice(0, 27) + '-COPY-' + Date.now().toString().slice(-6);
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

function resetQuestionForm(focus = false) {
  if (questionEditor.busy || !qField('questionForm')) return;
  questionEditor.original = null;
  qField('questionForm').reset();
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
  qField('questionFormError').classList.add('hidden');
  setQuestionBusy(true);
  try {
    await api('/api/admin/questions', { method: 'POST', body: JSON.stringify(payload) });
    setQuestionBusy(false); resetQuestionForm();
    await loadAdminQuestionsTable();
    questionMessage('Soal ' + payload.question_id.toUpperCase() + ' tersimpan dan tersinkron ke bank soal.');
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

function updateAudioPreview() {
  const audio = qField('questionAudioPreview');
  const url = qField('qFormAudio').value.trim();
  audio.pause();
  const valid = url.startsWith('/media/') || /^https:\/\//i.test(url);
  audio.classList.toggle('hidden', !valid);
  if (valid) audio.src = url; else audio.removeAttribute('src');
}

async function uploadQuestionAudio(event) {
  const file = event.target.files[0];
  if (!file || questionEditor.busy) return;
  if (file.size > 8 * 1024 * 1024) { event.target.value = ''; return questionMessage('Ukuran audio maksimal 8 MB.', true); }
  setQuestionBusy(true); questionMessage('Mengunggah audio…');
  try {
    const encoded = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(',')[1]); reader.onerror = () => reject(new Error('Berkas audio tidak dapat dibaca.')); reader.readAsDataURL(file); });
    const data = await api('/api/admin/audio', { method: 'POST', body: JSON.stringify({ filename: file.name, data_base64: encoded }) });
    qField('qFormAudio').value = data.audio_url; updateAudioPreview();
    questionMessage('Audio diunggah. Simpan soal untuk menghubungkan audio ini.');
  } catch (error) { questionMessage(error.message, true); }
  finally { setQuestionBusy(false); event.target.value = ''; }
}

function previewQuestion() {
  const q = questionPayload();
  const el = qField('questionPreviewBody');
  el.innerHTML = `<h4>${escapeHtml(q.title || questionModuleLabels[q.section])}</h4>${q.section === 'reading' ? `<p class="preview-passage">${escapeHtml(readablePassage(q.passage))}</p>` : ''}${q.section === 'listening' && (q.audio_url.startsWith('/media/') || /^https:\/\//i.test(q.audio_url)) ? `<audio controls preload="none" src="${escapeHtml(q.audio_url)}" aria-label="Audio soal pratinjau"></audio>` : ''}<p>${escapeHtml(q.prompt || 'Pertanyaan belum diisi.')}</p>${q.question_type === 'multiple_choice' ? `<ol type="A" class="preview-options">${q.options.map((option, index) => `<li>${escapeHtml(choiceText(option) || 'Opsi belum diisi')}${String(index) === String(q.correct_answer) ? ' <strong>(kunci)</strong>' : ''}</li>`).join('')}</ol>` : '<p>Peserta menulis jawaban pada lembar tugas.</p>'}`;
  qField('questionPreview').classList.remove('hidden');
  qField('questionPreview').tabIndex = -1;
  qField('questionPreview').focus({ preventScroll: true });
}

async function importQuestionBank(event) {
  const file = event.target.files[0];
  if (!file || questionEditor.busy) return;
  try {
    if (file.size > 2 * 1024 * 1024) throw new Error('Berkas JSON maksimal 2 MB.');
    const parsed = JSON.parse(await file.text());
    const questions = Array.isArray(parsed) ? parsed : parsed.questions;
    if (!Array.isArray(questions) || !questions.length || questions.length > 200) throw new Error('Gunakan JSON berisi 1 hingga 200 soal.');
    if (!await adminConfirm('Impor ' + questions.length + ' soal?', 'Kode soal yang sama akan diperbarui. Semua soal diperiksa sebelum perubahan disimpan.', 'Impor soal')) return;
    setQuestionBusy(true);
    const data = await api('/api/admin/questions/import', { method: 'POST', body: JSON.stringify({ questions }) });
    await loadAdminQuestionsTable(); questionMessage(data.imported + ' soal berhasil diimpor.');
  } catch (error) { questionMessage(error instanceof SyntaxError ? 'JSON tidak valid. Periksa kembali berkas impor.' : error.message, true); }
  finally { event.target.value = ''; setQuestionBusy(false); }
}

async function exportQuestionBank() {
  try {
    const data = await api('/api/admin/questions/export');
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    const a = Object.assign(document.createElement('a'), { href: url, download: 'linguapulse-ept-questions.json' });
    a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) { questionMessage(error.message, true); }
}
