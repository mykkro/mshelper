"""Tests for patcher.py. Run:  python -m unittest -v  (from the wizard folder)."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import patcher

APP = "def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b\n"


def reader(files: dict[str, str]) -> patcher.Reader:
    return lambda path: files.get(path)


class ParseTests(unittest.TestCase):
    def test_labels_blocks_and_new_files(self) -> None:
        answer = (
            "Here you go.\n\n"
            "FILE: src/app.py\n```python\n<<<<<<< SEARCH\n    return a + b\n=======\n    return b + a\n"
            ">>>>>>> REPLACE\n```\n\n"
            "**FILE: src/util.py (new)**\n```python\nX = 1\n```\n"
        )
        edits = patcher.parse_answer(answer)
        self.assertEqual([(e.path, e.is_new) for e in edits], [("src/app.py", False), ("src/util.py", True)])
        self.assertEqual(edits[0].blocks, [patcher.Block("    return a + b", "    return b + a")])
        self.assertEqual(edits[1].full_text, "X = 1")

    def test_label_as_first_line_inside_fence(self) -> None:
        answer = "```python\nFILE: a.py\nprint(1)\n```\n"
        edits = patcher.parse_answer(answer)
        self.assertEqual(edits[0].path, "a.py")
        self.assertEqual(edits[0].full_text, "print(1)")

    def test_label_suffix_and_backticks_stripped(self) -> None:
        edits = patcher.parse_answer("FILE: `src\\m.py` - replaces `f`\n```\nx\n```")
        self.assertEqual(edits[0].path, "src/m.py")

    def test_file_comment_inside_code_is_not_a_label(self) -> None:
        answer = "FILE: a.py\n```python\nx = 1\n# FILE: not a label\ny = 2\n```"
        edits = patcher.parse_answer(answer)
        self.assertEqual(len(edits), 1)
        self.assertIn("# FILE: not a label", edits[0].full_text)

    def test_default_path_without_labels(self) -> None:
        self.assertEqual(patcher.parse_answer("```\nx\n```", "m.py")[0].path, "m.py")
        with self.assertRaises(patcher.PatchError):
            patcher.parse_answer("```\nx\n```")

    def test_unterminated_block(self) -> None:
        with self.assertRaises(patcher.PatchError):
            patcher.parse_answer("FILE: a.py\n<<<<<<< SEARCH\nx\n=======\ny\n")


class ApplyBlockTests(unittest.TestCase):
    def test_exact(self) -> None:
        new, note = patcher.apply_block(APP, patcher.Block("    return a - b", "    return b - a"))
        self.assertIn("return b - a", new)
        self.assertEqual(note, "")

    def test_trailing_whitespace_tolerated(self) -> None:
        new, note = patcher.apply_block(APP, patcher.Block("def sub(a, b):   \n    return a - b", "def sub(a, b):\n    return 0"))
        self.assertIn("    return 0", new)
        self.assertIn("trailing whitespace", note)

    def test_indentation_tolerated_and_reindented(self) -> None:
        src = "class A:\n    def f(self):\n        return 1\n"
        block = patcher.Block("def f(self):\n    return 1", "def f(self):\n    x = 2\n    return x")
        new, note = patcher.apply_block(src, block)
        self.assertEqual(new, "class A:\n    def f(self):\n        x = 2\n        return x\n")
        self.assertIn("indentation", note)

    def test_ambiguous_and_missing(self) -> None:
        with self.assertRaisesRegex(patcher.PatchError, "matches 2 places"):
            patcher.apply_block(APP, patcher.Block("(a, b):", "x"))
        with self.assertRaisesRegex(patcher.PatchError, "not found"):
            patcher.apply_block(APP, patcher.Block("nope", "x"))
        with self.assertRaisesRegex(patcher.PatchError, "Empty SEARCH"):
            patcher.apply_block(APP, patcher.Block("", "x"))


class BuildPatchTests(unittest.TestCase):
    def test_modified_new_and_error_files(self) -> None:
        answer = (
            "FILE: app.py\n<<<<<<< SEARCH\n    return a + b\n=======\n    return b + a\n>>>>>>> REPLACE\n"
            "FILE: new.py (new)\n```python\nX = 1\n```\n"
            "FILE: missing.py\n<<<<<<< SEARCH\nx\n=======\ny\n>>>>>>> REPLACE\n"
        )
        result = patcher.build_patch(answer, reader({"app.py": APP}))
        self.assertEqual([(f.path, f.status) for f in result.files],
                         [("app.py", "modified"), ("new.py", "new"), ("missing.py", "error")])
        self.assertIn("diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n", result.patch)
        self.assertIn("-    return a + b\n+    return b + a\n", result.patch)
        self.assertIn("new file mode 100644\n--- /dev/null\n+++ b/new.py\n@@ -0,0 +1 @@\n+X = 1\n", result.patch)

    def test_cleaner_fixes_artifacts_in_answer(self) -> None:
        answer = "FILE: app.py\n<<<<<<< SEARCH\n    return a + b\n=======\n    return \\[a, b\\]\n>>>>>>> REPLACE\n"
        result = patcher.build_patch(answer, reader({"app.py": APP}))
        self.assertIn("+    return [a, b]\n", result.patch)

    def test_crlf_preserved(self) -> None:
        crlf = APP.replace("\n", "\r\n")
        answer = "FILE: app.py\n<<<<<<< SEARCH\n    return a + b\n=======\n    return b + a\n>>>>>>> REPLACE\n"
        result = patcher.build_patch(answer, reader({"app.py": crlf}))
        self.assertIn("+    return b + a\r\n", result.patch)

    def test_full_file_placeholder_warning(self) -> None:
        answer = "FILE: app.py\n```python\ndef add(a, b):\n    return a + b\n# ... rest unchanged ...\n```"
        result = patcher.build_patch(answer, reader({"app.py": APP}))
        self.assertTrue(any("placeholders" in n for n in result.files[0].notes))

    def test_unchanged(self) -> None:
        result = patcher.build_patch("FILE: app.py\n```\n" + APP + "```", reader({"app.py": APP}))
        self.assertEqual(result.files[0].status, "unchanged")
        self.assertEqual(result.patch, "")

    def test_patch_paths(self) -> None:
        result = patcher.build_patch("FILE: n.py (new)\n```\nx\n```", reader({}))
        self.assertEqual(patcher.patch_paths(result.patch), ["n.py"])


@unittest.skipUnless(shutil.which("git"), "git not installed")
class GitApplyTests(unittest.TestCase):
    def test_round_trip_with_git_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / "app.py").write_bytes(APP.replace("\n", "\r\n").encode())
            answer = (
                "FILE: app.py\n<<<<<<< SEARCH\ndef sub(a, b):\n    return a - b\n=======\n"
                "def sub(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n>>>>>>> REPLACE\n"
                "FILE: pkg/util.py (new)\n```python\nY = 2\n```\n"
            )
            result = patcher.build_patch(answer, patcher.file_reader(root))
            ok, output = patcher.git_apply(result.patch, root, check_only=True)
            self.assertTrue(ok, output)
            ok, output = patcher.git_apply(result.patch, root, check_only=False)
            self.assertTrue(ok, output)
            self.assertIn(b"def mul(a, b):\r\n    return a * b\r\n", (root / "app.py").read_bytes())
            self.assertEqual((root / "pkg" / "util.py").read_text(), "Y = 2\n")

    def test_reader_rejects_escaping_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(patcher.PatchError):
                patcher.file_reader(Path(tmp))("../outside.py")


if __name__ == "__main__":
    unittest.main()
