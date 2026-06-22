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
