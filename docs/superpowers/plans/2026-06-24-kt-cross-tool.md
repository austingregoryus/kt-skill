# Cross-Tool KT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tool-neutral knowledge-transfer system — one Python engine (`~/.kt/kt.py`, on PATH as `kt`) plus thin `SKILL.md` shims — so handoffs pass bidirectionally between Claude Code, Codex CLI, Antigravity CLI, and any terminal.

**Architecture:** A single stdlib-only Python engine owns all mechanics (save/resume/format/inject/list/cancel/share/local) operating on a per-repo `.kt/` markdown folder. The LLM (via each tool's shim) authors the full handoff body; the engine does zero body parsing on save (only `kt inject` reads one named section). An idempotent installer puts `kt` on PATH and lays down per-tool shims.

**Tech Stack:** Python 3 (stdlib only — `argparse`, `subprocess`, `json`, `re`, `glob`, `datetime`, `os`), `unittest` for tests, git (optional, detected). Dev in the `kt-skill` repo; installer deploys to `~/.kt/` and tool dirs.

## Global Constraints

- Engine is a single file `engine/kt.py`, **Python 3 stdlib only**, no third-party deps.
- All file writes UTF-8 **without BOM**, `\n` line endings (`open(..., encoding="utf-8", newline="\n")`).
- Every subcommand accepts `--cwd DIR` (default `os.getcwd()`) and operates on `<cwd>/.kt/`.
- Header line format (engine-owned): `# KT — {note}  ·  {YYYY-MM-DD HH:MM}  ·  by {tool}` (em-dash `—`, middot `·`, two-space padding around each `·`).
- `kt save` does **no body parsing** beyond echoing the `## Resume prompt` section; it prepends the header and persists verbatim.
- `--note` is the sole headline source; `--tool` defaults to `unknown`.
- Sentinel `.kt/.pending-handoff`: line 1 = absolute path to `.kt/kt.md`, line 2 = ISO-8601 timestamp.
- Freshness guard: 30 minutes.
- `kt inject` output: **nested** `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"<stub>"}}`, always exit 0, inject nothing on any error, cross-project abs-path guard.
- `kt inject` stub = the `## Resume prompt` **section** (named, via the single `section()` primitive — never positional counting).
- Filenames `kt-YYYYMMDD-HHMMSS.md`, with `O_EXCL` + `-2`,`-3`… suffix on same-second collision.
- Shims are `SKILL.md` files; the Claude hook and shims invoke the engine via the **absolute** `python <abs>/kt.py …` form (PATH may be stale until restart).
- Run engine tests with: `python -m unittest discover -s engine -p "test_*.py"`.

---

### Task 0: Spike 0 — empirically verify platform mechanics

De-risks the whole project before any shim is built. Produces findings, not shipping code.

**Files:**
- Create: `spikes/cross-tool-FINDINGS.md`
- Create: `spikes/probe-hook.py`

**Interfaces:**
- Produces: confirmed answers consumed by Task 7 (Claude hook JSON shape), Task 8 (Codex skills dir, Antigravity slash-vs-conversational invocation).

- [ ] **Step 1: Write a probe hook that logs SessionStart stdin and emits a nested-JSON test stub**

```python
# spikes/probe-hook.py
import sys, json, os
raw = sys.stdin.read()
os.makedirs(os.path.join(os.path.dirname(__file__), "out"), exist_ok=True)
with open(os.path.join(os.path.dirname(__file__), "out", "hook-stdin.json"), "w", encoding="utf-8") as f:
    f.write(raw)
sys.stdout.write(json.dumps({"hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "KT probe: nested additionalContext works."}}))
```

- [ ] **Step 2: Write the findings procedure doc**

```markdown
# Cross-tool KT — Spike 0 findings

## A. Claude hook nested JSON  (CONSUMED BY Task 7)
Procedure: add to a throwaway project's .claude/settings.json:
  {"hooks":{"SessionStart":[{"hooks":[{"type":"command",
   "command":"python C:/Projects/kt-skill/spikes/probe-hook.py"}]}]}}
Start a session. Does "KT probe: nested additionalContext works." appear in context?
Result: <YES/NO/UNVERIFIED>

## B. Codex skills directory  (CONSUMED BY Task 8)
Find where Codex CLI loads skills (prompts are deprecated). Confirm the dir and
that a SKILL.md there is invocable and can run shell commands.
Result dir: <FILL IN / UNVERIFIED>

## C. Antigravity slash invocation  (CONSUMED BY Task 8)
Drop .agents/skills/kt-resume/SKILL.md (trivial body). Does `/kt-resume`
invoke it as a slash command, or only conversational triggering?
Result: <slash / conversational-only / UNVERIFIED>
```

- [ ] **Step 3: Run the probes and record results**

These require live tools (Claude session, Codex, `agy`). The implementer fills each `<...>` from actual runs. If a tool is unavailable in this environment, mark that item `UNVERIFIED` and note it — do NOT fabricate a result. Tasks 7/8 read these and adapt.

- [ ] **Step 4: Commit**

```bash
git add spikes/cross-tool-FINDINGS.md spikes/probe-hook.py
git commit -m "spike: probe cross-tool mechanics (hook JSON, codex skills, antigravity slash)"
```

---

### Task 1: Engine scaffold + shared helpers

Creates `engine/kt.py` with the CLI skeleton and the pure helpers every later task depends on: `section()`, `parse_header()`, `read_text()`, `write_text()`, `kt_dir()`, `is_git_repo()`. TDD on the two pure parsers.

**Files:**
- Create: `engine/kt.py`
- Test: `engine/test_kt.py`

**Interfaces:**
- Produces:
  - `section(body: str, name: str) -> list[str]` — content lines of `## name` up to next `## ` or EOF, leading/trailing blanks stripped; `[]` if absent.
  - `parse_header(first_line: str) -> dict` with keys `headline`, `time`, `tool` (tolerates 2- and 3-field headers; `tool="unknown"` when absent).
  - `read_text(path)->str`, `write_text(path, text)->None`, `kt_dir(cwd)->str`, `is_git_repo(cwd)->bool`.
  - `main(argv)->int` dispatching subcommands (stubs return 0 for now).

- [ ] **Step 1: Write failing tests for `section()` and `parse_header()`**

```python
# engine/test_kt.py
import unittest, kt

DOC = """# KT — Demo  ·  2026-06-24 10:00  ·  by Claude Code

## Resume prompt
Resuming work. Read `.kt/kt.md`.
Next: do the thing.

## Next action
Do the thing.

## Status
- Done: nothing
"""

class TestSection(unittest.TestCase):
    def test_extracts_named_section_only(self):
        self.assertEqual(kt.section(DOC, "Resume prompt"),
                         ["Resuming work. Read `.kt/kt.md`.", "Next: do the thing."])
    def test_stops_at_next_header(self):
        self.assertEqual(kt.section(DOC, "Next action"), ["Do the thing."])
    def test_missing_section_returns_empty(self):
        self.assertEqual(kt.section(DOC, "Nope"), [])

class TestParseHeader(unittest.TestCase):
    def test_three_field(self):
        h = kt.parse_header("# KT — Demo  ·  2026-06-24 10:00  ·  by Claude Code")
        self.assertEqual((h["headline"], h["time"], h["tool"]),
                         ("Demo", "2026-06-24 10:00", "Claude Code"))
    def test_two_field_legacy(self):
        h = kt.parse_header("# KT — Old  ·  2026-06-22 09:00")
        self.assertEqual((h["headline"], h["tool"]), ("Old", "unknown"))

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest discover -s engine -p "test_*.py"`
Expected: FAIL — `ModuleNotFoundError: No module named 'kt'` (or AttributeError).

- [ ] **Step 3: Write `engine/kt.py` scaffold + helpers**

```python
#!/usr/bin/env python3
"""kt — tool-neutral knowledge-transfer engine."""
import sys, os, re, json, glob, argparse, subprocess
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline="")  # no BOM, no CRLF

SENTINEL = ".pending-handoff"
SHARED = ".shared"
FRESH_MIN = 30

def kt_dir(cwd): return os.path.join(cwd, ".kt")
def read_text(path):
    with open(path, encoding="utf-8") as f: return f.read()
def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f: f.write(text)

def section(body, name):
    lines = body.splitlines()
    pat = re.compile(r'^##\s+' + re.escape(name) + r'\s*$')
    start = next((i + 1 for i, ln in enumerate(lines) if pat.match(ln)), None)
    if start is None: return []
    out = []
    for ln in lines[start:]:
        if re.match(r'^##\s+', ln): break
        out.append(ln)
    while out and not out[0].strip(): out.pop(0)
    while out and not out[-1].strip(): out.pop()
    return out

def parse_header(first_line):
    m = re.match(r'^#\s*KT\s*—\s*(.*)$', first_line)
    if not m:
        return {"headline": first_line.lstrip('# ').strip(), "time": "", "tool": "unknown"}
    parts = [p.strip() for p in m.group(1).split('·')]
    headline = parts[0] if parts else ""
    time = parts[1] if len(parts) > 1 else ""
    tool = parts[2][3:].strip() if len(parts) > 2 and parts[2].lower().startswith("by ") else "unknown"
    return {"headline": headline, "time": time, "tool": tool}

def is_git_repo(cwd):
    try:
        r = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                           cwd=cwd, capture_output=True, text=True)
        return r.returncode == 0 and r.stdout.strip() == "true"
    except FileNotFoundError:
        return False

def build_parser():
    p = argparse.ArgumentParser(prog="kt")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("save", "resume", "format", "inject", "list", "cancel", "share", "local"):
        sp = sub.add_parser(name)
        sp.add_argument("--cwd", default=None)
        if name == "save":
            sp.add_argument("--tool", default="unknown")
            sp.add_argument("--note", default="")
        if name == "resume":
            sp.add_argument("timestamp", nargs="?", default=None)
    return p

def main(argv):
    args = build_parser().parse_args(argv)
    args.cwd = args.cwd or os.getcwd()
    return DISPATCH[args.cmd](args)

# Subcommand stubs (filled in later tasks)
def cmd_save(args): return 0
def cmd_resume(args): return 0
def cmd_format(args): return 0
def cmd_inject(args): return 0
def cmd_list(args): return 0
def cmd_cancel(args): return 0
def cmd_share(args): return 0
def cmd_local(args): return 0

DISPATCH = {"save": cmd_save, "resume": cmd_resume, "format": cmd_format,
            "inject": cmd_inject, "list": cmd_list, "cancel": cmd_cancel,
            "share": cmd_share, "local": cmd_local}

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest discover -s engine -p "test_*.py"`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add engine/kt.py engine/test_kt.py
git commit -m "feat: kt engine scaffold + section/parse_header helpers"
```

---

### Task 2: `kt save`

**Files:**
- Modify: `engine/kt.py` (implement `cmd_save`, add `unique_path`, `ensure_gitignore`)
- Test: `engine/test_kt.py` (add `TestSave`)

**Interfaces:**
- Consumes: `section`, `read_text`, `write_text`, `kt_dir`, `is_git_repo`.
- Produces: `cmd_save(args)` — reads stdin body, writes `.kt/kt-<ts>.md` + `.kt/kt.md`, sentinel, gitignore; echoes Resume prompt; returns 0 / non-zero. `unique_path(d, ts)->str`, `ensure_gitignore(cwd)->None`.

- [ ] **Step 1: Write failing tests**

```python
# add to engine/test_kt.py
import os, tempfile, subprocess, sys, json
KT = os.path.join(os.path.dirname(__file__), "kt.py")
BODY = """## Resume prompt
Resuming. Read `.kt/kt.md`.
Next: ship it.

## Next action
Ship it.
"""
def run(args, cwd, stdin=""):
    return subprocess.run([sys.executable, KT, *args, "--cwd", cwd],
                          input=stdin, capture_output=True, text=True)

class TestSave(unittest.TestCase):
    def test_writes_files_header_sentinel(self):
        with tempfile.TemporaryDirectory() as d:
            r = run(["save", "--tool", "Codex CLI", "--note", "My headline"], d, BODY)
            self.assertEqual(r.returncode, 0)
            kt_md = os.path.join(d, ".kt", "kt.md")
            self.assertTrue(os.path.exists(kt_md))
            text = open(kt_md, encoding="utf-8").read()
            self.assertTrue(text.startswith("# KT — My headline"))
            self.assertIn("· by Codex CLI", text)
            self.assertIn("## Resume prompt", text)          # body persisted verbatim
            self.assertEqual(len([f for f in os.listdir(os.path.join(d, ".kt"))
                                  if f.startswith("kt-")]), 1)
            sent = open(os.path.join(d, ".kt", ".pending-handoff"), encoding="utf-8").read().splitlines()
            self.assertEqual(os.path.normcase(sent[0]),
                             os.path.normcase(os.path.abspath(kt_md)))
            self.assertIn("Ship it.", r.stdout)              # resume prompt echoed

    def test_same_second_no_clobber(self):
        with tempfile.TemporaryDirectory() as d:
            run(["save", "--note", "a"], d, BODY)
            # force a second file with the same timestamp by pre-creating it
            ktd = os.path.join(d, ".kt")
            ts = [f for f in os.listdir(ktd) if f.startswith("kt-")][0][3:-3]
            run(["save", "--note", "b"], d, BODY)
            files = [f for f in os.listdir(ktd) if f.startswith("kt-")]
            self.assertGreaterEqual(len(files), 2)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s engine -p "test_*.py"`
Expected: FAIL (cmd_save is a stub; no files written).

- [ ] **Step 3: Implement `cmd_save`, `unique_path`, `ensure_gitignore`**

```python
def unique_path(d, ts):
    n = 2
    cand = os.path.join(d, f"kt-{ts}.md")
    while True:
        try:
            os.close(os.open(cand, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644))
            return cand
        except FileExistsError:
            cand = os.path.join(d, f"kt-{ts}-{n}.md"); n += 1

def ensure_gitignore(cwd):
    if not is_git_repo(cwd): return
    gi = os.path.join(cwd, ".gitignore")
    existing = read_text(gi) if os.path.exists(gi) else ""
    if any(l.strip() == ".kt/" for l in existing.splitlines()): return
    with open(gi, "a", encoding="utf-8", newline="\n") as f:
        if existing and not existing.endswith("\n"): f.write("\n")
        f.write(".kt/\n")

def cmd_save(args):
    d = kt_dir(args.cwd)
    body = sys.stdin.read()
    now = datetime.now()
    header = f"# KT — {args.note}  ·  {now.strftime('%Y-%m-%d %H:%M')}  ·  by {args.tool}\n\n"
    doc = header + body
    try:
        os.makedirs(d, exist_ok=True)
        path = unique_path(d, now.strftime("%Y%m%d-%H%M%S"))
        write_text(path, doc)
        write_text(os.path.join(d, "kt.md"), doc)
    except OSError as e:
        print(f"kt save: cannot write {d}: {e}", file=sys.stderr)
        rp = section(body, "Resume prompt")
        if rp: print("\n".join(rp))
        return 1
    kt_md_abs = os.path.abspath(os.path.join(d, "kt.md"))
    write_text(os.path.join(d, SENTINEL), kt_md_abs + "\n" + now.astimezone().isoformat() + "\n")
    if not os.path.exists(os.path.join(d, SHARED)):
        ensure_gitignore(args.cwd)
    rp = section(body, "Resume prompt")
    if rp: print("\n".join(rp))
    return 0
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest discover -s engine -p "test_*.py"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add engine/kt.py engine/test_kt.py
git commit -m "feat: kt save"
```

---

### Task 3: `kt resume` + `kt list`

**Files:**
- Modify: `engine/kt.py` (implement `cmd_resume`, `cmd_list`, add `first_line`, `format_entry`, `recent_files`)
- Test: `engine/test_kt.py` (add `TestResume`)

**Interfaces:**
- Consumes: `parse_header`, `read_text`, `kt_dir`.
- Produces: `cmd_resume(args)`, `cmd_list(args)`; `first_line(path)->str`, `format_entry(path)->str` (`"<basename> — <headline> (by <tool>, <time>)"`), `recent_files(d, limit=None)->list[str]` (newest first).

- [ ] **Step 1: Write failing tests**

```python
# add to engine/test_kt.py
class TestResume(unittest.TestCase):
    def test_prints_latest_and_footer(self):
        with tempfile.TemporaryDirectory() as d:
            run(["save", "--tool", "Claude Code", "--note", "First"], d, BODY)
            r = run(["resume"], d)
            self.assertEqual(r.returncode, 0)
            self.assertIn("# KT — First", r.stdout)
            self.assertIn("--- Recent handoffs ---", r.stdout)
            self.assertIn("(by Claude Code,", r.stdout)
    def test_missing_handoff_errors(self):
        with tempfile.TemporaryDirectory() as d:
            r = run(["resume"], d)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("no handoff", r.stderr.lower())
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s engine -p "test_*.py"`
Expected: FAIL (cmd_resume stub returns 0, prints nothing).

- [ ] **Step 3: Implement resume/list helpers**

```python
def first_line(path):
    with open(path, encoding="utf-8") as f:
        return f.readline().rstrip("\n")

def format_entry(path):
    h = parse_header(first_line(path))
    return f"{os.path.basename(path)} — {h['headline']} (by {h['tool']}, {h['time']})"

def recent_files(d, limit=None):
    files = sorted(glob.glob(os.path.join(d, "kt-*.md")), reverse=True)
    return files[:limit] if limit else files

def cmd_resume(args):
    d = kt_dir(args.cwd)
    target = os.path.join(d, f"kt-{args.timestamp}.md") if args.timestamp \
             else os.path.join(d, "kt.md")
    if not os.path.exists(target):
        print(f"kt resume: no handoff found at {target}", file=sys.stderr)
        return 1
    print(read_text(target))
    print("--- Recent handoffs ---")
    for f in recent_files(d, 5):
        print(format_entry(f))
    return 0

def cmd_list(args):
    d = kt_dir(args.cwd)
    files = recent_files(d)
    if not files:
        print("kt list: no handoffs", file=sys.stderr); return 1
    for f in files:
        print(format_entry(f))
    return 0
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest discover -s engine -p "test_*.py"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add engine/kt.py engine/test_kt.py
git commit -m "feat: kt resume + list"
```

---

### Task 4: `kt inject`

**Files:**
- Modify: `engine/kt.py` (implement `cmd_inject`, add `safe_remove`)
- Test: `engine/test_kt.py` (add `TestInject`)

**Interfaces:**
- Consumes: `section`, `read_text`, `kt_dir`, `SENTINEL`, `FRESH_MIN`.
- Produces: `cmd_inject(args)` — reads SessionStart JSON on stdin, emits nested `hookSpecificOutput` JSON for a fresh+consistent sentinel, else nothing; always returns 0; `safe_remove(path)`.

- [ ] **Step 1: Write failing tests**

```python
# add to engine/test_kt.py
from datetime import datetime, timedelta
def drop_sentinel(d, when):
    ktd = os.path.join(d, ".kt"); os.makedirs(ktd, exist_ok=True)
    with open(os.path.join(ktd, ".pending-handoff"), "w", encoding="utf-8", newline="\n") as f:
        f.write(os.path.abspath(os.path.join(ktd, "kt.md")) + "\n" + when.astimezone().isoformat() + "\n")
def inject(d):
    return subprocess.run([sys.executable, KT, "inject"],
                          input=json.dumps({"cwd": d}), capture_output=True, text=True)

class TestInject(unittest.TestCase):
    def test_no_sentinel_no_output(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".kt"))
            r = inject(d)
            self.assertEqual(r.returncode, 0); self.assertEqual(r.stdout.strip(), "")
    def test_fresh_emits_nested_json(self):
        with tempfile.TemporaryDirectory() as d:
            run(["save", "--note", "x"], d, BODY)        # writes kt.md + a fresh sentinel
            r = inject(d)
            self.assertEqual(r.returncode, 0)
            payload = json.loads(r.stdout)
            self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "SessionStart")
            self.assertIn("Ship it.", payload["hookSpecificOutput"]["additionalContext"])
            self.assertFalse(os.path.exists(os.path.join(d, ".kt", ".pending-handoff")))
            self.assertFalse(r.stdout.startswith("﻿"))   # no BOM
    def test_stale_no_output_deletes(self):
        with tempfile.TemporaryDirectory() as d:
            run(["save", "--note", "x"], d, BODY)
            drop_sentinel(d, datetime.now() - timedelta(minutes=45))
            r = inject(d)
            self.assertEqual(r.stdout.strip(), "")
            self.assertFalse(os.path.exists(os.path.join(d, ".kt", ".pending-handoff")))
    def test_cross_project_guard(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as other:
            run(["save", "--note", "x"], d, BODY)
            # sentinel points at d's kt.md but we inject with cwd=other → must not emit
            ktd_other = os.path.join(other, ".kt"); os.makedirs(ktd_other)
            with open(os.path.join(ktd_other, ".pending-handoff"), "w", encoding="utf-8", newline="\n") as f:
                f.write(os.path.abspath(os.path.join(d, ".kt", "kt.md")) + "\n"
                        + datetime.now().astimezone().isoformat() + "\n")
            r = inject(other)
            self.assertEqual(r.stdout.strip(), "")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s engine -p "test_*.py"`
Expected: FAIL (cmd_inject stub emits nothing but also doesn't delete/guard; fresh test fails).

- [ ] **Step 3: Implement `cmd_inject`**

```python
def safe_remove(path):
    try: os.remove(path)
    except OSError: pass

def cmd_inject(args):
    try:
        raw = sys.stdin.read()
        cwd = args.cwd
        try:
            j = json.loads(raw)
            if isinstance(j, dict) and j.get("cwd"): cwd = j["cwd"]
        except Exception:
            pass
        d = kt_dir(cwd)
        sentinel = os.path.join(d, SENTINEL)
        if not os.path.exists(sentinel): return 0
        lines = read_text(sentinel).splitlines()
        if len(lines) < 2: safe_remove(sentinel); return 0
        doc_path, iso = lines[0].strip(), lines[1].strip()
        try:
            then = datetime.fromisoformat(iso)
        except ValueError:
            safe_remove(sentinel); return 0
        now = datetime.now(then.tzinfo) if then.tzinfo else datetime.now()
        if (now - then).total_seconds() / 60 > FRESH_MIN:
            safe_remove(sentinel); return 0
        expected = os.path.abspath(os.path.join(d, "kt.md"))
        if os.path.normcase(os.path.abspath(doc_path)) != os.path.normcase(expected):
            safe_remove(sentinel); return 0
        if not os.path.exists(doc_path):
            safe_remove(sentinel); return 0
        rp = section(read_text(doc_path), "Resume prompt")
        if not rp: safe_remove(sentinel); return 0
        stub = "## Resume prompt\n" + "\n".join(rp) + "\n\n(Read .kt/kt.md for the full handoff.)"
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "SessionStart", "additionalContext": stub}}))
        safe_remove(sentinel)
        return 0
    except Exception:
        return 0
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest discover -s engine -p "test_*.py"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add engine/kt.py engine/test_kt.py
git commit -m "feat: kt inject (nested hookSpecificOutput, cross-project guard)"
```

---

### Task 5: `kt format`, `kt cancel`, `kt share`, `kt local`

**Files:**
- Modify: `engine/kt.py` (implement the four; add `TEMPLATE` constant, `gitignore_remove`)
- Test: `engine/test_kt.py` (add `TestFormatToggles`)

**Interfaces:**
- Consumes: `kt_dir`, `ensure_gitignore`, `SHARED`, `SENTINEL`, `section`.
- Produces: `cmd_format` (prints `TEMPLATE`), `cmd_cancel`, `cmd_share`, `cmd_local`; `gitignore_remove(cwd)->None`. `TEMPLATE` MUST contain `## Resume prompt` and `## Next action` so `section()` round-trips.

- [ ] **Step 1: Write failing tests**

```python
# add to engine/test_kt.py
class TestFormatToggles(unittest.TestCase):
    def test_format_prints_template_with_sections(self):
        with tempfile.TemporaryDirectory() as d:
            r = run(["format"], d)
            self.assertEqual(r.returncode, 0)
            self.assertIn("## Resume prompt", r.stdout)
            self.assertIn("## Next action", r.stdout)
            self.assertEqual(kt.section(r.stdout, "Next action")[:0], [])  # section() parses it
            self.assertTrue(kt.section(r.stdout, "Resume prompt"))
    def test_share_then_local(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init", "-q"], cwd=d)
            run(["save", "--note", "x"], d, BODY)             # gitignores .kt/
            run(["share"], d)
            self.assertTrue(os.path.exists(os.path.join(d, ".kt", ".shared")))
            gi = open(os.path.join(d, ".gitignore"), encoding="utf-8").read()
            self.assertNotIn(".kt/", gi.splitlines())
            run(["local"], d)
            self.assertFalse(os.path.exists(os.path.join(d, ".kt", ".shared")))
            gi = open(os.path.join(d, ".gitignore"), encoding="utf-8").read()
            self.assertIn(".kt/", gi.splitlines())
    def test_cancel_removes_sentinel(self):
        with tempfile.TemporaryDirectory() as d:
            run(["save", "--note", "x"], d, BODY)
            run(["cancel"], d)
            self.assertFalse(os.path.exists(os.path.join(d, ".kt", ".pending-handoff")))
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s engine -p "test_*.py"`
Expected: FAIL (format prints nothing; share/local/cancel are stubs).

- [ ] **Step 3: Implement the four commands**

```python
TEMPLATE = """## Resume prompt
Resuming work. Read `.kt/kt.md` for the full handoff.
TL;DR: <headline>. Next: <next action>.
Start by <next action>, then continue.

## Next action
<the single most important first thing the next context should do>

## Status
- Done: ...
- In progress: ...
- Not started: ...

## Mental model
<current hypothesis/understanding — include ONLY if there is a real one>

## Decisions + rationale
- <decision> — <why>

## Dead ends
- <thing tried> — <why it failed / don't repeat>

## Key files
- path/to/file — <one-line why it matters>

## Signals (auto)
- Branch: <git rev-parse --abbrev-ref HEAD>
- Uncommitted: <git status -s, with .kt/ filtered, or "clean">
- Recent commits:
  - <git log -5 --oneline>
- Todos: <current todo list, or omit>
"""

def gitignore_remove(cwd):
    gi = os.path.join(cwd, ".gitignore")
    if not os.path.exists(gi): return
    kept = [l for l in read_text(gi).splitlines() if l.strip() != ".kt/"]
    write_text(gi, ("\n".join(kept) + "\n") if kept else "")

def cmd_format(args):
    sys.stdout.write(TEMPLATE); return 0

def cmd_cancel(args):
    safe_remove(os.path.join(kt_dir(args.cwd), SENTINEL))
    print("kt: pending handoff cancelled."); return 0

def cmd_share(args):
    d = kt_dir(args.cwd); os.makedirs(d, exist_ok=True)
    write_text(os.path.join(d, SHARED), "")
    gitignore_remove(args.cwd)
    print("kt: handoffs are now git-tracked (shared)."); return 0

def cmd_local(args):
    safe_remove(os.path.join(kt_dir(args.cwd), SHARED))
    ensure_gitignore(args.cwd)
    print("kt: handoffs are now local-only (gitignored)."); return 0
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest discover -s engine -p "test_*.py"`
Expected: PASS (full engine suite green).

- [ ] **Step 5: Commit**

```bash
git add engine/kt.py engine/test_kt.py
git commit -m "feat: kt format/cancel/share/local — engine complete"
```

---

### Task 6: Installer `kt-install.py`

**Files:**
- Create: `engine/kt-install.py`
- Test: `engine/test_install.py`

**Interfaces:**
- Consumes: `engine/kt.py` (copied), shim sources under `shims/` (created in Tasks 7-8; installer tolerates missing shim dirs and reports them skipped).
- Produces: a `main(argv, home=None)->int` where `home` overrides the install root for testing. Functions: `install_engine(home)`, `write_wrappers(home)`, `path_instructions(home)->str`. Deploys `kt.py` to `<home>/.kt/`, writes `<home>/.kt/kt` (POSIX) + `<home>/.kt/kt.cmd` (Windows), prints PATH + restart guidance. Idempotent.

- [ ] **Step 1: Write failing tests**

```python
# engine/test_install.py
import unittest, os, tempfile, importlib.util, sys
SPEC = importlib.util.spec_from_file_location(
    "kt_install", os.path.join(os.path.dirname(__file__), "kt-install.py"))
ki = importlib.util.module_from_spec(SPEC)

class TestInstaller(unittest.TestCase):
    @classmethod
    def setUpClass(cls): SPEC.loader.exec_module(ki)
    def test_installs_engine_and_wrappers_idempotently(self):
        with tempfile.TemporaryDirectory() as home:
            self.assertEqual(ki.main([], home=home), 0)
            ktdir = os.path.join(home, ".kt")
            self.assertTrue(os.path.exists(os.path.join(ktdir, "kt.py")))
            self.assertTrue(os.path.exists(os.path.join(ktdir, "kt")))       # POSIX wrapper (also on Win)
            self.assertTrue(os.path.exists(os.path.join(ktdir, "kt.cmd")))   # Windows wrapper
            cmd = open(os.path.join(ktdir, "kt.cmd"), encoding="utf-8").read()
            self.assertIn('python "%~dp0kt.py" %*', cmd)
            # idempotent: second run still 0, no duplicate content growth
            before = open(os.path.join(ktdir, "kt"), encoding="utf-8").read()
            self.assertEqual(ki.main([], home=home), 0)
            after = open(os.path.join(ktdir, "kt"), encoding="utf-8").read()
            self.assertEqual(before, after)
    def test_path_instructions_mention_restart(self):
        with tempfile.TemporaryDirectory() as home:
            ki.main([], home=home)
            self.assertIn("restart", ki.path_instructions(home).lower())
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s engine -p "test_*.py"`
Expected: FAIL (kt-install.py missing).

- [ ] **Step 3: Implement `kt-install.py`**

```python
#!/usr/bin/env python3
"""Install the kt engine to ~/.kt, write PATH wrappers, and lay down shims."""
import sys, os, shutil, argparse

REPO = os.path.dirname(os.path.abspath(__file__))

def install_engine(home):
    ktdir = os.path.join(home, ".kt")
    os.makedirs(ktdir, exist_ok=True)
    shutil.copy2(os.path.join(REPO, "kt.py"), os.path.join(ktdir, "kt.py"))
    return ktdir

def write_wrappers(ktdir):
    posix = os.path.join(ktdir, "kt")
    with open(posix, "w", encoding="utf-8", newline="\n") as f:
        f.write('#!/usr/bin/env python3\nimport os, sys\n'
                'os.execvp(sys.executable, [sys.executable, '
                'os.path.join(os.path.dirname(os.path.abspath(__file__)), "kt.py")] + sys.argv[1:])\n')
    try: os.chmod(posix, 0o755)
    except OSError: pass
    with open(os.path.join(ktdir, "kt.cmd"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write('@python "%~dp0kt.py" %*\n')

def path_instructions(home):
    ktdir = os.path.join(home, ".kt")
    return (
        f"Add to PATH: {ktdir}\n"
        f"  Windows: append to the registry HKCU\\Environment 'Path' (REG_EXPAND_SZ) — "
        f"NOT setx (it truncates at 1024 chars) — then broadcast WM_SETTINGCHANGE.\n"
        f"  POSIX: add 'export PATH=\"$HOME/.kt:$PATH\"' to your shell profile.\n"
        f"IMPORTANT: already-running terminals and AI tools will NOT see the new PATH "
        f"until you restart them. The shims/hook use the absolute 'python {ktdir}/kt.py ...' "
        f"form so they work before restart.\n")

def main(argv, home=None):
    parser = argparse.ArgumentParser(prog="kt-install")
    parser.parse_args(argv)
    home = home or os.path.expanduser("~")
    if not any(shutil.which(p) for p in ("python", "python3", "py")):
        print("kt-install: no python interpreter found on PATH.", file=sys.stderr)
        return 1
    ktdir = install_engine(home)
    write_wrappers(ktdir)
    print(f"kt: engine installed to {ktdir}")
    print(path_instructions(home))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

(Note: actual PATH/registry mutation and shim-copying are performed by the
documented manual steps + Task 9; the installer's automated scope here is
engine + wrappers + guidance, which is what is unit-testable without mutating
the real environment.)

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest discover -s engine -p "test_*.py"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add engine/kt-install.py engine/test_install.py
git commit -m "feat: kt-install (engine + PATH wrappers + guidance, idempotent)"
```

---

### Task 7: Claude Code shims + repointed hook

Depends on Spike 0 result A (hook nested JSON). Refactors the existing Claude `/kt` skill to call the engine and adds `/kt-resume`.

**Files:**
- Create: `shims/claude/kt/SKILL.md`
- Create: `shims/claude/kt-resume/SKILL.md`
- Create: `shims/claude/settings.hook.example.json`

**Interfaces:**
- Consumes: `kt format`, `kt save`, `kt resume`, `kt inject` (engine).

- [ ] **Step 1: Write the Claude `/kt` shim**

````markdown
---
name: kt
description: Knowledge-Transfer handoff. Use when the user runs /kt or wants to snapshot working state into a tool-neutral .kt/ handoff so another AI tool (or a fresh context) can resume. Lightweight alternative to /compact.
---

# /kt — Knowledge Transfer (cross-tool)

Snapshot the current working state via the shared `kt` engine.

## Steps

1. Parse the text after `/kt`: `--share`/`--local`/`--cancel` → run
   `python ~/.kt/kt.py <that>` and STOP. Otherwise the text (if any) is the
   handoff **headline note**; if empty, derive it from the active todo or the
   user's last stated goal.
2. Get the canonical template: run `python ~/.kt/kt.py format`.
3. Author the full handoff **body** following that template — including the
   `## Signals (auto)` section, for which YOU run:
   `git rev-parse --abbrev-ref HEAD`, `git status -s` (drop any `.kt/` lines),
   `git log -5 --oneline`, and the current todo list. Omit empty sections;
   always include Resume prompt + Next action.
4. Pipe the body to the engine:
   `printf '%s' "<body>" | python ~/.kt/kt.py save --tool "Claude Code" --note "<headline>"`
   (Use a heredoc/temp file for multi-line bodies.)
5. Show the engine's stdout (the resume prompt) to the user.

Use the absolute `python ~/.kt/kt.py` form (PATH may be stale until restart).
On Windows the home path is `C:/Users/<you>/.kt/kt.py`.
````

- [ ] **Step 2: Write the Claude `/kt-resume` shim**

````markdown
---
name: kt-resume
description: Resume work from a KT handoff. Use when the user runs /kt-resume or wants to pick up work captured by /kt (possibly from another AI tool). Reads the latest .kt/ handoff and continues.
---

# /kt-resume — Resume from a Knowledge-Transfer handoff

1. Run `python ~/.kt/kt.py resume` (append a timestamp arg to target an older
   handoff, e.g. `resume 20260624-103000`).
2. Read its stdout: the full latest handoff plus a "Recent handoffs" list.
3. If the handoff references other files (e.g. `.remember/remember.md` or files
   under "Key files"), read those too.
4. Begin with the handoff's **Next action**, then continue the work.

If stdout is a "no handoff found" error, tell the user there is nothing to
resume in this directory.
````

- [ ] **Step 3: Write the hook example (nested-JSON engine, absolute path)**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python C:/Users/<you>/.kt/kt.py inject"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 4: Validate the JSON + frontmatter**

Run:
```bash
python -c "import json; json.load(open('shims/claude/settings.hook.example.json')); print('json ok')"
python -c "import re,sys; t=open('shims/claude/kt/SKILL.md',encoding='utf-8').read(); print('fm ok' if re.match(r'^---\nname: kt\n', t) else sys.exit('bad fm'))"
python -c "import re,sys; t=open('shims/claude/kt-resume/SKILL.md',encoding='utf-8').read(); print('fm ok' if re.match(r'^---\nname: kt-resume\n', t) else sys.exit('bad fm'))"
```
Expected: `json ok`, `fm ok`, `fm ok`.

- [ ] **Step 5: Commit**

```bash
git add shims/claude/
git commit -m "feat: Claude kt + kt-resume shims, engine-backed hook"
```

---

### Task 8: Codex + Antigravity shims

Depends on Spike 0 results B (Codex skills dir) and C (Antigravity invocation). The SKILL.md content mirrors Claude's shims (same engine calls), differing only in `--tool` and the documented invocation/trigger.

**Files:**
- Create: `shims/codex/kt/SKILL.md`, `shims/codex/kt-resume/SKILL.md`
- Create: `shims/antigravity/kt/SKILL.md`, `shims/antigravity/kt-resume/SKILL.md`
- Create: `shims/README.md` (install locations per tool, from Spike 0)

- [ ] **Step 1: Write the Codex `/kt` and `/kt-resume` shims**

Codex `kt/SKILL.md` — identical body to Claude's `/kt` shim (Task 7 Step 1) except the save line uses `--tool "Codex CLI"`:
````markdown
---
name: kt
description: Knowledge-Transfer handoff via the shared kt engine. Snapshot working state into a tool-neutral .kt/ handoff so another AI tool or a fresh context can resume.
---

# /kt — Knowledge Transfer (cross-tool)

1. Parse args after /kt: `--share`/`--local`/`--cancel` → run
   `python ~/.kt/kt.py <that>` and STOP. Else the text is the headline note;
   if empty, derive from the active task or last goal.
2. Run `python ~/.kt/kt.py format` to get the template.
3. Author the full body per the template, including `## Signals (auto)` —
   run `git rev-parse --abbrev-ref HEAD`, `git status -s` (drop `.kt/` lines),
   `git log -5 --oneline`. Omit empty sections; keep Resume prompt + Next action.
4. Pipe to: `python ~/.kt/kt.py save --tool "Codex CLI" --note "<headline>"`.
5. Show the engine stdout (resume prompt) to the user.

Note: Codex auto-loads AGENTS.md; this skill does not modify it.
````

Codex `kt-resume/SKILL.md` — identical to Claude's `/kt-resume` (Task 7 Step 2) verbatim.

- [ ] **Step 2: Write the Antigravity `/kt` and `/kt-resume` shims**

Same two SKILL.md bodies as Codex but `--tool "Antigravity CLI"`. Frontmatter `name: kt` / `name: kt-resume`. If Spike 0 result C is `conversational-only`, add this line under each title:

```
NOTE: On Antigravity, invoke by asking the agent ("save a KT handoff" /
"resume from KT") — explicit /kt slash invocation is not supported on this build.
```

- [ ] **Step 3: Write `shims/README.md` with per-tool install locations**

```markdown
# kt shims — install locations

Copy each tool's `kt/` and `kt-resume/` SKILL.md folders to:

- Claude Code:   ~/.claude/skills/
- Codex CLI:     <SKILLS DIR FROM spikes/cross-tool-FINDINGS.md §B>
- Antigravity:   .agents/skills/   (project-scoped; per spikes §C)

All shims call the engine via the absolute `python ~/.kt/kt.py ...` form.
Generic/any tool: no shim needed — run `kt resume` / `kt save` directly.
```

- [ ] **Step 4: Validate frontmatter on all four shims**

Run:
```bash
python -c "import re,glob,sys
for p in glob.glob('shims/{codex,antigravity}/*/SKILL.md', recursive=False):
    t=open(p,encoding='utf-8').read()
    assert re.match(r'^---\nname: (kt|kt-resume)\n', t), p
print('all fm ok')"
```
Expected: `all fm ok`. (If the brace-glob is unsupported by the shell, run two globs.)

- [ ] **Step 5: Commit**

```bash
git add shims/
git commit -m "feat: Codex + Antigravity shims + shims README"
```

---

### Task 9: Acceptance, install, and migration note

**Files:**
- Create: `tests/cross-tool-acceptance.md`
- Modify: `README.md` (point at the engine + installer + migration note)

- [ ] **Step 1: Run the full engine suite as a gate**

Run: `python -m unittest discover -s engine -p "test_*.py"`
Expected: all tests pass (`OK`). If anything fails, STOP and report BLOCKED.

- [ ] **Step 2: Write the acceptance checklist**

```markdown
# Cross-tool KT acceptance

Run with the engine installed (`python engine/kt-install.py`) and shims copied.

## A. Engine round trip (any terminal)
- [ ] `printf '## Resume prompt\nx\n\n## Next action\ny\n' | python ~/.kt/kt.py save --tool "Manual" --note "t"`
- [ ] `python ~/.kt/kt.py resume` prints the doc + "Recent handoffs".
- [ ] `python ~/.kt/kt.py list` lists it; `--- by Manual` provenance shown.

## B. Claude save → resume
- [ ] `/kt fixing X` writes `.kt/kt.md` (header `· by Claude Code`), prints resume prompt.
- [ ] `/kt-resume` reads it back and starts at Next action.

## C. Cross-tool (the headline feature)
- [ ] `/kt` in Claude, then in Codex run `/kt-resume` (or its skill): Codex
      resumes from the Claude-authored handoff; provenance shows "by Claude Code".

## D. Hook auto-inject (Claude)
- [ ] With the Task 7 hook in a project's .claude/settings.json, `/kt` then
      `/clear`: the stub auto-injects (nested hookSpecificOutput). Sentinel gone.

## E. Toggles
- [ ] `/kt --share` then `/kt --local` flip `.kt/.shared` + `.gitignore`.
- [ ] `/kt --cancel` deletes a pending sentinel.
```

- [ ] **Step 3: Update README with install + migration note**

Add a section to `README.md`:
```markdown
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
```

- [ ] **Step 4: Commit**

```bash
git add tests/cross-tool-acceptance.md README.md
git commit -m "test: cross-tool acceptance + install/migration docs"
```

---

## Self-Review

**Spec coverage:**
- Engine, Python stdlib, `.kt/` per repo, `--cwd` → Tasks 1-5, Global Constraints.
- `section()` single primitive → Task 1; used only by inject (Task 4).
- `kt save` no-parse, header, sentinel, gitignore, O_EXCL, resume echo → Task 2.
- `kt resume` latest+footer, header tolerance, `kt list` → Task 3.
- `kt inject` nested JSON, freshness, cross-project guard, always-0, no-BOM → Task 4.
- `kt format` inlined template, `cancel`/`share`/`local` → Task 5.
- Installer: engine copy, POSIX (incl. Windows) + cmd wrappers, registry/restart guidance, idempotent → Task 6.
- Claude shims + repointed nested-JSON hook (absolute path) → Task 7.
- Codex skill (not deprecated prompt) + Antigravity shim (slash/conversational per spike) + AGENTS.md note → Task 8.
- Spike 0 (Antigravity invocation, Codex dir, hook JSON) → Task 0, consumed by 7/8.
- Provenance header + 2/3-field tolerance → Tasks 2,3.
- Migration (supersede inject scripts, per-repo repoint, format compat) → Task 9.
- Generic/any-tool usage → Task 9 acceptance A, shims/README.
- Edge cases (no git, unwritable, no handoff, stale, concurrent) → Tasks 2,3,4 tests.

**Placeholder scan:** No TBD/TODO in shipping code. Intentional fill-ins are Spike 0 results (real measurements) and the Spike-0-conditional Antigravity NOTE line (verbatim text supplied). The installer note explicitly bounds its automated scope (engine+wrappers+guidance) vs the documented manual PATH/shim steps — not a placeholder.

**Type/name consistency:** `section(body,name)->list[str]` used identically in save (echo), inject (stub), format test. `parse_header`/`format_entry`/`recent_files` consistent across resume+list. Sentinel format (abs path, ISO) written in `cmd_save` and read in `cmd_inject` identically. Engine invoked as `python ~/.kt/kt.py <cmd>` in every shim and the hook. `--tool`/`--note` flags consistent across shims.
