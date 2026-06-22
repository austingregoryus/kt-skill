# spikes/probe-sessionstart.ps1 — logs the SessionStart stdin payload, injects nothing.
$raw = [Console]::In.ReadToEnd()
$logDir = Join-Path $PSScriptRoot 'out'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
Set-Content -LiteralPath (Join-Path $logDir "probe-$stamp.json") -Value $raw -Encoding utf8
exit 0
