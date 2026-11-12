// Exam lifecycle: explicit start, device-local drafts, deadline and submission.
let examTimerId = null;
function draftKey() { return 'linguapulse_draft_' + appState.currentUser?.user_id; }

function readExamDraft() {
  try {
    const raw = localStorage.getItem(draftKey());
    return raw ? JSON.parse(raw) : null;
  } catch (_) { return null; }
}

function saveExamDraft() {
  if (!appState.exam) return;
  try {
    localStorage.setItem(draftKey(), JSON.stringify({
      exam: appState.exam, answers: appState.selectedAnswers,
      telemetry: getTelemetrySnapshot()
    }));
  } catch (_) { showToast('Penyimpanan perangkat penuh. Biarkan halaman terbuka sampai jawaban terkirim.'); }
}

function clearExamDraft() {
  if (appState.currentUser) localStorage.removeItem(draftKey());
  appState.exam = null;
  appState.selectedAnswers = {};
  stopExamCountdown();
  setTelemetryActive(false);
}

async function initExamPreparation() {
  const draft = readExamDraft();
  const isMobile = /Android|iPhone|iPad|Mobile/i.test(navigator.userAgent);
  document.getElementById('deviceProfile').value = draft?.exam?.device || (isMobile ? 'MOBILE_VIRTUAL' : 'PC_PHYSICAL');
  if (draft?.exam) {
    document.getElementById('taskCondition').value = draft.exam.condition;
    document.getElementById('resumeExamButton').classList.remove('hidden');
    document.getElementById('beginExamButton').textContent = 'Hapus draf & mulai ulang';
  }
  try {
    const bank = await loadExamQuestions(false);
    if (!document.getElementById('prepareBankSummary')) return;
    const modules = [['Listening', bank.listening.questions.length], ['Structure', bank.grammar_mc.length], ['Reading', bank.reading.questions.length]];
    document.getElementById('prepareBankSummary').innerHTML = modules.map(([name, count]) => `<div><dt>${name}</dt><dd>${count} soal</dd></div>`).join('');
    document.getElementById('prepareWritingSelect').innerHTML = bank.writing_tasks.map(item => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.title)}</option>`).join('') || '<option value="">Belum ada tugas tambahan</option>';
    if (typeof initAdminComboboxes === 'function') initAdminComboboxes();
  } catch (error) {
    const el = document.getElementById('prepareError');
    if (el) { el.textContent = error.message; el.classList.remove('hidden'); }
  }
}

async function beginExam(event) {
  event.preventDefault();
  const button = document.getElementById('beginExamButton');
  if (readExamDraft()?.exam && !confirm('Hapus draf sesi sebelumnya dan mulai sesi baru?')) return;
  button.disabled = true;
  const error = document.getElementById('prepareError');
  error.classList.add('hidden');
  try {
    await initSecurityHandshake();
    const started = await api('/api/exam/start', { method: 'POST', body: JSON.stringify({
      device_profile: document.getElementById('deviceProfile').value,
      task_condition: document.getElementById('taskCondition').value,
      writing_id: document.getElementById('prepareWritingSelect').value,
      consent_agreed: document.getElementById('examConsent').checked
    }) });
    clearExamDraft();
    resetTelemetry();
    appState.exam = {
      attemptId: started.attempt_id, deadline: started.deadline,
      device: document.getElementById('deviceProfile').value,
      condition: document.getElementById('taskCondition').value,
      section: 0, consent: true, marked: []
    };
    appState.questionsBank = started.bank;
    saveExamDraft();
    await navigate('/exam/session');
  } catch (err) {
    error.textContent = err.message;
    error.classList.remove('hidden');
  } finally { button.disabled = false; }
}

async function loadExamQuestions(render = true) {
  const data = await api('/api/questions');
  appState.questionsBank = data;
  appState.adminQuestionsList = data.all_questions || [];
  if (render && document.getElementById('grammarMcContainer')) renderExamQuestions(data);
  return data;
}

async function initExamPage() {
  const draft = readExamDraft();
  if (!appState.exam && draft?.exam?.consent) {
    appState.exam = draft.exam;
    appState.selectedAnswers = draft.answers || {};
    resetTelemetry(draft.telemetry);
  }
  if (!appState.exam?.consent) return navigate('/exam', true);
  let resumed;
  try {
    resumed = await api('/api/exam/resume?id=' + encodeURIComponent(appState.exam.attemptId));
  } catch (error) {
    if (!appState.currentUser) return;
    clearExamDraft(); showToast(error.message); return navigate('/exam', true);
  }
  appState.questionsBank = resumed.bank;
  appState.exam.deadline = resumed.deadline;
  renderExamQuestions(resumed.bank);
  if (appState.route !== '/exam/session') return;
  await initSecurityHandshake();
  const exit = document.createElement('button');
  exit.type = 'button'; exit.className = 'btn-secondary'; exit.textContent = 'Keluar sesi';
  exit.addEventListener('click', () => {
    if (appState.submitting) return;
    if (!confirm('Hentikan sesi dan hapus draf jawaban di perangkat ini?')) return;
    clearExamDraft(); navigate('/dashboard');
  });
  document.querySelector('.exam-heading').append(exit);
  document.getElementById('viewExam').addEventListener('input', event => {
    let key = null, val = null;
    if (event.target.type === 'radio') {
      key = event.target.name; val = Number(event.target.value);
    } else if (event.target.dataset.answer) {
      key = event.target.dataset.answer; val = event.target.value;
    }
    if (key) {
      const prev = appState.selectedAnswers[key];
      if (prev !== undefined && prev !== null && String(prev).trim() !== '' && String(prev) !== String(val)) {
        if (typeof recordAnswerChange === 'function') recordAnswerChange(key);
      }
      if (typeof recordItemAnswer === 'function') recordItemAnswer(key);
      appState.selectedAnswers[key] = val;
    }
    queueMicrotask(() => { refreshExamProgress(); saveExamDraft(); });
  });
  showExamSection(appState.exam.section ?? 0);
  refreshTelemetryMeters();
  setTelemetryActive(true);
  startExamCountdown();
}

async function submitExamSession(automatic = false) {
  if (!appState.exam || appState.submitting) return;
  if (!automatic && !confirm('Kirim jawaban dan akhiri sesi? Jawaban tidak dapat diubah setelah dikirim.')) return;
  appState.submitting = true;
  document.getElementById('examSubmitError').classList.add('hidden');
  stopExamCountdown();
  setTelemetryActive(false);
  saveExamDraft();
  document.querySelectorAll('#viewExam input, #viewExam textarea, #viewExam button').forEach(el => el.disabled = true);
  const button = document.getElementById('submitExamButton');
  button.textContent = 'Mengirim jawaban…';
  try {
    const payload = {
      attempt_id: appState.exam.attemptId,
      device_profile: appState.exam.device, task_condition: appState.exam.condition,
      consent_agreed: appState.exam.consent,
      duration_sec: Math.max(1, telemetryState.activeDurationMs / 1000),
      dwell_times: telemetryState.dwellTimes, flight_times: telemetryState.flightTimes,
      interkey_times: telemetryState.interkeyTimes, total_keydowns: telemetryState.totalKeydowns,
      backspace_count: telemetryState.backspaceCount, paste_count: telemetryState.pasteCount,
      bulk_insert_count: telemetryState.bulkInsertCount, focus_loss_episodes: telemetryState.focusLossEpisodes,
      hidden_duration_ms: telemetryState.hiddenDurationMs, zone_counts: telemetryState.zoneCounts,
      heatmap_points: telemetryState.heatmapPoints, timeline_events: telemetryState.timelineEvents,
      answer_change_count: telemetryState.answerChangeCount || 0,
      nav_switch_count: telemetryState.navSwitchCount || 0,
      item_response_times: telemetryState.itemResponseTimes || [],
      total_questions_attempted: Object.keys(appState.selectedAnswers || {}).length,
      answers: appState.selectedAnswers
    };
    await initSecurityHandshake();
    const encrypted = await encryptTelemetryPayload(payload);
    const data = await api('/api/submit', { method: 'POST', body: JSON.stringify(encrypted) });
    appState.latestResult = data.already_submitted ? null : data;
    clearExamDraft();
    appState.submitting = false;
    await navigate('/results?id=' + encodeURIComponent(data.session_id));
  } catch (error) {
    appState.submitting = false;
    if (!appState.exam || !appState.currentUser) return;
    showToast(error.message + ' Draf tetap tersimpan. Coba kirim kembali.');
    button.textContent = 'Coba kirim kembali';
    document.getElementById('examSubmitErrorText').textContent = error.message + ' Draf tetap tersimpan di perangkat ini.';
    document.getElementById('examSubmitError').classList.remove('hidden');
    document.querySelectorAll('#viewExam input, #viewExam textarea, #viewExam button').forEach(el => el.disabled = false);
    if (Date.now() < appState.exam.deadline) {
      setTelemetryActive(true); startExamCountdown();
    } else {
      document.querySelectorAll('#viewExam input, #viewExam textarea, .step-btn').forEach(el => el.disabled = true);
      document.getElementById('examTimer').textContent = 'Waktu habis';
    }
  }
}

function stopExamCountdown() { clearInterval(examTimerId); examTimerId = null; }
function startExamCountdown() {
  stopExamCountdown();
  const tick = () => {
    if (!appState.exam) return stopExamCountdown();
    const remaining = Math.max(0, Math.ceil((appState.exam.deadline - Date.now()) / 1000));
    document.getElementById('examTimer').textContent = `${String(Math.floor(remaining / 60)).padStart(2, '0')}:${String(remaining % 60).padStart(2, '0')}`;
    if (!remaining) submitExamSession(true);
  };
  examTimerId = setInterval(tick, 1000);
  tick();
}
