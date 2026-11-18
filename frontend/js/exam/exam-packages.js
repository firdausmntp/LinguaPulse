// Scheduled cohort and package selection before starting the exam timer.
const preparationPackages = { items: [], schedules: [], selected: null, selectedSchedule: null, request: 0 };

function formatScheduleDeadline(iso) {
  if (!iso) return 'Tanpa batas penutupan';
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return iso;
  return dt.toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' });
}

function renderScheduleChoices() {
  const container = document.getElementById('scheduleChoices');
  if (!container) return;
  container.innerHTML = preparationPackages.schedules.map(s => {
    const active = preparationPackages.selectedSchedule?.schedule_id === s.schedule_id;
    const statusLabel = s.window_state === 'upcoming' ? 'Belum dibuka' : s.window_state === 'closed' ? 'Ditutup' : (s.joinable ? 'Dibuka' : 'Belum siap');
    return `<button type="button" class="exam-package-card" data-schedule="${escapeHtml(s.schedule_id)}" aria-pressed="${String(active)}">
      <span class="package-card-top"><strong>${escapeHtml(s.title)}</strong><span>${escapeHtml(s.session_code)}</span></span>
      <span class="package-description">${escapeHtml(s.package_name)} · ${s.duration_minutes} menit · Batas waktu: ${escapeHtml(formatScheduleDeadline(s.closes_at))}</span>
      <span class="package-card-bottom">${s.question_count} soal &amp; tugas <span>${statusLabel}</span></span>
    </button>`;
  }).join('') || '<div class="package-empty"><strong>Belum ada sesi terjadwal</strong><p>Anda tetap dapat memilih paket latihan langsung di bawah bila tersedia.</p></div>';
  container.querySelectorAll('[data-schedule]').forEach(el => el.addEventListener('click', () => selectPreparationSchedule(el.dataset.schedule)));
}

async function selectPreparationSchedule(scheduleId) {
  const sched = preparationPackages.schedules.find(s => s.schedule_id === scheduleId);
  const feedback = document.getElementById('sessionCodeFeedback');
  if (!sched) return;
  preparationPackages.selectedSchedule = sched;
  document.getElementById('sessionCodeInput').value = sched.session_code;
  renderScheduleChoices();
  if (feedback) feedback.textContent = `Sesi ${sched.session_code} (${sched.title}) · Batas waktu: ${formatScheduleDeadline(sched.closes_at)}`;
  await selectPreparationPackage(sched.package_id, sched);
}

function applySessionCode() {
  const input = document.getElementById('sessionCodeInput');
  const feedback = document.getElementById('sessionCodeFeedback');
  const code = (input?.value || '').trim().toUpperCase();
  if (!code) {
    preparationPackages.selectedSchedule = null;
    renderScheduleChoices();
    if (feedback) feedback.textContent = 'Masukkan kode sesi atau pilih jadwal yang tersedia.';
    return;
  }
  const match = preparationPackages.schedules.find(s => s.session_code.toUpperCase() === code);
  if (!match) {
    preparationPackages.selectedSchedule = null;
    renderScheduleChoices();
    if (feedback) feedback.textContent = `Kode "${code}" tidak ditemukan di jadwal aktif. Anda tetap dapat memverifikasi lewat Mulai sesi.`;
    preparationPackages.manualSessionCode = code;
    return;
  }
  preparationPackages.manualSessionCode = null;
  selectPreparationSchedule(match.schedule_id);
}

async function loadPreparationPackages() {
  const error = document.getElementById('prepareError');
  const button = document.getElementById('beginExamButton');
  button.disabled = true;
  document.getElementById('applySessionCodeButton')?.addEventListener('click', applySessionCode);
  try {
    const [pkgData, schedData] = await Promise.all([api('/api/exam/packages'), api('/api/exam/schedules')]);
    if (!document.getElementById('packageChoices')) return;
    preparationPackages.items = pkgData.packages;
    preparationPackages.schedules = schedData.schedules || [];
    renderScheduleChoices();
    document.getElementById('packageChoices').innerHTML = pkgData.packages.map(p => `
      <button type="button" class="exam-package-card" data-package="${escapeHtml(p.package_id)}" aria-pressed="false">
        <span class="package-card-top"><strong>${escapeHtml(p.name)}</strong><span>${p.duration_minutes} menit</span></span>
        <span class="package-description">${escapeHtml(p.description || 'Paket ujian yang disiapkan admin.')}</span>
        <span class="package-card-bottom">${p.question_count} soal &amp; tugas <span>${p.ready ? 'Pilih paket' : 'Belum siap'}</span></span>
      </button>`).join('') || '<div class="package-empty"><strong>Belum ada paket yang tersedia</strong><p>Admin perlu menyiapkan dan memublikasikan paket terlebih dahulu.</p></div>';
    document.querySelectorAll('[data-package]').forEach(el => el.addEventListener('click', () => {
      preparationPackages.selectedSchedule = null;
      preparationPackages.manualSessionCode = null;
      const codeInput = document.getElementById('sessionCodeInput');
      if (codeInput) codeInput.value = '';
      renderScheduleChoices();
      const fb = document.getElementById('sessionCodeFeedback');
      if (fb) fb.textContent = '';
      selectPreparationPackage(el.dataset.package);
    }));
    const first = pkgData.packages.find(p => p.package_id === preparationPackages.selected) || pkgData.packages.find(p => p.ready) || pkgData.packages[0];
    if (first) await selectPreparationPackage(first.package_id);
    else document.getElementById('prepareDuration').textContent = 'Pilih paket yang tersedia untuk memulai.';
  } catch (e) { error.textContent = e.message; error.classList.remove('hidden'); }
}

async function selectPreparationPackage(id, sched = null) {
  const request = ++preparationPackages.request;
  const button = document.getElementById('beginExamButton');
  button.disabled = true;
  document.getElementById('prepareError').classList.add('hidden');
  preparationPackages.selected = id;
  document.querySelectorAll('[data-package]').forEach(el => el.setAttribute('aria-pressed', String(el.dataset.package === id)));
  try {
    const { package: selected, bank } = await api('/api/exam/packages?id=' + encodeURIComponent(id));
    if (request !== preparationPackages.request || !button.isConnected) return;
    appState.questionsBank = bank;
    document.getElementById('preparePackageName').textContent = sched ? `${selected.name} (${sched.session_code})` : selected.name;
    document.getElementById('prepareDuration').textContent = `${selected.duration_minutes} menit, dimulai setelah Anda menekan Mulai`;
    document.getElementById('prepareBankSummary').innerHTML = [['Listening', 'listening'], ['Structure', 'grammar'], ['Reading', 'reading']].map(([name, key]) => `<div><dt>${name}</dt><dd>${selected.counts[key]} soal</dd></div>`).join('');
    document.getElementById('prepareWritingSelect').innerHTML = bank.writing_tasks.map(q => `<option value="${escapeHtml(q.id)}">${escapeHtml(q.title)}</option>`).join('') || '<option value="">Tanpa Writing tambahan</option>';
    document.getElementById('prepareWritingSelect').disabled = !bank.writing_tasks.length;
    if (!selected.ready) throw new Error(selected.problems.join(' ') + ' Hubungi admin untuk menyiapkan paket ini.');
    if (sched && sched.window_state !== 'open') {
      throw new Error(sched.window_state === 'upcoming' ? 'Sesi jadwal ini belum dibuka.' : 'Batas waktu sesi jadwal ini sudah berakhir.');
    }
    button.disabled = false;
  } catch (e) {
    if (request !== preparationPackages.request || !button.isConnected) return;
    document.getElementById('prepareError').textContent = e.message;
    document.getElementById('prepareError').classList.remove('hidden');
  }
}
