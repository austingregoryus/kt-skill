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
