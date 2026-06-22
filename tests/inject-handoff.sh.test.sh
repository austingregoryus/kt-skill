#!/usr/bin/env bash
# tests/inject-handoff.sh.test.sh — no bats, plain bash. Exit 1 on any failure.
set -u
SCRIPT="$(cd "$(dirname "$0")/.." && pwd)/inject-handoff.sh"
fails=0
check() { if eval "$2"; then echo "PASS: $1"; else echo "FAIL: $1"; fails=$((fails+1)); fi; }
newproj() { d="$(mktemp -d)"; mkdir -p "$d/.kt"; echo "$d"; }
writedoc() {
  cat > "$1/.kt/kt.md" <<'EOF'
# KT — test

## Resume prompt
Resuming. Read .kt/kt.md.

## Next action
Do the first thing.

## Status
- Done: nothing
EOF
}
run() { printf '{"cwd":"%s"}' "$1" | sh "$SCRIPT"; }

# Case 1: no sentinel -> empty
p="$(newproj)"; out="$(run "$p")"
check "no sentinel -> empty" '[ -z "$out" ]'

# Case 2: fresh -> json with Next action, sentinel deleted
p="$(newproj)"; writedoc "$p"
printf '%s\n%s\n' "$p/.kt/kt.md" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$p/.kt/.pending-handoff"
out="$(run "$p")"
check "fresh -> has additionalContext" 'echo "$out" | grep -q additionalContext'
check "fresh -> has Next action text" 'echo "$out" | grep -q "Do the first thing"'
check "fresh -> sentinel deleted" '[ ! -f "$p/.kt/.pending-handoff" ]'

# Case 3: stale (>30m) -> empty, deleted
p="$(newproj)"; writedoc "$p"
old="$(date -u -d '-45 min' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-45M +%Y-%m-%dT%H:%M:%SZ)"
printf '%s\n%s\n' "$p/.kt/kt.md" "$old" > "$p/.kt/.pending-handoff"
out="$(run "$p")"
check "stale -> empty" '[ -z "$out" ]'
check "stale -> deleted" '[ ! -f "$p/.kt/.pending-handoff" ]'

# Case 4: missing doc -> empty, deleted
p="$(newproj)"
printf '%s\n%s\n' "$p/.kt/nope.md" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$p/.kt/.pending-handoff"
out="$(run "$p")"
check "missing doc -> empty" '[ -z "$out" ]'

if [ "$fails" -gt 0 ]; then echo "$fails FAILED"; exit 1; else echo "ALL PASS"; exit 0; fi
