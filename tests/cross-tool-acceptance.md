# Cross-tool KT acceptance

Run with the engine installed (`python engine/kt-install.py`) and shims copied.

## A. Engine round trip (any terminal)
- [ ] Choose the absolute launcher: Windows PowerShell uses
      `& "$HOME/.kt/kt.cmd"`; macOS/Linux uses `"$HOME/.kt/kt"`.
- [ ] Pipe `## Resume prompt`, content, `## Next action`, and content to
      `<kt> save --tool "Manual" --note "t"`.
- [ ] `<kt> resume` prints the doc + "Recent handoffs".
- [ ] `<kt> list` lists it; `(by Manual, ...)` provenance shown.
- [ ] A save missing either required section exits 2 and writes no handoff.

## B. Claude save → resume
- [ ] `/kt fixing X` writes `.kt/kt.md` (header `· by Claude Code`), prints resume prompt.
- [ ] `/kt-resume` reads it back and starts at Next action.

## C. Cross-tool (the headline feature)
- [ ] `/kt` in Claude, then in Codex run `/kt-resume` (or its skill): Codex
      resumes from the Claude-authored handoff; provenance shows "by Claude Code".

## D. Hook auto-inject (Claude)
- [ ] With the Task 7 hook in a project's .claude/settings.json, `/kt` then
      `/clear`: the stub auto-injects (nested hookSpecificOutput). Sentinel gone.

## E. Toggles
- [ ] `/kt --share` then `/kt --local` flip `.kt/.shared` + `.gitignore`.
- [ ] `/kt --cancel` deletes a pending sentinel.
