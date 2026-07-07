---
name: kt-resume
description: Resume work from a KT handoff. Use when the user runs /kt-resume or wants to pick up work captured by /kt (possibly from another AI tool). Reads the latest .kt/ handoff and continues.
---

# /kt-resume — Resume from a Knowledge-Transfer handoff

NOTE: On Antigravity, if `/kt`/`/kt-resume` slash invocation is unavailable, invoke by asking the agent ("save a KT handoff" / "resume from KT").

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
