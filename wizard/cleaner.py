"""Repair copy/paste artifacts in code produced by chat UIs such as Microsoft 365 Copilot.

Chat UIs render answers as Markdown + LaTeX, which can leak into copied code:
  * Markdown escapes:   arr\\[0\\]  ->  arr[0],   \\_\\_init\\_\\_  ->  __init__
  * LaTeX delimiters:   \\[ ... \\]  and  \\( ... \\)
  * Typography:         smart quotes, non-breaking spaces, zero-width characters
  * HTML entities:      &lt;  &gt;  &amp;  (optional)
  * Auto-links:         href="[a.css](http://a.css)"  or  src="<a href=...>...</a>"  ->  the bare URL
  * Broken HTML:        (html mode) split/mixed tags, <script src> with inline code, </link> ...

The fixer is language-aware: a backslash before punctuation is removed only in *code*
regions (outside strings and comments), where it is never valid in Python, Rust, C, C++,
Java or Kotlin (and, outside regex literals, in JavaScript/TypeScript). Inside strings such
sequences may be real regex escapes, so they are only reported. In bash, Dockerfile, YAML and
CMake a backslash is usually legitimate, so they only get targeted repairs: whitespace after a
continuation backslash, ${VAR\\_NAME}, NAME\\_X= / name\\_x( / key\\_x:, escaped exec-form or flow
brackets \\[ ... \\], plus a report of tab indentation in YAML.

CLI:  python cleaner.py FILE... [--lang python] [--write]
"""

from __future__ import annotations

import argparse
import bisect
import html
import re
import string
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path

LANGUAGES = ("python", "javascript", "typescript", "java", "kotlin", "rust", "c", "cpp", "bash",
             "dockerfile", "yaml", "cmake", "html")
EXT_TO_LANG = {
    ".py": "python", ".pyi": "python",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript", ".cts": "typescript",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
    ".sh": "bash", ".bash": "bash",
    ".dockerfile": "dockerfile", ".yml": "yaml", ".yaml": "yaml", ".cmake": "cmake",
    ".rs": "rust",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp", ".hxx": "cpp",
    ".html": "html", ".htm": "html",
}

SPACE_LIKE = {" ": "no-break space", " ": "narrow no-break space", " ": "figure space"}
INVISIBLE = {"​": "zero-width space", "‌": "zero-width non-joiner",
             "‍": "zero-width joiner", "⁠": "word joiner", "﻿": "BOM / zero-width no-break space"}
SMART_QUOTES = {"“": '"', "”": '"', "„": '"', "″": '"',
                "‘": "'", "’": "'", "‚": "'", "′": "'"}

PUNCT = set(string.punctuation) - {"\\"}
VALID_ESCAPES = {
    "python": set("\n\\'\"abfnrtv01234567xNuU"),
    "c": set("\n\\'\"?abfnrtv01234567xuU"),
    "cpp": set("\n\\'\"?abfnrtv01234567xuU"),
    "rust": set("\n\r\\'\"nrt0xu"),
    "java": set("\n\\'\"btnfrs01234567u"),
    "kotlin": set("\\'\"tbnr$u"),
    "javascript": None,  # JS/TS allow identity escapes like "\[": nothing to report
    "typescript": None,
}
REGEX_PRECEDERS = set("(,=:[!&|?{};+-*%<>~^")
REGEX_KEYWORDS = {"return", "typeof", "case", "do", "else", "in", "of", "void", "yield",
                  "await", "delete", "throw", "new"}


@dataclass
class Change:
    line: int
    col: int
    kind: str
    message: str
    fixed: bool


@dataclass
class CleanResult:
    code: str
    changes: list[Change] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "changes": [asdict(c) for c in self.changes]}


@dataclass
class Segment:
    kind: str  # "code" | "string" | "comment"
    start: int
    end: int
    raw: bool = False


# ---------------------------------------------------------------------------
# Lexers: split source into code / string / comment segments
# ---------------------------------------------------------------------------

Matcher = Callable[[str, int], "tuple[str, int, bool] | None"]


def _is_ident(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _scan_quoted(text: str, start: int, quote: str, *, multiline: bool) -> int:
    """Return the index just past the closing quote (escape-aware)."""
    k, n = start, len(text)
    while k < n:
        ch = text[k]
        if ch == "\\":
            k += 2
            continue
        if text.startswith(quote, k):
            return k + len(quote)
        if ch == "\n" and not multiline:
            return k  # unterminated: stop at end of line
        k += 1
    return n


def _line_end(text: str, i: int) -> int:
    end = text.find("\n", i)
    return len(text) if end == -1 else end


def _block_comment_end(text: str, i: int, *, nested: bool = False) -> int:
    depth, k, n = 1, i + 2, len(text)
    while k < n:
        if nested and text.startswith("/*", k):
            depth, k = depth + 1, k + 2
        elif text.startswith("*/", k):
            depth, k = depth - 1, k + 2
            if depth == 0:
                return k
        else:
            k += 1
    return n


def _python(text: str, i: int) -> tuple[str, int, bool] | None:
    ch = text[i]
    if ch == "#":
        return "comment", _line_end(text, i), False
    if ch not in "'\"":
        return None
    j = i
    while j > 0 and i - j < 3 and text[j - 1] in "rRbBfFuU":
        j -= 1
    prefix = "" if j > 0 and _is_ident(text[j - 1]) else text[j:i]
    raw = "r" in prefix.lower()
    quote = ch * 3 if text.startswith(ch * 3, i) else ch
    end = _scan_quoted(text, i + len(quote), quote, multiline=len(quote) == 3)
    return "string", end, raw


def _c_like(text: str, i: int, *, cpp: bool) -> tuple[str, int, bool] | None:
    ch = text[i]
    if text.startswith("//", i):
        return "comment", _line_end(text, i), False
    if text.startswith("/*", i):
        return "comment", _block_comment_end(text, i), False
    if ch == '"':
        if cpp and re.search(r"(?:^|[^A-Za-z0-9_])(?:u8|u|U|L)?R$", text[max(0, i - 4):i]):
            m = re.match(r'"([^()\\\s]{0,16})\(', text[i:])
            if m:
                closing = ")" + m.group(1) + '"'
                end = text.find(closing, i + m.end())
                return "string", len(text) if end == -1 else end + len(closing), True
        return "string", _scan_quoted(text, i + 1, '"', multiline=False), False
    if ch == "'":
        if cpp and i > 0 and _is_ident(text[i - 1]):
            m = re.search(r"[A-Za-z0-9_]+$", text[:i])
            if m and m.group(0) not in {"u8", "u", "U", "L"}:
                return None  # C++14 digit separator: 1'000'000
        return "string", _scan_quoted(text, i + 1, "'", multiline=False), False
    return None


RUST_CHAR = re.compile(r"'(?:\\(?:x[0-9a-fA-F]{2}|u\{[0-9a-fA-F_]{1,6}\}|.)|[^\\'\n])'")
RUST_RAW = re.compile(r'(?:b|c)?r(#*)"')


def _rust(text: str, i: int) -> tuple[str, int, bool] | None:
    ch = text[i]
    if text.startswith("//", i):
        return "comment", _line_end(text, i), False
    if text.startswith("/*", i):
        return "comment", _block_comment_end(text, i, nested=True), False
    if ch in "bcr" and (i == 0 or not _is_ident(text[i - 1])):
        m = RUST_RAW.match(text, i)
        if m:
            closing = '"' + m.group(1)
            end = text.find(closing, m.end())
            return "string", len(text) if end == -1 else end + len(closing), True
    if ch == '"':
        return "string", _scan_quoted(text, i + 1, '"', multiline=True), False
    if ch == "'":
        m = RUST_CHAR.match(text, i)
        return ("string", m.end(), False) if m else None  # otherwise a lifetime
    return None


def _javascript(text: str, i: int) -> tuple[str, int, bool] | None:
    ch = text[i]
    if text.startswith("//", i):
        return "comment", _line_end(text, i), False
    if text.startswith("/*", i):
        return "comment", _block_comment_end(text, i), False
    if ch in "'\"":
        return "string", _scan_quoted(text, i + 1, ch, multiline=False), False
    if ch == "`":
        return "string", _scan_quoted(text, i + 1, "`", multiline=True), False
    if ch == "/" and _js_regex_allowed(text, i):
        end = _scan_js_regex(text, i)
        if end is not None:
            return "string", end, True
    return None


def _js_regex_allowed(text: str, i: int) -> bool:
    before = text[:i].rstrip()
    if not before:
        return True
    if before[-1] in REGEX_PRECEDERS:
        return True
    m = re.search(r"[A-Za-z_$][\w$]*$", before)
    return bool(m and m.group(0) in REGEX_KEYWORDS)


def _scan_js_regex(text: str, i: int) -> int | None:
    k, n, in_class = i + 1, len(text), False
    while k < n:
        ch = text[k]
        if ch == "\n":
            return None
        if ch == "\\":
            k += 2
            continue
        if ch == "[":
            in_class = True
        elif ch == "]":
            in_class = False
        elif ch == "/" and not in_class:
            k += 1
            while k < n and text[k].isalpha():
                k += 1
            return k
        k += 1
    return None


def _java(text: str, i: int) -> tuple[str, int, bool] | None:
    if text.startswith('"""', i):  # text block: escapes are processed
        return "string", _scan_quoted(text, i + 3, '"""', multiline=True), False
    return _c_like(text, i, cpp=False)


def _kotlin(text: str, i: int) -> tuple[str, int, bool] | None:
    if text.startswith('"""', i):  # raw string: no escapes
        end = text.find('"""', i + 3)
        if end == -1:
            return "string", len(text), True
        while text.startswith('"', end + 3):  # """"quoted"""" ends at the last quote
            end += 1
        return "string", end + 3, True
    if text.startswith("/*", i):
        return "comment", _block_comment_end(text, i, nested=True), False
    return _c_like(text, i, cpp=False)


MATCHERS: dict[str, Matcher] = {
    "python": _python,
    "c": lambda t, i: _c_like(t, i, cpp=False),
    "cpp": lambda t, i: _c_like(t, i, cpp=True),
    "rust": _rust,
    "javascript": _javascript,
    "typescript": _javascript,
    "java": _java,
    "kotlin": _kotlin,
}


def segments(text: str, lang: str) -> list[Segment]:
    matcher = MATCHERS[lang]
    result: list[Segment] = []
    i = code_start = 0
    n = len(text)
    while i < n:
        hit = matcher(text, i)
        if hit is None:
            i += 1
            continue
        kind, end, raw = hit
        if i > code_start:
            result.append(Segment("code", code_start, i))
        result.append(Segment(kind, i, max(end, i + 1), raw))
        i = code_start = max(end, i + 1)
    if code_start < n:
        result.append(Segment("code", code_start, n))
    return result


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------

class _Positions:
    """Map string offsets to 1-based (line, col)."""

    def __init__(self, text: str) -> None:
        self._starts = [0] + [m.end() for m in re.finditer("\n", text)]

    def __call__(self, offset: int) -> tuple[int, int]:
        line = bisect.bisect_right(self._starts, offset) - 1
        return line + 1, offset - self._starts[line] + 1


def _strip_fences(text: str, changes: list[Change]) -> str:
    lines = text.split("\n")
    nonempty = [i for i, line in enumerate(lines) if line.strip()]
    if len(nonempty) >= 2 and lines[nonempty[0]].lstrip().startswith("```") \
            and lines[nonempty[-1]].strip().startswith("```"):
        changes.append(Change(1, 1, "fence", "Surrounding Markdown code fence", True))
        return "\n".join(lines[nonempty[0] + 1:nonempty[-1]])
    return text


def _typography(text: str, changes: list[Change], *, smart_quotes: bool, html_entities: bool) -> str:
    out_lines = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        new = []
        for col, ch in enumerate(line, start=1):
            if ch in SPACE_LIKE:
                changes.append(Change(lineno, col, "space", f"{SPACE_LIKE[ch].capitalize()} (-> space)", True))
                new.append(" ")
            elif ch in INVISIBLE:
                changes.append(Change(lineno, col, "invisible", f"Invisible {INVISIBLE[ch]}", True))
            elif ch in SMART_QUOTES and smart_quotes:
                changes.append(Change(lineno, col, "quote", f"Smart quote {ch} (-> {SMART_QUOTES[ch]})", True))
                new.append(SMART_QUOTES[ch])
            else:
                new.append(ch)
        line = "".join(new)
        if html_entities and re.search(r"&(?:lt|gt|amp|quot|#39|#x27|nbsp);", line):
            changes.append(Change(lineno, 1, "entity", "HTML entities (&lt; &gt; &amp; ...)", True))
            line = html.unescape(line).replace(" ", " ")
        out_lines.append(line)
    return "\n".join(out_lines)


def _clean_code_region(text: str, seg: Segment, pos: _Positions, changes: list[Change], fix: bool) -> str:
    chunk = text[seg.start:seg.end]
    out: list[str] = []
    k = 0
    while k < len(chunk):
        ch = chunk[k]
        if ch != "\\":
            out.append(ch)
            k += 1
            continue
        nxt = chunk[k + 1] if k + 1 < len(chunk) else ""
        line, col = pos(seg.start + k)
        if nxt in ("\n", "\r", ""):
            out.append(ch)  # legitimate line continuation
            k += 1
        elif nxt in PUNCT:
            changes.append(Change(line, col, "escape",
                                  f"Markdown/LaTeX escape '\\{nxt}' outside strings", fix))
            if not fix:
                out.append(ch)
            k += 1
        elif nxt in " \t" and re.match(r"[ \t]+\r?(\n|$)", chunk[k + 1:]):
            changes.append(Change(line, col, "continuation", "Whitespace after line-continuation backslash", fix))
            ws = re.match(r"[ \t]+", chunk[k + 1:])
            out.append(ch)
            k += 1 + (ws.end() if fix and ws else 0)
        else:
            changes.append(Change(line, col, "stray", f"Stray backslash before '{nxt}' outside strings: check by hand", False))
            out.append(ch)
            k += 1
    return "".join(out)


def _check_string_escapes(text: str, seg: Segment, lang: str, pos: _Positions, changes: list[Change]) -> None:
    valid = VALID_ESCAPES[lang]
    if valid is None or seg.raw:
        return
    chunk = text[seg.start:seg.end]
    for m in re.finditer(r"\\(.)", chunk, flags=re.DOTALL):
        nxt = m.group(1)
        if nxt in valid or nxt == "\\":
            continue
        line, col = pos(seg.start + m.start())
        hint = ("use a raw string r'...' if this is a regex, otherwise remove the backslash"
                if lang == "python" else "likely a Markdown artifact, or a regex needing '\\\\'")
        changes.append(Change(line, col, "string-escape",
                              f"Invalid escape '\\{nxt}' in string: {hint}", False))


MD_LINK = re.compile(r"\[(?P<label>[^\[\]\s()]+)\]\((?P<url>[^()\s]+)\)")
HTML_LINK = re.compile(r"""<a\s[^>]*?href=(?P<q>["'])(?P<url>[^"']+)(?P=q)[^>]*>(?P<label>[^<]+)</a>""")


def _same_link(label: str, url: str) -> bool:
    """True when url is just label turned into a link (optionally with a scheme added)."""
    if not re.search(r"[./@:]", label):
        return False  # e.g. Python funcs[k](k) must stay untouched
    bare = re.sub(r"^(?:https?://|mailto:)", "", url)
    return url == label or bare == label or bare == re.sub(r"^(?:https?://|mailto:)", "", label)


def _autolinks(text: str, changes: list[Change]) -> str:
    """Undo URLs/file names that the chat UI turned into Markdown or HTML links."""
    text = _md_autolinks(text, changes)
    pos = _Positions(text)

    def anchor(m: re.Match[str]) -> str:
        # Only inside a value (after a quote, '=' or '('); a real <a> in HTML content is left alone.
        if m.start() == 0 or text[m.start() - 1] not in "\"'=(`" \
                or not _same_link(m.group("label").strip(), m.group("url")):
            return m.group(0)
        line, col = pos(m.start())
        changes.append(Change(line, col, "autolink", f"HTML auto-link around {m.group('label')!r}", True))
        return m.group("label").strip()

    return HTML_LINK.sub(anchor, text)


def _md_autolinks(text: str, changes: list[Change]) -> str:
    pos = _Positions(text)

    def md(m: re.Match[str]) -> str:
        if not _same_link(m.group("label"), m.group("url")):
            return m.group(0)
        line, col = pos(m.start())
        changes.append(Change(line, col, "autolink", f"Markdown auto-link around {m.group('label')!r}", True))
        return m.group("label")

    return MD_LINK.sub(md, text)


MARKUP_LANGS = {"bash", "dockerfile", "yaml", "cmake"}
CONT_WS = re.compile(r"\\([ \t]+)(?=\n|\Z)")
VAR_ESC = re.compile(r"\$\{[^}\n]*\\_[^}\n]*\}")
ESCAPED_NAME = re.compile(r"(?<![\w\\])([A-Za-z][A-Za-z0-9]*(?:\\_[A-Za-z0-9]+)+)(?=\s*[=:(])")
DOCKER_EXEC = re.compile(
    r"^(\s*(?:CMD|ENTRYPOINT|RUN|SHELL|COPY|ADD|VOLUME|HEALTHCHECK(?:\s+--\S+)*\s+CMD)\s+)\\\[(.*)\\\](\s*)$",
    re.MULTILINE | re.IGNORECASE)
YAML_FLOW = re.compile(r"^(\s*(?:-\s+)?(?:[^\s:#\\][^:#]*:\s+)?)\\\[(.*)\\\](\s*)$", re.MULTILINE)
YAML_TAB = re.compile(r"^ *\t", re.MULTILINE)


def _markup_fixes(text: str, lang: str, changes: list[Change], fix: bool) -> str:
    """Targeted repairs for languages where a backslash is usually legitimate (shell, Dockerfile, YAML, CMake)."""

    def apply(pattern: re.Pattern[str], repl: Callable[[re.Match[str]], str], kind: str,
              message: Callable[[re.Match[str]], str], current: str) -> str:
        pos = _Positions(current)

        def sub(m: re.Match[str]) -> str:
            line, col = pos(m.start())
            changes.append(Change(line, col, kind, message(m), fix))
            return repl(m) if fix else m.group(0)

        return pattern.sub(sub, current)

    text = apply(CONT_WS, lambda m: "\\", "continuation",
                 lambda m: "Whitespace after line-continuation backslash", text)
    text = apply(VAR_ESC, lambda m: m.group(0).replace("\\_", "_"), "escape",
                 lambda m: f"Markdown escape inside variable reference {m.group(0)!r}", text)
    text = apply(ESCAPED_NAME, lambda m: m.group(1).replace("\\_", "_"), "escape",
                 lambda m: f"Markdown escapes in name {m.group(1)!r}", text)
    if lang == "cmake":
        # CMake's escape_identity makes \_ mean _ everywhere, so removing the backslash is always safe.
        text = apply(re.compile(r"\\_"), lambda m: "_", "escape",
                     lambda m: "Markdown escape '\\_'", text)
    if lang == "dockerfile":
        text = apply(DOCKER_EXEC, lambda m: f"{m.group(1)}[{m.group(2)}]{m.group(3)}", "escape",
                     lambda m: "Escaped exec-form brackets \\[ \\] (would silently become shell form)", text)
    if lang == "yaml":
        text = apply(YAML_FLOW, lambda m: f"{m.group(1)}[{m.group(2)}]{m.group(3)}", "escape",
                     lambda m: "Escaped flow-sequence brackets \\[ \\]", text)
        pos = _Positions(text)
        for m in YAML_TAB.finditer(text):
            line, col = pos(m.end() - 1)
            changes.append(Change(line, col, "yaml-tab", "Tab in indentation: YAML allows only spaces", False))
    return text


VOID_ELEMENTS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
                 "source", "track", "wbr"}


class _HtmlChecker(HTMLParser):
    """Report structural damage typical of HTML that went through a chat renderer."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.issues: list[Change] = []
        self._raw: list[tuple[str, bool, tuple[int, int]]] = []  # open script/style: (tag, has_src, pos)

    def _add(self, message: str, where: tuple[int, int] | None = None) -> None:
        line, offset = where or self.getpos()
        self.issues.append(Change(line, offset + 1, "html", message, False))

    def _check_attrs(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        names = [n for n, _ in attrs]
        dups = sorted({n for n in names if names.count(n) > 1})
        if dups:
            self._add(f"<{tag}> has duplicate attributes: {', '.join(dups)}")
        for name, value in attrs:
            if re.search(r"[<>\"'=]", name):
                self._add(f"<{tag}> has a malformed attribute name {name!r}: the tag is probably broken")
            elif value and re.search(r"<\w|\]\(", value):
                self._add(f"<{tag} {name}=...> contains markup: {value[:60]!r}")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._check_attrs(tag, attrs)
        if tag in ("script", "style"):
            has_src = tag == "script" and any(n == "src" for n, _ in attrs)
            self._raw.append((tag, has_src, self.getpos()))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._check_attrs(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_ELEMENTS:
            self._add(f"</{tag}>: <{tag}> is a void element and has no closing tag")
        if self._raw and self._raw[-1][0] == tag:
            self._raw.pop()

    def handle_data(self, data: str) -> None:
        if self._raw:
            tag, has_src, _ = self._raw[-1]
            if tag == "script" and has_src and data.strip():
                self._add("<script> has both a src attribute and inline code; browsers ignore the inline code")
        elif re.search(r"""\b(?:src|href|rel|type|integrity|crossorigin)\s*=\s*["']""", data):
            self._add("Attribute-like text outside any tag: a tag was probably split or mangled")

    def close(self) -> None:
        super().close()
        for tag, _, where in self._raw:
            self._add(f"<{tag}> is never closed", where)


def _html_segments(text: str) -> list[Segment]:
    """Markup is kept verbatim; inline <script> bodies are lexed as JavaScript."""
    result: list[Segment] = []
    last = 0
    for m in re.finditer(r"(<script\b[^>]*>)(.*?)(</script\s*>)", text, flags=re.DOTALL | re.IGNORECASE):
        body_start, body_end = m.start(2), m.end(2)
        if body_start > last:
            result.append(Segment("markup", last, body_start))
        for seg in segments(text[body_start:body_end], "javascript"):
            result.append(Segment(seg.kind, seg.start + body_start, seg.end + body_start, seg.raw))
        last = body_end
    if last < len(text):
        result.append(Segment("markup", last, len(text)))
    return result


def clean(code: str, lang: str, *, fix: bool = True, smart_quotes: bool = True,
          html_entities: bool = False) -> CleanResult:
    if lang not in LANGUAGES:
        raise ValueError(f"Unsupported language: {lang!r} (choose from {', '.join(LANGUAGES)})")
    changes: list[Change] = []
    original = code.replace("\r\n", "\n")
    # Fence stripping shifts line numbers, so it only happens when fixing.
    text = _strip_fences(original, changes) if fix else original
    text = _typography(text, changes, smart_quotes=smart_quotes, html_entities=html_entities)
    text = _autolinks(text, changes)
    pos = _Positions(text)
    parts: list[str] = []
    if lang == "html":
        segs = _html_segments(text)
    elif lang in MARKUP_LANGS:
        # A backslash is usually legitimate here (escapes, line continuations), so only
        # the targeted repairs apply on top of the typography and auto-link fixes.
        text = _markup_fixes(text, lang, changes, fix)
        pos = _Positions(text)
        segs = [Segment("markup", 0, len(text))]
    else:
        segs = segments(text, lang)
    escape_lang = "javascript" if lang == "html" else lang
    for seg in segs:
        if seg.kind == "code":
            parts.append(_clean_code_region(text, seg, pos, changes, fix))
        else:
            if seg.kind == "string":
                _check_string_escapes(text, seg, escape_lang, pos, changes)
            parts.append(text[seg.start:seg.end])
    if lang == "html":
        checker = _HtmlChecker()
        checker.feed("".join(parts))
        checker.close()
        changes.extend(checker.issues)
    changes.sort(key=lambda c: (c.line, c.col))
    if not fix:
        for c in changes:
            c.fixed = False
        return CleanResult(original, changes)
    return CleanResult("".join(parts), changes)


def detect_language(path: Path) -> str | None:
    name = path.name.lower()
    if name == "dockerfile" or name.startswith("dockerfile.") or name == "containerfile":
        return "dockerfile"
    if name == "cmakelists.txt":
        return "cmake"
    return EXT_TO_LANG.get(path.suffix.lower())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fix Markdown/LaTeX/typography artifacts in pasted code.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--lang", choices=LANGUAGES, help="override detection by file extension")
    parser.add_argument("--write", action="store_true", help="write fixes back (default: report only)")
    parser.add_argument("--no-smart-quotes", action="store_true", help="leave curly quotes alone")
    parser.add_argument("--html-entities", action="store_true", help="also decode &lt; &gt; &amp; ...")
    args = parser.parse_args(argv)

    found_any = False
    for path in args.files:
        lang = args.lang or detect_language(path)
        if lang is None:
            print(f"{path}: skipped (unknown extension, use --lang)", file=sys.stderr)
            continue
        with path.open(encoding="utf-8", newline="") as fh:
            original = fh.read()
        result = clean(original, lang, fix=args.write, smart_quotes=not args.no_smart_quotes,
                       html_entities=args.html_entities)
        for c in result.changes:
            found_any = True
            status = "fixed" if c.fixed else ("needs review" if c.kind in {"stray", "string-escape"} else "found")
            print(f"{path}:{c.line}:{c.col}: [{status}] {c.message}")
        if args.write and result.code != original.replace("\r\n", "\n"):
            newline = "\r\n" if "\r\n" in original else "\n"
            path.write_text(result.code, encoding="utf-8", newline=newline)
    return 1 if found_any and not args.write else 0


if __name__ == "__main__":
    sys.exit(main())
