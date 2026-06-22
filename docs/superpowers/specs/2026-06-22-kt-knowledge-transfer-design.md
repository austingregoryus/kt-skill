# /kt — Knowledge-Transfer Skill — Design

**Date:** 2026-06-22
**Status:** Approved design, ready for implementation plan

## Goal

A Claude Code skill, invoked as `/kt`, that snapshots the current working
state into a timestamped `kt.md` handoff document and prints a short
copy-paste resume prompt. A fresh (post-`/clear`) context reads the doc and
resumes exactly where the previous context left off. Lightweight to produce,
but carrying enough detail to resume cold.

Think of it as a deliberate, human-readable alternative to `/compact`: instead
of an opaque auto-summary, the user gets a structured, inspectable, version-ed
handoff they control.

## Invocation

- `/kt` — snapshot with an auto-derived headline.
- `/kt <note>` — the note becomes the handoff headline (e.g.
  `/kt paused mid-refactor of auth flow`).
- `/kt --share` / `/kt --local` — toggle git-tracking mode for `.kt/`
  (see "git tracking — configurable").
- `/kt --cancel` — delete a pending sentinel without writing a new handoff.

**Headline derivation** (when no note is given), in priority order:
1. the `/kt` note argument, else
2. the title of the active/most-recent todo, else
3. a one-line restatement of the user's last stated goal.

Skill location: `~/.claude/skills/kt/SKILL.md` with frontmatter `name: kt`
so it triggers as `/kt`. Description identifies it as the Knowledge-Transfer
handoff skill.

## Behavior when run

1. **Gather signals** (each step degrades gracefully — if unavailable, the
   section is omitted, never errors):
   - `git rev-parse --abbrev-ref HEAD` → current branch
   - `git status -s` → uncommitted changes
   - `git log -5 --oneline` → recent commits
   - current todo list (if any)
   Note: filter `.kt/` itself out of the captured `git status -s` so the
   handoff folder never shows up as noise in its own signals.
2. **Synthesize** the conversation + signals into the document structure below.
   Sections with no content are omitted entirely (keeps the doc lean).
3. **Write** the doc to `.kt/kt-YYYYMMDD-HHMMSS.md` (seconds precision so
   same-minute runs never collide / overwrite) and refresh `.kt/kt.md` as a
   copy of the just-written file (stable "read this" path).
4. **Drop the sentinel** `.kt/.pending-handoff` — a small file containing two
   lines: the **absolute path** to `.kt/kt.md`, and an **ISO-8601 timestamp**.
   Both are used by the opt-in hook (see below) for cross-project safety and
   freshness checking.
5. **Print the resume prompt** to chat for copy-paste.

## `kt.md` structure

Sections appear in this order; any section with no content is omitted.

```
# KT — <headline>  ·  <YYYY-MM-DD HH:MM>

## Resume prompt
<the same short prompt printed to chat>

## Next action
<the single most important first thing the next context should do>

## Status
- Done: ...
- In progress: ...
- Not started: ...

## Mental model
<current hypothesis / understanding of the system — most valuable mid-debug>

## Decisions + rationale
- <decision> — <why>

## Dead ends
- <thing tried> — <why it failed / don't repeat>

## Key files
- path/to/file — <one-line why it matters>

## Signals (auto)
- Branch: <branch>
- Uncommitted: <git status -s output, or "clean">
- Recent commits:
  - <git log -5 --oneline>
- Todos: <current todo list, or omitted>
```

Default sections (always attempted): Resume prompt, Next action, Status,
Decisions + rationale, Dead ends, Key files, Signals.
Conditional section: Mental model (include only when there is a genuine
working hypothesis — otherwise it is noise).

## Resume prompt format

A thin pointer, not a paste of the whole handoff — small enough to survive a
copy-paste and not itself consume meaningful context. Stored in the doc AND
printed to chat:

> Resuming work. Read `.kt/kt.md` for the full handoff.
> TL;DR: `<headline>`. Next: `<next action>`.
> Start by `<next action>`, then continue.

The heavy detail lives in `kt.md`; the new context reads one file and is
oriented.

## File handling — timestamped history

- Every run writes a new immutable `.kt/kt-YYYYMMDD-HHMMSS.md`.
- `.kt/kt.md` is overwritten each run with a copy of the latest — it is the
  stable path the resume prompt and hook always point at.
- History accumulates in `.kt/`, enabling diffing handoffs and recovering an
  older one. No automatic pruning in v1 (YAGNI; revisit if clutter is real).
- `.kt/` is created if missing.

## git tracking — configurable

Default: **local-only**. On first run the skill ensures `.kt/` is ignored
(adds `.kt/` to the repo's `.gitignore`, or `.git/info/exclude` if no tracked
`.gitignore` exists). Handoffs are personal scratch and don't pollute the repo.

To make handoffs **shareable** (committed so a teammate can pick up the work),
the user runs `/kt --share`: the skill removes the `.kt/` ignore entry and
writes a marker `.kt/.shared`. While `.shared` exists, the skill leaves git
tracking alone. `/kt --local` reverses it (re-adds the ignore entry, removes
the marker). The mode is persisted per-project via the presence/absence of
`.kt/.shared`, so it is sticky across runs.

Not in a git repo: tracking steps are skipped entirely (no error).

## Opt-in auto-injection hook

Full automation (skill clears context AND injects the new prompt) is
**impossible** on the platform: `/clear` is strictly user-driven with no API
surface for skills/hooks to trigger it or to send a follow-up prompt. The hook
below removes the copy-paste step, which is the bulk of the friction.

> **Verify first (implementation task #1):** This whole feature rests on
> `SessionStart` firing with `source: "clear"` after `/clear`. Before building
> the hook, confirm empirically on the target Claude Code version (a throwaway
> hook that logs the `source` field on stdin, run `/clear`, inspect). If it
> does not fire on clear, the hook degrades to firing on the next full session
> start instead — still useful, but the flow changes and must be documented.

**Scope — project-local, not global.** The hook is installed in the
**project's** `.claude/settings.json`, not global `~/.claude/settings.json`.
This prevents a global hook from firing in unrelated directories and injecting
the wrong project's handoff. As a second layer of safety, the sentinel records
the **absolute** path to the doc, and the hook injects only if that path
resolves and is consistent with the current working directory.

**Mechanism (the hook script):**
- A `SessionStart` hook runs on new sessions (including, pending verification,
  immediately after `/clear`).
- On fire it looks for `.kt/.pending-handoff` (relative to cwd). If absent →
  inject nothing.
- If present, it reads the sentinel's timestamp. **Freshness guard:** if older
  than 30 minutes, delete the sentinel and inject nothing (kills the
  "stale handoff injected days later" failure mode).
- If fresh, it reads `.kt/kt.md`, extracts the **Resume prompt + Next action**
  only (a short stub, not the whole doc — keeps SessionStart lightweight),
  emits it as `additionalContext`, then deletes the sentinel. The stub tells
  the agent to Read `.kt/kt.md` for full detail on demand.
- The sentinel makes injection fire **at most once** after a `/kt`.

**Failure contract:** the hook script **always exits 0**. On any error
(missing/unreadable file, malformed sentinel, parse failure) it injects
nothing and exits cleanly — a handoff hook must never disrupt session start.
Stdout must be UTF-8 **without BOM**; JSON only.

**Windows (primary target):** the hook command is specified as
`pwsh -NoProfile -File <skill_dir>/inject-handoff.ps1` so it runs without
relying on Git Bash being on PATH. (A POSIX `sh` variant is bundled for
non-Windows users.) The PowerShell script must emit clean UTF-8-no-BOM JSON
(avoid `Write-Output` object serialization; write the JSON string directly).

**Resulting flow:** `/kt` → `/clear` → start typing. The fresh context already
holds the stub and reads the full doc as needed; no paste.

**Known limitation — concurrent sessions:** the sentinel is a single per-project
flag with no session owner. If two sessions share one repo, whichever new
session fires first consumes the sentinel. Acceptable for v1; a future version
can scope the sentinel to a session ID if the hook payload exposes one.

**Opt-in, not default:** The skill ships standalone and works fully without the
hook (it still writes the doc + prints the prompt + drops the sentinel — the
sentinel is simply ignored if no hook consumes it). The hook is documented as
an optional add-on the user enables when they want it. The printed resume
prompt remains the fallback for brand-new terminals, other machines, or other
tools where the hook does not apply.

The skill's SKILL.md documents the exact project-scoped `SessionStart` config
and the bundled inject script so the user can enable it in one step.

## Edge cases / graceful degradation

- **Not a git repo:** git signal sub-steps are skipped; their lines are
  omitted. No error.
- **No todos:** Todos line omitted.
- **Empty / trivial conversation:** Doc still writes with whatever is known;
  Next action falls back to a best-effort restatement of the user's last goal.
- **`.kt/` write failure:** Surface the error plainly; still print the resume
  prompt to chat so nothing is lost.
- **Stale sentinel (user ran `/kt` but never `/clear`d):** freshness guard
  (30 min) in the hook prevents an old handoff from injecting into a much later
  session. `/kt --cancel` also deletes a pending sentinel manually.
- **Concurrent sessions in one repo:** documented limitation (see hook section);
  first new session to fire wins the sentinel.

## Out of scope (v1)

- Automatic history pruning / retention limits.
- Auto-triggering `/clear` (platform-impossible).
- Cross-machine sync of `.kt/`.
- Encryption of handoff contents.

## Components summary

| Component | Purpose | Depends on |
|-----------|---------|------------|
| `SKILL.md` | `/kt` instructions: gather, synthesize, write, print, toggle modes | git CLI (optional), todo list |
| `.kt/kt-*.md` | Immutable timestamped handoffs (seconds precision) | filesystem |
| `.kt/kt.md` | Latest handoff, stable path | latest timestamped doc |
| `.kt/.pending-handoff` | One-shot signal: abs path + ISO timestamp | written by skill, deleted by hook |
| `.kt/.shared` | Marker: handoffs are git-tracked/shareable | `/kt --share` / `/kt --local` |
| `inject-handoff.ps1` / `.sh` | Bundled hook script: freshness-checked stub injection, always exit 0 | sentinel, `.kt/kt.md` |
| `SessionStart` hook (opt-in) | Auto-inject handoff stub once after `/kt` | inject script, project `.claude/settings.json` |
