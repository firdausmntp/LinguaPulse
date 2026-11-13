// Operational overview, using actual database counts and submissions only.
async function loadAdminOverview() {
  const el = document.getElementById('adminOverviewContent');
  el.setAttribute('aria-busy', 'true');
  try {
    const data = await api('/api/admin/overview');
    if (!el.isConnected) return;
    const modules = [['listening', 'Listening', 'headphones'], ['grammar', 'Structure', 'layers'], ['reading', 'Reading', 'book'], ['writing', 'Writing riset', 'pen']];
    const total = data.modules.reduce((sum, item) => sum + item.active, 0);
    const missing = modules.slice(0, 3).filter(([section]) => !(data.modules.find(row => row.section === section)?.active_mc > 0));
    const readiness = missing.length ? 'Lengkapi soal aktif untuk ' + missing.map(item => item[1]).join(', ') + ' sebelum peserta memulai sesi.' : 'Materi Listening, Structure, dan Reading siap dipakai pada sesi baru.';
    const noticeActionBtn = missing.length ? `<button type="button" class="btn-primary readiness-action-btn" onclick="switchAdminTab('questions')">Lengkapi materi</button>` : '';
    const statItems = [
      ['Peserta terdaftar', data.students, 'Akun peserta aktif', 'users', 'blue', ''],
      ['Soal aktif', total, 'Siap sesi baru', 'fileText', 'green', ''],
      ['Sesi terkirim', data.completed, 'Hasil tersimpan', 'checkCircle', 'purple', ''],
      ['Sesi berjalan', data.ongoing, 'Batas waktu aktif', 'clock', 'amber', data.ongoing ? 'Berjalan' : '']
    ];
    el.innerHTML = `<div class="overview-readiness-notice ${missing.length ? 'notice-warning' : 'notice-success'}"><div class="notice-body"><span class="notice-icon">${icon(missing.length ? 'alert' : 'check')}</span><p>${readiness}</p></div>${noticeActionBtn}</div><dl class="overview-stats">${statItems.map(([label, value, detail, symbol, color, badge]) => `<div class="kpi-card"><div class="kpi-card-head"><dt class="kpi-label">${label}</dt><div class="kpi-icon-box kpi-icon-${color}">${icon(symbol)}</div></div><dd class="kpi-value">${value}</dd><div class="kpi-card-footer"><p class="kpi-subtext">${detail}</p>${badge ? `<span class="kpi-badge kpi-badge-amber">${badge}</span>` : ''}</div></div>`).join('')}</dl>
      <div class="overview-columns"><section class="overview-panel"><div class="panel-heading"><h3>Sesi terbaru</h3><button type="button" class="btn-subtle" onclick="switchAdminTab('proctor')">Buka pengawasan</button></div>${data.recent.length ? `<ul class="overview-session-list">${data.recent.map(item => `<li class="session-row"><span class="avatar" aria-hidden="true">${escapeHtml(getInitials(item.display_name))}</span><div class="session-main"><strong>${escapeHtml(item.display_name)}</strong><small>${escapeHtml(item.participant_code)}</small></div><div class="session-meta"><time>${escapeHtml(formatDateTime(item.submitted_at))}</time><button type="button" class="btn-secondary btn-inspect-session" data-inspect-session="${escapeHtml(item.session_id)}">Tinjau</button></div></li>`).join('')}</ul>` : `<div class="overview-empty">${icon('shield')}<h4>Belum ada sesi untuk ditinjau</h4><p>Sesi peserta akan muncul di sini setelah jawaban dikirim. Anda dapat menyiapkan bank soal dan akun terlebih dahulu.</p><button class="btn-secondary" type="button" onclick="switchAdminTab('questions')">Periksa bank soal</button></div>`}</section>

      <section class="overview-panel"><div class="panel-heading"><h3>Kesiapan materi</h3><button type="button" class="btn-subtle" onclick="switchAdminTab('questions')">Kelola</button></div><ul class="module-readiness">${modules.map(([section, label, symbol]) => { const item = data.modules.find(row => row.section === section); return `<li>${icon(symbol)}<div><strong>${label}</strong><small>${section === 'writing' ? 'Tugas tambahan penelitian' : 'Modul TOEFL EPT'}</small></div><span>${item?.active || 0} aktif <small>dari ${item?.total || 0} soal</small></span></li>`; }).join('')}</ul><p class="overview-note">Perubahan materi berlaku untuk sesi baru. Soal pada sesi yang sedang dikerjakan tetap sama.</p></section></div>
      <section class="admin-task-strip" aria-label="Akses pengelolaan"><a href="/admin?tab=questions">${icon('edit')}<div><strong>Siapkan bank soal</strong><span>Tambah materi, audio, dan pembahasan.</span></div>${icon('chevronRight')}</a><a href="/admin?tab=users">${icon('settings')}<div><strong>Kelola akses peserta</strong><span>Buat akun atau perbarui identitas.</span></div>${icon('chevronRight')}</a></section>`;
    el.querySelectorAll('[data-inspect-session]').forEach(button => button.addEventListener('click', () => openOverviewSession(button.dataset.inspectSession)));
  } catch (error) { if (el.isConnected) renderError(el, error.message, loadAdminOverview); }
  finally { el.removeAttribute('aria-busy'); }
}

async function openOverviewSession(id) {
  if (!await switchAdminTab('proctor')) return;
  const index = appState.proctorSessions.findIndex(session => session.session_id === id);
  if (index >= 0) { inspectTelemetrySession(index, true); }
}
