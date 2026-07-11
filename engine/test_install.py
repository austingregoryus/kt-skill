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
            with open(os.path.join(ktdir, "kt.cmd"), encoding="utf-8") as f:
                cmd = f.read()
            self.assertIn(f'@"{sys.executable}" "%~dp0kt.py" %*', cmd)
            self.assertNotIn('@python ', cmd)
            # idempotent: second run still 0, no duplicate content growth
            with open(os.path.join(ktdir, "kt"), encoding="utf-8") as f:
                before = f.read()
            self.assertEqual(ki.main([], home=home), 0)
            with open(os.path.join(ktdir, "kt"), encoding="utf-8") as f:
                after = f.read()
            self.assertEqual(before, after)
    def test_path_instructions_mention_restart(self):
        with tempfile.TemporaryDirectory() as home:
            ki.main([], home=home)
            self.assertIn("restart", ki.path_instructions(home).lower())
