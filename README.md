# kt — Knowledge-Transfer handoffs for AI coding tools

`/kt` snapshots your current working state — next action, status, mental
model, decisions, dead ends, key files, git signals — into a small,
tool-neutral handoff under `.kt/` in the project. `/kt-resume` (or a fresh
context in **any** supported tool) picks it right back up.

Use it when you're about to `/clear`, switch machines, or hand the same task
from one AI tool to another (Claude Code → Codex CLI → Antigravity → …).
It's a lightweight, cross-tool alternative to `/compact`.

## How it works

- A tiny Python engine (`~/.kt/kt.py`, no dependencies) owns the file format:
  it writes timestamped `.kt/kt-<ts>.md` handoffs plus a stable `.kt/kt.md`,
  records which tool wrote each one, and prints a paste-ready resume prompt.
- Per-tool **shims** (thin `SKILL.md` files in `shims/`) teach each AI tool to
  author the handoff body and call the engine. The AI does the thinking; the
  engine does the I/O.
- An optional **SessionStart hook** (Claude Code) auto-injects the resume
  stub into your next session after `/kt` → `/clear`, so there's nothing to
  paste. It fires at most once per handoff, only within 30 minutes, and never
  breaks session start (it exits 0 and stays silent on any error).

`.kt/` is gitignored by default (handoffs are personal scratch).
`/kt --share` flips a project to git-tracked handoffs; `/kt --local` flips it
back.

## Install

1. **Engine:** `python engine/kt-install.py` — copies the engine to `~/.kt/`
   and writes `kt` / `kt.cmd` PATH wrappers. Follow its printed PATH and
   restart guidance.
2. **Shims:** copy `shims/<tool>/kt/` and `shims/<tool>/kt-resume/` into each
   tool's skills directory — locations and caveats in `shims/README.md`.
3. **Optional auto-inject (Claude Code):** merge
   `shims/claude/settings.hook.example.json` into a project's
   `.claude/settings.json`, replacing `<you>` with your username (the hook
   command must be an absolute path).

## Use

| Command | What it does |
|---------|--------------|
| `/kt` | Write a handoff; headline derived from your active todo/goal |
| `/kt some note` | Write a handoff with that headline |
| `/kt-resume` | Read the latest handoff and continue the work |
| `/kt-resume <timestamp>` | Resume from an older handoff |
| `/kt --share` / `--local` | Toggle git-tracked vs. gitignored handoffs |
| `/kt --cancel` | Cancel a pending auto-inject |
| `kt list` / `kt resume` (CLI) | Use the engine directly from any tool or shell |

Typical cross-tool flow: run `/kt` in tool A, open tool B in the same
project, run `/kt-resume` — tool B reads `.kt/kt.md` (which names the tool
and time it was written) and starts from the handoff's **Next action**.

## Repo layout

- `engine/` — `kt.py` (the engine), `kt-install.py`, unit tests
- `shims/` — per-tool `SKILL.md` shims + Claude hook example
- `SKILL.md` — the original single-tool Claude Code skill (self-contained;
  superseded by the engine + shims, kept for reference/simple installs)
- `inject-handoff.ps1` / `.sh` — legacy hook scripts for the single-tool
  skill (superseded by `kt inject`)
- `docs/`, `spikes/`, `tests/` — design docs, probe findings, and test suites

## Testing

```sh
python -m unittest discover -s engine -p "test_*.py"   # engine + installer
sh tests/inject-handoff.sh.test.sh                     # POSIX hook script
pwsh -NoProfile tests/inject-handoff.Tests.ps1         # PowerShell hook script
```

Some integration points are marked UNVERIFIED in `spikes/` (they need a live
tool session to confirm): whether `/clear` triggers SessionStart on your
Claude Code version, the Codex skills directory, and Antigravity slash
invocation. The printed resume prompt always works as a manual fallback.

## Migrating from the single-tool version

`inject-handoff.ps1`/`.sh` are superseded by `kt inject`. Existing
per-project hooks that point at the old scripts keep working, but repoint
them to `python ~/.kt/kt.py inject` when convenient. The `.kt/` file format
is unchanged (the header gains a `· by <tool>` field; old handoffs still
resume fine).
