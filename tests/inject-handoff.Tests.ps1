# tests/inject-handoff.Tests.ps1 — standalone, no Pester. Exits 1 on any failure.
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot '..' 'inject-handoff.ps1'
$fails = 0
function Check($name, $cond) {
    if ($cond) { Write-Host "PASS: $name" }
    else { Write-Host "FAIL: $name"; $script:fails++ }
}
# Each case builds a temp project dir with a .kt/ folder, runs the script with
# that dir as cwd (passed via stdin JSON), and captures stdout.
function RunInDir($dir, $stdinJson) {
    Push-Location $dir
    try { $out = $stdinJson | pwsh -NoProfile -File $script 2>$null }
    finally { Pop-Location }
    return $out
}
function NewProj() {
    $d = Join-Path ([System.IO.Path]::GetTempPath()) ("kt-" + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force -Path (Join-Path $d '.kt') | Out-Null
    return $d
}
function WriteSentinel($dir, $docAbs, $iso) {
    Set-Content -LiteralPath (Join-Path $dir '.kt/.pending-handoff') -Value @($docAbs, $iso) -Encoding ascii
}
function WriteDoc($dir) {
    $doc = Join-Path $dir '.kt/kt.md'
    Set-Content -LiteralPath $doc -Encoding utf8 -Value @"
# KT — test  ·  2026-06-22 10:00

## Resume prompt
Resuming work. Read .kt/kt.md for the full handoff.

## Next action
Do the first thing.

## Status
- Done: nothing
"@
    return $doc
}

# Case 1: no sentinel -> empty output, exit 0
$p = NewProj
$out = RunInDir $p (@{cwd=$p} | ConvertTo-Json -Compress)
Check "no sentinel -> no output" ([string]::IsNullOrWhiteSpace($out))

# Case 2: fresh sentinel -> injects stub containing Next action, sentinel deleted
$p = NewProj; $doc = WriteDoc $p
WriteSentinel $p $doc ((Get-Date).ToString('o'))
$out = RunInDir $p (@{cwd=$p} | ConvertTo-Json -Compress)
Check "fresh -> outputs json" ($out -match 'additionalContext')
Check "fresh -> stub has Next action" ($out -match 'Do the first thing')
Check "fresh -> stub omits Status" (-not ($out -match 'nothing'))
Check "fresh -> sentinel deleted" (-not (Test-Path (Join-Path $p '.kt/.pending-handoff')))

# Case 3: stale sentinel (>30 min) -> no output, sentinel deleted
$p = NewProj; $doc = WriteDoc $p
WriteSentinel $p $doc ((Get-Date).AddMinutes(-45).ToString('o'))
$out = RunInDir $p (@{cwd=$p} | ConvertTo-Json -Compress)
Check "stale -> no output" ([string]::IsNullOrWhiteSpace($out))
Check "stale -> sentinel deleted" (-not (Test-Path (Join-Path $p '.kt/.pending-handoff')))

# Case 4: sentinel points to missing doc -> no output, sentinel deleted, exit 0
$p = NewProj
WriteSentinel $p (Join-Path $p '.kt/nope.md') ((Get-Date).ToString('o'))
$out = RunInDir $p (@{cwd=$p} | ConvertTo-Json -Compress)
Check "missing doc -> no output" ([string]::IsNullOrWhiteSpace($out))
Check "missing doc -> sentinel deleted" (-not (Test-Path (Join-Path $p '.kt/.pending-handoff')))

# Case 5: malformed sentinel -> no crash, no output, exit 0
$p = NewProj
Set-Content -LiteralPath (Join-Path $p '.kt/.pending-handoff') -Value "garbage" -Encoding ascii
$out = RunInDir $p (@{cwd=$p} | ConvertTo-Json -Compress)
Check "malformed -> no output" ([string]::IsNullOrWhiteSpace($out))

# Case 6: output is valid JSON with no BOM
$p = NewProj; $doc = WriteDoc $p
WriteSentinel $p $doc ((Get-Date).ToString('o'))
$out = RunInDir $p (@{cwd=$p} | ConvertTo-Json -Compress)
$parsed = $null
try { $parsed = $out | ConvertFrom-Json } catch {}
Check "output parses as JSON" ($null -ne $parsed -and $parsed.additionalContext)
Check "output has no BOM" (-not $out.StartsWith([char]0xFEFF))

if ($fails -gt 0) { Write-Host "`n$fails FAILED"; exit 1 } else { Write-Host "`nALL PASS"; exit 0 }
