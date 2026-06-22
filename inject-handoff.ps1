# inject-handoff.ps1 — SessionStart hook. Always exits 0. Emits {"additionalContext"}
# (UTF-8 no BOM) when a fresh .kt/.pending-handoff exists; otherwise nothing.
try {
    $raw = [Console]::In.ReadToEnd()
    $cwd = (Get-Location).Path
    if ($raw) { try { $j = $raw | ConvertFrom-Json; if ($j.cwd) { $cwd = $j.cwd } } catch {} }

    $sentinel = Join-Path $cwd '.kt/.pending-handoff'
    if (-not (Test-Path -LiteralPath $sentinel)) { exit 0 }

    $lines = @(Get-Content -LiteralPath $sentinel)
    if ($lines.Count -lt 2) {
        Remove-Item -LiteralPath $sentinel -Force -ErrorAction SilentlyContinue; exit 0
    }
    $docPath = $lines[0].Trim()
    $iso = $lines[1].Trim()

    $age = $null
    try { $age = (Get-Date) - ([datetimeoffset]::Parse($iso)).LocalDateTime } catch {
        Remove-Item -LiteralPath $sentinel -Force -ErrorAction SilentlyContinue; exit 0
    }
    if ($age.TotalMinutes -gt 30) {
        Remove-Item -LiteralPath $sentinel -Force -ErrorAction SilentlyContinue; exit 0
    }
    if (-not (Test-Path -LiteralPath $docPath)) {
        Remove-Item -LiteralPath $sentinel -Force -ErrorAction SilentlyContinue; exit 0
    }

    $docLines = @(Get-Content -LiteralPath $docPath)
    # Stub = from "## Resume prompt" up to the 3rd "## " header (Resume, Next action, then stop).
    $start = -1; for ($i=0; $i -lt $docLines.Count; $i++) { if ($docLines[$i] -match '^##\s+Resume prompt') { $start = $i; break } }
    if ($start -lt 0) {
        Remove-Item -LiteralPath $sentinel -Force -ErrorAction SilentlyContinue; exit 0
    }
    $headers = 0; $end = $docLines.Count
    for ($i=$start; $i -lt $docLines.Count; $i++) {
        if ($docLines[$i] -match '^##\s+') { $headers++; if ($headers -eq 3) { $end = $i; break } }
    }
    $stub = ($docLines[$start..($end-1)] -join "`n").Trim()
    $stub = "$stub`n`n(Read .kt/kt.md for the full handoff.)"

    $payload = @{ additionalContext = $stub } | ConvertTo-Json -Compress
    [Console]::Out.Write($payload)

    Remove-Item -LiteralPath $sentinel -Force -ErrorAction SilentlyContinue
    exit 0
}
catch { exit 0 }
