<div align="center">

<img src="frontend/assets/logo/linguapulse-master.svg" alt="Logo LinguaPulse" width="120" />

# LinguaPulse TOEFL EPT

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-Vanilla%20ES2022-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![MySQL](https://img.shields.io/badge/MySQL-8-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![License](https://img.shields.io/badge/License-Apache--2.0-blue?style=for-the-badge&logo=apache&logoColor=white)

**Platform simulasi TOEFL EPT dengan pengawasan integritas berbasis machine learning.**

Listening Â· Structure Â· Reading â€” plus telemetri perilaku (keystroke dynamics, fokus, pointer) yang dinilai model XGBoost dan 1D-CNN untuk riset integritas pengerjaan.

[Fitur](#-fitur-unggulan) Â· [Mulai Cepat](#-mulai-cepat) Â· [Arsitektur](#-arsitektur) Â· [API](#-ringkasan-api) Â· [Struktur Proyek](#-struktur-proyek) Â· [Pengujian](#-pengujian) Â· [Sitasi](#-sitasi-akademik) Â· [Lisensi](#-lisensi)

</div>

---

## Tentang Proyek

LinguaPulse adalah aplikasi web lengkap untuk latihan TOEFL EPT sekaligus instrumen riset: setiap sesi ujian merekam pola perilaku peserta secara **lokal dan privasi-sadar** â€” tanpa menyimpan isi ketikan mentah atau isi clipboard â€” lalu mengekstraknya menjadi fitur terukur (median dwell time, rasio backspace, entropi spasial pointer, episode kehilangan fokus) untuk diklasifikasikan oleh model integritas pengerjaan.

> Hasil latihan bukan skor atau sertifikat TOEFL resmi.

| | |
|---|---|
| **Backend** | Python standard library murni â€” `http.server`, `sqlite3`, tanpa framework |
| **Frontend** | SPA Vanilla JavaScript, tanpa bundler; font dimuat dari Google Fonts |
| **Database** | MySQL 8, InnoDB, utf8mb4; migrasi SQLite baca-saja tersedia |
| **Bank Soal** | MySQL; JSON digunakan untuk arsip serta impor/ekspor manual |
| **ML Pipeline** | XGBoost, 1D-CNN, dan baseline rule-based â€” via paket terpisah [`proctor_telemetry`](https://github.com/firdausmntp/proctor_telemetry) (lokal: `packages/`, diabaikan git) + `ml_pipeline/` |
| **Tema Visual** | *Cobalt Modern* â€” CSS tokens terpusat, tanpa emoji pada UI |

## Fitur Unggulan

### Ruang Ujian
- **Paket EPT utuh** â€” Listening (audio sintetis lokal), Structure, dan Reading dalam satu sesi dengan durasi yang diatur pengawas (bawaan 25 menit).
- **Snapshot bank soal per sesi** â€” `/api/exam/start` membekukan salinan soal ke database, sehingga pengeditan admin tidak pernah mengubah penilaian sesi yang sedang berjalan.
- **Draf tahan kegagalan** â€” jawaban, bagian aktif, dan sisa waktu tersimpan di perangkat; refresh tidak mengulang timer; kirim ulang otomatis terlindungi ID percobaan anti-duplikasi.
- **Auto-submit saat waktu habis** dengan jaring penyelamat: jika pengiriman gagal, draf tetap aman untuk dicoba kembali.
- **Latihan bebas** (`/practice`) â€” soal acak, pembahasan langsung, tanpa timer, tanpa rekaman, tidak menyentuh riwayat ujian.

### Pengawasan Integritas (Proctoring)
- **Sensor tiga kanal** â€” keystroke dynamics (dwell/flight/interkey, backspace, paste), fokus & visibilitas (blur, tab hidden), dan pointer (heatmap ternormalisasi, entropi spasial antar zona passage/answer/navigation).
- **Aktif hanya saat ujian** â€” sensor pointer dan ketikan mati total di landing, login, dasbor, latihan, dan panel admin.
- **Muatan terenkripsi** â€” handshake kunci dan enkripsi paket telemetri (`security.js` â†” `security.py`), verifikasi tantangan anti-bot, cookie sesi `HttpOnly`.
- **Inferensi ganda** â€” skor XGBoost, 1D-CNN, dan flag rule-based beserta ablation tersimpan terpisah dari hasil akademik.
- **Panel pengawas** â€” ringkasan operasional, detail sesi dengan timeline peristiwa dan heatmap, manajemen akun, CRUD bank soal dengan pratinjau peserta, impor/ekspor JSON, unggah audio hingga 8 MB.

### Privasi & Etika Riset
- Tidak ada karakter ketikan mentah, isi clipboard, atau data biometrik yang disimpan.
- Halaman `/privacy` dan `/terms` menjelaskan penggunaan data riset.

## Mulai Cepat

```bash
# 1. Masuk ke folder proyek
cd LinguaPulse

# 2. Pasang dependensi (Python 3.11+)
python -m pip install -r requirements.txt

# 3. Siapkan MySQL dan .env sesuai docs/mysql.md
# Pada komputer pengembangan ini, .env sudah tersedia; jangan ditimpa.
# Sesudah restart Windows: powershell -File scripts/start_mysql_local.ps1
python app.py

# 4. Buka browser
# http://localhost:8878 (server mendengarkan localhost secara default)
```

| Akun demo | Username | Sandi |
|---|---|---|
| Pengawas | `admin` | `admin123` |
| Peserta | `nadia_putri` | `student123` |

Petunjuk database baru, pemindahan SQLite, akun tes, dan backup: [docs/mysql.md](docs/mysql.md).

### Alur Peserta

```
/  landing  â†’  /register  â†’  /dashboard  â†’  /exam (persiapan + persetujuan)
      â†’  /exam/session (timer sesuai pengaturan, sensor aktif)  â†’  /results  â†’  /history
```

### Pemeriksaan Kualitas

```bash
python -m compileall -q backend questions      # sintaks Python
node --check frontend/js/exam/exam.js               # sintaks JavaScript (per berkas)
python tests/test_app.py                       # HTTP + headless browser (butuh playwright)
```

## Arsitektur

```mermaid
flowchart LR
    subgraph Browser
        A[index.html shell] --> B[router.js - History API]
        B --> C[exam.js / exam-render.js]
        B --> D[telemetry.js]
        C -- payload terenkripsi --> E
    end
    subgraph Backend["backend/ - stdlib HTTP"]
        E[router.py TOEFLPlatformRouter] --> F[routes_exam.py]
        E --> G[routes_admin.py]
        F --> H[telemetry_engine.py]
        H --> I[proctor_telemetry pkg]
        F --> J[(MySQL - InnoDB)]
        G --> J
        K[Arsip JSON] -. impor manual .-> G
    end
    subgraph ML["ml_pipeline/"]
        L[XGBoost] & M[1D-CNN] & N[Rule-based]
    end
    I -. fitur .-> ML
```

**Prinsip penting:**

1. **Snapshot per sesi** â€” bank soal aktif disalin ke `exam_attempts` saat sesi dimulai; resume dan penilaian memakai salinan yang sama.
2. **Pemisahan data** â€” hasil akademik (`exam_submissions`) dan telemetri (`telemetry_sessions`) berada di tabel berbeda sesuai batasan masalah penelitian.
3. **Kerangka modular** â€” `TOEFLPlatformRouter` mewarisi `AdminRoutes` + `ExamRoutes`; setiap berkas dibatasi maksimal 350 baris.

## Ringkasan API

| Endpoint | Method | Akses | Fungsi |
|---|---|---|---|
| `/api/auth/login` Â· `/api/auth/register` Â· `/api/auth/logout` | POST | Publik | Sesi akun, cookie `HttpOnly` |
| `/api/auth/me` | GET | Publik | Identitas sesi aktif |
| `/api/questions` | GET | Akun | Bank soal publik (admin melihat status aktif) |
| `/api/exam/settings` | GET | Akun | Durasi paket aktif |
| `/api/admin/exam-settings` | POST | Admin | Atur durasi sesi baru (1â€“240 menit) |
| `/api/exam/start` | POST | Peserta | Mulai sesi, bekukan bank, dapat `deadline` |
| `/api/exam/resume` | GET | Peserta | Lanjutkan sesi dari draf perangkat |
| `/api/submit` | POST | Peserta | Kirim jawaban + telemetri terenkripsi |
| `/api/practice/question` | GET/POST | Peserta | Latihan bebas dan pembahasan |
| `/api/history` Â· `/api/results?id=` | GET | Pemilik | Riwayat dan detail hasil |
| `/api/admin/overview` Â· `/api/proctor/sessions` | GET | Admin | Ringkasan dan detail pengawasan |
| `/api/admin/questions` (+`/import`, `/export`) | GET/POST/DELETE | Admin | CRUD, impor, ekspor bank soal |
| `/api/admin/audio` | POST | Admin | Unggah audio Listening â‰¤ 8 MB |
| `/api/admin/users` | GET/POST/DELETE | Admin | Manajemen akun |
| `/api/survey` | GET/POST | Akun | Kuesioner responden riset |

## Struktur Proyek

```
toefl/
â”œâ”€â”€ app.py                      # Entry point: init schema, seed, serve
â”œâ”€â”€ backend/                    # HTTP router + modul domain (semua < 350 baris)
â”‚   â”œâ”€â”€ router.py               #   SPA routes, API, proteksi origin/CSRF
â”‚   â”œâ”€â”€ routes_exam.py          #   Submit: penilaian + inferensi telemetri
â”‚   â”œâ”€â”€ routes_admin.py         #   Handler pengawas
â”‚   â”œâ”€â”€ attempts.py             #   Snapshot bank per sesi
â”‚   â”œâ”€â”€ telemetry_engine.py     #   Ekstraksi fitur + fallback engine
â”‚   â”œâ”€â”€ security.py             #   Handshake, dekripsi, challenge
â”‚   â”œâ”€â”€ auth.py / sessions.py   #   Akun, hash sandi, cookie HttpOnly
â”‚   â”œâ”€â”€ database.py             #   Koneksi MySQL + transaksi commit/rollback
â”‚   â””â”€â”€ legacy/                 #   kode migrasi lama (tidak dipanggil startup)
â”œâ”€â”€ frontend/
â”‚   â”œâ”€â”€ index.html              # Shell SPA + fallback tanpa JS
â”‚   â”œâ”€â”€ pages/                  # Fragmen per route
â”‚   â”œâ”€â”€ js/                     # JavaScript per fitur
â”‚   â”‚   â”œâ”€â”€ core/               # router, state, dan ikon bersama
â”‚   â”‚   â”œâ”€â”€ admin/              # panel, akun, dan editor soal admin
â”‚   â”‚   â”œâ”€â”€ exam/               # ujian, keamanan, dan telemetri
â”‚   â”‚   â”œâ”€â”€ account/            # autentikasi
â”‚   â”‚   â””â”€â”€ learning/           # landing, dasbor, latihan, dan hasil
â”‚   â”œâ”€â”€ css/                    # tokens, dasar, dan shell bersama
â”‚   â”‚   â”œâ”€â”€ admin/              # panel admin dan editor soal
â”‚   â”‚   â”œâ”€â”€ exam/               # ruang ujian
â”‚   â”‚   â”œâ”€â”€ account/            # autentikasi dan akun
â”‚   â”‚   â””â”€â”€ learning/           # halaman belajar dan hasil
â”‚   â””â”€â”€ assets/logo/            # Paket ikon & favicon standar
â”œâ”€â”€ questions/                  # Arsip soal JSON per modul (impor manual)
â”œâ”€â”€ packages/                   # (gitignored) proctor_telemetry â€” repo terpisah
â”œâ”€â”€ ml_pipeline/                # Evaluasi model klasifikasi integritas
â”œâ”€â”€ tests/                      # HTTP, headless browser, audit halaman
â””â”€â”€ docs/qa/                    # Screenshot verifikasi & catatan QA
```

> **Catatan `packages/`** â€” direktori ini berisi repo git terpisah
> ([`proctor_telemetry`](https://github.com/firdausmntp/proctor_telemetry)) dan sengaja
> diabaikan oleh `.gitignore`. Clone repo ini tidak menyertakannya; ambil manual:

```bash
git clone https://github.com/firdausmntp/proctor_telemetry.git packages/proctor_telemetry
```

MySQL adalah sumber data utama bank soal. Pada database baru bank soal kosong;
tambahkan soal lewat editor admin atau impor berkas JSON. Berkas di `questions/`
adalah arsip, tidak dibaca ulang otomatis saat server dimulai.

Tanpa direktori itu, `backend/telemetry_engine.py` otomatis memakai fallback engine lokal
(ekstraksi fitur + skor heuristik) sehingga aplikasi tetap berjalan.

## Pengujian

`python tests/test_app.py` menjalankan uji HTTP dan browser headless memakai skema MySQL sementara yang diisi contoh soal arsip â€” tanpa menambah data uji ke database aplikasi. Butuh `playwright` dan Chromium.

```bash
python -m pip install -r requirements.txt
python -m pip install playwright
python -m playwright install chromium
# Siapkan .env.test dengan akun tes terpisah; lihat docs/mysql.md.
python -m unittest discover -s tests -p 'test_*.py' -v
python tests/test_app.py
```

Pengujian membuat screenshot sementara (desktop dan mobile); contoh dokumentasi QA tersedia di `docs/qa/`.

## Konfigurasi Riset

- **`TOEFL_AI_API_KEY`** â€” jika diatur, layanan AI menghasilkan umpan balik esai; tanpa kunci, evaluasi lokal dipakai.
- **Turnstile** masih simulasi lokal dan belum memiliki widget produksi. Jangan gunakan sebagai perlindungan bot; integrasi widget, verifikasi token dan HTTPS diperlukan sebelum deploy publik. Mode `CF_ENFORCE_STRICT=true` menolak token simulasi dan belum dapat dipakai oleh antarmuka saat ini.
- **Model ML** â€” prediksi riset bersifat indikatif, bukan penetapan pelanggaran otomatis.

## Sitasi Akademik

Jika proyek ini â€” atau metodologi telemetri multimodal dan fusi perilaku pengerjaannya â€”
digunakan dalam skripsi, tesis, makalah, atau publikasi riset, silakan sitasi:

```bibtex
@software{utomo2026linguapulse,
  author  = {Utomo, Firdaus Satrio},
  title   = {LinguaPulse TOEFL EPT: Web-Based TOEFL EPT Simulation Platform
             with Machine Learning-Based Work Integrity Telemetry},
  year    = {2026},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/firdausmntp/LinguaPulse}},
  note    = {Engine telemetri: ProctorTelemetry (\url{https://github.com/firdausmntp/proctor_telemetry})}
}
```

> Engine telemetri [`proctor_telemetry`](https://github.com/firdausmntp/proctor_telemetry)
> punya entri sitasi tersendiri di README paket tersebut.

## Lisensi

Proyek ini dilisensikan di bawah [Apache License 2.0](LICENSE).

```
Copyright 2026 LinguaPulse Authors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
```

<div align="center">

**Dibangun sebagai instrumen riset skripsi â€” latihan bebas, data terlindungi, hasil jujur.**

</div>
