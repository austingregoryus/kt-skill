# SessionStart probe findings

## Procedure
1. In a throwaway project, add to `.claude/settings.json`:
   {"hooks":{"SessionStart":[{"hooks":[{"type":"command",
     "command":"pwsh -NoProfile -File C:/Projects/kt-skill/spikes/probe-sessionstart.ps1"}]}]}}
2. Start a session, then run `/clear`.
3. Inspect `spikes/out/*.json` for the `source` field.

## Result
- Fires on startup: UNVERIFIED — must confirm before relying on /clear trigger
- Fires on /clear with source="clear": UNVERIFIED — must confirm before relying on /clear trigger

## Decision
- If source="clear" fires: ship the documented `/kt` -> `/clear` -> type flow as-is.
- If it does NOT: document that the handoff injects on the NEXT full session
  start instead, and note `/clear` alone may not trigger it.
