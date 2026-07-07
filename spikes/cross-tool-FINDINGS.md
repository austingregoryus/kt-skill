# Cross-tool KT — Spike 0 findings

## A. Claude hook nested JSON  (CONSUMED BY Task 7)
Procedure: add to a throwaway project's .claude/settings.json:
  {"hooks":{"SessionStart":[{"hooks":[{"type":"command",
   "command":"python C:/Projects/kt-skill/spikes/probe-hook.py"}]}]}}
Start a session. Does "KT probe: nested additionalContext works." appear in context?
Result: UNVERIFIED — requires live Claude session with hook integration; run on user machine

## B. Codex skills directory  (CONSUMED BY Task 8)
Find where Codex CLI loads skills (prompts are deprecated). Confirm the dir and
that a SKILL.md there is invocable and can run shell commands.
Result dir: UNVERIFIED — requires live Codex CLI; run on user machine

## C. Antigravity slash invocation  (CONSUMED BY Task 8)
Drop .agents/skills/kt-resume/SKILL.md (trivial body). Does `/kt-resume`
invoke it as a slash command, or only conversational triggering?
Result: VERIFIED — While it doesn't automatically register as a clickable UI button, typing `/kt-resume` is read by the agent conversationally. It reliably matches the skill's description trigger and invokes the skill.
