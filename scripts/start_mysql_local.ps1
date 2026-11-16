param(
    [string]$MySqlBinary = 'C:\laragon\bin\mysql\mysql-8.0.30-winx64\bin\mysqld.exe',
    [int]$Port = 3307
)
$ErrorActionPreference = 'Stop'
$projectPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$mysqlData = Join-Path $projectPath 'data\mysql-local'
if (-not (Test-Path -LiteralPath (Join-Path $mysqlData 'mysql'))) {
    throw 'Datadir lokal belum disiapkan. Ikuti docs/mysql.md untuk server baru; script ini hanya menyalakan instance lokal yang sudah ada.'
}
if (-not (Test-Path -LiteralPath $MySqlBinary)) { throw 'mysqld.exe tidak ditemukan. Isi parameter -MySqlBinary.' }
$probe = [Net.Sockets.TcpClient]::new()
try {
    $pending = $probe.ConnectAsync('127.0.0.1', $Port)
    $null = $pending.Wait(1000)
    $alreadyListening = $probe.Connected
} catch { $alreadyListening = $false } finally { $probe.Dispose() }
if ($alreadyListening) {
    Write-Output "Port $Port sudah mendengarkan; instance baru tidak dijalankan."
    exit 0
}
$mysqlBase = Split-Path (Split-Path $MySqlBinary -Parent) -Parent
$arguments = @('--no-defaults', "--basedir=`"$mysqlBase`"", "--datadir=`"$mysqlData`"",
    "--port=$Port", '--bind-address=127.0.0.1', '--mysqlx=0', '--skip-log-bin',
    '--max-connections=160', '--innodb-buffer-pool-size=64M',
    "--log-error=`"$mysqlData\server.log`"", "--pid-file=`"$mysqlData\server.pid`""
)
$process = Start-Process -FilePath $MySqlBinary -ArgumentList $arguments -WindowStyle Hidden -PassThru
Write-Output "MySQL lokal dimulai, PID $($process.Id), port $Port. Periksa data/mysql-local/server.log bila koneksi gagal."
