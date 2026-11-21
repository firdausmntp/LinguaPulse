# PR.md — Daftar Tugas Redesign & Penyempurnaan UI LinguaPulse

Dokumen ini merangkum daftar tugas lanjutan setelah checkpoint ini agar redesign tiap halaman dapat dilanjutkan secara terarah.

---

## 1. Prioritas Utama: Redesign Landing Page (`/`)

Status saat ini: prototipe perbandingan tersedia di `frontend/prototypes/landing.html`, namun belum ada yang dipromosikan ke produksi.

- [ ] **Perkuat karakter desain & kombinasi warna:** hindari kesan generik/AI-slop (seperti badge pill dekoratif di atas judul pada varian `Tactile`), perkuat palet yang berkarakter namun tetap selaras dengan identitas akademik **LinguaPulse** (`Cobalt` / `Navy` + permukaan kertas netral).
- [ ] **Tingkatkan kualitas animasi & *motion feel*:**
  - Buat *entrance choreography* yang terasa nyata dan terarah (bukan sekadar fade/slide seragam).
  - Tambahkan interaksi responsif pada komponen utama (switcher modul Listening/Structure/Reading, kartu soal interaktif, pratinjau ruang ujian).
  - Tetap patuhi `prefers-reduced-motion` dan animasikan properti *composite-only* (`transform`, `opacity`, `clip-path`).
- [ ] **Finalisasi & promosikan ke produksi:** terapkan varian pemenang ke `frontend/pages/landing.html`, `frontend/css/learning/landing.css`, dan `frontend/js/learning/landing.js`.

---

## 2. Redesign Halaman Aplikasi Lainnya

Setelah arah visual Landing Page disepakati, lanjutkan evaluasi/redesign halaman berikut secara konsisten:

- [ ] **Autentikasi (`/login`, `/register`):** `frontend/pages/auth.html`, `frontend/css/account/account.css` — perbaiki hirarki visual, kejelasan validasi form, dan transisi antar mode masuk/daftar.
- [ ] **Dasbor Peserta (`/dashboard`):** perjelas dua jalur utama (Latihan Bebas tanpa timer vs Sesi Ujian berwaktu) tanpa elemen gamifikasi.
- [ ] **Latihan Bebas (`/practice`):** `frontend/pages/practice.html`, `frontend/css/learning/learning.css` — pertegas fokus satu soal per giliran, umpan balik benar/salah, dan pembahasan.
- [ ] **Persiapan & Ruang Ujian (`/exam`, `/exam/session`):** `frontend/pages/prepare.html`, `frontend/pages/exam.html`, `frontend/css/exam/exam-session.css`, `frontend/css/exam/ept-exam.css` — rapikan tata letak soal, pemutar Listening, Reading split-view, navigator kanan, dan lembar Esai Writing (pertahankan aturan sensor pointer hanya aktif di `/exam/session`).
- [ ] **Hasil & Riwayat (`/results`, `/history`):** `frontend/css/learning/outcomes.css` — perjelas breakdown akurasi Listening/Structure/Reading, pembahasan butir soal, dan keterbacaan tabel/kartu di layar ponsel (`375px`).
- [ ] **Panel Pengawas (`/admin`):** `frontend/pages/admin.html`, `frontend/css/admin/*.css` — selaraskan tampilan ringkasan operasional, paket ujian, jadwal, bank soal, dan tab pengawasan.

---

## 3. Verifikasi & Pembersihan Akhir

- [ ] Pastikan seluruh berkas kode (`.py`, `.js`, `.css`, `.html`) tetap `<= 350` baris sesuai `AGENTS.md`.
- [ ] Pastikan tidak ada emoji, tidak ada gamifikasi (XP/level/streak/badge/leaderboard), serta teks copy sesuai kondisi nyata aplikasi & naskah riset (`design.md`).
- [ ] Hapus folder prototipe sementara (`frontend/prototypes/`) dan tangkapan layar QA sementara (`docs/qa/test_temp_*/`) setelah redesign selesai dipromosikan.
- [ ] Jalankan verifikasi penuh sebelum rilis:
  - `python tests/test_app.py`
  - `python tests/accessibility_audit.py --ui-only`
  - Inspeksi visual Playwright pada viewport desktop (`1440x900`) dan ponsel (`375x812`) dengan 0 console/page error dan 0 horizontal overflow.
