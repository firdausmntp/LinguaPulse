# AGENTS.md — Pedoman Agen & Standar Pengembangan Proyek

Dokumen ini berisi konvensi, arsitektur, dan batasan teknis untuk agen pengembangan yang bekerja di repositori **LinguaPulse TOEFL EPT**.

---

## 1. Batasan Ukuran Berkas (Mandatory Rule)

* **Batas Maksimal Baris:** **Maksimal 350 baris per berkas (max 1 file 350 line)**.
* **Refactoring Modular:** Jika berkas kode (`.py`, `.js`, `.css`, dll.) mendekati atau melampaui 350 baris, pecah fungsi/modul ke dalam modul pembantu (*helper modules*, *sub-routers*, atau *component styles*) secara modular.

---

## 2. Arsitektur Proyek

* **Backend (`backend/`):**
  * HTTP memakai Python standard library (`http.server`); MySQL memakai PyMySQL dan konfigurasi `.env` memakai python-dotenv.
  * Router `TOEFLPlatformRouter` melayani API (`/api/*`), fallback route aplikasi, dan static files dari `frontend/`. Handler admin dan submit dipisah di `backend/routes_admin.py` dan `backend/routes_exam.py`.
  * Database aktif adalah MySQL 8 dengan tabel InnoDB dan utf8mb4. Konfigurasi `TOEFL_MYSQL_*` berada di `.env` atau environment; jangan menyimpan kredensial dalam Git. Tidak ada fallback runtime ke SQLite.
  * MySQL adalah sumber data utama bank soal. Berkas JSON di `questions/` hanya arsip dan dapat diimpor secara manual; startup tidak menyinkronkan atau mengisi ulang soal dari JSON.
  * SQLite lama hanya sumber migrasi baca-saja/cadangan. Gunakan `scripts/migrate_sqlite_to_mysql.py`; target yang sudah berisi data harus ditolak. Jangan hapus sumber setelah migrasi.
  * Akses database melalui context manager `get_connection()` agar commit/rollback dan penutupan koneksi deterministik. Simpan jawaban, telemetri, dan cache hasil dalam satu transaksi; kunci baris percobaan untuk mencegah submit ganda.
  * Tes database harus menggunakan `tests/mysql_support.py` dan akun `.env.test` khusus skema `linguapulse_test_*`. Jangan menjalankan data uji pada database aplikasi. Petunjuk di `docs/mysql.md`.
* **Frontend (`frontend/`):**
  * Single Page Application (SPA) berbasis Vanilla JavaScript murni, tanpa dependensi framework berat.
  * Shell `frontend/index.html`, fragmen halaman di `frontend/pages/`, dan router History API di `frontend/js/core/router.js`.
  * Route publik: `/`, `/login`, `/register`, `/privacy`. Route peserta: `/dashboard`, `/exam` (persiapan), `/exam/session`, `/results`, `/history`. `/admin` khusus pengawas.
  * Paket EPT terdiri dari Listening, Structure, dan Reading. Writing dan perbaikan kalimat merupakan tugas tambahan riset, terpisah dari ketepatan pilihan ganda EPT.
  * Soal dapat dikustomisasi melalui editor admin, unggah audio, impor/ekspor JSON, serta status aktif. Snapshot bank soal disimpan per sesi agar perubahan admin tidak mengubah penilaian ujian berjalan.
  * `/admin/packages` mengatur beberapa paket: nama, deskripsi, durasi 1–240 menit, pilihan soal, serta draf/publikasi. Soal baru tidak otomatis ditambahkan ke paket. Paket publik wajib memuat Listening dengan audio, Structure pilihan ganda, dan Reading dengan bacaan. Satu tugas Writing dipilih dari daftar paket bila tersedia.
  * `/exam` memilih paket sebelum persetujuan dan mulai. Snapshot percobaan membekukan metadata paket, soal, kunci, dan durasi. Dua tabel tambahan: `exam_packages` dan `exam_package_questions`. Endpoint durasi lama hanya kompatibilitas untuk Experimental.
  * Ruang ujian menampilkan satu soal pada satu waktu. Navigator nomor menandai posisi aktif, jawaban terisi, dan flag. Simpan posisi, jawaban, dan flag pada draf per akun. Navigator berada di kanan desktop dan dapat diciutkan di ponsel. Materi bacaan/audio mengikuti soal yang sedang dipilih.
  * Ruang ujian **tidak boleh** ditanam pada landing page. Timer dimulai setelah persetujuan dan tombol mulai di halaman persiapan.
  * `/practice` merupakan latihan bebas peserta: soal aktif acak, pembahasan langsung, tanpa timer, tanpa pencatatan sensor, dan tidak menambah riwayat ujian. `/admin` dibuka pada ringkasan operasional; detail inspeksi tetap di tab Pengawasan.
  * Tidak ada gamifikasi: XP, level, streak, lencana prestasi, dan leaderboard dilarang. Kolom lama database dipertahankan hanya demi kompatibilitas data; jangan aktifkan kembali.
  * Identitas akun divalidasi melalui cookie sesi `HttpOnly` dan API server; jangan percaya role/identitas dari localStorage atau cookie yang ditulis JavaScript.
  * CSS dan JavaScript dikelompokkan berdasarkan fitur: `admin/`, `exam/`, `account/`, dan `learning/`; utilitas JavaScript bersama berada di `js/core/`.
  * Desain sistem menggunakan CSS tokens di `frontend/css/tokens.css` dengan tema *Cobalt Modern*.
* **Machine Learning (`ml_pipeline/`):**
  * Rancangan eksperimen utama penelitian menggunakan XGBoost. Nama skor XGBoost/1D-CNN pada prototipe bukan bukti tersedianya model terlatih; periksa artefak dan jalur inferensi sebelum mengklaim hasil pelatihan. Skor berbasis koefisien manual harus dinyatakan sebagai heuristik.

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

## 5. Kesesuaian dengan naskah penelitian

* Narasi website, dokumentasi, implementasi, dan naskah aktif di `../NASKAH_LATEX/` harus sesuai. Periksa jalur kode serta pengujian sebelum mengklaim fitur bekerja; teks antarmuka atau nama fungsi bukan bukti hasil penelitian.
* Bedakan kemampuan yang sudah tersedia, rencana, simulasi, dan hasil yang benar-benar teruji. Dilarang mengarang data responden, hasil pelatihan/akurasi, dukungan perangkat/sensor, kapasitas pengguna, atau jaminan keamanan. Skor heuristik tidak boleh disebut hasil model XGBoost/1D-CNN terlatih hanya karena label pada kode atau layar.
* Writing sudah tersedia sebagai tugas esai tambahan riset untuk menyediakan variasi interaksi penulisan. Hasilnya terpisah dari ketepatan pilihan ganda Listening, Structure, dan Reading. Jawaban akhir disimpan sebagai data akademik; telemetri tidak merekam isi karakter ketikan mentah maupun isi clipboard. Jangan menyamakan tidak menyimpan keylog dengan tidak menyimpan jawaban esai.
* Bila ada ketidaksesuaian, perbaiki sesuai cakupan tugas atau catat sebagai kesenjangan yang belum diselesaikan. Jangan mengarang fitur atau diam-diam memperluas cakupan untuk mencocokkan narasi. Ikuti juga aturan narasi dan bukti pada `../AGENTS.md`.

