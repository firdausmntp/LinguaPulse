const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const stripChoicePrefix = (v) => String(v ?? '').replace(/^\s*[A-F][.)]\s+/i, '');

const protoModules = [
  {
    key: 'listening', iconName: 'headphones', name: 'Listening',
    title: 'Dengarkan konteksnya. Tangkap maksudnya.',
    desc: 'Putar rekaman percakapan atau pengumuman akademik langsung di ruang ujian, lalu jawab soal pilihan ganda yang terhubung.',
    bullets: ['Pemutar audio langsung di atas soal', 'Dukungan transkrip pada latihan & akomodasi', 'Navigasi soal menjaga progres tetap tersimpan']
  },
  {
    key: 'structure', iconName: 'layers', name: 'Structure',
    title: 'Pahami pola. Susun kalimat yang tepat.',
    desc: 'Kenali hubungan subjek, predikat, klausa, dan perbaikan struktur melalui soal pilihan ganda dan pembahasan grammar.',
    bullets: ['Pilihan jawaban A–D mudah ditinjau ulang', 'Penanda flag untuk soal yang perlu dicek lagi', 'Pembahasan tata bahasa tersedia setelah sesi']
  },
  {
    key: 'reading', iconName: 'book', name: 'Reading',
    title: 'Baca lebih teliti. Temukan gagasan utamanya.',
    desc: 'Latih pemahaman teks akademik, informasi rinci, dan makna kosakata dengan wacana berdampingan di layar lebar.',
    bullets: ['Bacaan dan pertanyaan berdampingan di desktop', 'Panel bacaan dapat dilipat di layar sempit', 'Jawaban tersimpan otomatis di perangkat']
  }
];

const fallbackSample = {
  id: 'PROTO-SAMPLE-1',
  prompt: 'Rarely _____ located near city lights or at lower elevations because light pollution interferes with astronomical observations.',
  options: ['observatories are', 'are', 'in the observatories', 'are observatories'],
  answer: 3,
  explanation: 'Setelah ungkapan negatif "Rarely" di awal kalimat, susunan kalimat mengalami inversi kata kerja bantu sebelum subjek ("are observatories").'
};

function renderPrecisionVariant() {
  return `<div class="v-precision">
    <header class="v1-header"><div class="v1-header-in">
      <a class="v1-brand" href="/"><img src="/assets/logo/linguapulse-master-app-icon.svg" width="32" height="32" alt="">LinguaPulse</a>
      <nav class="v1-nav" aria-label="Navigasi"><a href="#v1-modules">Materi</a><a href="#v1-sample">Coba Soal</a><a href="/practice">Latihan Bebas</a></nav>
      <div class="v1-actions"><a href="/login" class="btn-subtle btn-compact">Masuk</a><a href="/register" class="btn-primary btn-compact">Daftar</a></div>
    </div></header>
    <section class="v1-hero"><div class="v1-hero-grid">
      <div>
        <div class="v1-index v1-beat-1">SIMULASI TOEFL EPT · INSTRUMEN RISET</div>
        <h1 class="v1-beat-1">Lebih paham.<br>Lebih siap EPT.</h1>
        <p class="v1-beat-2">Latihan Listening, Structure, dan Reading dalam satu ruang ujian terstruktur—dari satu soal cepat hingga simulasi paket berdurasi.</p>
        <div class="v1-cta-row v1-beat-3">
          <a href="/register" class="btn-primary">Mulai persiapan EPT ${icon('chevronRight')}</a>
          <a href="#v1-sample" class="v1-cta-ghost">Coba satu soal</a>
        </div>
        <dl class="v1-specs v1-beat-3">
          <div><dt>MODUL EPT</dt><dd>Listening · Structure · Reading</dd></div>
          <div><dt>TUGAS RISET</dt><dd>Esai Writing terpisah</dd></div>
          <div><dt>PRIVASI SENSOR</dt><dd>Aktif hanya saat ujian</dd></div>
        </dl>
      </div>
      <figure class="v1-frame v1-beat-4">
        <div class="v1-frame-bar"><span>Ruang Ujian · Listening</span><span>1 soal / tampilan</span></div>
        <img src="/assets/previews/ept-workspace.png?v=2" alt="Antarmuka ruang ujian Listening LinguaPulse" width="758" height="494">
      </figure>
    </div></section>
    <section id="v1-modules" class="v1-band">
      <div class="v1-band-head"><span class="v1-kicker">01 / MATERI</span><h2>Tiga bagian utama EPT, tanpa gangguan.</h2></div>
      <div class="v1-tabs" role="tablist">${protoModules.map((m, i) => `<button type="button" class="v1-tab" role="tab" data-mod-tab="${i}" aria-selected="${i === 0}">${icon(m.iconName)}<span>${m.name}</span></button>`).join('')}</div>
      <div id="protoModPanel"></div>
    </section>
    <section id="v1-sample" class="v1-band">
      <div class="v1-band-head"><span class="v1-kicker">02 / COBA LANGSUNG</span><h2>Uji satu soal Structure tanpa masuk akun.</h2></div>
      <div class="v1-sample-grid">
        <div><p style="margin-bottom:16px">Pilih salah satu jawaban untuk melihat umpan balik instan beserta pembahasan tata bahasanya.</p><p class="disclaimer">Diambil dari bank soal aktif. Writing dicatat terpisah sebagai instrumen penelitian, bukan nilai EPT.</p></div>
        <div class="v1-sample-card" id="protoSampleBox"></div>
      </div>
    </section>
    <section class="v1-band" style="border-bottom:0">
      <div class="v1-band-head"><span class="v1-kicker">03 / ALUR KERJA</span><h2>Dari persiapan sampai pembahasan.</h2></div>
      <div class="v1-steps">
        <div><span>TAHAP 01</span><h3>Siapkan sesi</h3><p>Pilih paket ujian atau masukkan kode jadwal, periksa audio, dan konfirmasi persetujuan riset.</p></div>
        <div><span>TAHAP 02</span><h3>Kerjakan fokus</h3><p>Navigasi nomor soal, tandai soal ragu-ragu, dan simpan draf otomatis di perangkat.</p></div>
        <div><span>TAHAP 03</span><h3>Tinjau rincian</h3><p>Lihat ketepatan per modul Listening, Structure, Reading serta pembahasan setiap butir soal.</p></div>
      </div>
    </section>
  </div>`;
}

function renderTactileVariant() {
  return `<div class="v-tactile">
    <header class="v2-header"><div class="v2-header-pill">
      <a class="v2-brand" href="/"><img src="/assets/logo/linguapulse-master-app-icon.svg" width="28" height="28" alt="">LinguaPulse</a>
      <nav class="v2-nav" aria-label="Navigasi"><a href="#v2-modules">Materi</a><a href="#v2-sample">Coba Soal</a><a href="/practice">Latihan Bebas</a><a href="/privacy">Privasi</a></nav>
      <div class="v2-actions"><a href="/login" class="btn-subtle btn-compact">Masuk</a><a href="/register" class="btn-primary btn-compact">Daftar</a></div>
    </div></header>
    <section class="v2-hero">
      <div class="v2-chip v2-beat-1">${icon('shield')}<span>Latihan TOEFL EPT &amp; Pengamatan Integritas Riset</span></div>
      <h1 class="v2-beat-2">Belajar dengan fokus.<br>Siap menghadapi EPT.</h1>
      <p class="v2-beat-3">Simulasi Listening, Structure, dan Reading dalam antarmuka yang tenang, responsif di ponsel maupun desktop, tanpa iklan atau gamifikasi semu.</p>
      <div class="v2-cta-group v2-beat-3">
        <a href="/register" class="btn-primary">Mulai persiapan EPT ${icon('chevronRight')}</a>
        <a href="#v2-sample" class="btn-secondary">Coba satu soal</a>
      </div>
      <div class="v2-showcase v2-beat-4">
        <div class="v2-showcase-bar"><strong>Pratinjau Ruang Ujian Aktif</strong><span>Listening · Navigator kanan · Draf tersimpan lokal</span></div>
        <div class="v2-showcase-crop"><img src="/assets/previews/ept-workspace.png?v=2" alt="Tampilan ruang ujian Listening LinguaPulse" width="758" height="494"></div>
      </div>
    </section>
    <section id="v2-modules" class="v2-section">
      <div class="v2-section-head">
        <div><h2>Tiga keterampilan inti EPT.</h2><p>Ganti modul untuk melihat ringkasan ruang pengerjaannya.</p></div>
        <div class="v2-segment" role="tablist">${protoModules.map((m, i) => `<button type="button" class="v2-seg-btn" role="tab" data-mod-tab="${i}" aria-selected="${i === 0}">${m.name}</button>`).join('')}</div>
      </div>
      <div class="v2-surface" id="protoModPanel"></div>
    </section>
    <section id="v2-sample" class="v2-section">
      <div class="v2-bento">
        <div class="v2-surface" id="protoSampleBox"></div>
        <div class="v2-trust-stack">
          <div class="v2-trust-item"><h3>${icon('clock')}Latihan Bebas &amp; Sesi Jadwal</h3><p>Pilih latihan santai tanpa timer di /practice, atau masuk sesi terjadwal dengan kode kelas pengawas.</p></div>
          <div class="v2-trust-item"><h3>${icon('shield')}Batas Privasi Jelas</h3><p>Sensor telemetri hanya aktif saat /exam/session. Karakter ketikan mentah dan isi clipboard tidak direkam.</p></div>
          <div class="v2-trust-item"><h3>${icon('fileText')}Bukan Skor TOEFL Resmi</h3><p>Hasil menampilkan ketepatan pilihan ganda EPT; tugas Writing disimpan terpisah untuk keperluan riset.</p></div>
        </div>
      </div>
    </section>
  </div>`;
}

function renderSpecimenVariant() {
  return `<div class="v-specimen">
    <header class="v3-header"><div class="v3-header-in">
      <a class="v3-brand" href="/"><img src="/assets/logo/linguapulse-master-app-icon.svg" width="30" height="30" alt="">LinguaPulse</a>
      <nav class="v3-nav" aria-label="Navigasi"><a href="#v3-modules">Modul EPT</a><a href="/practice">Latihan Bebas</a><a href="/privacy">Privasi &amp; Riset</a></nav>
      <div class="v3-actions"><a href="/login" class="btn-subtle btn-compact">Masuk</a><a href="/register" class="btn-primary btn-compact">Buat Akun</a></div>
    </div></header>
    <section class="v3-fold">
      <div class="v3-left v3-beat-1">
        <div>
          <div class="v3-tag">LINGUAPULSE · SIMULASI TOEFL EPT</div>
          <h1>Satu soal dulu.<br>Lalu satu sesi utuh.</h1>
          <p>Platform latihan Listening, Structure, dan Reading dengan snapshot bank soal per sesi, pembahasan instan, dan telemetri perilaku hanya saat ujian berlangsung.</p>
          <div class="v3-cta-row">
            <a href="/register" class="btn-primary">Mulai persiapan EPT ${icon('chevronRight')}</a>
            <a href="/practice" class="btn-secondary">Buka latihan bebas</a>
          </div>
        </div>
        <div class="v3-facts">
          <div><strong>3 Modul</strong><span>Listening, Structure, Reading</span></div>
          <div><strong>24 Fitur</strong><span>Telemetri non-keylog saat ujian</span></div>
          <div><strong>1–240m</strong><span>Durasi paket &amp; jadwal fleksibel</span></div>
        </div>
      </div>
      <div class="v3-right v3-beat-2">
        <div class="v3-specimen-box" id="protoSampleBox"></div>
      </div>
    </section>
    <section id="v3-modules" class="v3-band">
      <div class="v3-workspace-row">
        <div>
          <h2 style="font-size:28px; margin-bottom:16px">Dirancang untuk ketenangan mengerjakan ujian.</h2>
          <div class="v3-module-list" role="tablist">
            ${protoModules.map((m, i) => `<button type="button" class="v3-mod-btn" role="tab" data-mod-tab="${i}" aria-selected="${i === 0}">${icon(m.iconName)}<div><strong>${m.name}</strong><small>${m.title}</small></div>${icon('chevronRight')}</button>`).join('')}
          </div>
          <div id="protoModPanel"></div>
        </div>
        <figure class="v3-preview">
          <img src="/assets/previews/ept-workspace.png?v=2" alt="Workspace Listening LinguaPulse" width="758" height="494">
        </figure>
      </div>
    </section>
  </div>`;
}

const variants = [renderPrecisionVariant, renderTactileVariant, renderSpecimenVariant];

function hydrateLandingVariant(variantIndex) {
  const renderMod = (idx) => {
    const m = protoModules[idx];
    const panel = document.getElementById('protoModPanel');
    if (!panel) return;
    if (variantIndex === 0) {
      panel.innerHTML = `<div class="v1-panel"><div><h3>${m.title}</h3><p>${m.desc}</p></div><ul>${m.bullets.map(b => `<li>${icon('check')}<span>${b}</span></li>`).join('')}</ul></div>`;
    } else if (variantIndex === 1) {
      panel.innerHTML = `<div class="v2-module-body"><div><h3>${m.title}</h3><p style="margin-bottom:16px">${m.desc}</p><a href="/practice?module=${m.key}" class="btn-secondary btn-compact">Coba latihan ${m.name} ${icon('chevronRight')}</a></div><div class="v2-module-points">${m.bullets.map(b => `<div>${icon('check')}<span>${b}</span></div>`).join('')}</div></div>`;
    } else {
      panel.innerHTML = `<div class="v3-mod-detail"><p style="margin-bottom:8px"><strong>${m.name}:</strong> ${m.desc}</p><p class="disclaimer">${m.bullets.join(' · ')}</p></div>`;
    }
  };

  document.querySelectorAll('[data-mod-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = Number(btn.dataset.modTab);
      document.querySelectorAll('[data-mod-tab]').forEach(b => b.setAttribute('aria-selected', String(b === btn)));
      renderMod(idx);
    });
  });
  renderMod(0);

  const box = document.getElementById('protoSampleBox');
  if (!box) return;
  const renderSample = (q) => {
    const prompt = esc(String(q.prompt ?? '').replace(/\s*\[[A-F]\]\s*/gi, ' '));
    const opts = (q.options || []).map(o => esc(stripChoicePrefix(o)));
    if (variantIndex === 0) {
      box.innerHTML = `<div class="v1-sample-meta"><span>STRUCTURE · CONTOH INTERAKTIF</span><span>Tanpa login</span></div><h3>${prompt}</h3><div class="v1-choice-list">${opts.map((o, i) => `<button type="button" class="v1-choice" data-pick="${i}"><span class="v1-choice-key">${String.fromCharCode(65 + i)}</span><span>${o}</span></button>`).join('')}</div><p class="v1-feedback" id="protoSampleFeedback">Pilih satu jawaban untuk memeriksa pembahasan.</p>`;
    } else if (variantIndex === 1) {
      box.innerHTML = `<div class="v1-sample-meta"><span>COBA SOAL STRUCTURE</span><span>Umpan balik instan</span></div><h3 style="font-size:20px; line-height:1.5">${prompt}</h3><div class="v2-choice-grid">${opts.map((o, i) => `<button type="button" class="v2-choice" data-pick="${i}"><span class="v2-choice-badge">${String.fromCharCode(65 + i)}</span><span>${o}</span></button>`).join('')}</div><p class="v1-feedback" id="protoSampleFeedback">Klik salah satu opsi untuk melihat hasil.</p>`;
    } else {
      box.innerHTML = `<div class="v3-specimen-head"><span>SPECIMEN STRUCTURE · INTERAKTIF</span><span>BANK SOAL AKTIF</span></div><h2>${prompt}</h2><div class="v3-options">${opts.map((o, i) => `<button type="button" class="v3-opt" data-pick="${i}"><span class="v3-opt-l">${String.fromCharCode(65 + i)}</span><span>${o}</span></button>`).join('')}</div><p class="v3-sample-msg" id="protoSampleFeedback">Pilih satu opsi untuk mengecek jawaban langsung di sini.</p>`;
    }

    box.querySelectorAll('[data-pick]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const pick = Number(btn.dataset.pick);
        box.querySelectorAll('[data-pick]').forEach(b => b.classList.remove('is-correct', 'is-incorrect'));
        const fb = document.getElementById('protoSampleFeedback');
        let ok = pick === q.answer;
        let explanation = q.explanation || 'Jawaban tepat.';
        if (q.id !== fallbackSample.id) {
          try {
            const res = await fetch('/api/sample-question', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: q.id, choice: pick }) });
            if (res.ok) {
              const data = await res.json();
              ok = !!data.correct;
              explanation = data.explanation || explanation;
            }
          } catch (_) {}
        }
        btn.classList.add(ok ? 'is-correct' : 'is-incorrect');
        fb.classList.toggle('is-correct', ok);
        fb.classList.toggle('is-incorrect', !ok);
        fb.textContent = ok ? `Tepat. ${explanation}` : 'Belum tepat. Coba pilihan lainnya.';
      });
    });
  };

  renderSample(fallbackSample);
  fetch('/api/sample-question').then(r => r.ok ? r.json() : null).then(d => {
    if (d?.question && box.isConnected) renderSample(d.question);
  }).catch(() => {});
}
