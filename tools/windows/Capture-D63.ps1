param(
    [string]$GamePath,
    [string]$Phase = 'manual',
    [int[]]$Indices = @(0, 1, 2048, 2049, 2095, 2096, 4095)
)
$ErrorActionPreference = 'Stop'
try {
    if (-not $GamePath) { $GamePath = Read-Host 'Enter the patched Steam Left 4 Dead 2 folder' }
    $GamePath = (Resolve-Path -LiteralPath $GamePath).Path.TrimEnd('\')
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class D63ReadMemory {
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern IntPtr OpenProcess(uint access, bool inherit, uint pid);
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool ReadProcessMemory(IntPtr process, IntPtr address, byte[] data, UIntPtr size, out UIntPtr read);
    [DllImport("kernel32.dll")]
    public static extern bool CloseHandle(IntPtr handle);
}
'@
    $exe = [IO.Path]::GetFullPath((Join-Path $GamePath 'left4dead2.exe'))
    $games = @(Get-Process left4dead2 -ErrorAction SilentlyContinue | Where-Object { $_.MainModule.FileName -eq $exe })
    if ($games.Count -ne 1) { throw 'Exactly one running patched D63 client is required.' }
    $game = $games[0]
    $client = $game.Modules | Where-Object { $_.FileName -eq (Join-Path $GamePath 'left4dead2\bin\client.dll') } | Select-Object -First 1
    if (-not $client) { throw 'client.dll is not loaded yet.' }
    $clientSha = (Get-FileHash -LiteralPath $client.FileName -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($clientSha -ne '3e5c3f2ee98c2bfa3f3672c654f7ae8b3ae401cc437a08ae1abbe57a6d363943') { throw 'Unexpected client.dll SHA.' }
    $handle = [D63ReadMemory]::OpenProcess(0x410, $false, [uint32]$game.Id)
    if ($handle -eq [IntPtr]::Zero) { throw 'Cannot open the private game for read-only observation.' }
    function Read-D63([long]$Address, [int]$Count) {
        $bytes = New-Object byte[] $Count
        $actual = [UIntPtr]::Zero
        $ok = [D63ReadMemory]::ReadProcessMemory($handle, [IntPtr]$Address, $bytes, [UIntPtr]$Count, [ref]$actual)
        if (-not $ok -or $actual.ToUInt64() -ne $Count) { throw ('Memory read failed at 0x{0:x}' -f $Address) }
        return ,$bytes
    }
    function U32-D63([long]$Address) { return [BitConverter]::ToUInt32((Read-D63 $Address 4), 0) }
    try {
        $base = $client.BaseAddress.ToInt64()
        $list = U32-D63 ($base + 0x6c50ac)
        if ($list -ne ($base + 0x963000)) { throw 'Unexpected entity-list address.' }
        $slots = @()
        foreach ($index in $Indices) {
            if ($index -lt 0 -or $index -ge 8192) { throw 'Entity index outside 0..8191.' }
            $raw = Read-D63 ($list + 4 + 16 * $index) 16
            $ptr = [BitConverter]::ToUInt32($raw, 0)
            $row = [ordered]@{ index = $index; pointer = ('0x{0:x}' -f $ptr); serial = [BitConverter]::ToUInt32($raw, 4) }
            if ($ptr) {
                try {
                    $vt = U32-D63 $ptr
                    $col = U32-D63 ($vt - 4)
                    $offset = U32-D63 ($col + 4)
                    $td = U32-D63 ($col + 12)
                    $name = [Text.Encoding]::ASCII.GetString((Read-D63 ($td + 8) 160)).Split([char]0)[0]
                    $complete = [long]$ptr - $offset
                    $origin = Read-D63 ($complete + 0x124) 12
                    $row['rtti'] = $name
                    $row['complete_object'] = ('0x{0:x}' -f $complete)
                    $row['origin'] = @([BitConverter]::ToSingle($origin, 0), [BitConverter]::ToSingle($origin, 4), [BitConverter]::ToSingle($origin, 8))
                } catch { $row['read_error'] = $_.Exception.Message }
            }
            $slots += [pscustomobject]$row
        }
        $modules = @($game.Modules | Where-Object { $_.ModuleName -in @('engine.dll', 'client.dll') } | ForEach-Object {
            [ordered]@{ path = $_.FileName; base = ('0x{0:x}' -f $_.BaseAddress.ToInt64()); sha256 = (Get-FileHash -LiteralPath $_.FileName -Algorithm SHA256).Hash.ToLowerInvariant() }
        })
        $result = [ordered]@{ schema = 'd63-client-memory-v1'; pid = $game.Id; time = ([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() / 1000.0); phase = $Phase; client_base = ('0x{0:x}' -f $base); client_sha256 = $clientSha; entity_list = ('0x{0:x}' -f $list); modules = $modules; slots = $slots }
        $file = Join-Path $PSScriptRoot ('D63-evidence-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmssfff') + '.json')
        $result | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $file -Encoding UTF8
        Write-Host ('Saved read-only client evidence: ' + $file)
    } finally { [D63ReadMemory]::CloseHandle($handle) | Out-Null }
} catch {
    Write-Host ('ERROR: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
