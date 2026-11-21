// Admin CRUD for scheduled exam sessions, class codes, and open-close deadlines.
const scheduleEditor = { items: [], packages: [], current: null, dirty: false, saving: false };
const scheduleCondNames = { MANDIRI: 'Mandiri', COPY_TYPING: 'Simulasi menyalin teks', AI_PARAPHRASE: 'Simulasi parafrase AI' };
const scheduleStateNames = { open: 'Dibuka', upcoming: 'Belum dibuka', closed: 'Ditutup', inactive: 'Nonaktif' };

function toLocalDatetimeInput(iso) {
  if (!iso) return '';
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return iso.slice(0, 16);
  const pad = n => String(n).padStart(2, '0');
  return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}T${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
}

async function confirmScheduleTransition() {
  if (scheduleEditor.saving) { showToast('Tunggu sampai sesi jadwal selesai disimpan.'); return false; }
  if (scheduleEditor.dirty && !confirm('Perubahan sesi jadwal belum disimpan. Tinggalkan editor?')) return false;
  scheduleEditor.dirty = false;
  return true;
}

async function loadAdminSchedules() {
  const root = document.getElementById('adminTabSchedules');
  if (!root) return;
  root.innerHTML = '<p role="status">Memuat sesi jadwal ujian…</p>';
  try {
    const [schedData, pkgData] = await Promise.all([api('/api/admin/schedules'), api('/api/admin/packages')]);
    if (!root.isConnected) return;
    scheduleEditor.items = schedData.schedules || [];
    scheduleEditor.packages = pkgData.packages || [];
    scheduleEditor.dirty = false;
    root.innerHTML = `<div class="package-manager-heading"><div><h2>Sesi jadwal &amp; kode kelas</h2><p>Atur gelombang, kode kelas, jadwal buka-tutup, dan batas waktu pengerjaan agar platform dapat dipakai berkelanjutan.</p></div><button class="btn-primary" id="newScheduleButton" type="button">Buat sesi jadwal</button></div>
      <div class="package-manager-layout"><div id="adminScheduleList" class="admin-package-list"></div><section id="scheduleEditorPanel" class="package-editor-panel"><div class="package-empty"><h3>Kelola gelombang &amp; kelas</h3><p>Pilih sesi jadwal untuk mengubah tenggatnya, atau buat sesi jadwal baru.</p></div></section></div>`;
    document.getElementById('newScheduleButton').addEventListener('click', () => editExamSchedule(null));
    renderAdminScheduleList();
  } catch (e) { renderError(root, e.message, loadAdminSchedules); }
}

function renderAdminScheduleList() {
  const root = document.getElementById('adminScheduleList');
  if (!root) return;
  root.innerHTML = scheduleEditor.items.map(s => `<button class="admin-package-card${scheduleEditor.current?.schedule_id === s.schedule_id ? ' is-selected' : ''}" type="button" data-edit-schedule="${escapeHtml(s.schedule_id)}">
    <span class="package-card-top"><strong>${escapeHtml(s.title)}</strong><span class="package-status">${escapeHtml(scheduleStateNames[s.window_state] || s.window_state)}</span></span>
    <span>Kode: <strong>${escapeHtml(s.session_code)}</strong> · ${escapeHtml(s.package_name)}</span>
    <small>${escapeHtml(scheduleCondNames[s.task_condition] || s.task_condition)} · ${s.closes_at ? 'Tutup: ' + escapeHtml(formatScheduleDeadline(s.closes_at)) : 'Tanpa batas tutup'}</small></button>`).join('') || '<p>Belum ada sesi jadwal. Buat sesi jadwal pertama Anda.</p>';
  root.querySelectorAll('[data-edit-schedule]').forEach(el => el.addEventListener('click', () => editExamSchedule(el.dataset.editSchedule)));
}

async function editExamSchedule(id) {
  if (!await confirmScheduleTransition()) return;
  const fallbackPkg = scheduleEditor.packages[0]?.package_id || '';
  const s = scheduleEditor.items.find(item => item.schedule_id === id) || {
    title: '', session_code: '', description: '', package_id: fallbackPkg,
    task_condition: 'MANDIRI', opens_at: '', closes_at: '', is_active: true
  };
  scheduleEditor.current = s;
  const panel = document.getElementById('scheduleEditorPanel');
  const pkgOptions = scheduleEditor.packages.map(p => `<option value="${escapeHtml(p.package_id)}" ${p.package_id === s.package_id ? 'selected' : ''}>${escapeHtml(p.name)} (${p.duration_minutes} menit)</option>`).join('');
  panel.innerHTML = `<form id="scheduleForm"><fieldset id="scheduleFields"><legend class="sr-only">Pengaturan sesi jadwal</legend><div class="package-editor-heading"><h3>${id ? 'Edit sesi jadwal' : 'Sesi jadwal baru'}</h3><span id="scheduleDirtyStatus" role="status">${id ? 'Tersimpan' : 'Belum disimpan'}</span></div>
    <label for="scheduleTitle">Judul gelombang / sesi</label><input id="scheduleTitle" type="text" maxlength="120" required value="${escapeHtml(s.title)}" placeholder="Misalnya EPT Gelombang 1 Kelas A">
    <div class="package-settings-row"><div><label for="scheduleCode">Kode sesi / kelas</label><input id="scheduleCode" type="text" maxlength="32" required pattern="[A-Za-z0-9_\\-]{3,32}" data-error-pattern="Gunakan 3 sampai 32 huruf, angka, tanda hubung, atau garis bawah." value="${escapeHtml(s.session_code)}" placeholder="EPT-2026-A"></div>
    <div><label for="schedulePackage">Paket ujian</label><select id="schedulePackage" required>${pkgOptions}</select></div></div>
    <div class="package-settings-row schedule-time-fields"><div><label for="scheduleOpensAt">Jadwal buka (opsional)</label><input id="scheduleOpensAt" type="datetime-local" value="${escapeHtml(toLocalDatetimeInput(s.opens_at))}"></div>
    <div><label for="scheduleClosesAt">Batas waktu / deadline (opsional)</label><input id="scheduleClosesAt" type="datetime-local" value="${escapeHtml(toLocalDatetimeInput(s.closes_at))}"></div></div>
    <label for="scheduleCondition">Penugasan kondisi riset (tidak tampil ke peserta)</label><select id="scheduleCondition"><option value="MANDIRI" ${s.task_condition === 'MANDIRI' ? 'selected' : ''}>Mandiri</option><option value="COPY_TYPING" ${s.task_condition === 'COPY_TYPING' ? 'selected' : ''}>Simulasi menyalin teks</option><option value="AI_PARAPHRASE" ${s.task_condition === 'AI_PARAPHRASE' ? 'selected' : ''}>Simulasi parafrase AI</option></select>
    <label for="scheduleDescription">Catatan / instruksi gelombang</label><textarea id="scheduleDescription" maxlength="2000" rows="2" placeholder="Keterangan gelombang atau kelompok peserta.">${escapeHtml(s.description || '')}</textarea>
    <label class="checkbox-label package-publish"><input id="scheduleActive" type="checkbox" ${s.is_active ? 'checked' : ''}><span>Aktifkan sesi jadwal untuk peserta</span></label>
    <div id="scheduleError" class="inline-error hidden" role="alert"></div>
    <div class="package-editor-actions"><button class="btn-primary" type="submit" id="saveScheduleButton">Simpan sesi jadwal</button>${id ? '<button class="btn-secondary btn-danger" type="button" id="deleteScheduleButton">Hapus sesi</button>' : ''}<span id="scheduleSaveStatus" role="status"></span></div></fieldset></form><section id="scheduleTimeAccommodations" class="schedule-time-accommodations" aria-label="Akomodasi peserta"></section>`;
  enableFormErrors(document.getElementById('scheduleForm'), form => {
    const opens = form.querySelector('#scheduleOpensAt').value;
    const closes = form.querySelector('#scheduleClosesAt').value;
    return { scheduleClosesAt: opens && closes && closes <= opens ? 'Pilih waktu tutup sesudah waktu buka.' : '' };
  });
  document.getElementById('scheduleForm').addEventListener('input', () => {
    scheduleEditor.dirty = true;
    const st = document.getElementById('scheduleDirtyStatus');
    if (st) st.textContent = 'Perubahan belum disimpan';
  });
  document.getElementById('scheduleForm').addEventListener('submit', saveExamSchedule);
  document.getElementById('deleteScheduleButton')?.addEventListener('click', () => removeExamSchedule(s.schedule_id));
  showTimeAccommodations(id);
  renderAdminScheduleList();
  document.getElementById('scheduleTitle').focus({ preventScroll: true });
}

async function saveExamSchedule(event) {
  event.preventDefault();
  if (scheduleEditor.saving) return;
  const button = document.getElementById('saveScheduleButton');
  const fields = document.getElementById('scheduleFields');
  const error = document.getElementById('scheduleError');
  scheduleEditor.saving = true; fields.disabled = true; button.disabled = true; error.classList.add('hidden');
  try {
    const old = scheduleEditor.current;
    const payload = {
      title: document.getElementById('scheduleTitle').value,
      session_code: document.getElementById('scheduleCode').value,
      package_id: document.getElementById('schedulePackage').value,
      task_condition: document.getElementById('scheduleCondition').value,
      opens_at: document.getElementById('scheduleOpensAt').value || null,
      closes_at: document.getElementById('scheduleClosesAt').value || null,
      description: document.getElementById('scheduleDescription').value,
      is_active: document.getElementById('scheduleActive').checked,
    };
    if (old?.schedule_id) Object.assign(payload, { schedule_id: old.schedule_id, version: old.version });
    const data = await api('/api/admin/schedules', { method: 'POST', body: JSON.stringify(payload) });
    const idx = scheduleEditor.items.findIndex(item => item.schedule_id === data.schedule.schedule_id);
    if (idx >= 0) scheduleEditor.items[idx] = data.schedule; else scheduleEditor.items.unshift(data.schedule);
    scheduleEditor.current = data.schedule; scheduleEditor.dirty = false;
    document.getElementById('scheduleDirtyStatus').textContent = 'Tersimpan';
    document.getElementById('scheduleSaveStatus').textContent = data.schedule.is_active ? 'Sesi jadwal aktif tersimpan.' : 'Sesi jadwal disimpan sebagai nonaktif.';
    if (!old?.schedule_id) showTimeAccommodations(data.schedule.schedule_id);
    renderAdminScheduleList(); showToast('Sesi jadwal berhasil disimpan.');
  } catch (e) { showFormError(error, e.message); }
  finally { scheduleEditor.saving = false; fields.disabled = false; button.disabled = false; }
}

async function removeExamSchedule(scheduleId) {
  if (!scheduleId || !await adminConfirm('Hapus sesi jadwal?', 'Riwayat telemetri sesi yang sudah terkirim tetap tersimpan.', 'Hapus sesi', true)) return;
  try {
    await api('/api/admin/schedules?id=' + encodeURIComponent(scheduleId), { method: 'DELETE' });
    scheduleEditor.items = scheduleEditor.items.filter(item => item.schedule_id !== scheduleId);
    scheduleEditor.current = null; scheduleEditor.dirty = false;
    document.getElementById('scheduleEditorPanel').innerHTML = '<div class="package-empty"><h3>Sesi jadwal dihapus</h3><p>Pilih sesi lain atau buat sesi jadwal baru.</p></div>';
    renderAdminScheduleList(); showToast('Sesi jadwal dihapus.');
  } catch (e) { showToast(e.message); }
}
