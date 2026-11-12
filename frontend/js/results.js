// Submitted answer reviews are private and use the original attempt snapshot.
const resultState = { data: null, module: 'listening', filter: 'all' };
const resultModules = [['listening', 'Listening', 'headphones'], ['grammar', 'Structure', 'layers'], ['reading', 'Reading', 'book']];

async function loadResults() {
  const el = document.getElementById('resultsContent');
  const sid = new URLSearchParams(location.search).get('id');
  if (!sid) {
    el.innerHTML = '<div class="empty-state"><h2>Pilih sesi yang ingin ditinjau</h2><p>Hasil dan pembahasan tersedia dalam riwayat pribadi Anda.</p><a href="/history" class="btn-primary">Buka riwayat latihan</a></div>';
    return;
  }
  try {
    const [data, surveyStatus] = await Promise.all([
      api('/api/results?id=' + encodeURIComponent(sid)),
      api('/api/survey?session_id=' + encodeURIComponent(sid)).catch(() => ({ submitted: false }))
    ]);
    if (!el.isConnected) return;
    resultState.data = data;
    resultState.filter = 'all';
    const result = data.toefl_practice_result;
    const ordered = [...resultModules].sort((a, b) => resultRatio(result, a[0]) - resultRatio(result, b[0]));
    resultState.module = ordered[0][0];
    const review = data.ai_tutor_explanation || {};
    const notes = review.summary ? [review.summary] : [review.grammar_review, review.essay_review, review.actionable_tip].filter(Boolean);
    const participantCode = data.participant_code || '';

    el.innerHTML = `
      <p class="result-meta">${data.submitted_at ? escapeHtml(formatDateTime(data.submitted_at)) + ' / ' : ''}ID Sesi: ${escapeHtml(sid)}${participantCode ? ' / Responden: ' + escapeHtml(participantCode) : ''}</p>
      <div id="surveyContainer">${renderSurveySection(sid, surveyStatus)}</div>
      <section class="result-summary">
        <div>
          <h2>Ketepatan jawaban EPT</h2>
          <p>Gabungan Listening, Structure, dan Reading.</p>
          <p class="disclaimer">Hasil latihan, bukan skor TOEFL resmi.</p>
        </div>
        <strong class="accuracy-value">${result.accuracy_percent}<span>%</span></strong>
      </section>
      <div class="result-module-grid" aria-label="Pilih modul untuk melihat pembahasan">
        ${resultModules.map(([key, label, symbol]) => `
          <button type="button" class="result-module-score" data-result-module="${key}" aria-pressed="${key === resultState.module}">
            ${icon(symbol)}
            <span>${label}</span>
            <strong>${result[key + '_mc_correct'] || 0}<small> / ${result[key + '_mc_total'] || 0} benar</small></strong>
            <progress value="${result[key + '_mc_correct'] || 0}" max="${Math.max(1, result[key + '_mc_total'] || 0)}"></progress>
            <span class="module-review-link">Tinjau jawaban ${icon('chevronRight')}</span>
          </button>
        `).join('')}
      </div>
      <aside class="result-next-step">
        <div>
          <h2>Fokus berikutnya: ${ordered[0][1]}</h2>
          <p>${result.accuracy_percent === 100 ? 'Pertahankan pemahaman Anda dengan soal lain dari bank aktif.' : 'Mulai dari modul dengan ketepatan paling rendah pada sesi ini.'}</p>
        </div>
        <a href="/practice?module=${ordered[0][0]}" class="btn-primary">Latih ${ordered[0][1]} ${icon('chevronRight')}</a>
      </aside>
      <section class="result-review-section">
        <div class="result-review-heading">
          <h2 id="resultReviewTitle">Pembahasan per soal</h2>
          <div class="review-filters" aria-label="Filter pembahasan">
            <button type="button" data-review-filter="all" aria-pressed="true">Semua</button>
            <button type="button" data-review-filter="review" aria-pressed="false">Salah / belum dijawab</button>
          </div>
        </div>
        <div id="resultReviewList"></div>
      </section>
      <details class="research-result-notes">
        <summary>Writing dan catatan tambahan riset</summary>
        <dl>
          <div><dt>Perbaikan kalimat</dt><dd>${result.rewrite_done || 0} terisi</dd></div>
          <div><dt>Writing</dt><dd>${result.essay_word_count || 0} kata</dd></div>
        </dl>
        <p>Tugas ini terpisah dari ketepatan pilihan ganda EPT. Jumlah kata menunjukkan panjang tulisan, bukan kualitasnya.</p>
        ${notes.map(text => `<p>${escapeHtml(text)}</p>`).join('')}
      </details>
      <div class="action-row result-bottom-actions">
        <a href="/exam" class="btn-secondary">Siapkan sesi ujian baru</a>
        <a href="/dashboard" class="text-link">Kembali ke dasbor</a>
      </div>
    `;

    attachSurveyEvents(sid);
    document.querySelectorAll('[data-result-module]').forEach(button => button.addEventListener('click', () => {
      resultState.module = button.dataset.resultModule;
      renderResultReview();
      document.getElementById('resultReviewTitle').scrollIntoView({ block: 'start' });
    }));
    document.querySelectorAll('[data-review-filter]').forEach(button => button.addEventListener('click', () => {
      resultState.filter = button.dataset.reviewFilter;
      renderResultReview();
    }));
    renderResultReview();
  } catch (error) {
    renderError(el, error.message, loadResults);
  }
}

function renderSurveySection(sid, status) {
  if (sessionStorage.getItem('skip_survey_' + sid) === '1' && !status.submitted) {
    return '';
  }
  if (status.submitted) {
    const s = status.survey || {};
    const labelText = s.honest_label === 'CHEATING_REPORTED' ? 'Terlaporkan Akses Luar / Copas' : 'Terlaporkan Mandiri Penuh';
    return `
      <section class="research-survey-card is-completed" id="researchSurveyCard">
        <div class="survey-badge">${icon('shield')}<span>Validasi Data Riset</span></div>
        <div class="survey-header">
          <h3>Konfirmasi Responden Tersimpan</h3>
          <p>Status label riset skripsi: <strong>${escapeHtml(labelText)}</strong>. Data ini berkontribusi untuk validasi ground-truth deteksi.</p>
        </div>
      </section>
    `;
  }
  return `
    <section class="research-survey-card" id="researchSurveyCard">
      <div class="survey-badge">${icon('shield')}<span>Survei Integritas Riset (Opsional)</span></div>
      <div class="survey-header">
        <h3>Konfirmasi Perilaku Pengerjaan Responden</h3>
        <p>Bantu validasi data riset skripsi integritas akademik. Jawaban bersifat rahasia dan <strong>tidak memengaruhi</strong> perolehan hasil TOEFL EPT Anda.</p>
      </div>
      <form id="respondentSurveyForm" class="survey-form">
        <fieldset class="survey-fieldset">
          <legend class="survey-legend">1. Selama ujian berlangsung, apakah Anda sempat berpindah tab atau meminimalkan jendela ujian?</legend>
          <div class="survey-radios">
            <label><input type="radio" name="surveyTabSwitch" value="0" checked><span>Tidak, saya tetap di layar ujian</span></label>
            <label><input type="radio" name="surveyTabSwitch" value="1"><span>Ya, saya sempat keluar/berpindah tab</span></label>
          </div>
        </fieldset>
        <fieldset class="survey-fieldset">
          <legend class="survey-legend">2. Apakah Anda melakukan aksi copy-paste atau mencari bantuan luar (kamus, catatan, AI)?</legend>
          <div class="survey-radios">
            <label><input type="radio" name="surveyCopyPaste" value="0" checked><span>Tidak, saya mengerjakan mandiri</span></label>
            <label><input type="radio" name="surveyCopyPaste" value="1"><span>Ya, saya melakukan copy-paste / membuka contekan</span></label>
          </div>
        </fieldset>
        <div class="survey-field">
          <label for="surveyNote">Catatan atau kendala selama pengerjaan (opsional)</label>
          <textarea id="surveyNote" rows="2" placeholder="Tuliskan kendala jaringan, tidak sengaja refresh, atau penjelasan lain..."></textarea>
        </div>
        <div class="survey-actions">
          <button type="submit" class="btn-primary" id="btnSubmitSurvey">Kirim Konfirmasi Riset</button>
          <button type="button" class="btn-subtle" id="btnSkipSurvey">Lewati</button>
        </div>
      </form>
    </section>
  `;
}

function attachSurveyEvents(sid) {
  const form = document.getElementById('respondentSurveyForm');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = document.getElementById('btnSubmitSurvey');
      btn.disabled = true;
      btn.textContent = 'Menyimpan…';
      const tabSwitched = form.surveyTabSwitch.value === '1';
      const copiedPasted = form.surveyCopyPaste.value === '1';
      const note = document.getElementById('surveyNote')?.value || '';
      try {
        const res = await api('/api/survey', {
          method: 'POST',
          body: JSON.stringify({
            session_id: sid,
            tab_switched: tabSwitched,
            copied_pasted: copiedPasted,
            feedback_note: note
          })
        });
        showToast(res.message || 'Konfirmasi survei berhasil disimpan.');
        const container = document.getElementById('surveyContainer');
        if (container) {
          container.innerHTML = renderSurveySection(sid, { submitted: true, survey: { honest_label: res.label } });
        }
      } catch (err) {
        showToast(err.message);
        btn.disabled = false;
        btn.textContent = 'Kirim Konfirmasi Riset';
      }
    });
  }
  const skipBtn = document.getElementById('btnSkipSurvey');
  if (skipBtn) {
    skipBtn.addEventListener('click', () => {
      sessionStorage.setItem('skip_survey_' + sid, '1');
      document.getElementById('researchSurveyCard')?.remove();
    });
  }
}

function resultRatio(result, key) {
  return (result[key + '_mc_correct'] || 0) / Math.max(1, result[key + '_mc_total'] || 0);
}

function renderResultReview() {
  const result = resultState.data.toefl_practice_result;
  const label = resultModules.find(item => item[0] === resultState.module)[1];
  document.getElementById('resultReviewTitle').textContent = 'Pembahasan ' + label;
  document.querySelectorAll('[data-result-module]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.resultModule === resultState.module)));
  document.querySelectorAll('[data-review-filter]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.reviewFilter === resultState.filter)));
  const reviews = result.section_reviews?.[resultState.module];
  const list = document.getElementById('resultReviewList');
  if (!reviews) {
    list.innerHTML = `<div class="review-archive-note"><h3>Arsip pembahasan terbatas</h3><p>Sesi lama ini tidak menyimpan rincian soal yang diperlukan. Ketepatan asli tetap ditampilkan; kunci dari bank terbaru tidak digunakan untuk menilai ulang sesi.</p>${resultState.module === 'grammar' ? (result.grammar_feedback || []).map(item => `<article><h4>${escapeHtml(item.title)}</h4><p>${escapeHtml(item.explanation)}</p></article>`).join('') : ''}</div>`;
    return;
  }
  const shown = reviews.map((q, index) => ({ ...q, number: index + 1 })).filter(q => resultState.filter === 'all' || q.status !== 'correct');
  list.innerHTML = shown.map((q, index) => renderReviewedQuestion(q, index === 0)).join('') || '<div class="review-archive-note"><h3>Tidak ada jawaban yang perlu ditinjau</h3><p>Gunakan filter Semua untuk membaca kembali pembahasannya.</p></div>';
}

function renderReviewedQuestion(q, open) {
  const statuses = { correct: 'Benar', incorrect: 'Salah', unanswered: 'Belum dijawab' };
  const context = q.passage ? `<details class="review-context"><summary>Baca wacana</summary><div>${escapeHtml(readablePassage(q.passage))}</div></details>` : q.audio_url ? `<audio controls preload="none" src="${escapeHtml(q.audio_url)}" aria-label="Audio soal yang ditinjau"></audio>` : '';
  return `<details class="review-question" ${open ? 'open' : ''}><summary><span class="review-number">${q.number}</span><span>${escapeHtml(q.title || 'Soal ' + q.number)}</span><span class="answer-status ${q.status}">${statuses[q.status]}</span></summary><div class="review-question-content"><h3>${escapeHtml(q.prompt)}</h3>${context}<ol class="review-options">${q.options.map((option, index) => `<li class="${index === q.correct_answer ? 'is-correct' : index === q.selected_answer ? 'is-incorrect' : ''}"><span class="review-letter">${String.fromCharCode(65 + index)}</span><span>${escapeHtml(choiceText(option))}</span><small>${index === q.correct_answer ? 'Kunci' : ''}${index === q.selected_answer ? (index === q.correct_answer ? ' / ' : '') + 'Pilihan Anda' : ''}</small></li>`).join('')}</ol>${q.status === 'unanswered' ? '<p class="review-unanswered">Anda belum memilih jawaban untuk soal ini.</p>' : ''}<div class="review-explanation"><h4>Alasan jawaban</h4><p>${escapeHtml(q.explanation || 'Pembahasan belum disediakan untuk soal ini.')}</p></div></div></details>`;
}
