# Paket ujian dan tampilan satu soal

Revisi 18 November 2026. Cakupan: repositori APLIKASI, tanpa commit/push otomatis.

## Perubahan

- `/admin/packages`: membuat serta mengubah nama, deskripsi, durasi, pilihan soal, dan status publikasi. Penyimpanan menolak versi edit kedaluwarsa. Penyimpanan gagal tidak mengubah paket atau daftar soal sebelumnya.
- `/exam`: peserta memilih paket publik. Paket yang belum lengkap tidak dapat dimulai. Persiapan tidak menyalakan timer atau sensor.
- `/exam/session`: satu soal terlihat pada satu waktu, nomor aktif/terisi/ditandai, sebelumnya/berikutnya, materi sesuai soal, dan posisi yang dipulihkan bersama jawaban serta flag dari localStorage per akun.
- Navigator di kanan desktop dan dapat diciutkan di ponsel. Pada layar sempit, tab materi/jawaban berada di bawah timer tanpa saling menutupi.
- Percobaan menyimpan metadata paket dan bank beserta kunci dalam snapshot server. Durasi dibekukan saat mulai. Penarikan atau perubahan paket tidak mengubah percobaan yang sudah dibuat.
- Satu Writing dipilih dari tugas dalam paket bila tersedia. Paket tanpa Writing tidak menampilkan tugas palsu. Jawaban di luar tugas Writing snapshot tidak dihitung menjadi jumlah kata Writing pada percobaan baru.
- Hasil mencantumkan nama paket snapshot. API durasi lama dipertahankan khusus sebagai kompatibilitas Experimental.

## Database

Dua tabel tambahan: `exam_packages` dan `exam_package_questions`. Keanggotaan berelasi FK ke paket dan bank soal. Migrasi satu kali mengelompokkan bank aktif yang memang sudah ada menjadi Experimental. Tidak ada impor JSON saat startup.

Pemeriksaan database aplikasi sebelum dan sesudah startup: 11 soal, 0 percobaan, dan 0 sesi terkirim. Setelah migrasi tersedia Experimental dengan durasi 25 menit. Paket tambahan dan pengiriman jawaban dalam pengujian hanya berada pada skema MySQL sementara.

## Bukti pemeriksaan

| Pemeriksaan | Hasil |
| --- | --- |
| `python -m unittest discover -s tests -p 'test_*.py' -v` | 15 tes lulus, termasuk paket, snapshot, validasi, migrasi, dan rollback. |
| `python tests/test_app.py` | Regresi HTTP dan Chromium lulus. Mencakup otorisasi, akun/bank soal, draf, timer, kegagalan jaringan, submit bersamaan tanpa duplikasi, hasil privat, latihan bebas, admin, serta paket. |
| `python tests/package_checks.py` | Alur admin draf/publikasi, pilihan paket, durasi, satu soal, flag/jawaban/posisi setelah refresh, perubahan paket saat sesi berjalan, paket tanpa Writing, dan submit lulus. |
| Tampilan Chromium | Desktop 1440 px serta lebar 1100, 768, 375, dan 320 px diperiksa. Screenshot desktop/ponsel ditinjau visual. Tidak ditemukan overflow horizontal pada tampilan yang diuji. |
| Sensor | Persiapan dan hasil tidak mengaktifkan sensor. Regresi menguji sensor berhenti di luar sesi. |
| Sintaks | 22 berkas JavaScript lolos `node --check`. Python lolos `compileall`. Berkas kode tidak melampaui 350 baris. |

Screenshot lokal dari runner khusus berada di `docs/qa/polish-packages-2026-11-18/` dan diabaikan Git. Log QA `*.log` juga diabaikan. Hasil browser pada runner lengkap dibersihkan setelah selesai.

## Batas dan tindak lanjut naskah

Pemeriksaan dilakukan menggunakan Chromium headless dan data fixture pada MySQL sementara. Ini bukan pengujian perangkat fisik, uji beban 1.000 peserta, atau pengumpulan data responden. Draf masih bergantung pada penyimpanan perangkat dan tidak disinkronkan antarperangkat. Pemeriksaan kelengkapan audio berdasarkan URL tidak menjamin media eksternal selalu dapat diakses.

Status penyelarasan naskah (18 November 2026): telah ditindaklanjuti pada revisi Bab III (`pemodelan.tex`, `basis_data.tex`, `wireframe_admin.tex`, `prosedur.tex`, `rekrutmen.tex`, `cakupan.tex`, `tahapan.tex`, `kebutuhan.tex`, `pengujian.tex`, `use_case.tex`, `aktivitas_ujian.tex`, `alur_responden.tex`, `erd_akun_bank.tex`, wireframe `admin_ringkasan.tex` & `admin_ponsel.tex`, serta `ARTEFAK_BAB3_BUKTI.md`). Perubahan aplikasi ini tetap tidak membuktikan peningkatan akurasi model atau kapasitas pengguna bersamaan.
