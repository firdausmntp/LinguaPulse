// Personal dashboard and history; no public rankings or reward metrics.
async function initDashboard() {
  const user = appState.currentUser;
  document.getElementById('dashboardGreeting').textContent = 'Selamat datang, ' + user.display_name + '.';
  document.getElementById('participantDetails').innerHTML = `<div><dt>Nama</dt><dd>${escapeHtml(user.display_name)}</dd></div><div><dt>Kode peserta</dt><dd>${escapeHtml(user.participant_code)}</dd></div><div><dt>Email</dt><dd>${escapeHtml(user.email)}</dd></div>`;
  if (readExamDraft()?.exam) {
    const draft = document.getElementById('dashboardDraft');
    draft.classList.remove('hidden');
    draft.innerHTML = `${icon('clock')}<div><strong>Ada draf sesi ujian di perangkat ini.</strong><p>Buka persiapan untuk melanjutkan atau memulai sesi baru.</p></div><a href="/exam" class="btn-secondary">Buka draf</a>`;
  }
  const container = document.getElementById('recentSessions');
  try {
    const data = await api('/api/history');
    if (container.isConnected) container.innerHTML = sessionTable(data.submissions.slice(0, 3));
  } catch (error) { renderError(container, error.message, initDashboard); }
}

function sessionAccuracy(session) {
  const total = (session.listening_mc_total || 0) + session.grammar_mc_total + session.reading_mc_total;
  const correct = (session.listening_mc_correct || 0) + session.grammar_mc_correct + session.reading_mc_correct;
  return total ? Math.round(correct / total * 100) : 0;
}
function sessionTable(sessions) {
  if (!sessions.length) return '<div class="empty-state history-empty"><span class="history-empty-icon">' + icon('book') + '</span><h3>Belum ada sesi yang selesai</h3><p>Setelah sesi ujian dikirim, hasil dan pembahasannya tersimpan di sini.</p><a href="/exam" class="btn-secondary">Siapkan latihan pertama</a></div>';
  const link = session => '/results?id=' + encodeURIComponent(session.session_id);
  const score = (s, key) => `${s[key + '_mc_correct'] || 0} / ${s[key + '_mc_total'] || 0}`;
  return `<div class="history-desktop"><table class="history-table"><caption class="sr-only">Sesi latihan pribadi</caption><thead><tr><th>Sesi</th><th>Listening</th><th>Structure</th><th>Reading</th><th>Ketepatan</th><th>Hasil</th></tr></thead><tbody>${sessions.map(s => `<tr><td><time datetime="${escapeHtml(s.submitted_at.replace(' ', 'T'))}">${escapeHtml(formatDateTime(s.submitted_at))}</time><small>${escapeHtml(s.session_id.slice(0, 16))}</small></td><td>${score(s, 'listening')}</td><td>${score(s, 'grammar')}</td><td>${score(s, 'reading')}</td><td><strong>${sessionAccuracy(s)}%</strong></td><td><a href="${link(s)}" class="btn-secondary">Tinjau hasil ${icon('chevronRight')}</a></td></tr>`).join('')}</tbody></table></div><ol class="history-cards">${sessions.map(s => `<li><div class="history-card-heading"><time datetime="${escapeHtml(s.submitted_at.replace(' ', 'T'))}">${escapeHtml(formatDateTime(s.submitted_at))}</time><strong>${sessionAccuracy(s)}<span>% tepat</span></strong></div><dl><div><dt>Listening</dt><dd>${score(s, 'listening')}</dd></div><div><dt>Structure</dt><dd>${score(s, 'grammar')}</dd></div><div><dt>Reading</dt><dd>${score(s, 'reading')}</dd></div></dl><a href="${link(s)}">Tinjau hasil dan pembahasan ${icon('chevronRight')}</a></li>`).join('')}</ol>`;
}
const historyState = { sessions: [] };
async function loadHistory() {
  const el = document.getElementById('historyContent');
  try {
    const data = await api('/api/history');
    if (!el.isConnected) return;
    historyState.sessions = data.submissions;
    document.getElementById('historySummary').textContent = data.submissions.length + ' sesi tersimpan dalam akun Anda.';
    document.getElementById('historySearch').addEventListener('input', renderHistory);
    document.getElementById('historyFilter').addEventListener('change', renderHistory);
    initAdminComboboxes();
    renderHistory();
  } catch (error) { renderError(el, error.message, loadHistory); }
}
function renderHistory() {
  const search = document.getElementById('historySearch').value.trim().toLowerCase();
  const filter = document.getElementById('historyFilter').value;
  const sessions = historyState.sessions.filter(s => (!filter || sessionAccuracy(s) < 100) && (s.session_id + ' ' + s.submitted_at + ' ' + formatDateTime(s.submitted_at)).toLowerCase().includes(search));
  document.getElementById('historyCount').textContent = sessions.length + ' sesi ditampilkan';
  document.getElementById('historyContent').innerHTML = historyState.sessions.length && !sessions.length ? '<div class="empty-state"><h2>Tidak ada sesi yang cocok</h2><p>Coba tanggal atau kode lain, atau tampilkan semua sesi.</p><button type="button" class="btn-secondary" onclick="resetHistoryFilters()">Reset pencarian</button></div>' : sessionTable(sessions);
}
function resetHistoryFilters() {
  document.getElementById('historySearch').value = '';
  document.getElementById('historyFilter').value = '';
  document.getElementById('historyFilter')._syncCombobox?.(); renderHistory();
}
