"""Tests for cleaner.py. Run:  python -m unittest -v  (from the wizard folder)."""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import cleaner


def fixed(code: str, lang: str = "python", **kw: bool) -> str:
    return cleaner.clean(code, lang, **kw).code


def kinds(code: str, lang: str = "python") -> list[str]:
    return [c.kind for c in cleaner.clean(code, lang).changes]


class PythonTests(unittest.TestCase):
    def test_removes_markdown_escapes_in_code(self) -> None:
        self.assertEqual(fixed('x = d\\["key"\\]\n'), 'x = d["key"]\n')
        self.assertEqual(fixed("def \\_\\_init\\_\\_(self): pass"), "def __init__(self): pass")
        self.assertEqual(fixed("y = a \\* b"), "y = a * b")

    def test_keeps_escapes_inside_strings_and_reports_invalid_ones(self) -> None:
        src = 'pat = "\\[a\\]"\n'
        result = cleaner.clean(src, "python")
        self.assertEqual(result.code, src)
        self.assertEqual([c.kind for c in result.changes], ["string-escape", "string-escape"])

    def test_raw_strings_are_not_reported(self) -> None:
        src = 'pat = r"\\[a\\]"\n'
        self.assertEqual(fixed(src), src)
        self.assertEqual(kinds(src), [])

    def test_triple_quoted_and_fstrings(self) -> None:
        src = 'doc = """a \\n b"""\nmsg = f"{x}\\n"\nv = arr\\[0\\]\n'
        self.assertEqual(fixed(src), 'doc = """a \\n b"""\nmsg = f"{x}\\n"\nv = arr[0]\n')

    def test_comments_untouched(self) -> None:
        src = "# matches \\[x\\]\n"
        self.assertEqual(fixed(src), src)
        self.assertEqual(kinds(src), [])

    def test_line_continuation_kept_and_trailing_space_removed(self) -> None:
        self.assertEqual(fixed("x = 1 + \\\n    2"), "x = 1 + \\\n    2")
        self.assertEqual(fixed("x = 1 + \\   \n    2"), "x = 1 + \\\n    2")

    def test_fixed_code_compiles(self) -> None:
        src = "values = \\[1, 2, 3\\]\nprint(values\\[0\\])\n"
        compile(fixed(src), "<test>", "exec")


class TypographyTests(unittest.TestCase):
    def test_smart_quotes_and_spaces(self) -> None:
        self.assertEqual(fixed("s = \u201chi\u201d\u00a0# c"), 's = "hi" # c')

    def test_smart_quotes_can_be_kept(self) -> None:
        self.assertEqual(fixed("s = \u201chi\u201d", smart_quotes=False), "s = \u201chi\u201d")

    def test_zero_width_removed(self) -> None:
        self.assertEqual(fixed("x\u200b = 1"), "x = 1")

    def test_html_entities_opt_in(self) -> None:
        self.assertEqual(fixed("if a &lt; b: pass"), "if a &lt; b: pass")
        self.assertEqual(fixed("if a &lt; b: pass", html_entities=True), "if a < b: pass")

    def test_strips_surrounding_fence(self) -> None:
        self.assertEqual(fixed("```python\nx = 1\n```\n"), "x = 1")


class OtherLanguageTests(unittest.TestCase):
    def test_javascript_keeps_regex_literals(self) -> None:
        src = "const re = /\\[(\\d+)\\]/g;\nconst x = arr\\[0\\];"
        self.assertEqual(fixed(src, "javascript"), "const re = /\\[(\\d+)\\]/g;\nconst x = arr[0];")

    def test_javascript_division_is_not_regex(self) -> None:
        self.assertEqual(fixed("const r = a / b / c\\[0\\];", "javascript"), "const r = a / b / c[0];")

    def test_rust_raw_strings_chars_and_lifetimes(self) -> None:
        src = "fn f<'a>(s: &'a str) -> char { let r = r#\"\\[x\\]\"#; v\\[0\\]; '\\n' }"
        out = fixed(src, "rust")
        self.assertEqual(out, "fn f<'a>(s: &'a str) -> char { let r = r#\"\\[x\\]\"#; v[0]; '\\n' }")

    def test_rust_invalid_string_escape_reported(self) -> None:
        self.assertIn("string-escape", kinds('let s = "\\[";', "rust"))

    def test_c_macro_continuation_and_artifact(self) -> None:
        src = "#define SQ(x) ((x) \\\n  * (x))\nint a = b\\[1\\];"
        self.assertEqual(fixed(src, "c"), "#define SQ(x) ((x) \\\n  * (x))\nint a = b[1];")

    def test_cpp_raw_string_and_digit_separator(self) -> None:
        src = 'auto s = R"(\\[x\\])"; int n = 1\'000; v\\[0\\];'
        self.assertEqual(fixed(src, "cpp"), 'auto s = R"(\\[x\\])"; int n = 1\'000; v[0];')


class JvmAndShellTests(unittest.TestCase):
    def test_java_artifacts_and_text_block(self) -> None:
        src = 'int x = arr\\[0\\];\nString re = "\\\\d+";\nString tb = """\n  a\\tb\n  """;'
        self.assertEqual(fixed(src, "java"), 'int x = arr[0];\nString re = "\\\\d+";\nString tb = """\n  a\\tb\n  """;')
        self.assertEqual(kinds(src, "java"), ["escape", "escape"])

    def test_java_invalid_string_escape_reported(self) -> None:
        self.assertIn("string-escape", kinds('String s = "\\[";', "java"))

    def test_kotlin_raw_string_untouched(self) -> None:
        src = 'val re = """\\[\\d+\\]"""\nval x = list\\[0\\]'
        self.assertEqual(fixed(src, "kotlin"), 'val re = """\\[\\d+\\]"""\nval x = list[0]')
        self.assertEqual(kinds(src, "kotlin"), ["escape", "escape"])

    def test_typescript_uses_js_rules(self) -> None:
        src = "const a: number[] = b\\[0\\];\nconst re = /\\[x\\]/;"
        self.assertEqual(fixed(src, "typescript"), "const a: number[] = b[0];\nconst re = /\\[x\\]/;")

    def test_bash_backslashes_untouched_but_typography_fixed(self) -> None:
        src = 'find . -name \\*.txt -exec rm {} \\;\necho \u201cdone\u201d'
        self.assertEqual(fixed(src, "bash"), 'find . -name \\*.txt -exec rm {} \\;\necho "done"')


class AutolinkTests(unittest.TestCase):
    def test_markdown_autolink_in_string(self) -> None:
        src = 'url = "[https://example.com/a](https://example.com/a)"'
        self.assertEqual(fixed(src), 'url = "https://example.com/a"')

    def test_markdown_autolink_with_added_scheme(self) -> None:
        src = 'open("[data.csv](http://data.csv)")'
        self.assertEqual(fixed(src), 'open("data.csv")')

    def test_indexing_then_call_untouched(self) -> None:
        src = "result = funcs[k](k)"
        self.assertEqual(fixed(src), src)

    def test_real_markdown_link_with_different_text_untouched(self) -> None:
        src = 's = "[docs](https://example.com/docs)"'
        self.assertEqual(fixed(src), src)


class HtmlTests(unittest.TestCase):
    def test_fixes_autolinked_attributes(self) -> None:
        src = ('<link rel="stylesheet" href="[style.css](http://style.css)">\n'
               '<script src="<a href="https://cdn.x.org/lib.js">https://cdn.x.org/lib.js</a>"></script>')
        result = cleaner.clean(src, "html")
        self.assertEqual(result.code, '<link rel="stylesheet" href="style.css">\n'
                                      '<script src="https://cdn.x.org/lib.js"></script>')
        self.assertEqual([c.kind for c in result.changes], ["autolink", "autolink"])

    def test_real_anchor_in_content_untouched(self) -> None:
        src = '<p>See <a href="https://x.org">https://x.org</a></p>'
        self.assertEqual(fixed(src, "html"), src)
        self.assertEqual(kinds(src, "html"), [])

    def test_inline_script_cleaned_as_javascript(self) -> None:
        src = "<script>\nconst a = b\\[0\\];\nconst re = /\\[x\\]/;\n</script>"
        self.assertEqual(fixed(src, "html"), "<script>\nconst a = b[0];\nconst re = /\\[x\\]/;\n</script>")

    def test_reports_structural_damage(self) -> None:
        src = ('<head>\n<link rel="stylesheet" href="a.css"></link>\n'
               '<script src="app.js">init();</script>\n'
               '<p> src="b.js" type="module"></p>\n<style>p{}\n')
        messages = [c.message for c in cleaner.clean(src, "html").changes]
        self.assertTrue(any("void element" in m for m in messages))
        self.assertTrue(any("src attribute and inline code" in m for m in messages))
        self.assertTrue(any("outside any tag" in m for m in messages))
        self.assertTrue(any("<style> is never closed" in m for m in messages))

    def test_duplicate_and_malformed_attributes(self) -> None:
        src = '<script src="a.js" src="b.js"></script><link href="x.css" rel"stylesheet">'
        messages = [c.message for c in cleaner.clean(src, "html").changes]
        self.assertTrue(any("duplicate attributes: src" in m for m in messages))
        self.assertTrue(any("malformed attribute name" in m for m in messages))


class ReportModeTests(unittest.TestCase):
    def test_report_only_returns_original(self) -> None:
        src = "a = b\\[0\\]\n"
        result = cleaner.clean(src, "python", fix=False)
        self.assertEqual(result.code, src)
        self.assertEqual(len(result.changes), 2)
        self.assertTrue(all(not c.fixed for c in result.changes))
        self.assertEqual((result.changes[0].line, result.changes[0].col), (1, 6))

    def test_unknown_language(self) -> None:
        with self.assertRaises(ValueError):
            cleaner.clean("x", "cobol")


class CliTests(unittest.TestCase):
    def test_write_fixes_file_and_preserves_crlf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            path = Path(tmp) / "m.py"
            path.write_bytes(b"x = a\\[0\\]\r\n")
            self.assertEqual(cleaner.main([str(path)]), 1)          # report only: issues found
            self.assertEqual(cleaner.main([str(path), "--write"]), 0)
            self.assertEqual(path.read_bytes(), b"x = a[0]\r\n")
            self.assertEqual(cleaner.main([str(path)]), 0)          # clean now


if __name__ == "__main__":
    unittest.main()
