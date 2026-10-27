param(
    [string]$GamePath,
    [string]$RepoPath = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent),
    [string]$Server = '47.109.190.101:23067',
    [switch]$PrepareOnly,
    [switch]$Restore
)
$ErrorActionPreference = 'Stop'

function Find-GamePath {
    $steam = (Get-ItemProperty 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue).SteamPath
    $libraries = @($steam)
    if ($steam -and (Test-Path (Join-Path $steam 'steamapps\libraryfolders.vdf'))) {
        $vdf = Get-Content (Join-Path $steam 'steamapps\libraryfolders.vdf') -Raw
        foreach ($m in [regex]::Matches($vdf, '"path"\s+"([^"]+)"')) {
            $libraries += $m.Groups[1].Value.Replace('\\', '\')
        }
    }
    foreach ($library in ($libraries | Select-Object -Unique)) {
        if (-not $library) { continue }
        $candidate = Join-Path $library 'steamapps\common\Left 4 Dead 2'
        if (Test-Path (Join-Path $candidate 'left4dead2.exe')) { return $candidate }
    }
    return $null
}

try {
    if (-not $GamePath) { $GamePath = Find-GamePath }
    if (-not $GamePath) { $GamePath = Read-Host 'Enter the Steam Left 4 Dead 2 folder (contains left4dead2.exe)' }
    $GamePath = (Resolve-Path -LiteralPath $GamePath).Path.TrimEnd('\')
    $RepoPath = (Resolve-Path -LiteralPath $RepoPath).Path.TrimEnd('\')
    $manifest = Join-Path $RepoPath 'release\manifests\windows-client.json'
    $installer = Join-Path $RepoPath 'tools\release\install.py'
    if (-not (Test-Path (Join-Path $GamePath 'left4dead2.exe'))) { throw 'GamePath does not contain left4dead2.exe.' }
    if (-not (Test-Path $manifest) -or -not (Test-Path $installer)) { throw 'RepoPath must point to the l4d2-entity-4096 clone.' }
    if (Get-Process 'left4dead2' -ErrorAction SilentlyContinue) { throw 'Close Left 4 Dead 2 before changing its modules.' }

    $py = Get-Command py -ErrorAction SilentlyContinue
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        $pythonCommand = $py.Source
        $pythonArgs = @('-3')
        $pythonLabel = 'py -3'
    } elseif ($python) {
        $pythonCommand = $python.Source
        $pythonArgs = @()
        $pythonLabel = 'python'
    } else {
        throw 'Python 3 is required. Install Python or use the repository environment.'
    }

    if ($Restore) {
        $receipt = Join-Path $GamePath 'l4d2-4096-install.json'
        if (-not (Test-Path $receipt)) { throw 'No in-place install receipt was found in GamePath.' }
        & $pythonCommand @pythonArgs $installer restore --receipt $receipt
    } else {
        Write-Host "Patching only the manifest modules in $GamePath with $pythonLabel. No game copy is created."
        & $pythonCommand @pythonArgs $installer install --manifest $manifest --game $GamePath
        if ($LASTEXITCODE -ne 0) { throw "Installer failed with exit code $LASTEXITCODE." }
    }
    if ($LASTEXITCODE -ne 0) { throw "Installer failed with exit code $LASTEXITCODE." }
    if ($Restore -or $PrepareOnly) { exit 0 }

    $env:SteamAppId = '550'
    $env:SteamGameId = '550'
    Start-Process (Join-Path $GamePath 'left4dead2.exe') -WorkingDirectory $GamePath -ArgumentList @('-steam', '-insecure', '-novid', '-console', '-condebug', '+connect', $Server)
    Write-Host ('Patched Steam game started; connecting to ' + $Server)
} catch {
    Write-Host ('ERROR: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
