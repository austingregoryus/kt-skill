#!/usr/bin/env sh
# inject-handoff.sh — POSIX SessionStart hook. Always exits 0.
# Emits {"additionalContext":"..."} on stdout when a fresh sentinel exists.
raw="$(cat)"
cwd="$(echo "$raw" | sed -n 's/.*"cwd"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
[ -z "$cwd" ] && cwd="$(pwd)"
sentinel="$cwd/.kt/.pending-handoff"
[ -f "$sentinel" ] || exit 0

doc="$(sed -n '1p' "$sentinel")"
iso="$(sed -n '2p' "$sentinel")"
[ -n "$doc" ] && [ -n "$iso" ] || { rm -f "$sentinel"; exit 0; }

# Freshness: 30 min. Convert ISO to epoch; bail to delete on parse failure.
now=$(date -u +%s)
then=$(date -u -d "$iso" +%s 2>/dev/null || date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$iso" +%s 2>/dev/null)
[ -n "$then" ] || { rm -f "$sentinel"; exit 0; }
age=$(( (now - then) / 60 ))
[ "$age" -gt 30 ] && { rm -f "$sentinel"; exit 0; }
[ -f "$doc" ] || { rm -f "$sentinel"; exit 0; }

# Stub = from "## Resume prompt" through the line before the 3rd "## " header.
stub="$(awk '
  /^##[[:space:]]+Resume prompt/ {grab=1}
  grab {
    if (/^##[[:space:]]/) {h++; if (h==3) exit}
    print
  }' "$doc")"
[ -n "$stub" ] || { rm -f "$sentinel"; exit 0; }
stub="$stub

(Read .kt/kt.md for the full handoff.)"

# JSON-escape: backslash, double-quote, then newlines -> \n.
esc="$(printf '%s' "$stub" | sed 's/\\/\\\\/g; s/"/\\"/g' | awk '{printf "%s\\n", $0}')"
printf '{"additionalContext":"%s"}' "$esc"
rm -f "$sentinel"
exit 0
