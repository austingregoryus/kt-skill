# kt shims — install locations

Each shim is a thin `SKILL.md` that teaches a specific AI coding tool to drive
the shared engine at `~/.kt/kt.py`. Copy each tool's `kt/` and `kt-resume/`
folders into that tool's skills directory:

| Tool        | Skills directory | Notes |
|-------------|------------------|-------|
| Claude Code | `~/.claude/skills/` | Verified. Optional auto-inject hook: see `claude/settings.hook.example.json`. |
| Codex CLI   | Codex's skills directory | Unverified — confirm the location on your machine per `spikes/cross-tool-FINDINGS.md` §B. |
| Antigravity | `.agents/skills/` (project-scoped) or `~/.gemini/config/skills/` (global) | Verified. Slash commands (e.g. `/kt`) trigger conversationally. |

All shims call the engine via the absolute `python ~/.kt/kt.py ...` form so
they work even before a PATH refresh.

Any other tool needs no shim — run `kt save` / `kt resume` (or
`python ~/.kt/kt.py ...`) directly.
