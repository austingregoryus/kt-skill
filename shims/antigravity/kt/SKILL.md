---
name: kt
description: Knowledge-Transfer handoff via the shared kt engine. Snapshot working state into a tool-neutral .kt/ handoff so another AI tool or a fresh context can resume.
---

# /kt — Knowledge Transfer (cross-tool)

NOTE: On Antigravity, if `/kt`/`/kt-resume` slash invocation is unavailable, invoke by asking the agent ("save a KT handoff" / "resume from KT").

Choose the engine launcher for the current shell: Windows PowerShell uses
`& "$HOME/.kt/kt.cmd"`; macOS/Linux uses `"$HOME/.kt/kt"`. Substitute that
launcher for `<kt>` below.

1. Parse args after /kt: `--share`/`--local`/`--cancel` → run
   `<kt> <that>` and STOP. Else the text is the headline note;
   if empty, derive from the active task or last goal.
2. Run `<kt> format` to get the template.
3. Author the full body per the template, including `## Signals (auto)` —
   run `git rev-parse --abbrev-ref HEAD`, `git status -s` (drop `.kt/` lines),
   `git log -5 --oneline`. Omit empty sections; keep Resume prompt + Next action.
4. Write the handoff to a temporary file (e.g., `.kt/tmp.md`), then pipe it to the engine to avoid PowerShell encoding issues: `Get-Content .kt/tmp.md | <kt> save --tool "Antigravity" --note "<headline>"` (then delete the temp file).
5. Show the engine stdout (resume prompt) to the user.
