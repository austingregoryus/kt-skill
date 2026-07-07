---
name: kt
description: Knowledge-Transfer handoff. Use when the user runs /kt or wants to snapshot working state into a tool-neutral .kt/ handoff so another AI tool (or a fresh context) can resume. Lightweight alternative to /compact.
---

# /kt — Knowledge Transfer (cross-tool)

Snapshot the current working state via the shared `kt` engine.

Use `python $HOME/.kt/kt.py ...` for engine commands. Do not pass
`~/.kt/kt.py` to Python; PowerShell treats that as a literal relative path.

## Steps

1. Parse the text after `/kt`: `--share`/`--local`/`--cancel` → run
   `python $HOME/.kt/kt.py <that>` and STOP. Otherwise the text (if any) is the
   handoff **headline note**; if empty, derive it from the active todo or the
   user's last stated goal.
2. Get the canonical template: run `python $HOME/.kt/kt.py format`.
3. Author the full handoff **body** following that template — including the
   `## Signals (auto)` section, for which YOU run:
   `git rev-parse --abbrev-ref HEAD`, `git status -s` (drop any `.kt/` lines),
   `git log -5 --oneline`, and the current todo list. Omit empty sections;
   always include Resume prompt + Next action.
4. Pipe the body to the engine:
   `printf '%s' "<body>" | python $HOME/.kt/kt.py save --tool "Claude Code" --note "<headline>"`
   (Use a heredoc/temp file for multi-line bodies.)
5. Show the engine's stdout (the resume prompt) to the user.

