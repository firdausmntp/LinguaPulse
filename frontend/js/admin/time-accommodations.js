// Per-participant accommodations for this schedule.
async function showTimeAccommodations(scheduleId) {
  const panel = document.getElementById('scheduleTimeAccommodations');
  if (!panel) return;
  if (!scheduleId) {
    panel.textContent = 'Simpan jadwal sebelum mengatur akomodasi peserta.';
    return;
  }
  panel.innerHTML = `<h3>Akomodasi peserta</h3>
    <p>Pengaturan berlaku untuk sesi baru pada jadwal ini. Jam tutup tetap menjadi batas akhir.</p>
    <form id="timeAccommodationForm">
      <div class="package-settings-row"><div><label for="accommodationUser">Username peserta</label>
      <input id="accommodationUser" required maxlength="64" autocomplete="off"></div>
      <div><label for="accommodationMinutes">Tambahan menit</label>
      <input id="accommodationMinutes" type="number" required min="0" max="240" aria-describedby="accommodationHelp" value="0"></div></div>
      <p id="accommodationHelp">Masukkan 0 untuk menghapus tambahan waktu.</p>
    <label class="checkbox-label"><input id="accommodationTranscript" type="checkbox">
      <span>Izinkan transkrip Listening selama ujian</span></label>
      <div id="accommodationError" class="inline-error hidden" role="alert" tabindex="-1"></div>
      <button type="submit" class="btn-secondary">Simpan akomodasi</button>
    </form><p id="accommodationStatus" role="status"></p><ul id="accommodationList"></ul>`;
  const form = panel.querySelector('form');
  const status = panel.querySelector('#accommodationStatus');
  const summary = panel.querySelector('#accommodationError');
  const list = panel.querySelector('#accommodationList');
  const user = form.querySelector('#accommodationUser');
  const minutes = form.querySelector('#accommodationMinutes');
  const transcript = form.querySelector('#accommodationTranscript');
  let records = new Map();
  const render = data => {
    records = new Map(data.accommodations.map(item => [item.username.toLowerCase(), item]));
    list.replaceChildren(...data.accommodations.map(item => {
      const row = document.createElement('li');
      const grants = [];
      if (item.extra_minutes) grants.push(`${item.extra_minutes} menit tambahan`);
      if (item.listening_transcript) grants.push('transkrip Listening');
      row.textContent = `${item.username} · ${grants.join(' · ')}`;
      return row;
    }));
  };
  const loadParticipant = () => {
    const saved = records.get(user.value.trim().toLowerCase());
    minutes.value = saved?.extra_minutes || 0;
    transcript.checked = !!saved?.listening_transcript;
  };
  user.addEventListener('input', loadParticipant);
  enableFormErrors(form);
  const button = form.querySelector('button');
  button.disabled = true;
  status.textContent = 'Memuat akomodasi…';
  try {
    render(await api('/api/admin/time-accommodations?schedule_id=' + encodeURIComponent(scheduleId)));
    loadParticipant();
    status.textContent = list.childElementCount ? '' : 'Belum ada akomodasi.';
  } catch (error) { showFormError(summary, error.message, false); status.textContent = ''; }
  finally { button.disabled = false; }
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (button.disabled) return;
    if (!user.value.trim()) return setFieldError(user, 'Masukkan username peserta.');
    const extraMinutes = Number(minutes.value);
    summary.classList.add('hidden');
    button.disabled = true;
    try {
      const data = await api('/api/admin/time-accommodations', { method: 'POST', body: JSON.stringify({
        schedule_id: scheduleId, username: user.value, extra_minutes: extraMinutes,
        listening_transcript: transcript.checked
      }) });
      render(data);
      status.textContent = extraMinutes || transcript.checked ? 'Akomodasi tersimpan.' : 'Akomodasi dihapus.';
    } catch (error) { showFormError(summary, error.message); }
    finally {
      button.disabled = false;
      if (form.isConnected && summary.classList.contains('hidden') && document.activeElement === document.body) button.focus();
    }
  });
}
