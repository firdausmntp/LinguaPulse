// Question Bank I/O helper
if (typeof qField === 'undefined') {
  window.qField = id => document.getElementById(id);
}

function updateAudioPreview() {
  const audio = qField('questionAudioPreview');
  const url = qField('qFormAudio').value.trim();
  audio.pause();
  const valid = url.startsWith('/media/') || /^https:\/\//i.test(url);
  audio.classList.toggle('hidden', !valid);
  if (valid) audio.src = url; else audio.removeAttribute('src');
}

async function uploadQuestionAudio(event) {
  const file = event.target.files[0];
  if (!file || questionEditor.busy) return;
  if (file.size > 8 * 1024 * 1024) { event.target.value = ''; return questionMessage('Ukuran audio maksimal 8 MB.', true); }
  setQuestionBusy(true); questionMessage('Mengunggah audio…');
  try {
    const encoded = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(',')[1]); reader.onerror = () => reject(new Error('Berkas audio tidak dapat dibaca.')); reader.readAsDataURL(file); });
    const data = await api('/api/admin/audio', { method: 'POST', body: JSON.stringify({ filename: file.name, data_base64: encoded }) });
    qField('qFormAudio').value = data.audio_url; updateAudioPreview();
    questionMessage('Audio diunggah. Simpan soal untuk menghubungkan audio ini.');
  } catch (error) { questionMessage(error.message, true); }
  finally { setQuestionBusy(false); event.target.value = ''; }
}

async function importQuestionBank(event) {
  const file = event.target.files[0];
  if (!file || questionEditor.busy) return;
  try {
    if (file.size > 2 * 1024 * 1024) throw new Error('Berkas JSON maksimal 2 MB.');
    const parsed = JSON.parse(await file.text());
    const questions = Array.isArray(parsed) ? parsed : parsed.questions;
    if (!Array.isArray(questions) || !questions.length || questions.length > 200) throw new Error('Gunakan JSON berisi 1 hingga 200 soal.');
    if (!await adminConfirm('Impor ' + questions.length + ' soal?', 'Kode soal yang sama akan diperbarui. Semua soal diperiksa sebelum perubahan disimpan.', 'Impor soal')) return;
    setQuestionBusy(true);
    const data = await api('/api/admin/questions/import', { method: 'POST', body: JSON.stringify({ questions }) });
    await loadAdminQuestionsTable(); questionMessage(data.imported + ' soal berhasil diimpor.');
  } catch (error) { questionMessage(error instanceof SyntaxError ? 'JSON tidak valid. Periksa kembali berkas impor.' : error.message, true); }
  finally { event.target.value = ''; setQuestionBusy(false); }
}

async function exportQuestionBank() {
  try {
    const data = await api('/api/admin/questions/export');
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    const a = Object.assign(document.createElement('a'), { href: url, download: 'linguapulse-ept-questions.json' });
    a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) { questionMessage(error.message, true); }
}
