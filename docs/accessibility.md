# Aksesibilitas antarmuka LinguaPulse

Pemeriksaan 18 November 2026 menargetkan WCAG 2.2 tingkat AA, menggunakan
[acuan W3C](https://www.w3.org/WAI/WCAG22/quickref/).
Cakupannya antarmuka publik, akun peserta, latihan, persiapan dan ruang ujian,
hasil/riwayat, serta panel admin. Ini merupakan catatan perbaikan dan bukti
pengujian, bukan pernyataan sertifikasi atau kepatuhan penuh.

## Perbaikan

| Area | Perubahan | Kriteria terkait |
| --- | --- | --- |
| Warna | Token teks sekunder, status hijau/kuning, badge modul dan placeholder dipertegas. Batas input memakai warna yang lebih terlihat. | 1.4.3, 1.4.11 |
| Struktur | Statistik memakai struktur `dl`/`dt`/`dd` yang sah. Grup kontrol mempunyai role yang mendukung nama aksesibel. | 1.3.1, 4.1.2 |
| Fokus dan navigasi | Tautan lewati navigasi benar-benar memindahkan fokus pada setiap shell. Judul dan fokus diperbarui saat menu admin berganti. Halaman gagal muat tetap memiliki landmark utama dan tombol coba lagi. | 2.4.1, 2.4.2, 2.4.3 |
| Keyboard | Area bacaan, tabel dan catatan peristiwa dapat difokuskan untuk digulir. Fokus memiliki outline biru dan lapisan putih. | 2.1.1, 2.4.7, 2.4.11 |
| Menu admin | Drawer ponsel memindahkan dan menahan fokus, membuat konten latar inert, serta mengembalikan fokus ketika ditutup. Menu akun memakai pola disclosure dan mendukung Escape. | 2.1.1, 2.1.2, 4.1.2 |
| Combobox | ArrowUp memilih kandidat terakhir dari posisi awal. Kandidat tidak mengganti nilai sampai Enter atau klik. Escape membatalkan kandidat dan membersihkan referensi aktif. Aksi pointer dilakukan setelah pelepasan. | 2.1.1, 2.5.2, 4.1.2 |
| Layout | Tombol dapat membungkus pada batas kata. Ringkasan bank soal menjadi dua kolom pada ponsel. Dialog dapat digulir pada viewport pendek. Bar ujian mengalir pada ponsel agar tidak menutupi kontrol. | 1.4.4, 1.4.10, 1.4.12, 2.4.11 |
| Status | Jawaban terisi diberi garis bawah dan flag diberi tanda bintang. Notifikasi menggunakan live region yang tetap terpasang. Peringatan waktu dibacakan pada ambang lima dan satu menit, tanpa pengumuman setiap detik. | 1.4.1, 4.1.3 |
| Preferensi pengguna | Animasi/transisi menghormati reduced motion dan indikator fokus mendukung forced colours. Kontrol bersama memiliki ukuran minimum 24 CSS px. | 2.5.8 dan dukungan preferensi tampilan |

Aturan bersama berada di `frontend/css/accessibility.css`. Perubahan warna
tetap memakai token `frontend/css/tokens.css` dan komponen fitur terkait.
Helper fokus SPA berada di `frontend/js/core/accessibility.js`.

Beberapa pasangan warna yang dihitung dari nilai sRGB:

| Teks/batas | Latar | Rasio |
| --- | --- | --- |
| `#526176` | `#F1F5F9` | 5,76:1 |
| `#047857` | `#ECFDF5` | 5,21:1 |
| `#92400E` | `#FFFBEB` | 6,84:1 |
| `#0E7490` | `#ECFEFF` | 5,15:1 |
| `#64748B` | `#FFFFFF` | 4,76:1 |
| `#FFFFFF` | `#2563EB`, ujung terang gradien tombol utama | 5,17:1 |

## Hasil pemeriksaan

- Audit awal: 68 kombinasi keadaan layar/viewport, 39 temuan aturan axe
  A/AA, tanpa galat JavaScript. Temuan aturan dihitung per render, bukan
  sebagai 39 masalah unik.
- Audit akhir: 74 kombinasi pada lebar 1440 dan 320 CSS px, tanpa pelanggaran
  otomatis A/AA dan tanpa galat JavaScript. Cakupan tambahan meliputi menu
  publik, drawer admin, menu akun dan opsi combobox yang terbuka.
- Tidak ada temuan `aria-prohibited-attr` yang tersisa dalam hasil
  `incomplete`. Hasil `color-contrast` yang belum dapat ditentukan otomatis
  tetap dicatat, terutama gradien, lapisan transparan, dan konten di luar
  area gulir yang terlihat.
- Pemeriksaan perilaku lulus: skip link, tab materi, error login, pengembalian
  fokus dialog, pemilihan/pembatalan combobox, pembatalan pointer, fokus drawer,
  dialog pada viewport pendek, reflow 320 px, text spacing, pembesaran font
  200% pada login, reduced motion, forced colours dan pemulihan gagal muat.
- Text spacing diuji dengan line height 1,5, letter spacing 0,12 em, word
  spacing 0,16 em dan jarak sesudah paragraf 2 em pada halaman terpilih.
- `python tests/test_app.py` lulus pada skema MySQL sementara. Pengujian
  mencakup HTTP, otorisasi, akun, bank soal, paket, navigasi ujian, draf,
  pengiriman jawaban dan batas aktivasi telemetri.
  Pengulangan akhir selesai dengan exit code 0, dengan satu log koneksi klien
  terputus (`WinError 10053`) pada GET akun admin. Assertion tetap lulus.
- Sintaks JavaScript dan kedua skrip audit serta `git diff --check` lulus.
- Gambar hasil render ditinjau untuk landing/registrasi ponsel, ringkasan
  admin desktop, bank soal ponsel, dialog akun, drawer admin dan ujian Listening.

Ringkasan mesin tersimpan pada `docs/qa/accessibility-2026-11-18.json`.
Laporan lengkap beserta screenshot lokal berada di
`docs/qa/test_temp_wcag/final/` dan tidak masuk Git. Akun dan sesi pada
screenshot berasal dari fixture pengujian, bukan data responden penelitian.

## Menjalankan ulang

Siapkan `.env.test` sesuai `docs/mysql.md`. Tes membuat dan menghapus skema
`linguapulse_test_*`, tanpa memakai skema aplikasi untuk data uji. Gunakan
Python dengan Playwright/Chromium dan dependensi proyek yang tersedia.
Audit menerima berkas lokal axe-core 4.10.3 dan tidak mengirim data ke layanan
audit eksternal. Berkas tersebut dapat diperoleh dari
[CDN axe-core 4.10.3](https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.3/axe.min.js).

```powershell
python tests/accessibility_audit.py --axe docs/qa/test_temp_wcag/axe.min.js --output final --check
python tests/accessibility_audit.py --ui-only
python tests/test_app.py
```

## Batas pemeriksaan pada 18 November 2026

Lolos axe tidak menguji seluruh kriteria WCAG. Sesi pembaca layar nyata
dengan NVDA, JAWS atau VoiceOver belum dijalankan. Emulasi forced colours dan
reduced motion dilakukan melalui Chromium, bukan pemeriksaan seluruh
browser/perangkat atau seluruh pengaturan Windows.

Penilaian kontras otomatis tidak menuntaskan seluruh teks di atas gradien,
lapisan transparan dan konten bergulir. Pasangan warna di atas dihitung
terpisah, tetapi bukan sertifikasi setiap piksel dan setiap keadaan UI.
Isi soal/audio baru dari admin tetap memerlukan pemeriksaan bahasa,
alternatif konten, label, dan panjang teks masing-masing.

Durasi ujian tetap mengikuti pengaturan paket dan tenggat server. Penyesuaian
waktu per peserta atau penerapan pengecualian tes pada kriteria 2.2.1 belum
ditetapkan sebagai kebijakan aksesibilitas. Kebutuhan alternatif audio
Listening juga perlu ditentukan bersama pengelola sesuai tujuan tes.
Perubahan antarmuka ini tidak mengubah rancangan riset atau mengklaim
akomodasi tersebut sudah tersedia.

## Tindak lanjut 20 November 2026

- Formulir masuk, daftar, persetujuan ujian, akun admin, bank soal, paket,
  jadwal, dan tambahan waktu menampilkan kesalahan di dekat kolom saat isian
  yang bermasalah bisa ditentukan. Fokus berpindah ke kolom pertama dan
  pembaca layar dapat mengaitkan pesan dengan label kolom. Isian lain tetap
  tersedia untuk diperbaiki. Kesalahan umum seperti kegagalan koneksi muncul
  sebagai pesan formulir. [Acuan saran perbaikan W3C](https://www.w3.org/WAI/WCAG22/Understanding/error-suggestion.html)
- Di **Admin → Sesi jadwal**, simpan atau pilih jadwal lalu isi username
  peserta dan tambahan waktu. Masukkan `0` untuk mencabut pengaturan. Rentang
  tambahan ialah 1–240 menit. Server mengambil nilai untuk pasangan jadwal
  dan akun. Tenggat tersimpan saat sesi dimulai. Jam tutup jadwal tetap
  membatasi durasi. Persiapan menampilkan durasi dasar, tambahan, dan
  perkiraan sisa waktu jika jadwal hampir tutup. Pengaturan oleh pengawas
  ini belum membuktikan pemenuhan kriteria penyesuaian waktu WCAG.
  Jika aplikasi sudah berjalan saat pembaruan, mulai ulang backend agar
  inisialisasi MySQL membuat tabel tambahan waktu.
  [Acuan waktu W3C](https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html)
- Pada editor soal **Listening**, isi kolom **Transkrip audio** dengan ucapan,
  pembicara, dan bunyi yang membawa informasi. Peserta dapat memilih **Transkrip
  teks** di latihan bebas. Hanya soal dengan transkrip tersedia pada mode
  tersebut. Hasil ujian dapat menampilkan transkrip dari snapshot setelah
  pengiriman. Soal Listening pada ujian aktif tetap menggunakan audio.
  Penggunaan teks dalam penilaian memerlukan keputusan pengelola tentang
  keterampilan yang diukur dan penafsiran hasilnya.
  [Acuan alternatif audio W3C](https://www.w3.org/WAI/WCAG22/Understanding/audio-only-and-video-only-prerecorded.html)
- Playwright menjalankan alur admin memasukkan tiga soal, mengunggah audio,
  memublikasikan paket, membuat jadwal, dan menetapkan tambahan waktu. Alur
  peserta mencakup pendaftaran dengan koreksi kesalahan, latihan transkrip,
  persetujuan, pengerjaan, pengiriman, pembahasan dan riwayat. Perbandingan
  akun uji memeriksa durasi 35 menit dan 20 menit serta tenggat yang tetap
  sama setelah akomodasi dicabut. Tes batas jadwal membuktikan jam tutup
  tetap berlaku saat ada tambahan waktu.
- Pengulangan audit axe lulus pada 74 kombinasi layar dan viewport yang sama
  dengan pengujian 18 November. Uji keyboard, reflow dan regresi aplikasi
  `tests/test_app.py` juga lulus. Alur baru
  menggunakan fixture pada skema sementara. Hasilnya menguji fungsi perangkat
  lunak. Pengujian penggunaan oleh peserta manusia belum dilakukan.
- Pengujian Chromium berjendela menggunakan NVDA portabel 2026.3.1.
  Log ucapan aplikasi menunjukkan pengumuman kesalahan kata sandi, kontrol
  tambahan menit dan status penyimpanan, radio jawaban, teks transkrip
  pembahasan, serta area tabel pengawasan. Playwright juga menguji pemutaran
  audio hasil unggahan di ruang ujian dan pada pembahasan. Synthesizer pada
  sesi ini melaporkan suara Indonesia tidak tersedia. Pelafalan Indonesia
  dan pengalaman pengguna NVDA sehari-hari masih perlu diuji.

```powershell
python tests/test_accessible_workflow.py
python tests/test_exam_schedules.py
python tests/accessibility_audit.py --output followup-2026-11-20 --check
```

## Transkrip pada ruang ujian

Pemutar Listening hadir bersama pertanyaan di semua ukuran layar. Di
**Admin → Sesi jadwal → Akomodasi peserta**, masukkan username peserta dan
aktifkan **Izinkan transkrip Listening selama ujian**. Paket perlu memiliki
satu transkrip yang konsisten untuk setiap rekaman. Pertanyaan yang berbagi
rekaman memakai transkrip yang sama. Pengawas dapat mencabut akses untuk sesi
berikutnya melalui pengaturan yang sama.

Hak akses dan teksnya ditetapkan dalam snapshot saat peserta mulai. Peserta
lain, pratinjau paket, dan sesi tanpa jadwal hanya menerima materi Listening
biasa. Hasil menyimpan `listening_transcript_enabled` untuk menunjukkan bahwa
akses diberikan selama sesi. Catatan ini tidak merekam apakah transkrip dibuka.
Gunakan penanda tersebut saat membandingkan hasil menurut format yang
disediakan. Mulai ulang backend agar inisialisasi MySQL membuat tabel
`exam_listening_accommodations` dan menerapkan nama bawaan baru.
