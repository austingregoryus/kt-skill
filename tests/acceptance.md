# kt acceptance scenarios

Run each in a throwaway git repo with the skill installed (see Task 7).

## A. Basic handoff (local mode, default)
- [ ] Run `/kt fixing the login bug`.
- [ ] `.kt/kt-<ts>.md` exists; `.kt/kt.md` is an identical copy.
- [ ] Headline is "fixing the login bug"; Resume prompt + Next action present.
- [ ] `.kt/.pending-handoff` has 2 lines (abs path, ISO timestamp).
- [ ] `.gitignore` contains `.kt/`; `git status` does not list `.kt/`.
- [ ] Resume prompt was printed to chat.

## B. Hook injection
- [ ] Enable the hook (project .claude/settings.json from hooks-settings.example.json).
- [ ] Run `/kt`, then `/clear`. New context receives the stub (Resume prompt + Next action), NOT the whole doc.
- [ ] `.kt/.pending-handoff` is gone after injection.
- [ ] Start another new session with no prior `/kt`: nothing is injected.

## C. Freshness guard
- [ ] Run `/kt`, hand-edit the sentinel timestamp to 45 min ago, start a new session.
- [ ] Nothing injected; sentinel deleted.

## D. Share / local toggle
- [ ] `/kt --share`: `.kt/.shared` created, `.kt/` removed from `.gitignore`.
- [ ] `/kt --local`: `.kt/.shared` gone, `.kt/` back in `.gitignore`.

## E. Cancel
- [ ] `/kt`, then `/kt --cancel`: `.kt/.pending-handoff` deleted, no new doc written.

## F. No-git fallback
- [ ] In a non-git folder, `/kt` still writes `.kt/` docs without error; git steps skipped.
