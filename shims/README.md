# kt shims — install locations

Copy each tool's `kt/` and `kt-resume/` SKILL.md folders to:

- Claude Code:   ~/.claude/skills/
- Codex CLI:     <SKILLS DIR FROM spikes/cross-tool-FINDINGS.md §B> (UNVERIFIED — confirm via spikes/cross-tool-FINDINGS.md on your machine)
- Antigravity:   .agents/skills/   (project-scoped; per spikes §C) (UNVERIFIED — confirm via spikes/cross-tool-FINDINGS.md on your machine)

All shims call the engine via the absolute `python ~/.kt/kt.py ...` form.
Generic/any tool: no shim needed — run `kt resume` / `kt save` directly.
