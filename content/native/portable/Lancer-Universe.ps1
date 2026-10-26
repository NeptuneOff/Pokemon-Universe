# Uses Windows PowerShell, already included with Windows 10 and 11.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Backup-Save {
    $source = Join-Path $PSScriptRoot 'save.bin'
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { return }
    $data = [System.IO.File]::ReadAllBytes($source)
    if ($data.Length -eq 0) { return }
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        $digest = [BitConverter]::ToString($hasher.ComputeHash($data)).Replace('-', '').ToLowerInvariant()
    } finally {
        $hasher.Dispose()
    }
    $folder = Join-Path $PSScriptRoot 'universe-backups'
    [System.IO.Directory]::CreateDirectory($folder) | Out-Null
    $target = Join-Path $folder ($digest + '.sav')
    if (Test-Path -LiteralPath $target) {
        if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $digest) {
            throw 'Une copie de secours est alteree. La sauvegarde actuelle reste intacte.'
        }
        return
    }
    $temporary = Join-Path $folder ('.save-' + [Guid]::NewGuid().ToString('N') + '.tmp')
    try {
        [System.IO.File]::WriteAllBytes($temporary, $data)
        [System.IO.File]::Move($temporary, $target)
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary }
    }
}

$sessionLock = $null
$exitCode = 1
try {
    # Refuse a second launcher using the same save folder.
    $sessionLock = [System.IO.File]::Open((Join-Path $PSScriptRoot 'universe-session.lock'),
        [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
    Backup-Save
    & (Join-Path $PSScriptRoot 'main.exe')
    $exitCode = $LASTEXITCODE
    Backup-Save
} catch {
    Write-Host ('Lancement interrompu : ' + $_.Exception.Message)
    $exitCode = 1
} finally {
    if ($null -ne $sessionLock) { $sessionLock.Dispose() }
}
exit $exitCode
