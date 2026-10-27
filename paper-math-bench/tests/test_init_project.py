# Contents
# 1. Module setup: imports and init_project loader.
# 2. ProjectTests: creation, reuse, and invalid target checks.
# 3. Test entry point: unittest.main().

"""Verify creation and lossless reuse of TeX project files."""

# Module setup
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("bench_init", Path(__file__).resolve().parents[1] / "scripts/init_project.py")
init_project = importlib.util.module_from_spec(spec)
spec.loader.exec_module(init_project)


# ProjectTests: project creation and reuse
class ProjectTests(unittest.TestCase):
    def test_template_has_only_tier_sections_and_global_problem_counter(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project"
            init_project.initialize(path)
            text = (path / "main.tex").read_text()
            self.assertEqual(re.findall(r"\\section\{([^}]+)\}", text),
                             ["T2", "T3", "T4", "Solutions"])
            self.assertIn(r"\newtheorem{problem}{Problem}", text)
            self.assertNotRegex(text, r"\\newtheorem\{problem\}[^\n]*\[section\]")
            self.assertNotIn(r"\setcounter{problem}", text)
            self.assertNotIn(r"\begin{problem}[", text)

    def test_new_then_reuse_preserves_user_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project"
            self.assertEqual(len(init_project.initialize(path)["created"]), 2)
            contents = "custom user format\n\\medskip\n"
            (path / "main.tex").write_text(contents)
            result = init_project.initialize(path)
            self.assertEqual(len(result["preserved"]), 2)
            self.assertEqual((path / "main.tex").read_text(), contents)

    def test_bad_existing_target_is_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "references.bib").mkdir()
            with self.assertRaises(ValueError):
                init_project.initialize(path)
            self.assertFalse((path / "main.tex").exists())


# Test entry point
if __name__ == "__main__":
    unittest.main()
