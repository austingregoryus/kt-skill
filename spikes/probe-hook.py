import sys, json, os
raw = sys.stdin.read()
os.makedirs(os.path.join(os.path.dirname(__file__), "out"), exist_ok=True)
with open(os.path.join(os.path.dirname(__file__), "out", "hook-stdin.json"), "w", encoding="utf-8") as f:
    f.write(raw)
sys.stdout.write(json.dumps({"hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "KT probe: nested additionalContext works."}}))
