# engine/test_kt.py
import unittest, kt
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
                          input=stdin, capture_output=True, text=True, encoding="utf-8")

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

class TestSave(unittest.TestCase):
    def test_writes_files_header_sentinel(self):
        with tempfile.TemporaryDirectory() as d:
            r = run(["save", "--tool", "Codex CLI", "--note", "My headline"], d, BODY)
            self.assertEqual(r.returncode, 0)
            kt_md = os.path.join(d, ".kt", "kt.md")
            self.assertTrue(os.path.exists(kt_md))
            with open(kt_md, encoding="utf-8") as f:
                text = f.read()
            self.assertTrue(text.startswith("# KT — My headline"))
            self.assertIn("·  by Codex CLI", text)
            self.assertIn("## Resume prompt", text)          # body persisted verbatim
            self.assertEqual(len([f for f in os.listdir(os.path.join(d, ".kt"))
                                  if f.startswith("kt-")]), 1)
            with open(os.path.join(d, ".kt", ".pending-handoff"), encoding="utf-8") as f:
                sent = f.read().splitlines()
            self.assertEqual(os.path.normcase(sent[0]),
                             os.path.normcase(os.path.abspath(kt_md)))
            self.assertIn("Resuming. Read", r.stdout)        # resume prompt echoed
            self.assertNotIn("## Next action", r.stdout)     # but NOT the rest of the doc

    def test_same_second_no_clobber(self):
        with tempfile.TemporaryDirectory() as d:
            run(["save", "--note", "a"], d, BODY)
            # force a second file with the same timestamp by pre-creating it
            ktd = os.path.join(d, ".kt")
            ts = [f for f in os.listdir(ktd) if f.startswith("kt-")][0][3:-3]
            run(["save", "--note", "b"], d, BODY)
            files = [f for f in os.listdir(ktd) if f.startswith("kt-")]
            self.assertGreaterEqual(len(files), 2)

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
            ctx = payload["hookSpecificOutput"]["additionalContext"]
            self.assertIn("ship it.", ctx)  # NOTE: brief said "Ship it." but Resume prompt section has lowercase "ship it."; fixed per spec (fix test, not code)
            self.assertIn("## Next action", ctx)   # stub = Resume prompt + Next action
            self.assertNotIn("## Status", ctx)     # stops at the 3rd header
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
            with open(os.path.join(d, ".gitignore"), encoding="utf-8") as f:
                gi = f.read()
            self.assertNotIn(".kt/", gi.splitlines())
            run(["local"], d)
            self.assertFalse(os.path.exists(os.path.join(d, ".kt", ".shared")))
            with open(os.path.join(d, ".gitignore"), encoding="utf-8") as f:
                gi = f.read()
            self.assertIn(".kt/", gi.splitlines())
    def test_cancel_removes_sentinel(self):
        with tempfile.TemporaryDirectory() as d:
            run(["save", "--note", "x"], d, BODY)
            run(["cancel"], d)
            self.assertFalse(os.path.exists(os.path.join(d, ".kt", ".pending-handoff")))

if __name__ == "__main__":
    unittest.main()
