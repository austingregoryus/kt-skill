# kt shims — install locations

Each shim is a thin `SKILL.md` that teaches a specific AI coding tool to drive
the shared engine at `$HOME/.kt/kt.py`. Copy each tool's `kt/` and `kt-resume/`
folders into that tool's skills directory:

| Tool        | Skills directory | Notes |
|-------------|------------------|-------|
| Claude Code | `~/.claude/skills/` | Verified. Optional auto-inject hook: see `claude/settings.hook.example.json`. |
| Codex CLI   | `$CODEX_HOME/skills/` or `~/.codex/skills/` | Verified in Codex Desktop/CLI local skill layout. Each shim also ships a Codex `agents/openai.yaml` (see below). |
| ZCode       | `~/.zcode/skills/` (or `~/.agents/skills/` to share with other tools) | Verified. Same `SKILL.md` format; invoke from the `/` menu (Skills group) or by asking the agent. |
| Antigravity | `.agents/skills/` (project-scoped) or `~/.gemini/config/skills/` (global) | Verified. Slash commands (e.g. `/kt`) trigger conversationally. |

## Codex `agents/openai.yaml`

The `shims/codex/kt/` and `shims/codex/kt-resume/` folders each include an
`agents/openai.yaml`. This is the manifest Codex Desktop/CLI uses to surface
the skill as a named agent (`$kt`, `$kt-resume`). Copy the whole folder
(`SKILL.md` **and** `agents/`) into Codex's skills directory; the `agents/`
subdir is ignored by other tools, so it is harmless to include.

All shims call the engine via `python $HOME/.kt/kt.py ...` so they work even
before a PATH refresh. Do not use `python ~/.kt/kt.py ...`; PowerShell passes
that tilde path to Python as a literal relative path.

Any other tool needs no shim — run `kt save` / `kt resume` (or
`python $HOME/.kt/kt.py ...`) directly.
