#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT

export HOME="$scratch/home"
mkdir -p "$HOME"
python3 "$repo/engine/kt-install.py" >/dev/null

kt="$HOME/.kt/kt"
test -x "$kt"
"$kt" format | grep -q '^## Resume prompt$'

project="$scratch/project"
mkdir -p "$project"
git -C "$project" init -q

cat <<'EOF' | "$kt" save --cwd "$project" --tool "POSIX smoke" --note "portable round trip" >/dev/null
## Resume prompt
Resume the POSIX smoke test.

## Next action
Verify list and resume.
EOF

"$kt" list --cwd "$project" | grep -q 'portable round trip'
"$kt" resume --cwd "$project" | grep -q 'Verify list and resume.'
"$kt" share --cwd "$project" >/dev/null
git -C "$project" check-ignore -q .kt/.pending-handoff
if git -C "$project" check-ignore -q .kt/kt.md; then
  echo 'shared handoff remained ignored' >&2
  exit 1
fi

invalid="$scratch/invalid"
mkdir -p "$invalid"
if printf 'plain text only\n' | "$kt" save --cwd "$invalid" --note invalid >/dev/null 2>&1; then
  echo 'invalid handoff unexpectedly succeeded' >&2
  exit 1
fi
test ! -e "$invalid/.kt"

echo 'POSIX SMOKE PASS'
