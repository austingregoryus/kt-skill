---
name: kt
description: Knowledge-Transfer handoff. Use when the user runs /kt, asks to snapshot or hand off their current working state, or wants to save a resumable handoff so another AI tool or a fresh context can pick up the work. Lightweight alternative to /compact.
---

# kt — Knowledge Transfer (cross-tool)

Snapshot the current working state via the shared `kt` engine. In ZCode this
skill is invoked from the `/` menu (Skills group) or by asking the agent to
"save a KT handoff" — it is not a built-in slash command.

Choose the engine launcher for the current shell: Windows PowerShell uses
`& "$HOME/.kt/kt.cmd"`; macOS/Linux uses `"$HOME/.kt/kt"`. Substitute that
launcher for `<kt>` below.

1. Parse any note after the request: `--share`/`--local`/`--cancel` → run
   `<kt> <that>` and STOP. Else the text is the headline note;
   if empty, derive from the active task or last goal.
2. Run `<kt> format` to get the template.
3. Author the full body per the template, including `## Signals (auto)` —
   run `git rev-parse --abbrev-ref HEAD`, `git status -s` (drop `.kt/` lines),
   `git log -5 --oneline`. Omit empty sections; keep Resume prompt + Next action.
4. Pipe the body to `<kt> save --tool "ZCode" --note "<headline>"`.
5. Show the engine stdout (resume prompt) to the user.
