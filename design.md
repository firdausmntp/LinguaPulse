# LinguaPulse TOEFL EPT Design System

Brand sendiri — bukan template pihak ketiga. Cobalt Modern, Familjen Grotesk headings, IBM Plex Sans body. Tokens di `frontend/css/tokens.css`. Tanpa emoji, tanpa gamifikasi, tanpa eyebrow labels, tanpa gradien dekoratif, tanpa fake metrics.

2026-11-10 EPT revision: Listening, Structure dan Reading adalah tiga modul EPT. Writing dan sentence rewriting mendukung tugas riset; bukan skor TOEFL resmi.

## Arah Visual: Evolve Cobalt

- **Palet:** white work surfaces (#FFFFFF), crisp neutral paper (#F8FAFC, #F1F5F9), deep navy ink (#0A1322, #0F172A), vivid cobalt accent (#1D4ED8 / #2563EB).
- **Tipografi:** Familjen Grotesk untuk display/heading dengan tracking ketat, IBM Plex Sans untuk body (measure 65–75ch), JetBrains Mono hanya untuk data/metrik/angka telemetri.
- **Kedalaman:** shadow berlapis offset + blur lembut (bukan flat keras, bukan halo glow). Radius presisi: 6px kecil, 10px kontrol, 14px kartu.
- **Form:** border input jelas, focus ring cobalt solid offset 2px, hover/active tegas, placeholder ≥4.5:1.
- **Browser surfaces:** selection, caret, scrollbar, focus ring, underline offset, angka tabular — semua di-theme dari palet, bukan default browser.
- **States:** hover, disabled, loading, error, empty wajib ada dan terlihat.

## Halaman

- **Landing (`/`):** hero gelap dengan screenshot nyata workspace Listening, switcher tiga modul EPT, sampel Structure interaktif tanpa login, feedback hijau/merah dengan label teks.
- **Ruang ujian (`/exam/session`):** empat tab (Listening, Structure, Reading, Writing riset), progres nyata, navigator soal, penanda ragu-ragu, audio Listening, Reading per wacana, timer sticky di mobile, minim chrome.
- **Panel pengawas (`/admin`):** sidebar collapsible, ringkasan operasional dengan hierarchy jelas, detail inspeksi di tab Pengawasan (tanpa klaim live monitoring), editor soal master/detail dengan pratinjau, unggah audio, impor/ekspor.
- **Hasil & riwayat (`/results`, `/history`):** breakdown akurasi per modul, pembahasan terstruktur, riwayat tanpa scroll samping di mobile.
- **Dasbor peserta (`/dashboard`):** dua jalur jelas — latihan tanpa timer dan ujian berwaktu.
- **Latihan bebas (`/practice`):** satu soal acak MC per giliran dari Listening/Structure/Reading; pilih, cek, baca pembahasan, lanjut. Tanpa timer, tanpa sensor, tanpa riwayat ujian. Parameter `module` bertahan saat refresh.

## Aturan Teknis

- Max 350 baris per berkas kode; refaktor modular bila mendekati.
- Responsif di 320/375px; hormati `prefers-reduced-motion`; tanpa animasi page-load dekoratif di app views.
- Satu resep tombol primer (`btn-primary`); ikon dari SVG helper `icons.js` dengan `aria-hidden="true"`; tombol ikon wajib nama aksesibel.
- Panel harus muat di mobile viewport, bukan sekadar `overflow: hidden`.
- Edit template/CSS/JS di tempat; tambah helper modular bila perlu; jangan hapus route.
- Pertahankan: sesi akun, restore draf, telemetri hanya saat ujian aktif, hasil owner-only, escape semua teks soal saat render.
