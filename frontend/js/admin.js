// Admin dashboard controller with URL-based subtab navigation and deep inspection panels.
async function initAdminPage() {
  const params = new URLSearchParams(location.search);
  let tab = params.get('tab') || 'overview';
  const path = appState.route || location.pathname;
  if (path.startsWith('/admin/')) tab = path.replace('/admin/', '');
  if (!['overview', 'proctor', 'questions', 'users'].includes(tab)) tab = 'overview';
  await switchAdminTab(tab, false);
}

async function switchAdminTab(tab, updateHistory = true) {
  if (typeof confirmQuestionTransition === 'function' && !await confirmQuestionTransition()) return false;
  if (updateHistory) {
    history.pushState(null, '', `/admin/${tab}`);
    appState.route = `/admin/${tab}`;
  }
  const tabMap = {
    overview: ["adminTabOverview", "subtabOverview"],
    proctor: ["adminTabProctor", "subtabProctor"],
    questions: ["adminTabQuestions", "subtabQuestions"],
    users: ["adminTabUsers", "subtabUsers"]
  };
  Object.keys(tabMap).forEach(key => {
    const [sectionId, btnId] = tabMap[key];
    const section = document.getElementById(sectionId);
    const btn = document.getElementById(btnId);
    if (section) section.classList.toggle("hidden", key !== tab);
    if (btn) btn.classList.toggle("active", key !== tab);
  });
  const titles = { overview: 'Ringkasan', proctor: 'Pengawasan', questions: 'Bank soal', users: 'Akun pengguna' };
  const currentTitle = document.getElementById('adminCurrentTitle');
  if (currentTitle) currentTitle.textContent = titles[tab] || 'Ringkasan';
  const operations = { overview: loadAdminOverview, proctor: loadProctorSessions, questions: loadAdminQuestionsTable, users: loadAdminUsersTable };
  if (operations[tab]) await operations[tab]();
  return true;
}

const proctorView = { selected: null };
function proctorPercent(value) { return Math.max(0, Math.min(100, Number(value || 0) * 100)).toFixed(1); }
function proctorScenario(value) { return { MANDIRI: 'Mandiri', COPY_TYPING: 'Simulasi menyalin', AI_PARAPHRASE: 'Simulasi parafrase AI' }[value] || value; }

function proctorLabelBadge(label) {
  if (label === 'CHEATING_REPORTED' || label === 'MANUAL_CHEATING') return '<span class="risk-badge risk-high">Akses Luar</span>';
  if (label === 'CLEAN_REPORTED' || label === 'MANUAL_CLEAN') return '<span class="risk-badge risk-low">Mandiri</span>';
  return '<span class="risk-badge monitor-neutral">Belum dilabeli</span>';
}

async function loadProctorSessions() {
  const body = document.getElementById('proctorSessionsBody');
  try {
    const data = await api('/api/proctor/sessions');
    if (!body?.isConnected) return;
    appState.proctorSessions = data.sessions || [];
    const sessions = appState.proctorSessions;
    const flagged = sessions.filter(s => s.rule_flag).length;
    const proctorStats = [
      ['Sesi terkirim', sessions.length, 'check', 'blue'],
      ['Rule terpicu', flagged, 'alert', 'red'],
      ['Rule tidak terpicu', sessions.length - flagged, 'shield', 'green']
    ];
    document.getElementById('proctorKpiGrid').innerHTML = proctorStats.map(([label, count, iconName, color]) =>
      `<div class="kpi-card"><div class="kpi-card-head"><div class="kpi-icon-box kpi-icon-${color}">${icon(iconName)}</div></div><strong class="kpi-value">${count}</strong><span class="kpi-label">${label}</span></div>`
    ).join('');
    renderProctorList();
    const selected = sessions.findIndex(s => s.session_id === proctorView.selected);
    if (selected >= 0) inspectTelemetrySession(selected);
    else { proctorView.selected = null; document.getElementById('proctorDetailPanel').classList.add('hidden'); document.getElementById('adminTabProctor').classList.remove('is-inspecting'); }
  } catch (error) { if (body?.isConnected) { document.getElementById('proctorListCount').textContent = error.message; showToast(error.message); } }
}

function renderProctorList() {
  const query = document.getElementById('proctorSearch').value.trim().toLowerCase();
  const filter = document.getElementById('proctorFilter').value;
  const sessions = appState.proctorSessions.map((session, index) => ({ session, index })).filter(({ session: s }) => (!query || [s.display_name, s.participant_code, s.session_id, s.created_at].join(' ').toLowerCase().includes(query)) && (!filter || (filter === 'flagged' ? s.rule_flag : !s.rule_flag)));
  document.getElementById('proctorListCount').textContent = sessions.length + ' sesi';
  document.getElementById('proctorSessionsBody').innerHTML = sessions.map(({ session: s, index }) => `
    <tr id="proctorRow${index}" class="${s.session_id === proctorView.selected ? 'selected-row' : ''}">
      <td data-label="Peserta"><strong>${escapeHtml(s.display_name || s.participant_code)}</strong><small>${escapeHtml(s.participant_code)}</small><small><time>${escapeHtml(formatDateTime(s.created_at))}</time></small><small class="monitor-session-code" title="${escapeHtml(s.session_id)}">Sesi ${escapeHtml(s.session_id.slice(-8))}</small></td>
      <td data-label="Perangkat">${icon(s.device_profile === 'PC_PHYSICAL' ? 'laptop' : 'smartphone')}${s.device_profile === 'PC_PHYSICAL' ? 'Komputer' : 'Ponsel'}</td>
      <td data-label="Skenario peserta">${escapeHtml(proctorScenario(s.task_condition))}</td>
      <td data-label="Indikator rule"><span class="risk-badge ${s.rule_flag ? 'risk-mid' : 'monitor-neutral'}">${s.rule_flag ? 'Terpicu' : 'Tidak terpicu'}</span></td>
      <td data-label="Label riset">${proctorLabelBadge(s.ground_truth_label || s.survey_label)}</td>
      <td data-label="Tindakan"><button type="button" class="btn-secondary" data-inspect-index="${index}" aria-label="Tinjau sesi ${escapeHtml(s.participant_code)} ${escapeHtml(s.session_id.slice(-8))}">Tinjau</button></td>
    </tr>
  `).join('') || '<tr class="monitor-empty-row"><td colspan="6"><h4>Belum ada sesi yang cocok</h4><p>Sesi muncul setelah peserta mengirim jawaban. Jika menggunakan filter, coba tampilkan semua sesi.</p></td></tr>';
  document.querySelectorAll('[data-inspect-index]').forEach(button => button.addEventListener('click', () => inspectTelemetrySession(Number(button.dataset.inspectIndex), true)));
}

function inspectTelemetrySession(index, focus = false) {
  const s = appState.proctorSessions[index];
  if (!s) return;
  proctorView.selected = s.session_id;
  document.getElementById('proctorDetailPanel').classList.remove('hidden');
  document.getElementById('adminTabProctor').classList.add('is-inspecting');
  document.querySelectorAll('#proctorSessionsBody tr').forEach(row => row.classList.toggle('selected-row', row.id === 'proctorRow' + index));
  const title = document.getElementById('inspectTitle');
  title.textContent = 'Peserta ' + s.participant_code;

  const currentLabel = s.ground_truth_label || s.survey_label || 'UNLABELED';
  const surveyInfo = s.survey_submitted_at ? `
    <div class="monitor-survey-info" style="margin-top:12px;padding:12px;background:var(--color-paper-2);border-radius:var(--radius-sm);border:1px solid var(--color-rule);">
      <h4 style="font-size:13px;margin:0 0 6px 0;">Konfirmasi Responden (Survei)</h4>
      <p style="font-size:12px;margin:0 0 4px 0;">Beralih tab/jendela: <strong>${s.survey_tab_switched ? 'Ya' : 'Tidak'}</strong> | Aksi copy/paste/bantuan luar: <strong>${s.survey_copied_pasted ? 'Ya' : 'Tidak'}</strong></p>
      ${s.survey_note ? `<p style="font-size:12px;color:var(--color-muted);margin:0;">Catatan: ${escapeHtml(s.survey_note)}</p>` : ''}
    </div>
  ` : '<p class="monitor-caveat" style="margin-top:8px;">Responden belum/tidak mengisi survei konfirmasi integritas.</p>';

  const labelSelector = `
    <div style="margin-top:12px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
      <label for="inspectLabelSelect" style="font-size:12px;font-weight:600;">Label Ground Truth:</label>
      <select id="inspectLabelSelect" onchange="changeProctorLabel('${escapeHtml(s.session_id)}', this.value)" style="padding:4px 8px;font-size:12px;border:1px solid var(--color-rule);border-radius:var(--radius-sm);background:var(--color-paper);color:var(--color-ink);">
        <option value="UNLABELED" ${currentLabel === 'UNLABELED' ? 'selected' : ''}>Belum dilabeli</option>
        <option value="CLEAN_REPORTED" ${currentLabel === 'CLEAN_REPORTED' ? 'selected' : ''}>Mandiri (Survei)</option>
        <option value="CHEATING_REPORTED" ${currentLabel === 'CHEATING_REPORTED' ? 'selected' : ''}>Akses Luar (Survei)</option>
        <option value="MANUAL_CLEAN" ${currentLabel === 'MANUAL_CLEAN' ? 'selected' : ''}>Validasi Manual: Mandiri</option>
        <option value="MANUAL_CHEATING" ${currentLabel === 'MANUAL_CHEATING' ? 'selected' : ''}>Validasi Manual: Curang</option>
      </select>
    </div>
  `;

  document.getElementById('inspectSummary').innerHTML = `
    <p class="monitor-session-meta"><time>${escapeHtml(formatDateTime(s.created_at))}</time><span>${s.device_profile === 'PC_PHYSICAL' ? 'Komputer' : 'Ponsel'}</span></p>
    <dl class="monitor-session-details">
      <div><dt>Kode sesi</dt><dd>${escapeHtml(s.session_id)}</dd></div>
      <div><dt>Skenario yang dipilih peserta</dt><dd>${escapeHtml(proctorScenario(s.task_condition))}</dd></div>
    </dl>
    <p class="monitor-rule-message">${icon(s.rule_flag ? 'alert' : 'shield')}<span>${s.rule_flag ? 'Rule terpicu. Tinjau konteks dan catatan sesi.' : 'Rule tidak terpicu. Hasil ini tetap perlu dibaca bersama konteks sesi.'}</span></p>
    ${surveyInfo}
    ${labelSelector}
  `;

  const features = s.features || {};
  document.getElementById('inspectFacts').innerHTML = [
    ['Perubahan fokus', Number(features.focus_loss_episodes || 0) + ' kali'],
    ['Durasi tersembunyi', (Number(features.hidden_duration_ms || 0) / 1000).toFixed(1) + 's'],
    ['Revisi jawaban', Number(features.answer_change_count || 0) + ' kali'],
    ['Lompatan navigasi', Number(features.nav_switch_count || 0) + ' kali'],
    ['Waktu rata-rata soal', Number(features.mean_item_time_sec || 0).toFixed(1) + 's'],
    ['Jawaban kilat (<2.5s)', Number(features.rapid_answer_count || 0) + ' soal'],
    ['Peristiwa tempel', Number(features.paste_count || 0) + ' kali'],
    ['Durasi pengerjaan', Math.round(Number(s.duration_sec || 0) / 60) + ' menit']
  ].map(([label, value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`).join('');

  document.getElementById('inspectModelScores').innerHTML = [
    ['XGBoost', s.xgboost_score],
    ['1D-CNN', s.cnn1d_score]
  ].map(([label, value]) => `<div><span>${label}</span><strong>${proctorPercent(value)}%</strong><meter min="0" max="100" value="${proctorPercent(value)}" aria-label="Indikator ${label}">${proctorPercent(value)}%</meter></div>`).join('') + `<p>Latensi inferensi: ${Number(s.inference_latency_ms || 0).toFixed(2)} ms.</p>`;

  const ablation = s.ablation || {};
  const rows = [
    ['Ketikan', 'keystroke_only'],
    ['Fokus browser', 'focus_only'],
    ['Pointer', 'heatmap_only'],
    ['Perilaku pengerjaan', 'work_behavior_only'],
    ['Fusi telemetri & perilaku', 'telemetry_work_fusion'],
    ['Semua fitur (Fusi penuh)', 'full_fusion_xgboost']
  ];
  document.getElementById('ablationContainer').innerHTML = rows.map(([label, key]) => `<div class="abl-row"><span>${label}</span><div class="abl-track"><div class="abl-fill" style="width:${proctorPercent(ablation[key])}%"></div></div><strong>${proctorPercent(ablation[key])}%</strong></div>`).join('');
  document.getElementById('timelineContainer').innerHTML = (s.timeline_events || []).map(ev => `<li><strong>+${Number(ev.t || 0)} detik, ${escapeHtml(ev.type)}</strong><span>${escapeHtml(ev.detail)}</span></li>`).join('') || '<li>Tidak ada catatan peristiwa pada sesi ini.</li>';
  document.getElementById('heatmapLegend').innerHTML = [['Navigasi', 'zone_nav_prop'], ['Bacaan/instruksi', 'zone_passage_prop'], ['Jawaban', 'zone_answer_prop']].map(([label, key]) => `<span>${label}: ${proctorPercent(features[key])}%</span>`).join('');
  renderHeatmapCanvas(s.heatmap_points || []);
  if (focus) { title.focus({ preventScroll: true }); document.getElementById('proctorDetailPanel').scrollIntoView({ block: 'start' }); }
}

async function changeProctorLabel(sessionId, newLabel) {
  try {
    await api('/api/proctor/label', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, label: newLabel })
    });
    showToast('Label ground truth berhasil disimpan.');
    const item = appState.proctorSessions.find(s => s.session_id === sessionId);
    if (item) {
      item.ground_truth_label = newLabel;
      item.survey_label = newLabel;
    }
    renderProctorList();
  } catch (err) {
    showToast(err.message);
  }
}

function closeProctorDetail() {
  const index = appState.proctorSessions.findIndex(s => s.session_id === proctorView.selected);
  document.getElementById('adminTabProctor').classList.remove('is-inspecting');
  document.getElementById('proctorDetailPanel').classList.add('hidden');
  proctorView.selected = null;
  renderProctorList();
  (document.querySelector(`[data-inspect-index="${index}"]`) || document.getElementById('proctorSearch'))?.focus();
}

function renderHeatmapCanvas(points) {
  const canvas = document.getElementById('heatmapCanvas');
  const ctx = canvas.getContext('2d');
  const css = getComputedStyle(document.documentElement);
  const token = name => css.getPropertyValue(name).trim();
  const width = canvas.width, height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = token('--color-paper-3'); ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = token('--color-rule-2'); ctx.lineWidth = 1;
  ctx.strokeRect(16, 16, width - 32, 48);
  ctx.strokeRect(16, 80, width * .46 - 24, height - 96);
  ctx.strokeRect(width * .46 + 8, 80, width * .54 - 24, height - 96);
  ctx.fillStyle = token('--color-ink-2'); ctx.font = '18px ' + token('--font-body');
  ctx.fillText('Navigasi', 28, 48); ctx.fillText('Bacaan / instruksi', 28, 110); ctx.fillText('Jawaban', width * .46 + 20, 110);
  ctx.globalAlpha = .42;
  (points || []).forEach(pt => {
    const x = Math.min(width, Math.max(0, pt.x * width));
    const y = Math.min(height, Math.max(0, pt.y * height));
    const rad = ctx.createRadialGradient(x, y, 2, x, y, 16);
    rad.addColorStop(0, 'rgba(14, 165, 233, 0.55)');
    rad.addColorStop(1, 'rgba(14, 165, 233, 0)');
    ctx.fillStyle = rad;
    ctx.beginPath();
    ctx.arc(x, y, 16, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.globalAlpha = 1.0;
}
