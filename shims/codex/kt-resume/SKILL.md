---
name: kt-resume
description: Resume work from a KT handoff. Use when the user runs /kt-resume or wants to pick up work captured by /kt (possibly from another AI tool). Reads the latest .kt/ handoff and continues.
---

# /kt-resume — Resume from a Knowledge-Transfer handoff

Choose the engine launcher for the current shell: Windows PowerShell uses
`& "$HOME/.kt/kt.cmd"`; macOS/Linux uses `"$HOME/.kt/kt"`. Substitute that
launcher for `<kt>` below.

1. Run `<kt> resume` (append a timestamp arg to target an older
   handoff, e.g. `resume 20260624-103000`).
2. Read its stdout: the full latest handoff plus a "Recent handoffs" list.
3. If the handoff references other files (e.g. `.remember/remember.md` or files
   under "Key files"), read those too.
4. Begin with the handoff's **Next action**, then continue the work.

If stdout is a "no handoff found" error, tell the user there is nothing to
resume in this directory.
