# AGENTS.md — Pedoman Agen & Standar Pengembangan Proyek

Dokumen ini berisi konvensi, arsitektur, dan batasan teknis untuk agen pengembangan yang bekerja di repositori **LinguaPulse TOEFL EPT**.

---

## 1. Batasan Ukuran Berkas (Mandatory Rule)

* **Batas Maksimal Baris:** **Maksimal 350 baris per berkas (max 1 file 350 line)**.
* **Refactoring Modular:** Jika berkas kode (`.py`, `.js`, `.css`, dll.) mendekati atau melampaui 350 baris, pecah fungsi/modul ke dalam modul pembantu (*helper modules*, *sub-routers*, atau *component styles*) secara modular.

---

## 2. Arsitektur Proyek

* **Backend (`backend/`):**
  * Python standard library (`http.server`, `sqlite3`, `hashlib`, `json`, dll.).
  * Router `TOEFLPlatformRouter` melayani API (`/api/*`), fallback route aplikasi, dan static files dari `frontend/`. Handler admin dan submit dipisah di `backend/routes_admin.py` dan `backend/routes_exam.py`.
  * Database tersimpan di `data/toefl_platform.db`.
  * Bank soal tersinkronisasi dua arah dengan berkas JSON di `questions/` (`listening/`, `grammar/`, `reading/`, `writing/`).
* **Frontend (`frontend/`):**
  * Single Page Application (SPA) berbasis Vanilla JavaScript murni, tanpa dependensi framework berat.
  * Shell `frontend/index.html`, fragmen halaman di `frontend/pages/`, dan router History API di `frontend/js/router.js`.
  * Route publik: `/`, `/login`, `/register`, `/privacy`. Route peserta: `/dashboard`, `/exam` (persiapan), `/exam/session`, `/results`, `/history`. `/admin` khusus pengawas.
  * Paket EPT terdiri dari Listening, Structure, dan Reading. Writing dan perbaikan kalimat merupakan tugas tambahan riset, terpisah dari ketepatan pilihan ganda EPT.
  * Soal dapat dikustomisasi melalui editor admin, unggah audio, impor/ekspor JSON, serta status aktif. Snapshot bank soal disimpan per sesi agar perubahan admin tidak mengubah penilaian ujian berjalan.
  * Ruang ujian **tidak boleh** ditanam pada landing page. Timer dimulai setelah persetujuan dan tombol mulai di halaman persiapan.
  * `/practice` merupakan latihan bebas peserta: soal aktif acak, pembahasan langsung, tanpa timer, tanpa pencatatan sensor, dan tidak menambah riwayat ujian. `/admin` dibuka pada ringkasan operasional; detail inspeksi tetap di tab Pengawasan.
  * Tidak ada gamifikasi: XP, level, streak, lencana prestasi, dan leaderboard dilarang. Kolom lama database dipertahankan hanya demi kompatibilitas data; jangan aktifkan kembali.
  * Identitas akun divalidasi melalui cookie sesi `HttpOnly` dan API server; jangan percaya role/identitas dari localStorage atau cookie yang ditulis JavaScript.
  * Desain sistem menggunakan CSS tokens di `frontend/css/tokens.css` dengan tema *Cobalt Modern*.
* **Machine Learning (`ml_pipeline/`):**
  * Model klasifikasi integritas pengerjaan: XGBoost, 1D-CNN, dan baseline rule-based.

---

## 3. Aturan Telemetri & UX

* **Sensor Pointer:**
  * Sensor pointer (`pointerdown`, `pointermove`) **hanya boleh aktif pada sesi ujian aktif** (`/exam/session`, `#viewExam`).
  * Jangan merekam koordinat atau menambah hitungan pointer saat pengguna berada di landing page, login/register, dasbor, persiapan, hasil, riwayat, atau Panel Admin (`#viewAdmin`).
* **Privasi & Tampilan Telemetri:**
  * Bar info telemetri mentah (`Ketikan | Fokus Hilang | Pointer`) harus tetap tersembunyi dari navigasi umum agar tidak mendistraksi peserta.
  * Tampilan metrik live hanya diperuntukkan pada lembar kerja esai Section 3 (Dwell, Flight, Backspace, Entropy).

---

## 4. Standar Kode & Aset

* **Bahasa & Komunikasi:**
  * Dokumentasikan kode dengan ringkas.
  * Sesuaikan respons dengan bahasa pengguna (Bahasa Indonesia).
* **Aset Ikon & Logo:**
  * **Emoji dilarang** pada antarmuka, label, tombol, notifikasi, dan konten aplikasi. Gunakan ikon atau SVG yang konsisten; ikon dekoratif wajib memakai `aria-hidden="true"`, sedangkan tombol ikon wajib memiliki label aksesibel.
  * Gunakan berkas SVG geometris bersih (`viewBox="0 0 256 256"`) dan paket favicon standar di `frontend/assets/logo/` dan `frontend/`.

