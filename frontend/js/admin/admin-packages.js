// Each package owns its selection and duration; running attempts keep snapshots.
const packageEditor = { items: [], questions: [], selected: new Set(), current: null, dirty: false, saving: false };
const packageModuleNames = { listening: 'Listening', grammar: 'Structure', reading: 'Reading', writing: 'Esai riset' };

async function confirmAdminTransition() {
  if (packageEditor.saving) { showToast('Tunggu sampai paket selesai disimpan.'); return false; }
  if (typeof confirmScheduleTransition === 'function' && !await confirmScheduleTransition()) return false;
  if (typeof confirmQuestionTransition === 'function' && !await confirmQuestionTransition()) return false;
  if (packageEditor.dirty && !confirm('Perubahan paket belum disimpan. Tinggalkan editor?')) return false;
  packageEditor.dirty = false;
  return true;
}

async function loadAdminPackages() {
  const root = document.getElementById('adminTabPackages');
  root.innerHTML = '<p role="status">Memuat paket ujian…</p>';
  try {
    const [data, bank] = await Promise.all([api('/api/admin/packages'), api('/api/questions')]);
    if (!root.isConnected) return;
    packageEditor.items = data.packages;
    packageEditor.questions = bank.all_questions || [];
    packageEditor.dirty = false;
    root.innerHTML = `<div class="package-manager-heading"><div><h2>Paket ujian</h2><p>Tentukan materi, durasi, dan paket yang dapat dipilih peserta.</p></div><button class="btn-primary" id="newPackageButton" type="button">Buat paket</button></div>
      <div class="package-manager-layout"><div id="adminPackageList" class="admin-package-list"></div><section id="packageEditorPanel" class="package-editor-panel"><div class="package-empty"><h3>Susun sesi sesuai kebutuhan</h3><p>Pilih paket untuk mengubahnya, atau buat paket baru dari bank soal.</p></div></section></div>`;
    document.getElementById('newPackageButton').addEventListener('click', () => editExamPackage(null));
    renderAdminPackageList();
  } catch (e) { renderError(root, e.message, loadAdminPackages); }
}

function renderAdminPackageList() {
  const root = document.getElementById('adminPackageList');
  root.innerHTML = packageEditor.items.map(p => `<button class="admin-package-card${packageEditor.current?.package_id === p.package_id ? ' is-selected' : ''}" type="button" data-edit-package="${escapeHtml(p.package_id)}">
    <span class="package-card-top"><strong>${escapeHtml(p.name)}</strong><span class="package-status">${p.is_active ? 'Dipublikasikan' : 'Draf'}</span></span>
    <span>${p.duration_minutes} menit · ${p.question_count} soal &amp; tugas</span><small>${p.ready ? 'Materi siap' : 'Materi perlu dilengkapi'}</small></button>`).join('') || '<p>Belum ada paket. Buat paket pertama Anda.</p>';
  root.querySelectorAll('[data-edit-package]').forEach(el => el.addEventListener('click', () => editExamPackage(el.dataset.editPackage)));
}

async function editExamPackage(id) {
  if (!await confirmAdminTransition()) return;
  const p = packageEditor.items.find(item => item.package_id === id) || { name: '', description: '', duration_minutes: 25, is_active: false, question_ids: [] };
  packageEditor.current = p;
  packageEditor.selected = new Set(p.question_ids);
  const panel = document.getElementById('packageEditorPanel');
  panel.innerHTML = `<form id="packageForm"><fieldset id="packageFields"><legend class="sr-only">Pengaturan paket ujian</legend><div class="package-editor-heading"><h3>${id ? 'Edit paket' : 'Paket baru'}</h3><span id="packageDirtyStatus" role="status">${id ? 'Tersimpan' : 'Belum disimpan'}</span></div>
    <label for="packageName">Nama paket</label><input id="packageName" type="text" maxlength="100" required value="${escapeHtml(p.name)}" placeholder="Misalnya Simulasi TOEFL EPT">
    <label for="packageDescription">Deskripsi</label><textarea id="packageDescription" maxlength="2000" rows="2" placeholder="Jelaskan tujuan atau materi paket ini.">${escapeHtml(p.description)}</textarea>
    <div class="package-settings-row"><div><label for="packageDuration">Durasi (menit)</label><input id="packageDuration" type="number" min="1" max="240" required value="${p.duration_minutes}"></div><label class="checkbox-label package-publish"><input id="packagePublished" type="checkbox" ${p.is_active ? 'checked' : ''}><span>Publikasikan untuk peserta</span></label></div>
    <div class="package-picker-heading"><div><h4>Pilih soal dari bank</h4><p id="packageSelectionCount" role="status"></p></div><button type="button" class="btn-secondary" id="packageSelectVisible">Pilih hasil pencarian</button></div>
    <div class="package-question-filters"><label><span>Cari soal</span><input id="packageQuestionSearch" type="search" placeholder="Judul, pertanyaan, atau kode soal"></label><label><span>Modul</span><select id="packageQuestionModule"><option value="">Semua modul</option>${Object.entries(packageModuleNames).map(([key,name]) => `<option value="${key}">${name}</option>`).join('')}</select></label></div>
    <div id="packageQuestionList" class="package-question-picker"></div>
    <p class="package-editor-note">Untuk dipublikasikan, paket memerlukan soal aktif Listening dengan audio, Structure, dan Reading dengan bacaan. Jika tersedia beberapa tugas Writing, peserta memilih satu sebelum mulai. Perubahan hanya berlaku untuk sesi baru.</p>
    <div id="packageError" class="inline-error hidden" role="alert"></div><div class="package-editor-actions"><button class="btn-primary" type="submit" id="savePackageButton">Simpan paket</button><span id="packageSaveStatus" role="status"></span></div></fieldset></form>`;
  enableFormErrors(document.getElementById('packageForm'));
  document.getElementById('packageForm').addEventListener('input', markPackageDirty);
  document.getElementById('packageForm').addEventListener('change', markPackageDirty);
  document.getElementById('packageForm').addEventListener('submit', saveExamPackage);
  document.getElementById('packageQuestionSearch').addEventListener('input', renderPackageQuestions);
  document.getElementById('packageQuestionModule').addEventListener('change', renderPackageQuestions);
  document.getElementById('packageSelectVisible').addEventListener('click', () => {
    filteredPackageQuestions().filter(q => q.is_active).forEach(q => packageEditor.selected.add(q.id));
    markPackageDirty(); renderPackageQuestions();
  });
  renderPackageQuestions(); renderAdminPackageList();
  document.getElementById('packageName').focus({ preventScroll: true });
}

function markPackageDirty(event) {
  if (['packageQuestionSearch', 'packageQuestionModule'].includes(event?.target.id)) return;
  packageEditor.dirty = true;
  const status = document.getElementById('packageDirtyStatus');
  if (status) status.textContent = 'Perubahan belum disimpan';
}

function filteredPackageQuestions() {
  const query = document.getElementById('packageQuestionSearch').value.trim().toLowerCase();
  const module = document.getElementById('packageQuestionModule').value;
  return packageEditor.questions.filter(q => (!module || q.section === module) && (!query || [q.id, q.title, q.prompt].join(' ').toLowerCase().includes(query)));
}

function renderPackageQuestions() {
  const root = document.getElementById('packageQuestionList');
  root.innerHTML = filteredPackageQuestions().map(q => `<label class="package-question-row"><input type="checkbox" data-package-question="${escapeHtml(q.id)}" ${packageEditor.selected.has(q.id) ? 'checked' : ''}><span><span class="package-question-label">${escapeHtml(packageModuleNames[q.section] || q.section)} · ${escapeHtml(q.id)}${q.is_active ? '' : ' · Nonaktif'}</span><strong>${escapeHtml(q.prompt)}</strong><small>${escapeHtml(q.title || '')}</small></span></label>`).join('') || '<p>Tidak ada soal yang cocok. Tambahkan soal melalui menu Bank soal.</p>';
  root.querySelectorAll('[data-package-question]').forEach(input => input.addEventListener('change', () => {
    input.checked ? packageEditor.selected.add(input.dataset.packageQuestion) : packageEditor.selected.delete(input.dataset.packageQuestion);
    updatePackageSelection();
  }));
  updatePackageSelection();
}

function updatePackageSelection() {
  const selected = packageEditor.questions.filter(q => packageEditor.selected.has(q.id));
  document.getElementById('packageSelectionCount').textContent = `${selected.length} dipilih · ` + Object.entries(packageModuleNames).map(([key, name]) => `${name} ${selected.filter(q => q.section === key).length}`).join(' · ');
}

async function saveExamPackage(event) {
  event.preventDefault();
  if (packageEditor.saving) return;
  const button = document.getElementById('savePackageButton');
  const fields = document.getElementById('packageFields');
  const error = document.getElementById('packageError');
  packageEditor.saving = true; fields.disabled = true;
  button.disabled = true; error.classList.add('hidden');
  try {
    const old = packageEditor.current;
    const payload = { name: document.getElementById('packageName').value, description: document.getElementById('packageDescription').value,
      duration_minutes: Number(document.getElementById('packageDuration').value), is_active: document.getElementById('packagePublished').checked,
      question_ids: [...packageEditor.selected] };
    if (old?.package_id) Object.assign(payload, { package_id: old.package_id, version: old.version });
    const data = await api('/api/admin/packages', { method: 'POST', body: JSON.stringify(payload) });
    const index = packageEditor.items.findIndex(p => p.package_id === data.package.package_id);
    if (index >= 0) packageEditor.items[index] = data.package; else packageEditor.items.push(data.package);
    packageEditor.current = data.package; packageEditor.dirty = false;
    document.getElementById('packageDirtyStatus').textContent = 'Tersimpan';
    document.getElementById('packageSaveStatus').textContent = data.package.is_active ? 'Paket tersedia untuk peserta.' : 'Draf tersimpan, belum ditampilkan kepada peserta.';
    renderAdminPackageList(); showToast('Paket berhasil disimpan.');
  } catch (e) { showFormError(error, e.message); }
  finally { packageEditor.saving = false; fields.disabled = false; button.disabled = false; }
}
