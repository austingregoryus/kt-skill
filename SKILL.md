---
name: kt
description: Create a compact, tool-neutral Knowledge Transfer handoff for the current task. Use when the user runs /kt, asks to preserve working context before clearing or changing tools, or wants another AI coding tool or fresh context to resume from the same project state.
---

# kt Knowledge Transfer

Choose the installed engine launcher for the current shell and use it for each
`<kt>` command below:

- Windows PowerShell: `& "$HOME/.kt/kt.cmd"`
- macOS or Linux: `"$HOME/.kt/kt"`

If the engine is missing, tell the user to run
`engine/kt-install.py` from the kt repository before continuing. Resolve that
installer relative to this `SKILL.md` and show its absolute path. Do not assume
the user's current project contains the kt repository.

1. Parse the request. For `--share`, `--local`, or `--cancel`, run the matching
   engine command and stop. Otherwise, use supplied text as the headline. If
   there is no text, derive a short headline from the active task or last goal.
2. Run `<kt> format` to get the canonical handoff template.
3. Fill the template from the current conversation and workspace. Keep it lean.
   Always include `## Resume prompt` and `## Next action`. Gather git branch,
   status, and recent commits when available, filtering `.kt/` from status.
4. Pipe the completed body to
   `<kt> save --tool "<current tool>" --note "<headline>"`.
5. Show the engine stdout to the user. It is the paste-ready resume prompt.

Do not include secrets, credentials, or unrelated personal data in a handoff.
The default local mode gitignores `.kt/`. Shared mode makes handoff documents
eligible for git tracking while keeping `.kt/.pending-handoff` private.
