param(
    [string]$GamePath,
    [string]$TestPath = (Join-Path $env:LOCALAPPDATA 'L4D2-4096-D63'),
    [string]$Server = '47.109.190.101:23067',
    [switch]$PrepareOnly
)
$ErrorActionPreference = 'Stop'

function Get-Sha256([byte[]]$Bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
}

try {
    $manifest = Get-Content (Join-Path $PSScriptRoot 'patches.json') -Raw | ConvertFrom-Json
    if (-not $GamePath) {
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
            if (Test-Path (Join-Path $candidate 'left4dead2.exe')) { $GamePath = $candidate; break }
        }
    }
    if (-not $GamePath) { $GamePath = Read-Host 'Enter the Steam Left 4 Dead 2 folder (contains left4dead2.exe)' }
    $GamePath = (Resolve-Path -LiteralPath $GamePath).Path.TrimEnd('\')
    $TestPath = [IO.Path]::GetFullPath($TestPath).TrimEnd('\')
    if ($TestPath -eq $GamePath -or $TestPath.StartsWith($GamePath + '\', [StringComparison]::OrdinalIgnoreCase) -or
        $TestPath -match '(?i)\\steamapps(?:\\|$)') { throw 'Choose a private test folder outside Steam.' }
    $marker = Join-Path $TestPath '.l4d2-d63-private-copy'
    if ((Test-Path $TestPath) -and -not (Test-Path $marker)) { throw 'Test folder already exists without our private-copy marker. Choose an empty path.' }
    if (Get-Process 'left4dead2' -ErrorAction SilentlyContinue) { throw 'Close Left 4 Dead 2 before preparing the test copy.' }
    # Validate every original before making the private copy. A newer build must fail closed.
    foreach ($image in $manifest.images) {
        $source = Join-Path $GamePath $image.path
        if ((Get-Sha256 ([IO.File]::ReadAllBytes($source))) -ne $image.source_sha256) {
            throw ('Unsupported original file: ' + $image.path + '. No Steam file was modified.')
        }
    }
    Write-Host 'Copying the game to a private test folder. This requires roughly one extra game installation of free disk space.'
    New-Item -ItemType Directory -Path $TestPath -Force | Out-Null
    Set-Content -LiteralPath $marker -Value 'L4D2-4096 D63 private test copy' -Encoding ASCII
    & robocopy $GamePath $TestPath /E /COPY:DAT /DCOPY:T /R:1 /W:1 /XJ /NP /NFL /NDL
    if ($LASTEXITCODE -ge 8) { throw ('Game copy failed, robocopy code ' + $LASTEXITCODE) }
    foreach ($image in $manifest.images) {
        $sourceBytes = [IO.File]::ReadAllBytes((Join-Path $GamePath $image.path))
        if ((Get-Sha256 $sourceBytes) -ne $image.source_sha256) { throw 'Original changed during copying. Try again after Steam finishes updating.' }
        $patched = New-Object byte[] ([int]$image.output_size)
        [Array]::Copy($sourceBytes, $patched, [Math]::Min($sourceBytes.Length, $patched.Length))
        foreach ($hunk in $image.hunks) {
            $offset = [int]$hunk.offset
            $old = [Convert]::FromBase64String($hunk.old)
            $new = [Convert]::FromBase64String($hunk.new)
            for ($i = 0; $i -lt $old.Length; $i++) {
                if ($patched[$offset + $i] -ne $old[$i]) { throw ('Source byte assertion failed: ' + $image.path) }
            }
            [Array]::Copy($new, 0, $patched, $offset, $new.Length)
        }
        if ((Get-Sha256 $patched) -ne $image.output_sha256) { throw ('Patched SHA mismatch: ' + $image.path) }
        [IO.File]::WriteAllBytes((Join-Path $TestPath $image.path), $patched)
        Write-Host ('Verified: ' + $image.path + ' ' + $image.output_sha256)
    }
    # Preserve the copied workshop cache, matching the local D62 recovery condition.
    $addonList = Join-Path $TestPath 'left4dead2\addonlist.txt'
    if (Test-Path $addonList) {
        $text = Get-Content -LiteralPath $addonList -Raw
        $text = [regex]::Replace($text, '("[^"\r\n]+"\s+)"1"', '$1"0"')
        [IO.File]::WriteAllText($addonList, $text)
    }
    # Check source files again so the installation log proves Steam was preserved.
    foreach ($image in $manifest.images) {
        if ((Get-Sha256 ([IO.File]::ReadAllBytes((Join-Path $GamePath $image.path)))) -ne $image.source_sha256) { throw 'Steam original verification failed.' }
    }
    $receipt = [ordered]@{ prepared_utc = [DateTime]::UtcNow.ToString('o'); source = $GamePath; private_copy = $TestPath; server = $Server; images = $manifest.images | Select-Object path, source_sha256, output_sha256 }
    $receipt | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $TestPath 'd63-install-receipt.json') -Encoding UTF8
    Write-Host ('Private test copy ready: ' + $TestPath)
    if (-not $PrepareOnly) {
        $env:SteamAppId = '550'
        $env:SteamGameId = '550'
        Start-Process (Join-Path $TestPath 'left4dead2.exe') -WorkingDirectory $TestPath -ArgumentList @('-steam', '-insecure', '-novid', '-console', '-condebug', '+connect', $Server)
        Write-Host ('Connecting to ' + $Server + '. Keep Steam signed in with your own account.')
    }
} catch {
    Write-Host ('ERROR: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
