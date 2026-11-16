// Admin-only account management; text is always rendered through escaping.
const userManagement = { users: [], editing: null, busy: false };
function initUserManagement() {
  document.getElementById('userSearch').addEventListener('input', renderAdminUsers);
  document.getElementById('userRoleFilter').addEventListener('change', renderAdminUsers);
  document.getElementById('userEditorDialog').addEventListener('cancel', event => { if (userManagement.busy) event.preventDefault(); });
}
async function loadAdminUsersTable() {
  const status = document.getElementById('userListStatus');
  status.textContent = 'Memuat akun…';
  try {
    const data = await api('/api/admin/users');
    if (!status.isConnected) return;
    userManagement.users = data.users || [];
    renderAdminUsers();
  } catch (error) { if (status.isConnected) status.textContent = error.message; }
}
function renderAdminUsers() {
  const search = document.getElementById('userSearch').value.trim().toLowerCase();
  const role = document.getElementById('userRoleFilter').value;
  const users = userManagement.users.filter(user => (!role || user.role === role) && [user.display_name, user.username, user.email, user.participant_code].join(' ').toLowerCase().includes(search));
  const counts = [ ['Total akun', userManagement.users.length], ['Admin', userManagement.users.filter(u => u.role === 'admin').length], ['Peserta', userManagement.users.filter(u => u.role === 'student').length] ];
  document.getElementById('usersSummary').innerHTML = counts.map(([label, number]) => `<div><span>${label}</span><strong>${number}</strong></div>`).join('');
  document.getElementById('userListStatus').textContent = `${users.length} akun ditampilkan`;
  document.getElementById('adminUsersBody').innerHTML = users.map(user => `<tr><td data-label="Pengguna"><div class="user-cell"><span class="user-initials" aria-hidden="true">${escapeHtml(getInitials(user.display_name))}</span><div><strong>${escapeHtml(user.display_name)}</strong><small>${escapeHtml(user.username)}${user.user_id === appState.currentUser.user_id ? ' (Anda)' : ''}</small><small>${escapeHtml(user.participant_code)}</small></div></div></td><td data-label="Kontak">${escapeHtml(user.email)}</td><td data-label="Peran"><span class="user-role-badge">${user.role === 'admin' ? 'Admin' : 'Peserta'}</span></td><td data-label="Dibuat"><time datetime="${escapeHtml(user.created_at.replace(' ', 'T'))}">${escapeHtml(formatDateTime(user.created_at))}</time></td><td data-label="Aksi"><div class="user-row-actions"><button type="button" class="btn-secondary" data-edit-user="${user.user_id}">Edit</button><button type="button" class="btn-secondary user-delete" data-delete-user="${user.user_id}" ${user.user_id === appState.currentUser.user_id ? 'disabled title="Akun yang sedang digunakan"' : ''}>Hapus</button></div></td></tr>`).join('') || '<tr><td colspan="5">Tidak ada akun yang cocok. Ubah pencarian atau tambahkan akun.</td></tr>';
  document.querySelectorAll('[data-edit-user]').forEach(button => button.addEventListener('click', () => openUserEditor(Number(button.dataset.editUser))));
  document.querySelectorAll('[data-delete-user]').forEach(button => button.addEventListener('click', () => deleteAdminUser(Number(button.dataset.deleteUser))));
}
function openUserEditor(id = null) {
  const user = id === null ? null : userManagement.users.find(item => item.user_id === id);
  userManagement.editing = user?.user_id ?? null;
  const form = document.getElementById('userEditorForm'); form.reset();
  document.getElementById('userEditorError').classList.add('hidden');
  document.getElementById('userEditorTitle').textContent = user ? 'Edit akun' : 'Tambah akun';
  for (const [field, value] of Object.entries({ editUserName: user?.display_name || '', editUserUsername: user?.username || '', editUserEmail: user?.email || '', editUserRole: user?.role || 'student' })) document.getElementById(field).value = value;
  document.getElementById('editUserPassword').required = !user;
  document.getElementById('editPasswordHelp').textContent = user ? 'Biarkan kosong untuk mempertahankan kata sandi.' : 'Minimal 8 karakter.';
  document.getElementById('editUserRole').disabled = user?.user_id === appState.currentUser.user_id;
  document.getElementById('editUserRole')._syncCombobox?.();
  document.getElementById('userEditorDialog').showModal();
  document.getElementById('editUserName').focus();
}
function closeUserEditor() { if (!userManagement.busy) document.getElementById('userEditorDialog').close(); }
async function saveAdminUser(event) {
  event.preventDefault();
  if (userManagement.busy) return;
  const error = document.getElementById('userEditorError');
  const button = document.getElementById('saveUserButton');
  const editing = userManagement.editing;
  const payload = { mode: editing === null ? 'create' : 'update', user_id: editing, display_name: document.getElementById('editUserName').value, username: document.getElementById('editUserUsername').value, email: document.getElementById('editUserEmail').value, role: document.getElementById('editUserRole').value, password: document.getElementById('editUserPassword').value };
  error.classList.add('hidden'); userManagement.busy = true; button.disabled = true; button.textContent = 'Menyimpan…';
  try {
    const data = await api('/api/admin/users', { method: 'POST', body: JSON.stringify(payload) });
    document.getElementById('userEditorDialog').close();
    if (data.reauthenticate) { updateProfileUI(null); await navigate('/login'); return; }
    if (data.user.user_id === appState.currentUser.user_id) updateProfileUI(data.user);
    await loadAdminUsersTable();
    document.getElementById('userListStatus').textContent = 'Akun ' + data.user.username + ' tersimpan.';
  } catch (err) { error.textContent = err.message; error.classList.remove('hidden'); }
  finally { userManagement.busy = false; button.disabled = false; button.textContent = 'Simpan akun'; }
}
async function deleteAdminUser(id) {
  const user = userManagement.users.find(item => item.user_id === id);
  if (!user || userManagement.busy || !await adminConfirm('Hapus akun ' + user.username + '?', 'Akses login dan sesi aktif akun ini akan dihapus. Riwayat ujian yang telah dikirim tetap tersimpan.', 'Hapus akun')) return;
  userManagement.busy = true;
  try {
    await api('/api/admin/users?id=' + id, { method: 'DELETE' });
    await loadAdminUsersTable();
    document.getElementById('userListStatus').textContent = 'Akun dihapus.';
  } catch (err) { document.getElementById('userListStatus').textContent = err.message; }
  finally { userManagement.busy = false; }
}

function adminConfirm(title, message, accept = 'Lanjutkan') {
  const dialog = document.getElementById('adminConfirmDialog');
  if (!dialog || dialog.open) return Promise.resolve(false);
  const previousFocus = document.activeElement;
  document.getElementById('adminConfirmTitle').textContent = title;
  document.getElementById('adminConfirmMessage').textContent = message;
  document.getElementById('adminConfirmAccept').textContent = accept;
  dialog.returnValue = 'cancel';
  return new Promise(resolve => {
    dialog.addEventListener('close', () => {
      if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
      resolve(dialog.returnValue === 'confirm');
    }, { once: true });
    dialog.showModal();
  });
}
