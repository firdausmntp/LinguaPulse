# Database MySQL

Runtime aplikasi menggunakan MySQL 8, InnoDB, utf8mb4, dan PyMySQL. SQLite hanya dibaca oleh alat migrasi; aplikasi tidak membuka atau membuat database SQLite. HTTP/API dan folder fitur frontend tetap sama.

## Komputer pengembangan saat ini

Instance khusus proyek memakai MySQL Community 8.0.30 yang tersedia di Laragon, alamat `127.0.0.1:3307`, database `linguapulse`. Ini MySQL, bukan MariaDB dari XAMPP. Datadir `data/mysql-local/`, `.env`, `.env.test`, dan cadangan tidak masuk Git. Akun aplikasi dan tes terpisah dari root; password acak tersimpan lokal.

Setelah restart komputer, dari folder `APLIKASI`:

```powershell
./scripts/start_mysql_local.ps1
python app.py
```

Script hanya menyalakan datadir yang sudah disiapkan. Ia tidak menginisialisasi ulang data, mengubah password, atau menghentikan server lain. Jika port sudah terpakai, periksa bahwa `.env` menunjuk instance yang benar. Bila executable dipindahkan, berikan `-MySqlBinary 'C:\lokasi\bin\mysqld.exe'`. Jangan membuka dua versi server pada datadir yang sama.

## Instalasi baru / clone GitHub

1. Sediakan MySQL 8 yang terpelihara, misalnya MySQL 8.4 LTS. Instalasi Laragon lokal saat ini hanya lingkungan pengembangan.
2. Buat database kosong dan akun khusus menggunakan administrator MySQL. Ganti placeholder password berikut dengan password sendiri; jangan commit password.

```sql
CREATE DATABASE linguapulse CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE USER 'linguapulse_app'@'localhost' IDENTIFIED BY 'GANTI_PASSWORD_APLIKASI';
GRANT ALL PRIVILEGES ON linguapulse.* TO 'linguapulse_app'@'localhost';
```

Akun perlu DDL pada database tersebut karena startup menjalankan inisialisasi skema. Untuk host aplikasi terpisah, sesuaikan bagian host akun serta konfigurasi TLS, bukan memberi hak global/root kepada aplikasi.

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env: host, port, database, user, password sesuai server sendiri.
python app.py
```

Environment sistem mengungguli nilai `.env`. `TOEFL_MYSQL_SSL_CA` dapat menunjuk CA untuk verifikasi sertifikat dan hostname saat memakai TLS. Akun demo dibuat hanya jika tabel akun kosong. Bank soal baru tetap kosong sampai diisi admin atau diimpor manual.

## Memindahkan data SQLite lama

Hentikan aplikasi lama terlebih dahulu agar tidak ada penulisan ke SQLite setelah snapshot. Arahkan `.env` ke **database MySQL kosong**. Jalankan migrasi sebelum menjalankan `app.py`, karena startup pada database kosong membuat akun demo.

```powershell
python scripts/migrate_sqlite_to_mysql.py --source data/toefl_platform.db
python scripts/migrate_sqlite_to_mysql.py --source data/toefl_platform.db --apply
python app.py
```

Tanpa `--apply`, perintah hanya memeriksa sumber dan menampilkan jumlah baris. Saat diterapkan, alat membuat snapshot konsisten SQLite di `.workspace-backups/`, memeriksa integritas dan kompatibilitas kolom, lalu mengimpor seluruh tabel dalam satu transaksi MySQL. Seluruh nilai kolom asal dan jumlah baris dibandingkan sebelum commit. Kegagalan membatalkan data impor. Target yang telah berisi data ditolak; jangan mengosongkan database aplikasi untuk mengulang perintah.

ID, hash password, sesi login, soal/pilihan, jawaban, pengaturan durasi, snapshot ujian, telemetri, survei, serta hasil historis dipertahankan jika ada di sumber. Kolom `submission_order` menggantikan pengurutan internal `rowid` SQLite. Satu penanda `mysql_from_sqlite_v1` ditambahkan setelah verifikasi. Laporan JSON berada di samping snapshot, tanpa isi data pengguna. Sumber SQLite tidak dihapus atau ditimpa.

Migrasi lokal 16 November 2026 memverifikasi 2 akun, 11 soal, 32 pilihan, 9 sesi login, dan 2 penanda migrasi asal. Tabel hasil, percobaan, telemetri, dan survei pada sumber belum berisi data. Penanda migrasi baru membuat total penanda menjadi 3. Durasi bawaan tetap 25 menit karena sumber belum mempunyai pengaturan khusus.

## Pengujian terisolasi

Siapkan akun terpisah. Pola hak akses berikut membatasi pembuatan/penghapusan ke database tes berawalan `linguapulse_test_` (garis bawah di-escape agar bukan wildcard):

```sql
CREATE USER 'linguapulse_test'@'localhost' IDENTIFIED BY 'GANTI_PASSWORD_TES';
GRANT ALL PRIVILEGES ON `linguapulse\_test\_%`.* TO 'linguapulse_test'@'localhost';
```

```powershell
Copy-Item .env.test.example .env.test
# Isi koneksi akun tes; pada komputer ini sudah tersedia, jangan ditimpa.
python -m pip install playwright
python -m playwright install chromium
python -m unittest discover -s tests -p 'test_*.py' -v
python tests/test_app.py
```

Setiap konteks tes membuat nama acak, memastikan prefix valid sebelum DROP, dan menutup database tes setelah selesai. Tidak ada fallback ke database aplikasi jika akun tes belum diatur. Suite meliputi impor seluruh tabel, nilai Unicode, hash password, penolakan impor ulang, rollback akibat FK/kolom tak dikenal, transaksi InnoDB, autentikasi, admin, durasi, snapshot, pengiriman bersamaan, browser desktop/ponsel, dan privasi hasil.

## Cadangan dan kapasitas

Snapshot SQLite adalah kondisi sebelum migrasi; data baru hanya berada di MySQL. Cadangkan MySQL secara berkala dengan `mysqldump`, menggunakan akun dan prompt password, bukan password pada baris perintah:

```powershell
mysqldump --host=127.0.0.1 --port=3307 --user=linguapulse_app --password --single-transaction --no-tablespaces --set-gtid-purged=OFF --result-file=.workspace-backups/linguapulse.sql linguapulse
```

Buat folder `.workspace-backups` dahulu bila belum ada. Jangan menyalin datadir yang sedang hidup sebagai pengganti backup konsisten. Jangan commit dump berisi akun/data responden.

MySQL mendukung penulisan serentak melalui transaksi dan penguncian baris. Hasil, jawaban, telemetri, dan cache hasil disimpan atomik; pengiriman ulang untuk percobaan yang sama tidak menggandakan data. Migrasi ini belum membuktikan kapasitas 1.000 peserta. Kapasitas tetap bergantung pada server HTTP Python, CPU inferensi, koneksi database, ukuran payload, dan konfigurasi deployment; uji beban pada lingkungan tujuan diperlukan sebelum menyatakan angka kapasitas.
