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
