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
                          input=stdin, capture_output=True, text=True)

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
            text = open(kt_md, encoding="utf-8").read()
            self.assertTrue(text.startswith("# KT — My headline"))
            self.assertIn("·  by Codex CLI", text)
            self.assertIn("## Resume prompt", text)          # body persisted verbatim
            self.assertEqual(len([f for f in os.listdir(os.path.join(d, ".kt"))
                                  if f.startswith("kt-")]), 1)
            sent = open(os.path.join(d, ".kt", ".pending-handoff"), encoding="utf-8").read().splitlines()
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

if __name__ == "__main__":
    unittest.main()
