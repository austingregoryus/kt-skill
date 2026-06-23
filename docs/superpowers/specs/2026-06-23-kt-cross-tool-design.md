# Cross-Tool KT — Design

**Date:** 2026-06-23 (rev 2 — incorporates architecture + platform review)
**Status:** Approved design, ready for implementation plan
**Builds on:** `2026-06-22-kt-knowledge-transfer-design.md` (the original single-tool `/kt`)

## Goal

Turn `/kt` from a Claude-Code-only skill into a tool-neutral knowledge-transfer
standard so work can hand off **bidirectionally** between AI coding tools
(Claude Code, Codex CLI, Antigravity CLI, and any tool with shell + file
access). When one tool runs out of usage or context, you switch to another and
resume exactly where you left off.

The `.kt/` folder and `kt.md` format are plain markdown — platform neutral by
construction. This project moves all *mechanical* logic into one shared Python
engine and gives each tool a thin shim. **All three named tools now use the
same `SKILL.md` open standard**, so the shims are one format in three
locations, not four bespoke formats.

> **UX caveat (to be resolved by Spike 0):** "run `/kt-resume` in any tool" is
> confirmed for Claude Code and Codex CLI. Antigravity CLI's skill invocation
> may be **conversational-only** (no `/name` slash). Spike 0 verifies this; if
> slash invocation is unavailable, the Antigravity shim ships with a documented
> "ask the agent to resume KT" trigger instead of a slash command.

## Architecture (shared engine + thin shims)

```
        ┌──────────── per-tool shims (all SKILL.md; generic = none) ───────────┐
        │  Claude skill     Codex skill      Antigravity skill   generic       │
        │  /kt /kt-resume   /kt /kt-resume   (slash TBD, Spike0) `kt …` direct  │
        └───────────────────────────────┬─────────────────────────────────────┘
                                         │ all shell out to
                                ┌────────▼─────────┐
                                │  kt engine        │  ~/.kt/kt.py (on PATH as `kt`)
                                │  Python 3 stdlib  │
                                │  save resume format│
                                │  inject list cancel│
                                │  share local       │
                                └────────┬─────────┘
                                         │ reads/writes
                                ┌────────▼─────────┐
                                │  .kt/  (per repo)  │  tool-neutral interchange
                                │  kt.md, kt-<ts>.md │
                                │  .pending-handoff  │
                                │  .shared           │
                                └──────────────────┘
```

**Division of labor (the engine does NO body parsing on save):**
- **LLM (via shim):** authors the *entire* handoff body following `kt format` —
  the `## Resume prompt` block, Next action, Status, Mental model (if any),
  Decisions, Dead ends, Key files, and the `## Signals (auto)` section (the LLM
  runs git itself, as the original skill did). The model is the only thing that
  can write judgment content, and having it own the whole body removes every
  fragile "engine parses LLM markdown" path.
- **Engine (deterministic):** prepends the one header line it fully controls,
  persists files, manages the sentinel, gitignore, provenance, resume
  discovery, and the SessionStart stub injection. The only place the engine
  reads body content is `kt inject`, which extracts a single **named** section.

## Engine: `kt` (Python 3, stdlib only)

Installed at `~/.kt/kt.py`, invokable as `kt` (see Installer). Python chosen
over parallel `.ps1`+`.sh` so there is ONE implementation that runs identically
in every shell. No third-party dependencies.

Every subcommand accepts `--cwd DIR` (default `os.getcwd()`) and operates on
that directory's `.kt/` folder, creating it when needed. All writes are UTF-8
**without BOM**, `\n` line endings.

### One shared primitive: `section(body, name)`

A single internal helper used wherever a section must be located (only
`kt inject` needs it):
> A section named `X` starts at a line matching `^## X\s*$` and runs until the
> next line matching `^## ` or EOF. Returns the lines between (exclusive of the
> next header). Defined once; never reimplemented.

### `kt save`

```
kt save --tool NAME --note "HEADLINE" [--cwd DIR]
```
- Reads the **complete handoff body from stdin** (LLM-authored per
  `kt format`; begins at `## Resume prompt`).
- Computes a local timestamp. Filenames use seconds precision and an
  `O_EXCL` create that bumps a `-2`, `-3`… suffix if a same-second file already
  exists (prevents two concurrent saves clobbering each other).
- Prepends exactly one header line it fully owns:
  `# KT — {note}  ·  {YYYY-MM-DD HH:MM}  ·  by {tool}` + blank line, then the
  stdin body verbatim. **No other parsing or assembly.**
- Writes `.kt/kt-<ts>.md` (immutable) and copies it to `.kt/kt.md` (stable
  latest).
- Drops `.kt/.pending-handoff` — two lines: absolute path to `.kt/kt.md`,
  ISO-8601 timestamp.
- git tracking: if `.kt/.shared` absent, ensure `.kt/` is in `.gitignore`
  (create if needed); skip if not a git repo. If `.shared` present, leave git
  rules untouched.
- Echoes the stdin's `## Resume prompt` section to stdout (so the shim can
  display it in chat) using `section()`.
- Exit 0 on success; non-zero + clear stderr if `.kt/` is unwritable (the shim
  still surfaces the body in chat so nothing is lost).

`--tool` defaults to `unknown`; `--note` is the sole headline source (no
fallback parsing — the shim always supplies it, derived by the LLM from the
active todo / last goal).

### `kt resume`

```
kt resume [TIMESTAMP] [--cwd DIR]
```
- Prints the full content of `.kt/kt.md` (or `.kt/kt-<TIMESTAMP>.md`) to stdout.
- Then prints a `--- Recent handoffs ---` footer: the last 5 timestamped files
  (newest first) as `kt-<ts>.md — <headline> (by <tool>, <time>)`. Headline /
  tool / time are read from each file's header line, tolerating both the 2-field
  (legacy) and 3-field (`· by …`) header shapes via a single header-parse
  helper.
- If `.kt/kt.md` is missing → clear message on stderr, non-zero exit.
- Read-only: never writes, never touches the sentinel.

### `kt format`

Prints the canonical template (below) to stdout — the single source of truth
the shims reference instead of re-describing the format. `{tool}` and the
timestamp are filled by the engine on save; the LLM fills everything else.
Sections with no content are omitted by the LLM (except Resume prompt + Next
action, always present).

```
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
- Branch: <git rev-parse --abbrev-ref HEAD>
- Uncommitted: <git status -s, with .kt/ filtered, or "clean">
- Recent commits:
  - <git log -5 --oneline>
- Todos: <current todo list, or omit>
```

The stub `kt inject` extracts is exactly the `## Resume prompt` **section** —
self-contained (it already carries the TL;DR + next action), so no positional
"3rd header" counting is needed.

### `kt inject`

The SessionStart stub emitter — replaces the standalone
`inject-handoff.ps1`/`.sh` from the original design. Reads SessionStart JSON on
stdin (uses `.cwd`, falls back to `os.getcwd()`):
- No `.kt/.pending-handoff` → exit 0, no output.
- Sentinel malformed, older than 30 minutes, **its recorded absolute doc path
  does not resolve under the resolved cwd's `.kt/`** (cross-project guard,
  restored from v1), or the doc is missing → delete sentinel, exit 0, no
  output.
- Fresh and consistent: extract the `## Resume prompt` section via `section()`,
  print the **nested** SessionStart contract and delete the sentinel:
  ```json
  {"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"<stub>"}}
  ```
  as UTF-8-no-BOM JSON.
- **Always exits 0**; injects nothing on any error.

### `kt list`, `kt cancel`, `kt share`, `kt local`

All accept `--cwd`.
- `kt list` — all timestamped handoffs (newest first) with headline, tool,
  time, using the same formatter as `resume`'s footer.
- `kt cancel` — delete `.kt/.pending-handoff` if present; report.
- `kt share` — remove `.kt/` from `.gitignore`, create `.kt/.shared`.
- `kt local` — delete `.kt/.shared`, re-add `.kt/` to `.gitignore`.

## Per-tool shims (all `SKILL.md`)

Each shim is thin and nearly identical across tools: (save) "produce a body
matching `kt format`, run git for the Signals section yourself, then pipe it to
`kt save --tool <name> --note <headline>`"; (resume) "run `kt resume` and
continue from its output." Each references the engine by the **absolute
interpreter form** when run from a non-interactive surface (see PATH caveats).

- **Claude Code** — refactor `~/.claude/skills/kt/SKILL.md` to call the engine;
  add `~/.claude/skills/kt-resume/SKILL.md`. Repoint the SessionStart hook (see
  Hook).
- **Codex CLI** — a Codex **skill** (`SKILL.md`), NOT a `~/.codex/prompts/*.md`
  prompt (prompts are deprecated; Codex now uses the skills standard). Exact
  skills directory confirmed in Spike 0. Acknowledge that Codex auto-loads
  `AGENTS.md`; the shim must not duplicate/conflict with it.
- **Antigravity CLI** — `.agents/skills/kt/SKILL.md` +
  `.agents/skills/kt-resume/SKILL.md`. Invocation model (slash vs
  conversational) resolved by Spike 0; ship accordingly.
- **Generic / any tool** — no command file. Documented: run `kt resume` /
  `kt save` directly; the printed resume prompt pastes into any tool.

## Claude SessionStart hook (repointed)

Project `.claude/settings.json`, command defaults to the **absolute
interpreter** form (hooks are non-interactive and may not see a freshly-added
PATH):
```json
{ "hooks": { "SessionStart": [ { "hooks": [
  { "type": "command",
    "command": "python C:/Users/<you>/.kt/kt.py inject" } ] } ] } }
```
(The installer writes the correct absolute path for the user; `kt inject` is
the convenience form only when PATH is known-good.)

## Provenance

The header records the authoring tool: `# KT — <headline> · <time> · by
<tool>`. `kt resume`/`kt list` surface it. The header parser tolerates legacy
2-field headers (no `· by …`) and reports tool as `unknown` for those.

## Installer: `kt-install`

Python script (`~/.kt/kt-install.py`, shipped in the repo). Refuses early with
a clear message if no `python`/`py`/`python3` is found. Steps:
1. Copy `kt.py` to `~/.kt/`.
2. Put `kt` on PATH for every shell that matters:
   - **POSIX wrapper `~/.kt/kt`** (`#!/usr/bin/env python3` exec), chmod +x —
     **installed on Windows too**, because Git Bash ignores `PATHEXT` and won't
     resolve `kt.cmd` (Claude's Windows hooks default to Git Bash).
   - **Windows `~/.kt/kt.cmd`** (`@python "%~dp0kt.py" %*`) for cmd/pwsh.
   - **PATH entry:** on Windows, append `~\.kt` to the **registry**
     `HKCU\Environment` (`REG_EXPAND_SZ`) — NOT `setx` (which truncates at 1024
     chars and can merge system PATH into user PATH) — then broadcast
     `WM_SETTINGCHANGE`. On POSIX, append a PATH line to the shell profile.
3. Detect installed tools and lay down their `SKILL.md` shims; report actions.
4. Idempotent: re-running updates files in place, never duplicates PATH entries.

**Restart caveat (documented prominently):** already-running terminals and AI
tools will NOT see the new PATH until restarted. Because of this, the shims and
the hook use the absolute `python ~/.kt/kt.py …` form, which works regardless
of PATH state; bare `kt` is the convenience for fresh terminals.

## Migration from the original design

- `inject-handoff.ps1` / `inject-handoff.sh` are **superseded** by `kt inject`.
  They remain in repo history. **Existing per-project `.claude/settings.json`
  hooks are NOT auto-repointed** (the installer operates on `~/` and tool dirs,
  not every repo). They keep working against the old script unchanged; repoint
  is a per-repo manual step, documented. The installer offers to repoint a hook
  only in the current repo if it detects one.
- The `.kt/` on-disk format is unchanged except the header's optional `· by
  <tool>` suffix; the header parser handles both shapes, so old handoffs resume
  fine.
- The original Claude `SKILL.md` inline mechanics are replaced by engine calls.

## Spike 0 (first implementation task — de-risks the whole project)

Empirically verify, on the installed builds, BEFORE building the four shims:
1. **Antigravity:** does a `.agents/skills/kt-resume/SKILL.md` invoke as an
   explicit `/kt-resume` slash command, or only conversationally? Record the
   answer; it decides the Antigravity shim's documented trigger.
2. **Codex:** confirm the current skills directory/format (since prompts are
   deprecated) and that a skill can shell out to `kt resume`.
3. **Claude hook:** confirm `kt inject`'s **nested** `hookSpecificOutput` JSON
   is accepted and injects on SessionStart.

## Edge cases / failure handling

- **Not a git repo:** gitignore management and (LLM-side) git signals skip;
  no error.
- **`.kt/` unwritable on save:** non-zero exit, clear stderr; shim shows body.
- **`kt resume` with no handoff:** clear message, non-zero exit.
- **`kt` not on PATH in a tool's shell:** shims/hook use absolute
  `python ~/.kt/kt.py …` (the default for non-interactive surfaces).
- **Same-second concurrent saves:** `O_EXCL` + numeric suffix avoids clobber.
- **Concurrent sessions in one repo:** single per-repo sentinel; first new
  session consumes it (documented limitation, unchanged).
- **Python missing:** installer refuses with a clear message.

## Out of scope (v1)

- Auto-resume hooks for non-Claude tools (explicit resume only).
- History pruning, cross-machine sync, encryption (unchanged).
- Network/cloud handoff — `.kt/` is local to the repo.

## Components summary

| Component | Purpose | Depends on |
|-----------|---------|------------|
| `~/.kt/kt.py` | Engine: save/resume/format/inject/list/cancel/share/local + `section()` | Python 3 stdlib, git (optional) |
| `~/.kt/kt` (POSIX, incl. Windows) + `kt.cmd` (Windows) | PATH wrappers so `kt` runs anywhere | kt.py, PATH |
| `kt-install.py` | Install engine, set PATH (registry+broadcast on Win), lay down shims, idempotent | kt.py, per-tool dirs |
| Claude `kt` / `kt-resume` skills | Shims (SKILL.md) | kt engine |
| Claude SessionStart hook | Auto-inject stub after /clear (absolute `python … inject`) | kt engine, project settings.json |
| Codex `kt` / `kt-resume` skills | Shims (SKILL.md, skills dir) | kt engine |
| Antigravity `kt` / `kt-resume` skills | Shims (`.agents/skills/`, trigger per Spike 0) | kt engine |
| `.kt/` (per repo) | Tool-neutral interchange: handoffs, sentinel, markers | filesystem |
| Engine test suite | stdlib unittest covering all subcommands + edge cases | kt.py |

## Testing

- **Engine:** stdlib `unittest`, runnable as `python -m unittest`. Covers:
  - save: header line (incl. provenance + `--note` headline), writes both files,
    sentinel format, gitignore in local vs shared, no-git fallback, same-second
    `O_EXCL` suffixing, body persisted verbatim (no mutation), Resume-prompt
    echo to stdout.
  - resume: latest, by-timestamp, recent-handoffs footer, header parse for both
    2-field and 3-field headers, missing-handoff error.
  - inject: no/fresh/stale/missing-doc/malformed sentinel; **cross-project
    abs-path guard**; **nested `hookSpecificOutput` JSON shape**; no-BOM;
    `## Resume prompt` section extraction via `section()`; always exit 0.
  - format: prints the canonical template; `section()` round-trips against it.
  - list/cancel/share/local.
- **Shims:** acceptance checklist (manual) — Claude save→resume round trip;
  Claude→Codex cross-tool handoff with provenance shown; hook auto-inject via
  `kt inject`; generic terminal `kt resume`. Antigravity per Spike 0 outcome.
