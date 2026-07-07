---
name: kt
description: Knowledge-Transfer handoff. Use when the user runs /kt, asks to snapshot or hand off their current working state, or wants to save a resumable handoff so another AI tool or a fresh context can pick up the work. Lightweight alternative to /compact.
---

# kt — Knowledge Transfer (cross-tool)

Snapshot the current working state via the shared `kt` engine. In ZCode this
skill is invoked from the `/` menu (Skills group) or by asking the agent to
"save a KT handoff" — it is not a built-in slash command.

Use `python $HOME/.kt/kt.py ...` for engine commands. Do not pass
`~/.kt/kt.py` to Python; PowerShell treats that as a literal relative path.

1. Parse any note after the request: `--share`/`--local`/`--cancel` → run
   `python $HOME/.kt/kt.py <that>` and STOP. Else the text is the headline note;
   if empty, derive from the active task or last goal.
2. Run `python $HOME/.kt/kt.py format` to get the template.
3. Author the full body per the template, including `## Signals (auto)` —
   run `git rev-parse --abbrev-ref HEAD`, `git status -s` (drop `.kt/` lines),
   `git log -5 --oneline`. Omit empty sections; keep Resume prompt + Next action.
4. Pipe to: `python $HOME/.kt/kt.py save --tool "ZCode" --note "<headline>"`.
5. Show the engine stdout (resume prompt) to the user.
