# Verifikasi pembaruan TOEFL EPT

Paket pengguna: Listening, Structure, Reading; Writing tambahan untuk riset. Semua pengujian menggunakan database, bank soal JSON, dan folder unggahan sementara.

## Cakupan

- Migrasi aman database lama, Listening contoh dengan audio sintetis orisinal, nilai Listening di hasil/riwayat.
- Paket soal per percobaan: perubahan kunci setelah sesi dimulai tidak mengubah hasil penilaian. Identitas peserta datang dari sesi server, bukan payload.
- Resume hanya oleh pemilik; kirim ulang ID percobaan menghasilkan satu hasil.
- Soal custom melalui UI: tambah, edit, salin, pencarian, pratinjau, export JSON; validasi duplikasi kode.
- Impor atomik: salah satu soal tidak valid tidak menulis soal lain. Soal nonaktif tidak dikirim kepada peserta.
- Unggah audio: signature format diverifikasi, nama penyimpanan acak, batas ukuran, akses admin; audio palsu ditolak.
- Pemutar Listening benar-benar memuat WAV dan diputar pada browser, audio dijeda saat berganti bagian.
- Reading dapat berpindah antarwacana, Writing memakai tugas yang dipilih saat mulai.
- Progres dihitung dari jawaban, tanda soal dipulihkan sesudah refresh, draf/deadline tidak terulang.
- Timer otomatis, percobaan ulang setelah gangguan jaringan, dan sensor tidak aktif di luar ruang ujian tetap diuji.
- Preview hero merupakan screenshot komponen ruang Listening yang benar-benar dijalankan, tanpa identitas pengguna.
- Landing ditinjau pada 320, 375, 1280, 1440, dan 1920 px; editor dan ruang ujian dicek pada desktop serta ponsel.

## Hallmark

Static lint pada shell beserta CSS terkait: 0 FAIL, 0 REFLEX. Lima WARN tentang resep tombol dan input lintas route telah ditinjau, dengan gaya kontrol sengaja konsisten. Render bawaan tidak berjalan karena puppeteer-core tidak tersedia; screenshot aktual diperoleh lewat Playwright Chromium.

Laporan tes: `test-ept.log`. Screenshot: `hero-*.png`, `listening-*.png`, `custom-editor-*.png`, serta halaman akun, persiapan dan hasil.

## Review akhir

Review Hallmark dalam konteks terpisah menemukan dua hal: tombol utama pengguna yang sudah masuk perlu langsung menuju persiapan, serta timer ponsel perlu tetap terlihat ketika menjawab. Keduanya diperbaiki; navigasi nomor soal juga tertutup secara default pada ponsel. Verifikasi browser memastikan timer tetap pada bagian atas viewport saat menggulir soal.
