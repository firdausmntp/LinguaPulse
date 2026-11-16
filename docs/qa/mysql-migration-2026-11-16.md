# Verifikasi migrasi MySQL, 16 November 2026

## Implementasi dan data

- Server yang diuji: MySQL Community 8.0.30, `127.0.0.1:3307`, tabel InnoDB/utf8mb4.
- Koneksi aktif: PyMySQL; kredensial di `.env`. Akun tes dan database tes terpisah.
- SQLite sumber tidak dihapus atau ditulis ulang. SHA-256 setelah migrasi tetap sama dengan sebelum migrasi.
- Verifikasi seluruh nilai kolom asal: 2 akun, 11 soal, 32 pilihan, 9 sesi login, serta 2 penanda lama cocok. Tabel data penelitian lainnya kosong pada sumber. Satu penanda migrasi MySQL ditambahkan.
- Cadangan konsisten dan laporan migrasi berada di `.workspace-backups/`; kredensial, cadangan, datadir, dan log terverifikasi diabaikan Git. Contoh `.env.example` dan `.env.test.example` tersedia untuk clone baru.
- Delapan kiriman HTTP bersamaan untuk satu percobaan menghasilkan tepat satu hasil, satu sesi telemetri, dan satu cache hasil. Ketujuh kiriman lainnya mendapat status sudah dikirim.

## Pemeriksaan yang dijalankan

| Pemeriksaan | Hasil |
| --- | --- |
| `python -m unittest discover -s tests -p 'test_*.py' -v` | 12 tes lulus. |
| `python tests/test_app.py` | Seluruh pemeriksaan HTTP dan browser Chromium desktop/ponsel lulus. |
| `python -m compileall -q backend questions scripts tests` | Lulus. |
| `git diff --check` di repositori aplikasi | Lulus; Git hanya memberi pemberitahuan konversi LF/CRLF. |
| Ukuran file Python aktif di backend, scripts, tests | Tidak ada yang melebihi 350 baris. |
| Aplikasi aktual pada port 8878 | Landing, login, persiapan, shell admin, dan API contoh soal merespons 200; API membaca soal MySQL. |
| Script `start_mysql_local.ps1` saat port 3307 terpakai | Menghindari menjalankan instance ganda. Cabang cold start belum diuji lewat script ini. |

Tes database mencakup impor seluruh tabel dengan data historis nonkosong, Unicode, hash password, penolakan target berisi data, rollback akibat FK tak valid dan kolom sumber tak dikenal, transaksi InnoDB, jumlah baris yang cocok pada UPDATE tanpa perubahan nilai, serta survei dan pelabelan pengawas.

Suite HTTP/browser mencakup autentikasi, pembatasan peran, CRUD akun dan soal, impor/ekspor, audio, durasi admin, snapshot soal dan deadline, pengiriman berulang/bersamaan, hasil/riwayat privat, sensor yang mati di luar ujian, penyimpanan draf saat jaringan gagal, dan tampilan ponsel.

## Batas verifikasi

Belum ada uji beban 1.000 peserta atau deployment publik. Pengujian ini bukan jaminan kapasitas server produksi. Turnstile tetap mode lokal yang sebelumnya disepakati; model riset tetap memerlukan pelatihan dan validasi pada data responden. Audit Hallmark terdahulu tidak dijalankan ulang dalam migrasi database ini. Tidak ada commit atau push otomatis.
