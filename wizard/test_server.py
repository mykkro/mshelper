"""Tests for the Prompt Wizard backend. Run:  python -m unittest -v  (from the wizard folder)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import server


class FillTests(unittest.TestCase):
    def test_substitutes_placeholders(self) -> None:
        self.assertEqual(server.fill("Hello {{name}}!", {"name": "Ana"}), "Hello Ana!")

    def test_drops_paragraph_when_all_placeholders_empty(self) -> None:
        template = "Intro\n\nConstraints:\n{{constraints}}\n\nOutro"
        self.assertEqual(server.fill(template, {"constraints": "  "}), "Intro\n\nOutro")

    def test_drops_only_line_when_paragraph_has_other_values(self) -> None:
        template = "Input: {{a}}\nOnly when: {{b}}\nDone."
        self.assertEqual(server.fill(template, {"a": "x"}), "Input: x\nDone.")

    def test_keeps_static_paragraphs(self) -> None:
        self.assertEqual(server.fill("A\n\nB", {}), "A\n\nB")

    def test_multiline_value_with_blank_lines_is_kept_intact(self) -> None:
        out = server.fill("Code:\n{{code}}", {"code": "a\n\nb"})
        self.assertEqual(out, "Code:\na\n\nb")


class FenceTests(unittest.TestCase):
    def test_default_fence(self) -> None:
        self.assertEqual(server.fence("x = 1", "python"), "```python\nx = 1\n```")

    def test_fence_longer_than_inner_backticks(self) -> None:
        out = server.fence("```\ninner\n```")
        self.assertTrue(out.startswith("````\n"))
        self.assertTrue(out.endswith("\n````"))


class RenderTests(unittest.TestCase):
    templates = server.load_templates()

    def test_all_templates_use_exactly_their_fields(self) -> None:
        for task in self.templates["tasks"]:
            with self.subTest(task=task["id"]):
                fields = {f["name"] for f in task["fields"]}
                used = set(server.PLACEHOLDER.findall(task["template"]))
                self.assertEqual(fields, used)

    def test_task_ids_unique(self) -> None:
        ids = [t["id"] for t in self.templates["tasks"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_blocks_have_valid_kinds(self) -> None:
        for block_id, block in self.templates["blocks"].items():
            with self.subTest(block=block_id):
                self.assertIn(block["kind"], {"primer", "language", "format"})

    def test_render_combines_blocks_and_fences_code(self) -> None:
        prompt = server.render_prompt(
            {
                "task_id": "review",
                "values": {"code": "def f(): pass", "context": ""},
                "options": {"primer": "primer_short", "language": "lang_python", "format": ""},
            },
            self.templates,
        )
        self.assertTrue(prompt.startswith("Act as a senior engineer."))
        self.assertIn("PYTHON CONVENTIONS", prompt)
        self.assertIn("```\ndef f(): pass\n```", prompt)
        self.assertNotIn("Context:", prompt)
        self.assertNotIn("{{", prompt)

    def test_missing_required_field_raises(self) -> None:
        with self.assertRaisesRegex(server.WizardError, "Code or diff"):
            server.render_prompt({"task_id": "review", "values": {}}, self.templates)

    def test_unknown_task_raises(self) -> None:
        with self.assertRaises(server.WizardError):
            server.render_prompt({"task_id": "nope"}, self.templates)

    def test_block_kind_mismatch_raises(self) -> None:
        with self.assertRaises(server.WizardError):
            server.render_prompt(
                {"task_id": "handoff", "options": {"primer": "lang_rust"}}, self.templates
            )


class ProjectContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
        (self.root / "node_modules").mkdir()
        (self.root / "node_modules" / "junk.js").write_text("x", encoding="utf-8")
        (self.root / "README.md").write_text("# Demo\n", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_project_files_skips_excluded_dirs(self) -> None:
        self.assertEqual(server.project_files(self.root), ["README.md", "src/app.py"])

    def test_tree_skips_excluded_dirs(self) -> None:
        tree = server.project_tree(self.root)
        self.assertIn("app.py", tree)
        self.assertNotIn("node_modules", tree)

    def test_build_context_bundles_files_with_language_fence(self) -> None:
        ctx = server.build_context({"root": str(self.root), "files": ["src/app.py"]})
        self.assertIn("FILE: src/app.py\n```python\nprint('hi')\n```", ctx)

    def test_path_traversal_rejected(self) -> None:
        with self.assertRaisesRegex(server.WizardError, "escapes"):
            server.build_context({"root": str(self.root / "src"), "files": ["../README.md"]})

    def test_missing_file_rejected(self) -> None:
        with self.assertRaisesRegex(server.WizardError, "not found"):
            server.build_context({"root": str(self.root), "files": ["nope.py"]})

    def test_empty_project_gives_no_context(self) -> None:
        self.assertEqual(server.build_context({"root": "", "files": []}), "")


if __name__ == "__main__":
    unittest.main()
