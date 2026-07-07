---
name: kt-resume
description: Resume work from a KT handoff. Use when the user runs /kt-resume, asks to resume or pick up work captured earlier (possibly by /kt or by another AI tool), and the project has a .kt/ handoff to continue from.
---

# kt-resume — Resume from a Knowledge-Transfer handoff

In ZCode this skill is invoked from the `/` menu (Skills group) or by asking
the agent to "resume from KT" — it is not a built-in slash command.

Use `python $HOME/.kt/kt.py ...` for engine commands. Do not pass
`~/.kt/kt.py` to Python; PowerShell treats that as a literal relative path.

1. Run `python $HOME/.kt/kt.py resume` (append a timestamp arg to target an older
   handoff, e.g. `resume 20260624-103000`).
2. Read its stdout: the full latest handoff plus a "Recent handoffs" list.
3. If the handoff references other files (e.g. `.remember/remember.md` or files
   under "Key files"), read those too.
4. Begin with the handoff's **Next action**, then continue the work.

If stdout is a "no handoff found" error, tell the user there is nothing to
resume in this directory.
