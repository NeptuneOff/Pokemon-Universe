# Windows PowerShell 5.1. All game packages come from this Git checkout.
[CmdletBinding()]
param([switch]$PrepareOnly, [switch]$Admin, [switch]$CopyCampaign, [switch]$Menu)

# JOUER.bat presents one entry point; direct/CI invocations remain non-interactive.
if ($Menu -and -not $PrepareOnly) {
    Write-Host 'Pokemon Universe'
    Write-Host '1 - Jouer / continuer la campagne'
    Write-Host '2 - Mode admin / continuer les tests'
    Write-Host '3 - Mode admin / copier ma campagne pour tester'
    Write-Host '0 - Quitter'
    $selection = Read-Host 'Choix'
    switch ($selection) {
        '1' { }
        '2' { $Admin = $true }
        '3' { $Admin = $true; $CopyCampaign = $true }
        '0' { exit 0 }
        default { Write-Host 'Choix inconnu. Relancer JOUER.bat.'; exit 1 }
    }
}
if ($CopyCampaign -and -not $Admin) { Write-Host '-CopyCampaign exige -Admin.'; exit 1 }

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$repository = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$distribution = Join-Path $repository 'distribution\windows'
$storage = Join-Path $repository 'native-runtime'
$builds = Join-Path $storage 'windows-builds'
$backupFolder = Join-Path $storage 'universe-backups'
$statePath = Join-Path $storage 'windows-current.json'
if ($Admin) {
    $builds = Join-Path $storage 'windows-admin-builds'
    $backupFolder = Join-Path $storage 'universe-admin-backups'
    $statePath = Join-Path $storage 'windows-admin-current.json'
}
$logFolder = Join-Path $repository 'logs'
$runId = (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + $PID
$runLog = Join-Path $logFolder ('universe-' + $runId + '.log')
$latestLog = Join-Path $logFolder 'dernier-lancement.log'
$utf8 = New-Object System.Text.UTF8Encoding($false)
$sessionLock = $null
$sourceLock = $null
$stage = $null
$mirrorLog = $false
$phase = 'initialisation'
$exitStatus = 1
$timer = [Diagnostics.Stopwatch]::StartNew()

function Write-Log([string]$Message, [string]$Level = 'INFO') {
    $line = '{0} [{1}] [{2}] {3}' -f (Get-Date -Format 'o'), $Level, $script:phase, $Message
    Write-Host $line
    [IO.File]::AppendAllText($script:runLog, $line + [Environment]::NewLine, $script:utf8)
    if ($script:mirrorLog) {
        [IO.File]::AppendAllText($script:latestLog, $line + [Environment]::NewLine, $script:utf8)
    }
}

function Relative-File([string]$Base, [string]$Name) {
    if ([string]::IsNullOrWhiteSpace($Name) -or [IO.Path]::IsPathRooted($Name) -or
        $Name -match '[\\:\x00-\x1f<>"|?*]') { throw ('Chemin de paquet invalide : ' + $Name) }
    foreach ($part in $Name.Split('/')) {
        if ($part -eq '' -or $part -eq '.' -or $part -eq '..' -or $part.EndsWith('.') -or $part.EndsWith(' ')) {
            throw ('Chemin de paquet invalide : ' + $Name)
        }
    }
    return Join-Path $Base ($Name.Replace('/', [IO.Path]::DirectorySeparatorChar))
}

function Hash-File([string]$Path) {
    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        $stream = [IO.File]::OpenRead($Path)
        try { return [BitConverter]::ToString($hasher.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
        finally { $stream.Dispose() }
    } finally { $hasher.Dispose() }
}

function Assert-File([string]$Path, [long]$Size, [string]$Sha256) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw ('Fichier absent : ' + $Path + '. Verifier que git pull est termine.') }
    if ((Get-Item -LiteralPath $Path).Length -ne $Size) { throw ('Taille incorrecte : ' + $Path) }
    $actual = Hash-File $Path
    if ($actual -ne $Sha256) { throw ('Empreinte incorrecte : ' + $Path + '; attendu=' + $Sha256 + '; obtenu=' + $actual) }
}

function Assert-NoLink([string]$Path) {
    $current = [IO.Path]::GetFullPath($Path)
    while ($current -and $current.Length -gt $script:repository.Length) {
        if ((Test-Path -LiteralPath $current) -and
            ((Get-Item -Force -LiteralPath $current).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw ('Le dossier ou fichier de jeu est un lien : ' + $current)
        }
        $current = [IO.Path]::GetDirectoryName($current)
    }
}

function Atomic-Write([string]$Path, [byte[]]$Data) {
    $temporary = $Path + '.tmp-' + [Guid]::NewGuid().ToString('N')
    try {
        $stream = [IO.File]::Open($temporary, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try { $stream.Write($Data, 0, $Data.Length); $stream.Flush($true) } finally { $stream.Dispose() }
        if (Test-Path -LiteralPath $Path) { [IO.File]::Replace($temporary, $Path, [NullString]::Value) }
        else { [IO.File]::Move($temporary, $Path) }
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary }
    }
}

function Backup-Save([string]$Runtime) {
    $save = Join-Path $Runtime 'save.bin'
    if (-not (Test-Path -LiteralPath $save -PathType Leaf)) { return }
    Assert-NoLink $save
    $data = [IO.File]::ReadAllBytes($save)
    if ($data.Length -eq 0) { throw ('Sauvegarde vide : ' + $save + '. Les copies precedentes restent dans ' + $script:backupFolder) }
    $hasher = [Security.Cryptography.SHA256]::Create()
    try { $hash = [BitConverter]::ToString($hasher.ComputeHash($data)).Replace('-', '').ToLowerInvariant() }
    finally { $hasher.Dispose() }
    [IO.Directory]::CreateDirectory($script:backupFolder) | Out-Null
    Assert-NoLink $script:backupFolder
    $copy = Join-Path $script:backupFolder ($hash + '.sav')
    if (Test-Path -LiteralPath $copy) {
        if ((Hash-File $copy) -ne $hash) { throw ('Copie de secours alteree : ' + $copy + '. Aucune sauvegarde ne sera remplacee.') }
    } else { Atomic-Write $copy $data }
    Write-Log ('Sauvegarde protegee : ' + $hash + ' (' + $data.Length + ' octets)')
}

function Assert-GameStopped([string]$Runtime) {
    $expected = [IO.Path]::GetFullPath((Join-Path $Runtime 'main.exe'))
    foreach ($processInfo in @(Get-Process -Name main -ErrorAction SilentlyContinue)) {
        $executablePath = $null
        try { $executablePath = $processInfo.Path } catch { }
        if ($null -ne $executablePath -and [string]::Equals($expected, $executablePath, [StringComparison]::OrdinalIgnoreCase)) {
            throw ('Le jeu est deja ouvert (PID ' + $processInfo.Id + '). Fermer cette session avant de continuer.')
        }
    }
}

function Read-Release {
    $path = Join-Path $script:distribution 'release.json'
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw 'Distribution Windows absente. Terminer git pull puis relancer JOUER.bat.' }
    $release = [IO.File]::ReadAllText($path, $script:utf8) | ConvertFrom-Json
    if ($release.schema -ne 1 -or $release.platform -ne 'windows-x64' -or $release.build_id -cnotmatch '^[0-9a-f]{20}$' -or
        $release.executable -ne 'main.exe' -or @($release.files).Count -eq 0 -or @($release.packages).Count -eq 0) {
        throw 'Manifeste de distribution Windows incompatible.'
    }
    $script:fileIndex = @{}
    $packageIds = @{}
    foreach ($package in $release.packages) {
        if ($package.id -cnotmatch '^[a-z0-9-]+$' -or $packageIds.ContainsKey($package.id) -or
            $package.sha256 -cnotmatch '^[0-9a-f]{64}$' -or $package.bytes -le 0 -or @($package.chunks).Count -eq 0) {
            throw 'Definition de paquet invalide.'
        }
        $packageIds[$package.id] = $true
        $chunkPaths = @{}
        [long]$total = 0
        foreach ($chunk in $package.chunks) {
            $null = Relative-File $script:distribution $chunk.path
            if ($chunkPaths.ContainsKey($chunk.path) -or $chunk.sha256 -cnotmatch '^[0-9a-f]{64}$' -or $chunk.bytes -le 0) {
                throw 'Definition de fragment invalide.'
            }
            $chunkPaths[$chunk.path] = $true
            $total += $chunk.bytes
        }
        if ($total -ne $package.bytes) { throw ('Taille de paquet incoherente : ' + $package.id) }
    }
    foreach ($entry in $release.files) {
        $null = Relative-File $script:builds $entry.path
        if ($script:fileIndex.ContainsKey($entry.path) -or -not $packageIds.ContainsKey($entry.package) -or
            $entry.sha256 -cnotmatch '^[0-9a-f]{64}$' -or $entry.bytes -lt 0 -or
            $entry.path -match '(?i)(\.nds|\.sav|\.log)$|(^|/)save\.bin$|(^|/)sim_config(_prj)?\.ini$') {
            throw ('Entree de distribution invalide : ' + $entry.path)
        }
        $script:fileIndex[$entry.path] = $entry
    }
    if (-not $script:fileIndex.ContainsKey('main.exe') -or -not $script:fileIndex.ContainsKey('universe-install.json')) {
        throw 'Le manifeste ne contient pas le moteur et son identification.'
    }
    return $release
}

function Install-Release($Release, [string]$Runtime) {
    Assert-NoLink $Runtime
    $repair = $false
    foreach ($entry in $Release.files) {
        $path = Relative-File $Runtime $entry.path
        Assert-NoLink $path
        try { Assert-File $path $entry.bytes $entry.sha256 }
        catch { Write-Log $_.Exception.Message 'WARN'; $repair = $true; break }
    }
    if (-not $repair) { Write-Log ('Installation verifiee : ' + @($Release.files).Count + ' fichiers.'); return }
    Write-Log 'Preparation automatique des fichiers du depot...'
    $script:stage = Join-Path $script:storage ('.installation-' + [Guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($script:stage) | Out-Null
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    foreach ($package in $Release.packages) {
        Write-Log ('Verification et extraction : ' + $package.id + ', ' + @($package.chunks).Count + ' fragments.')
        $archivePath = Join-Path $script:stage ($package.id + '.pack')
        $outputStream = [IO.File]::Create($archivePath)
        try {
            foreach ($chunk in $package.chunks) {
                $part = Relative-File $script:distribution $chunk.path
                Assert-File $part $chunk.bytes $chunk.sha256
                $inputStream = [IO.File]::OpenRead($part)
                try { $inputStream.CopyTo($outputStream) } finally { $inputStream.Dispose() }
            }
        } finally { $outputStream.Dispose() }
        Assert-File $archivePath $package.bytes $package.sha256
        $archive = [IO.Compression.ZipFile]::OpenRead($archivePath)
        $found = @{}
        try {
            foreach ($member in $archive.Entries) {
                $name = $member.FullName
                if (-not $script:fileIndex.ContainsKey($name) -or $found.ContainsKey($name)) { throw ('Entree inattendue dans ' + $package.id + ' : ' + $name) }
                $entry = $script:fileIndex[$name]
                if ($entry.package -ne $package.id -or $member.Length -ne $entry.bytes) { throw ('Entree incompatible : ' + $name) }
                $destination = Relative-File (Join-Path $script:stage 'files') $name
                [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($destination)) | Out-Null
                $inputStream = $member.Open()
                try {
                    $outputStream = [IO.File]::Create($destination)
                    try { $inputStream.CopyTo($outputStream) } finally { $outputStream.Dispose() }
                } finally { $inputStream.Dispose() }
                Assert-File $destination $entry.bytes $entry.sha256
                $found[$name] = $true
            }
            foreach ($entry in $Release.files) {
                if ($entry.package -eq $package.id -and -not $found.ContainsKey($entry.path)) { throw ('Entree manquante dans le paquet : ' + $entry.path) }
            }
        } finally { $archive.Dispose() }
        Remove-Item -LiteralPath $archivePath
    }
    # Every archive has passed verification before any installed file changes.
    [IO.Directory]::CreateDirectory($Runtime) | Out-Null
    foreach ($entry in $Release.files) {
        $target = Relative-File $Runtime $entry.path
        Assert-NoLink $target
        [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target)) | Out-Null
        [IO.File]::Copy((Relative-File (Join-Path $script:stage 'files') $entry.path), $target, $true)
    }
    Write-Log ('Installation prete : ' + @($Release.files).Count + ' fichiers verifies.')
}

function Select-SaveSource($Release, [string]$Runtime) {
    if (Test-Path -LiteralPath $script:statePath) {
        $previous = [IO.File]::ReadAllText($script:statePath, $script:utf8) | ConvertFrom-Json
        if ($previous.build_id -cnotmatch '^[0-9a-f]{20}$') { throw 'Identification de la partie courante invalide ; sauvegardes conservees.' }
        $source = Join-Path $script:builds $previous.build_id
        if (-not (Test-Path -LiteralPath $source -PathType Container)) { throw ('Ancienne installation absente : ' + $source + '. Aucune nouvelle partie ne sera creee automatiquement.') }
        return $source
    }
    if (Test-Path -LiteralPath (Join-Path $Runtime 'save.bin')) { return $Runtime }
    if ($Admin) { return $Runtime }
    $legacy = Join-Path $script:storage 'windows-fr'
    if (Test-Path -LiteralPath (Join-Path $legacy 'save.bin')) { return $legacy }
    return $Runtime
}

function Import-Progress($Release, [string]$Source, [string]$Runtime) {
    Assert-NoLink $Source
    Assert-GameStopped $Source
    if ([string]::Equals($Source, $Runtime, [StringComparison]::OrdinalIgnoreCase)) { return }
    $sourceSave = Join-Path $Source 'save.bin'
    if (Test-Path -LiteralPath $sourceSave) {
        $identity = [IO.File]::ReadAllText((Join-Path $Source 'universe-install.json'), $script:utf8) | ConvertFrom-Json
        if ($identity.platform -ne 'windows' -or $identity.upstream_release -ne $Release.upstream_release) {
            throw 'Sauvegarde incompatible avec cette version du moteur. Ancienne installation conservee.'
        }
        $script:sourceLock = [IO.File]::Open((Join-Path $Source 'universe-session.lock'), [IO.FileMode]::OpenOrCreate,
            [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
        Backup-Save $Source
        Backup-Save $Runtime
        Atomic-Write (Join-Path $Runtime 'save.bin') ([IO.File]::ReadAllBytes($sourceSave))
        Write-Log ('Partie reprise depuis : ' + $Source + '. Original conserve.')
    }
    foreach ($setting in @('sim_config.ini', 'sim_config_prj.ini')) {
        $oldSetting = Join-Path $Source $setting
        $newSetting = Join-Path $Runtime $setting
        if ((Test-Path -LiteralPath $oldSetting -PathType Leaf) -and -not (Test-Path -LiteralPath $newSetting)) {
            [IO.File]::Copy($oldSetting, $newSetting)
        }
    }
}

function Copy-CampaignToAdmin($Release, [string]$Runtime) {
    $campaignState = Join-Path $script:storage 'windows-current.json'
    if (Test-Path -LiteralPath $campaignState) {
        $campaign = [IO.File]::ReadAllText($campaignState, $script:utf8) | ConvertFrom-Json
        if ($campaign.build_id -cnotmatch '^[0-9a-f]{20}$') { throw 'Identification de campagne invalide.' }
        $source = Join-Path (Join-Path $script:storage 'windows-builds') $campaign.build_id
    } else { $source = Join-Path $script:storage 'windows-fr' }
    if (-not (Test-Path -LiteralPath (Join-Path $source 'save.bin') -PathType Leaf)) {
        throw 'Aucune sauvegarde de campagne a copier. Choisir 2 pour commencer une nouvelle partie admin.'
    }
    # Import-Progress locks the source, validates compatibility and backs up both copies.
    Import-Progress $Release $source $Runtime
    Write-Log 'Copie de campagne dans le profil ADMIN. La campagne originale reste conservee.'
}

function Enable-AdminTools([string]$Runtime) {
    $config = Join-Path $Runtime 'sim_config.ini'
    Assert-NoLink $config
    $text = [IO.File]::ReadAllText($config, $script:utf8)
    # SDL2 SDLK_F10, supported by the pinned libntr PAD/GUIKey parser.
    $text = [regex]::Replace($text, '(?im)^GUIKey=.*(?:\r?\n|$)', '')
    if ($text -match '(?im)^\[PAD\]\s*$') {
        $text = [regex]::Replace($text, '(?im)^\[PAD\]\s*$', "[PAD]`r`nGUIKey=1073741891")
    } else { $text += "`r`n[PAD]`r`nGUIKey=1073741891`r`n" }
    Atomic-Write $config ($script:utf8.GetBytes($text))
    Write-Log 'ADMIN : F10 > Application > Gen Pokemon / Gen Items / Jump to Map / Cheats.'
    Write-Log 'Attendre la carte, fermer les dialogues et menus avant de modifier la partie. Outils limites au contenu natif installe.'
}

function Include-NativeLog([string]$Path, [string]$Name) {
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        Write-Log ('--- ' + $Name + ' : ' + $Path + ' (dernieres 2000 lignes) ---')
        foreach ($line in @(Get-Content -LiteralPath $Path -Tail 2000 -Encoding UTF8)) { Write-Log ([string]$line) 'JEU' }
    }
}

try {
    [IO.Directory]::CreateDirectory($logFolder) | Out-Null
    [IO.File]::WriteAllText($runLog, '', $utf8)
    Write-Log ('Pokemon Universe - Windows - ' + $repository)
    Write-Log ('PowerShell ' + $PSVersionTable.PSVersion + '; OS ' + [Environment]::OSVersion.VersionString + '; processus ' + ([IntPtr]::Size * 8) + ' bits')
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or [IntPtr]::Size -ne 8) { throw 'Windows 64 bits est requis. Utiliser JOUER.bat.' }
    [IO.Directory]::CreateDirectory($storage) | Out-Null
    Assert-NoLink $storage
    $sessionLock = [IO.File]::Open((Join-Path $storage 'universe-windows.lock'), [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    [IO.File]::Copy($runLog, $latestLog, $true)
    $mirrorLog = $true
    if ((Test-Path -LiteralPath (Join-Path $repository '.git')) -and (Get-Command git -ErrorAction SilentlyContinue)) {
        try {
            $revision = & git -C $repository rev-parse HEAD 2>$null
            if ($LASTEXITCODE -eq 0) { Write-Log ('Revision Git : ' + $revision) }
        } catch { Write-Log 'Revision Git indisponible ; poursuite avec le manifeste verifie.' 'WARN' }
    }
    if ($Admin) { Write-Log 'Profil : ADMIN (sauvegarde et reglages separes)' } else { Write-Log 'Profil : CAMPAGNE' }
    $phase = 'distribution'
    $release = Read-Release
    Write-Log ('Version : ' + $release.build_id + '; moteur ' + $release.upstream_release + '; ressources ' + $release.resource_count)
    $runtime = Join-Path $builds $release.build_id
    Assert-GameStopped $runtime
    $phase = 'installation'
    Install-Release $release $runtime
    if ($PrepareOnly) {
        Write-Log 'Verification terminee. Aucun jeu lance, aucune partie importee.'
        $exitStatus = 0
    } else {
        $phase = 'sauvegarde'
        if ($Admin -and $CopyCampaign) { Copy-CampaignToAdmin $release $runtime }
        else {
            $source = Select-SaveSource $release $runtime
            Import-Progress $release $source $runtime
        }
        Backup-Save $runtime
        $config = Join-Path $runtime 'sim_config.ini'
        if (-not (Test-Path -LiteralPath $config)) { [IO.File]::WriteAllText($config, $release.default_config, $utf8) }
        if ($Admin) { Enable-AdminTools $runtime }
        $current = @{schema = 1; build_id = $release.build_id; upstream_release = $release.upstream_release} | ConvertTo-Json
        Atomic-Write $statePath ($utf8.GetBytes($current))
        $phase = 'jeu'
        $stdout = Join-Path $logFolder ('jeu-' + $runId + '.stdout.log')
        $stderr = Join-Path $logFolder ('jeu-' + $runId + '.stderr.log')
        Write-Log ('Demarrage : ' + (Join-Path $runtime 'main.exe'))
        Write-Log ('Dossier de partie : ' + $runtime)
        Write-Log ('Sorties du jeu : ' + $stdout + ' ; ' + $stderr)
        $started = Get-Date
        $gameProcess = Start-Process -FilePath (Join-Path $runtime 'main.exe') -WorkingDirectory $runtime -PassThru -Wait -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        $exitStatus = $gameProcess.ExitCode
        if ($null -eq $exitStatus) { throw 'Le code de sortie du jeu est indisponible.' }
        Write-Log ('Code de sortie du jeu : ' + $exitStatus)
        Include-NativeLog $stdout 'sortie standard'
        Include-NativeLog $stderr 'erreurs natives'
        $debug = Join-Path $runtime 'DbgLog.txt'
        if ((Test-Path -LiteralPath $debug) -and (Get-Item -LiteralPath $debug).LastWriteTime -ge $started) { Include-NativeLog $debug 'DbgLog' }
        $phase = 'sauvegarde'
        Backup-Save $runtime
    }
} catch {
    $exitStatus = 1
    $detail = $_.Exception.ToString() + [Environment]::NewLine + $_.ScriptStackTrace
    try { Write-Log $detail 'ERREUR' } catch { Write-Host $detail }
} finally {
    if ($null -ne $sourceLock) { $sourceLock.Dispose() }
    if ($null -ne $stage -and (Test-Path -LiteralPath $stage)) {
        try { Remove-Item -LiteralPath $stage -Recurse -Force } catch { Write-Host ('Dossier temporaire conserve : ' + $stage) }
    }
    $timer.Stop()
    try { Write-Log ('Fin : code=' + $exitStatus + '; duree=' + [math]::Round($timer.Elapsed.TotalSeconds, 1) + ' s') } catch { }
    Write-Host ('Diagnostic : ' + $runLog)
    if ($mirrorLog) { Write-Host ('A transmettre en cas de probleme : ' + $latestLog) }
    if ($null -ne $sessionLock) { $sessionLock.Dispose() }
}
exit $exitStatus
