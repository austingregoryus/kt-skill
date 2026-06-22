# /kt Knowledge-Transfer Skill — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `/kt` Claude Code skill that writes a timestamped handoff doc capturing current working state, prints a thin resume prompt, and ships an opt-in `SessionStart` hook that auto-injects the handoff stub into the next context after `/clear`.

**Architecture:** The repo at `C:\Projects\kt-skill` is the skill source. `SKILL.md` holds LLM instructions for the `/kt` behaviors (write doc, toggle git mode, cancel). A bundled `inject-handoff.ps1` (+ POSIX `inject-handoff.sh`) is the deterministic hook script — it is the only code with automated tests. A final task installs the skill into `~/.claude/skills/kt`. Handoffs live in each consuming project's `.kt/` folder.

**Tech Stack:** Markdown (SKILL.md), PowerShell 7 (`pwsh`) for the primary hook script + tests, POSIX `sh` for the cross-platform hook variant, git for commits.

## Global Constraints

- Skill installed at `~/.claude/skills/kt/SKILL.md` with frontmatter `name: kt` (invokes as `/kt`).
- Handoff docs: `.kt/kt-YYYYMMDD-HHMMSS.md` (seconds precision, immutable) + `.kt/kt.md` (latest copy, stable path).
- Sentinel `.kt/.pending-handoff`: two lines — line 1 = absolute path to `.kt/kt.md`, line 2 = ISO-8601 timestamp.
- Hook freshness guard: ignore + delete sentinel if older than **30 minutes**.
- Hook **always exits 0**; injects nothing on any error.
- Hook stdout: UTF-8 **without BOM**, JSON only (`{"additionalContext": "..."}`).
- Hook injects a **stub** (Resume prompt + Next action only), not the full doc.
- Hook installed **project-scoped** (`.claude/settings.json`), never global `~/.claude`.
- Hook command: `pwsh -NoProfile -File <skill_dir>/inject-handoff.ps1` (POSIX users use `inject-handoff.sh`).
- git tracking default **local-only** (auto-gitignore `.kt/`); `/kt --share` / `/kt --local` toggle via `.kt/.shared` marker.
- No external CLI deps in the hook script: no `jq`, no Pester (tests are plain `pwsh`).

---

### Task 0: Initialize repository

**Files:**
- Create: `C:\Projects\kt-skill\.gitignore`
- Create: `C:\Projects\kt-skill\README.md`

- [ ] **Step 1: Initialize git**

Run:
```bash
cd /c/Projects/kt-skill && git init && git config user.name "$(git config --global user.name || echo dev)" >/dev/null 2>&1; true
```
Expected: `Initialized empty Git repository in C:/Projects/kt-skill/.git/`

- [ ] **Step 2: Create `.gitignore`**

```
# transient test fixtures
tmp/
*.tmp
```

- [ ] **Step 3: Create `README.md`**

```markdown
# kt — Knowledge-Transfer skill

Source for the `/kt` Claude Code skill. See `docs/superpowers/specs/` for the
design and `docs/superpowers/plans/` for the build plan. Install with the
steps in `SKILL.md` (final task: copy this folder to `~/.claude/skills/kt`).
```

- [ ] **Step 4: Commit**

```bash
cd /c/Projects/kt-skill && git add -A && git commit -m "chore: initialize kt-skill repo"
```
Expected: commit succeeds with 3+ files.

---

### Task 1: Spike — verify SessionStart fires on `/clear`

This de-risks the entire hook feature before any hook code is written. It produces a documented finding, not shipping code.

**Files:**
- Create: `C:\Projects\kt-skill\spikes\probe-sessionstart.ps1`
- Create: `C:\Projects\kt-skill\spikes\FINDINGS.md`

**Interfaces:**
- Produces: a documented boolean — does `SessionStart` fire with `source: "clear"` on this Claude Code version — consumed by Task 5 (hook install docs) to confirm or adjust the documented flow.

- [ ] **Step 1: Write the probe hook script**

```powershell
# spikes/probe-sessionstart.ps1 — logs the SessionStart stdin payload, injects nothing.
$raw = [Console]::In.ReadToEnd()
$logDir = Join-Path $PSScriptRoot 'out'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
Set-Content -LiteralPath (Join-Path $logDir "probe-$stamp.json") -Value $raw -Encoding utf8
exit 0
```

- [ ] **Step 2: Document the manual probe procedure in FINDINGS.md**

```markdown
# SessionStart probe findings

## Procedure
1. In a throwaway project, add to `.claude/settings.json`:
   {"hooks":{"SessionStart":[{"hooks":[{"type":"command",
     "command":"pwsh -NoProfile -File C:/Projects/kt-skill/spikes/probe-sessionstart.ps1"}]}]}}
2. Start a session, then run `/clear`.
3. Inspect `spikes/out/*.json` for the `source` field.

## Result
- Fires on startup: <YES/NO>
- Fires on /clear with source="clear": <YES/NO — FILL IN AFTER RUNNING>

## Decision
- If source="clear" fires: ship the documented `/kt` -> `/clear` -> type flow as-is.
- If it does NOT: document that the handoff injects on the NEXT full session
  start instead, and note `/clear` alone may not trigger it.
```

- [ ] **Step 3: Run the probe and record the result**

This step is manual (the user runs `/clear`). The implementer fills in the `<YES/NO>` blanks in `FINDINGS.md` from `spikes/out/*.json`. Do not proceed to fabricate a result — if it cannot be run in this environment, mark the result `UNVERIFIED — must confirm before relying on /clear trigger` and continue (the hook still works on full session start).

- [ ] **Step 4: Commit**

```bash
cd /c/Projects/kt-skill && git add spikes/ && git commit -m "spike: probe SessionStart on /clear"
```

---

### Task 2: Hook script — `inject-handoff.ps1` (TDD)

The deterministic core. Built test-first with a standalone pwsh test runner (no Pester).

**Files:**
- Create: `C:\Projects\kt-skill\inject-handoff.ps1`
- Test: `C:\Projects\kt-skill\tests\inject-handoff.Tests.ps1`

**Interfaces:**
- Consumes: a `.kt/.pending-handoff` sentinel (line 1 = abs path to doc, line 2 = ISO-8601 timestamp) and the doc it points to; SessionStart JSON on stdin (uses `.cwd` if present).
- Produces: on stdout, either nothing (no/stale/broken sentinel) or `{"additionalContext":"<stub>"}` as UTF-8-no-BOM JSON. Always exit 0. Deletes the sentinel after a successful or stale read.

- [ ] **Step 1: Write the failing test runner**

```powershell
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
```

- [ ] **Step 2: Run the test to verify it fails (script doesn't exist yet)**

Run:
```bash
pwsh -NoProfile -File /c/Projects/kt-skill/tests/inject-handoff.Tests.ps1
```
Expected: FAIL — cases error/fail because `inject-handoff.ps1` does not exist yet (exit 1).

- [ ] **Step 3: Write `inject-handoff.ps1`**

```powershell
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
pwsh -NoProfile -File /c/Projects/kt-skill/tests/inject-handoff.Tests.ps1
```
Expected: `ALL PASS`, exit 0.

- [ ] **Step 5: Commit**

```bash
cd /c/Projects/kt-skill && git add inject-handoff.ps1 tests/inject-handoff.Tests.ps1 && git commit -m "feat: add inject-handoff.ps1 hook with tests"
```

---

### Task 3: POSIX hook variant — `inject-handoff.sh`

Mirror of the PowerShell script for non-Windows users. Tested with a parallel sh-based runner.

**Files:**
- Create: `C:\Projects\kt-skill\inject-handoff.sh`
- Test: `C:\Projects\kt-skill\tests\inject-handoff.sh.test.sh`

**Interfaces:**
- Consumes/Produces: identical contract to `inject-handoff.ps1`. No `jq` — JSON is emitted by hand with a sed-based escaper.

- [ ] **Step 1: Write the failing sh test**

```bash
#!/usr/bin/env bash
# tests/inject-handoff.sh.test.sh — no bats, plain bash. Exit 1 on any failure.
set -u
SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/inject-handoff.sh"
fails=0
check() { if eval "$2"; then echo "PASS: $1"; else echo "FAIL: $1"; fails=$((fails+1)); fi; }
newproj() { d="$(mktemp -d)"; mkdir -p "$d/.kt"; echo "$d"; }
writedoc() {
  cat > "$1/.kt/kt.md" <<'EOF'
# KT — test

## Resume prompt
Resuming. Read .kt/kt.md.

## Next action
Do the first thing.

## Status
- Done: nothing
EOF
}
run() { printf '{"cwd":"%s"}' "$1" | sh "$SCRIPT"; }

# Case 1: no sentinel -> empty
p="$(newproj)"; out="$(run "$p")"
check "no sentinel -> empty" '[ -z "$out" ]'

# Case 2: fresh -> json with Next action, sentinel deleted
p="$(newproj)"; writedoc "$p"
printf '%s\n%s\n' "$p/.kt/kt.md" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$p/.kt/.pending-handoff"
out="$(run "$p")"
check "fresh -> has additionalContext" 'echo "$out" | grep -q additionalContext'
check "fresh -> has Next action text" 'echo "$out" | grep -q "Do the first thing"'
check "fresh -> sentinel deleted" '[ ! -f "$p/.kt/.pending-handoff" ]'

# Case 3: stale (>30m) -> empty, deleted
p="$(newproj)"; writedoc "$p"
old="$(date -u -d '-45 min' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-45M +%Y-%m-%dT%H:%M:%SZ)"
printf '%s\n%s\n' "$p/.kt/kt.md" "$old" > "$p/.kt/.pending-handoff"
out="$(run "$p")"
check "stale -> empty" '[ -z "$out" ]'
check "stale -> deleted" '[ ! -f "$p/.kt/.pending-handoff" ]'

# Case 4: missing doc -> empty, deleted
p="$(newproj)"
printf '%s\n%s\n' "$p/.kt/nope.md" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$p/.kt/.pending-handoff"
out="$(run "$p")"
check "missing doc -> empty" '[ -z "$out" ]'

if [ "$fails" -gt 0 ]; then echo "$fails FAILED"; exit 1; else echo "ALL PASS"; exit 0; fi
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```bash
bash /c/Projects/kt-skill/tests/inject-handoff.sh.test.sh
```
Expected: FAIL — `inject-handoff.sh` does not exist (exit 1).

- [ ] **Step 3: Write `inject-handoff.sh`**

```bash
#!/usr/bin/env sh
# inject-handoff.sh — POSIX SessionStart hook. Always exits 0.
# Emits {"additionalContext":"..."} on stdout when a fresh sentinel exists.
raw="$(cat)"
cwd="$(echo "$raw" | sed -n 's/.*"cwd"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
[ -z "$cwd" ] && cwd="$(pwd)"
sentinel="$cwd/.kt/.pending-handoff"
[ -f "$sentinel" ] || exit 0

doc="$(sed -n '1p' "$sentinel")"
iso="$(sed -n '2p' "$sentinel")"
[ -n "$doc" ] && [ -n "$iso" ] || { rm -f "$sentinel"; exit 0; }

# Freshness: 30 min. Convert ISO to epoch; bail to delete on parse failure.
now=$(date -u +%s)
then=$(date -u -d "$iso" +%s 2>/dev/null || date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$iso" +%s 2>/dev/null)
[ -n "$then" ] || { rm -f "$sentinel"; exit 0; }
age=$(( (now - then) / 60 ))
[ "$age" -gt 30 ] && { rm -f "$sentinel"; exit 0; }
[ -f "$doc" ] || { rm -f "$sentinel"; exit 0; }

# Stub = from "## Resume prompt" through the line before the 3rd "## " header.
stub="$(awk '
  /^##[[:space:]]+Resume prompt/ {grab=1}
  grab {
    if (/^##[[:space:]]/) {h++; if (h==3) exit}
    print
  }' "$doc")"
[ -n "$stub" ] || { rm -f "$sentinel"; exit 0; }
stub="$stub

(Read .kt/kt.md for the full handoff.)"

# JSON-escape: backslash, double-quote, then newlines -> \n.
esc="$(printf '%s' "$stub" | sed 's/\\/\\\\/g; s/"/\\"/g' | awk '{printf "%s\\n", $0}')"
printf '{"additionalContext":"%s"}' "$esc"
rm -f "$sentinel"
exit 0
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```bash
bash /c/Projects/kt-skill/tests/inject-handoff.sh.test.sh
```
Expected: `ALL PASS`, exit 0.

- [ ] **Step 5: Commit**

```bash
cd /c/Projects/kt-skill && git add inject-handoff.sh tests/inject-handoff.sh.test.sh && git commit -m "feat: add POSIX inject-handoff.sh variant with tests"
```

---

### Task 4: Author `SKILL.md` — the `/kt` behavior

The skill body: LLM instructions for the `/kt` command and its flags. Not unit-tested (it is instructions to a model); validated by the acceptance scenarios in Task 6.

**Files:**
- Create: `C:\Projects\kt-skill\SKILL.md`

**Interfaces:**
- Consumes: conversation context, git CLI (optional), todo list, `inject-handoff.ps1`/`.sh` (referenced in hook-install docs).
- Produces: `.kt/kt-YYYYMMDD-HHMMSS.md`, `.kt/kt.md`, `.kt/.pending-handoff`, `.kt/.shared` (when shared), `.gitignore` entry; a printed resume prompt.

- [ ] **Step 1: Write `SKILL.md`**

````markdown
---
name: kt
description: Knowledge-Transfer handoff. Use when the user runs /kt or wants to snapshot current working state into a kt.md handoff doc and a resume prompt so a fresh (post-/clear) context can pick up the work. Lightweight alternative to /compact.
---

# /kt — Knowledge Transfer

Snapshot the current working state into a timestamped handoff doc, refresh the
stable `.kt/kt.md`, drop a one-shot sentinel for the optional auto-injection
hook, and print a thin resume prompt the user can paste into a fresh context.

## Argument parsing

Read the text after `/kt`:
- `--share` → enable shareable/git-tracked mode (see "git tracking"), then STOP (no new handoff unless other text is also present).
- `--local` → restore local-only mode, then STOP.
- `--cancel` → delete `.kt/.pending-handoff` if present, report done, then STOP.
- anything else → treat the whole string as the handoff **headline note**.
- empty → derive the headline (see below).

## Headline derivation (when no note given)

In priority order: (1) the active/most-recent todo title, else (2) a one-line
restatement of the user's last stated goal.

## Steps when writing a handoff

1. **Gather signals** (each optional; skip silently if unavailable — never error):
   - `git rev-parse --abbrev-ref HEAD` → branch
   - `git status -s` → uncommitted changes (filter out any line under `.kt/`)
   - `git log -5 --oneline` → recent commits
   - the current todo list
2. **Synthesize** the doc below from the conversation + signals. Omit any
   section that would be empty. Keep it lean — this is a handoff, not a report.
3. **Compute timestamp** `YYYYMMDD-HHMMSS` (local time). Create `.kt/` if missing.
4. **Write** `.kt/kt-<timestamp>.md` with the structure below, then copy it to
   `.kt/kt.md` (overwrite).
5. **git mode:** if `.kt/.shared` does NOT exist, ensure `.kt/` is ignored —
   add a line `.kt/` to the repo's `.gitignore` (create it if absent; if not a
   git repo, skip). If `.kt/.shared` exists, do not touch git ignore rules.
6. **Drop sentinel** `.kt/.pending-handoff` with exactly two lines:
   line 1 = absolute path to `.kt/kt.md`; line 2 = ISO-8601 timestamp (e.g.
   the output of an `o`-format date). Overwrite if present.
7. **Print the resume prompt** (the exact "## Resume prompt" block) to chat so
   the user can copy it.

If `.kt/` cannot be written, tell the user plainly AND still print the resume
prompt to chat so nothing is lost.

## Document structure

Write sections in this order; omit any that are empty. The **Resume prompt**
and **Next action** sections MUST come first and in this order (the hook
extracts everything from "## Resume prompt" up to the third `##` header).

```
# KT — <headline>  ·  <YYYY-MM-DD HH:MM>

## Resume prompt
Resuming work. Read `.kt/kt.md` for the full handoff.
TL;DR: <headline>. Next: <next action>.
Start by <next action>, then continue.

## Next action
<the single most important first thing the next context should do>

## Status
- Done: ...
- In progress: ...
- Not started: ...

## Mental model
<current hypothesis/understanding — include ONLY if there is a real one>

## Decisions + rationale
- <decision> — <why>

## Dead ends
- <thing tried> — <why it failed / don't repeat>

## Key files
- path/to/file — <one-line why it matters>

## Signals (auto)
- Branch: <branch>
- Uncommitted: <git status -s, or "clean">
- Recent commits:
  - <git log -5 --oneline>
- Todos: <current todos, or omit>
```

## git tracking

Default is **local-only**: `.kt/` is gitignored, handoffs are personal scratch.
- `/kt --share`: remove the `.kt/` line from `.gitignore` (if present) and
  create an empty `.kt/.shared` marker. Report that handoffs are now tracked.
- `/kt --local`: delete `.kt/.shared` and re-add `.kt/` to `.gitignore`.
The mode is sticky per-project via the presence of `.kt/.shared`.

## Optional auto-injection hook

Removes the copy-paste step: after `/kt` then `/clear`, the next context is
auto-fed the handoff stub. Cannot be fully automatic — `/clear` is user-driven.

To enable, add this to the **project's** `.claude/settings.json` (NOT global):

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [
        { "type": "command",
          "command": "pwsh -NoProfile -File ~/.claude/skills/kt/inject-handoff.ps1" }
      ] }
    ]
  }
}
```

POSIX users: use `~/.claude/skills/kt/inject-handoff.sh` instead.

The hook reads `.kt/.pending-handoff`, injects the Resume prompt + Next action
stub (only when fresh, within 30 min), and deletes the sentinel — firing at
most once per `/kt`. It always exits 0 and injects nothing on any error.

**Flow:** `/kt` → `/clear` → start typing.

**Known limit:** the sentinel is a single per-project flag; with concurrent
sessions in one repo, the first new session consumes it.
````

- [ ] **Step 2: Validate frontmatter and structure**

Run:
```bash
pwsh -NoProfile -Command "$c = Get-Content -Raw 'C:/Projects/kt-skill/SKILL.md'; if ($c -match '(?s)^---\s*\nname: kt\s*\ndescription: .+?\n---' ) { 'frontmatter ok' } else { 'BAD frontmatter'; exit 1 }; foreach ($h in '## Resume prompt','## Next action','## git tracking','## Optional auto-injection hook') { if ($c -notmatch [regex]::Escape($h)) { \"missing $h\"; exit 1 } }; 'sections ok'"
```
Expected: `frontmatter ok` then `sections ok`.

- [ ] **Step 3: Commit**

```bash
cd /c/Projects/kt-skill && git add SKILL.md && git commit -m "feat: author kt SKILL.md behavior"
```

---

### Task 5: Hook-install reference + spike finding reconciliation

Bundle a copy-pasteable settings snippet and reconcile the documented flow with the Task 1 spike result.

**Files:**
- Create: `C:\Projects\kt-skill\hooks-settings.example.json`
- Modify: `C:\Projects\kt-skill\SKILL.md` (only if the spike showed `/clear` does NOT fire SessionStart)

**Interfaces:**
- Consumes: `spikes/FINDINGS.md` result from Task 1.

- [ ] **Step 1: Create the example settings file**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "pwsh -NoProfile -File ~/.claude/skills/kt/inject-handoff.ps1"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Reconcile with spike finding**

Read `spikes/FINDINGS.md`. If the result is `source="clear" fires: YES`, no SKILL.md change needed. If `NO` or `UNVERIFIED`, edit the SKILL.md "Optional auto-injection hook" section to add this line verbatim:

```
NOTE: On this version, /clear may not trigger SessionStart; the stub then
injects on your next full session start instead. The printed resume prompt is
always available as an immediate fallback.
```

- [ ] **Step 3: Validate the JSON parses**

Run:
```bash
pwsh -NoProfile -Command "Get-Content -Raw 'C:/Projects/kt-skill/hooks-settings.example.json' | ConvertFrom-Json | Out-Null; 'json ok'"
```
Expected: `json ok`.

- [ ] **Step 4: Commit**

```bash
cd /c/Projects/kt-skill && git add hooks-settings.example.json SKILL.md && git commit -m "docs: bundle hook settings example and reconcile spike finding"
```

---

### Task 6: End-to-end acceptance scenarios

Manual, scripted verification that the whole skill behaves. Produces a checklist doc with recorded results; no shipping code.

**Files:**
- Create: `C:\Projects\kt-skill\tests\acceptance.md`

- [ ] **Step 1: Write the acceptance checklist**

```markdown
# kt acceptance scenarios

Run each in a throwaway git repo with the skill installed (see Task 7).

## A. Basic handoff (local mode, default)
- [ ] Run `/kt fixing the login bug`.
- [ ] `.kt/kt-<ts>.md` exists; `.kt/kt.md` is an identical copy.
- [ ] Headline is "fixing the login bug"; Resume prompt + Next action present.
- [ ] `.kt/.pending-handoff` has 2 lines (abs path, ISO timestamp).
- [ ] `.gitignore` contains `.kt/`; `git status` does not list `.kt/`.
- [ ] Resume prompt was printed to chat.

## B. Hook injection
- [ ] Enable the hook (project .claude/settings.json from hooks-settings.example.json).
- [ ] Run `/kt`, then `/clear`. New context receives the stub (Resume prompt + Next action), NOT the whole doc.
- [ ] `.kt/.pending-handoff` is gone after injection.
- [ ] Start another new session with no prior `/kt`: nothing is injected.

## C. Freshness guard
- [ ] Run `/kt`, hand-edit the sentinel timestamp to 45 min ago, start a new session.
- [ ] Nothing injected; sentinel deleted.

## D. Share / local toggle
- [ ] `/kt --share`: `.kt/.shared` created, `.kt/` removed from `.gitignore`.
- [ ] `/kt --local`: `.kt/.shared` gone, `.kt/` back in `.gitignore`.

## E. Cancel
- [ ] `/kt`, then `/kt --cancel`: `.kt/.pending-handoff` deleted, no new doc written.

## F. No-git fallback
- [ ] In a non-git folder, `/kt` still writes `.kt/` docs without error; git steps skipped.
```

- [ ] **Step 2: Run the unit suites as a pre-acceptance gate**

Run:
```bash
pwsh -NoProfile -File /c/Projects/kt-skill/tests/inject-handoff.Tests.ps1 && bash /c/Projects/kt-skill/tests/inject-handoff.sh.test.sh
```
Expected: both print `ALL PASS`.

- [ ] **Step 3: Commit**

```bash
cd /c/Projects/kt-skill && git add tests/acceptance.md && git commit -m "test: add end-to-end acceptance checklist"
```

---

### Task 7: Install the skill

Deploy the repo into the Claude Code skills directory so `/kt` is live.

**Files:**
- Create: `~/.claude/skills/kt/` (SKILL.md + inject-handoff.ps1 + inject-handoff.sh)

- [ ] **Step 1: Copy skill files into place**

Run:
```bash
mkdir -p ~/.claude/skills/kt && cp /c/Projects/kt-skill/SKILL.md /c/Projects/kt-skill/inject-handoff.ps1 /c/Projects/kt-skill/inject-handoff.sh ~/.claude/skills/kt/
```
Expected: no output (success).

- [ ] **Step 2: Verify install**

Run:
```bash
ls ~/.claude/skills/kt/
```
Expected: `SKILL.md  inject-handoff.ps1  inject-handoff.sh`

- [ ] **Step 3: Confirm the skill is discoverable**

The skill appears as `/kt` in a fresh Claude Code session (frontmatter `name: kt`). This is verified by the user starting a new session and running `/kt` per Task 6 scenario A. Record the result in `tests/acceptance.md`.

- [ ] **Step 4: Commit the installation note**

```bash
cd /c/Projects/kt-skill && git add -A && git commit -m "chore: install kt skill to ~/.claude/skills/kt" --allow-empty
```

---

## Self-Review

**Spec coverage:**
- Invocation `/kt [note]`, `--share`/`--local`, `--cancel` → Task 4 (SKILL.md arg parsing).
- Headline derivation → Task 4.
- Auto-gather git + todo signals, filter `.kt/` from status → Task 4 step 1.
- Doc structure + lean/omit-empty + Mental-model-conditional → Task 4 doc structure.
- Timestamped immutable docs (seconds) + stable `kt.md` → Task 4 steps 3-4; constraint section.
- Sentinel (abs path + ISO timestamp) → Task 4 step 6; consumed in Tasks 2/3.
- Resume prompt (thin pointer) printed + stored → Task 4 doc structure + step 7.
- git tracking configurable (default local, `.shared` marker) → Task 4 git tracking.
- Hook: project-scoped, freshness 30m, exit 0, UTF-8 no BOM, stub injection, Windows pwsh cmd + sh variant → Tasks 2, 3, 5; SKILL.md hook section.
- Verify-first spike → Task 1.
- Edge cases (no git, no todos, write failure, stale sentinel, concurrent sessions) → Task 4 + Tasks 2/3 tests + acceptance F/C.
- Install location `~/.claude/skills/kt` name `kt` → Task 7 + Task 4 frontmatter.

**Placeholder scan:** No TBD/TODO in shipping steps. The only intentional fill-in is the spike RESULT in Task 1 (a genuine empirical measurement, not a code placeholder) and the conditional SKILL.md note in Task 5 (verbatim text supplied).

**Type/name consistency:** sentinel format (line1 abs path, line2 ISO) consistent across Tasks 2, 3, 4. Stub extraction rule ("from `## Resume prompt` to 3rd `##`") identical in ps1 (Task 2), sh (Task 3), and documented in SKILL.md (Task 4). Hook command string identical in SKILL.md and `hooks-settings.example.json`. File paths consistent throughout.
