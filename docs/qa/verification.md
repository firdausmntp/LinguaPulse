# Verifikasi refactor halaman LinguaPulse

Pemeriksaan memakai SQLite dan bank soal sementara. Database aplikasi dan bank soal asli tidak digunakan untuk penulisan data uji.

## Hasil

- HTTP route langsung dan refresh: landing, akun, dasbor, persiapan, ujian, hasil, riwayat, admin, privasi.
- Validasi register, password konfirmasi, login salah/benar, sesi HttpOnly, logout, penolakan origin lain.
- Pendaftaran tidak dapat menaikkan role menjadi admin. API dan fragmen admin menolak peserta/anonim.
- Kunci jawaban tidak dikirim melalui API soal peserta. Hasil hanya dapat dilihat pemilik sesi.
- Draf jawaban, bagian aktif, deadline dan metrik tetap tersedia setelah refresh.
- Timer tidak berjalan di landing/persiapan. Sensor ketikan, fokus dan pointer tidak aktif di luar ruang ujian.
- Waktu habis mengirim otomatis; kegagalan jaringan menyimpan draf dan menyediakan kirim ulang di luar panel per bagian.
- CRUD soal admin, tab monitoring, daftar pengguna, escaping teks yang mengandung markup.
- Screenshot landing pada 320, 375, 1280, 1440, 1920px; halaman login/register dan ujian pada mobile serta desktop.
- Pemeriksaan mobile memakai lebar panel nyata, bukan hanya scrollWidth, sehingga overflow yang tertutup tidak lolos.
- Semua file kode aktif maksimal 350 baris; sintaks Python/JavaScript diperiksa.

## Hallmark

`sloplint frontend/index.html --genre modern-minimal --render`: static tier 0 FAIL, 0 REFLEX, 4 WARN. Render bawaan tidak dijalankan karena puppeteer-core tidak tersedia. Verifikasi tampilan memakai Chromium headless Playwright dan screenshot aktual yang dilihat langsung.

Empat WARN diperiksa: F4 menghitung tombol dan tab dari beberapa route dalam stylesheet bersama, sementara CTA utama tiap konteks konsisten; F6 salah menganggap selector h2/h3 empty-state sebagai angka besar; dua F7 menandai resep input seragam yang memang diperlukan untuk konsistensi formulir.

Review Hallmark terpisah menemukan tiga hal dan semuanya diperbaiki: spasi pada judul mobile, saran Writing yang terlalu menjanjikan skor, serta lebar paragraf pembahasan. Pemeriksaan sendiri juga memperbaiki cascade CSS mobile dan mengutamakan formulir login pada layar kecil.

## Batasan

Tidak ada deployment publik. Integrasi model dan Turnstile lokal yang sudah ada tetap merupakan bagian prototipe. Tidak ada klaim skor TOEFL resmi. Kolom reward historis disimpan untuk kompatibilitas; perolehan dan tampilan reward sudah dihapus.
