# kt — Knowledge-Transfer skill

Source for the `/kt` Claude Code skill. See `docs/superpowers/specs/` for the
design and `docs/superpowers/plans/` for the build plan. Install with the
steps in `SKILL.md` (final task: copy this folder to `~/.claude/skills/kt`).

## Install (cross-tool)

1. `python engine/kt-install.py` — installs the engine to `~/.kt/` and writes
   PATH wrappers. Follow its printed PATH + restart guidance.
2. Copy shims from `shims/<tool>/` to each tool's skills dir (see `shims/README.md`).
3. For Claude auto-inject, add `shims/claude/settings.hook.example.json`'s
   SessionStart hook to a project's `.claude/settings.json` (absolute path).

## Migration from the single-tool version

`inject-handoff.ps1`/`.sh` are superseded by `kt inject`. Existing per-project
hooks pointing at the old script keep working but should be repointed to
`python ~/.kt/kt.py inject` per repo. The `.kt/` format is unchanged (header
gains `· by <tool>`; old handoffs still resume).
