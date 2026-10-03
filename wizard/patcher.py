"""Turn a Copilot answer into a git-style patch against your current files.

Copilot is unreliable at writing unified diffs (wrong hunk headers, stale context). Instead, ask it
for complete files or SEARCH/REPLACE blocks (see toolkit/03-output-formats.md), paste the answer
here, and this module computes a correct patch from your files on disk:

    FILE: src/app.py
    <<<<<<< SEARCH
    old lines
    =======
    new lines
    >>>>>>> REPLACE

    FILE: src/new_module.py (new)
    ```python
    ...complete file...
    ```

SEARCH text is matched exactly first, then ignoring trailing whitespace, then ignoring indentation
(the replacement is re-indented to match). Line endings (CRLF/LF) of existing files are preserved.

CLI:  python patcher.py answer.md --root C:/proj [-o change.patch] [--apply] [--no-clean]
"""

from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cleaner

MAX_FILE_BYTES = 1_000_000
FILE_LABEL = re.compile(r"^[\s>#*_`-]*FILE\s*:\s*(?P<rest>.+)$", re.IGNORECASE)
FENCE = re.compile(r"^\s*(?P<fence>`{3,}|~{3,})")
SEARCH_START = re.compile(r"^\s*<{5,}\s*SEARCH\s*$")
DIVIDER = re.compile(r"^\s*={5,}\s*$")
REPLACE_END = re.compile(r"^\s*>{5,}\s*REPLACE\s*$")

Reader = Callable[[str], "str | None"]  # path -> current content (None if the file doesn't exist)


class PatchError(Exception):
    pass


@dataclass
class Block:
    search: str
    replace: str


@dataclass
class FileEdit:
    path: str
    is_new: bool = False
    full_text: str | None = None
    blocks: list[Block] = field(default_factory=list)


@dataclass
class FileResult:
    path: str
    status: str  # "modified" | "new" | "unchanged" | "error"
    notes: list[str] = field(default_factory=list)
    error: str = ""


@dataclass
class PatchResult:
    patch: str
    files: list[FileResult]

    def to_dict(self) -> dict[str, object]:
        return {"patch": self.patch, "files": [asdict(f) for f in self.files]}


# ---------------------------------------------------------------------------
# Parsing the answer
# ---------------------------------------------------------------------------

def _parse_label(rest: str) -> tuple[str, bool]:
    rest = rest.strip().strip("*_`").strip()
    is_new = bool(re.search(r"\(\s*new\s*\)", rest, re.IGNORECASE))
    path = re.split(r"\s+(?:\(|-|—|–)", rest, maxsplit=1)[0]
    path = path.strip().strip("*_`'\"").replace("\\", "/")
    if path.startswith("./"):
        path = path[2:]
    return path, is_new


def _first_fenced_block(lines: list[str]) -> str | None:
    for i, line in enumerate(lines):
        m = FENCE.match(line)
        if not m:
            continue
        fence = m.group("fence")
        for j in range(i + 1, len(lines)):
            closing = FENCE.match(lines[j])
            if closing and closing.group("fence")[0] == fence[0] and len(closing.group("fence")) >= len(fence) \
                    and lines[j].strip() == closing.group("fence"):
                return "\n".join(lines[i + 1:j])
        return "\n".join(lines[i + 1:])  # unterminated fence: take the rest
    return None


def _parse_blocks(lines: list[str]) -> list[Block]:
    blocks: list[Block] = []
    state, search, replace = "out", [], []
    for line in lines:
        if state == "out" and SEARCH_START.match(line):
            state, search, replace = "search", [], []
        elif state == "search" and DIVIDER.match(line):
            state = "replace"
        elif state == "replace" and REPLACE_END.match(line):
            blocks.append(Block("\n".join(search), "\n".join(replace)))
            state = "out"
        elif state == "search":
            search.append(line)
        elif state == "replace":
            replace.append(line)
    if state != "out":
        raise PatchError("Unterminated SEARCH/REPLACE block (missing ======= or >>>>>>> REPLACE)")
    return blocks


def _section_edit(path: str, is_new: bool, lines: list[str]) -> FileEdit:
    if any(SEARCH_START.match(line) for line in lines):
        return FileEdit(path, is_new, blocks=_parse_blocks(lines))
    code = _first_fenced_block(lines)
    if code is None:
        code = "\n".join(lines).strip("\n")
    return FileEdit(path, is_new, full_text=code)


def parse_answer(text: str, default_path: str = "") -> list[FileEdit]:
    """Split a Copilot answer into per-file edits."""
    lines = text.replace("\r\n", "\n").split("\n")
    sections: list[tuple[str, bool, list[str]]] = []
    current: tuple[str, bool, list[str]] | None = None
    in_fence = ""
    fence_line = ""  # the opening fence line, while we're on the first line inside it
    for line in lines:
        fm = FENCE.match(line)
        # Labels count outside fences, or as the very first line inside one ("```py\nFILE: x.py").
        label = FILE_LABEL.match(line) if (not in_fence or fence_line) else None
        if label:
            path, is_new = _parse_label(label.group("rest"))
            current = (path, is_new, [fence_line] if fence_line else [])
            if fence_line and sections and sections[-1][2] and sections[-1][2][-1] == fence_line:
                sections[-1][2].pop()  # the fence opener belongs to the new section
            sections.append(current)
            fence_line = ""
            continue
        fence_line = ""
        if fm:
            fence = fm.group("fence")
            if not in_fence:
                in_fence = fence
                fence_line = line
            elif line.strip() == fence[0] * len(line.strip()) and len(line.strip()) >= len(in_fence):
                in_fence = ""
        if current is not None:
            current[2].append(line)
    if not sections:
        if not default_path:
            raise PatchError("No 'FILE: path' labels found. Enter the target file path.")
        sections = [(default_path.replace("\\", "/"), False, lines)]
    edits = []
    for path, is_new, body in sections:
        if not path:
            raise PatchError("A FILE: label has no path")
        edits.append(_section_edit(path, is_new, body))
    return edits


# ---------------------------------------------------------------------------
# Applying SEARCH/REPLACE
# ---------------------------------------------------------------------------

def _indent(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def _find_line_matches(content_lines: list[str], search_lines: list[str], key: Callable[[str], str]) -> list[int]:
    n = len(search_lines)
    wanted = [key(s) for s in search_lines]
    return [i for i in range(len(content_lines) - n + 1)
            if all(key(content_lines[i + k]) == wanted[k] for k in range(n))]


def apply_block(content: str, block: Block) -> tuple[str, str]:
    """Return (new content, note). Raises PatchError when the SEARCH text can't be located uniquely."""
    search, replace = block.search, block.replace
    if not search.strip():
        raise PatchError("Empty SEARCH block: Copilot must include anchor lines")
    count = content.count(search)
    if count == 1:
        return content.replace(search, replace, 1), ""
    if count > 1:
        raise PatchError(f"SEARCH text matches {count} places; it must be unique:\n{_preview(search)}")

    c_lines, s_lines, r_lines = content.split("\n"), search.split("\n"), replace.split("\n")
    # Drop leading/trailing blank lines in SEARCH, which Copilot often adds or removes.
    while s_lines and not s_lines[0].strip():
        s_lines.pop(0)
    while s_lines and not s_lines[-1].strip():
        s_lines.pop()

    matches = _find_line_matches(c_lines, s_lines, str.rstrip)
    note = "matched ignoring trailing whitespace"
    reindent = None
    if not matches:
        matches = _find_line_matches(c_lines, s_lines, str.strip)
        note = "matched ignoring indentation (replacement re-indented)"
        if len(matches) == 1:
            first = next(k for k, s in enumerate(s_lines) if s.strip())
            actual, given = _indent(c_lines[matches[0] + first]), _indent(s_lines[first])
            reindent = (given, actual)
    if len(matches) > 1:
        raise PatchError(f"SEARCH text matches {len(matches)} places (fuzzy); add more context:\n{_preview(search)}")
    if not matches:
        raise PatchError(f"SEARCH text not found in the file:\n{_preview(search)}")

    if reindent:
        given, actual = reindent
        r_lines = [actual + line[len(given):] if line.startswith(given) and line.strip() else
                   (actual + line.lstrip() if line.strip() else line) for line in r_lines]
    start = matches[0]
    new_lines = c_lines[:start] + r_lines + c_lines[start + len(s_lines):]
    return "\n".join(new_lines), note


def _preview(text: str, limit: int = 6) -> str:
    lines = text.split("\n")
    shown = "\n".join("    " + line for line in lines[:limit])
    return shown + ("\n    ..." if len(lines) > limit else "")


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------

def unified_diff(path: str, old: str | None, new: str) -> str:
    """git-style unified diff; old=None means a new file. Line endings are kept as-is."""
    a = old.splitlines(keepends=True) if old else []
    b = new.splitlines(keepends=True)
    if a == b:
        return ""
    out = [f"diff --git a/{path} b/{path}\n"]
    if old is None:
        out.append("new file mode 100644\n")
    from_file = "/dev/null" if old is None else f"a/{path}"
    for line in difflib.unified_diff(a, b, fromfile=from_file, tofile=f"b/{path}", n=3):
        if line.endswith("\n"):
            out.append(line)
        else:
            out.append(line + "\n\\ No newline at end of file\n")
    return "".join(out)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def _clean(text: str, path: str) -> str:
    lang = cleaner.detect_language(Path(path))
    return cleaner.clean(text, lang).code if lang else text


def build_patch(text: str, read: Reader, *, default_path: str = "", clean: bool = True) -> PatchResult:
    patches: list[str] = []
    results: list[FileResult] = []
    for edit in parse_answer(text, default_path):
        result = FileResult(edit.path, "error")
        results.append(result)
        try:
            original = read(edit.path)
            eol = "\r\n" if original and "\r\n" in original else "\n"
            base = original.replace("\r\n", "\n") if original is not None else None

            if edit.full_text is not None:
                new = _clean(edit.full_text, edit.path) if clean else edit.full_text
                if base is not None and edit.is_new:
                    result.notes.append("marked (new) but the file exists: replaced completely")
                if base is not None and len(new.split("\n")) < 0.5 * len(base.split("\n")):
                    result.notes.append("WARNING: the new version is less than half as long; check for omitted code")
                if re.search(r"(?:\.\.\.|…)\s*(?:rest|remaining|existing|unchanged)", new, re.IGNORECASE):
                    result.notes.append("WARNING: looks like it contains placeholders such as '... rest unchanged'")
            else:
                if base is None:
                    raise PatchError("File doesn't exist, but the answer has SEARCH/REPLACE blocks for it")
                new = base
                for i, block in enumerate(edit.blocks, start=1):
                    candidates = [block]
                    if clean:  # cleaned first; the raw text is the fallback (e.g. real curly quotes)
                        candidates.insert(0, Block(_clean(block.search, edit.path),
                                                   _clean(block.replace, edit.path)))
                    last_error: PatchError | None = None
                    for candidate in candidates:
                        try:
                            new, note = apply_block(new, candidate)
                            break
                        except PatchError as err:
                            last_error = err
                    else:
                        raise PatchError(f"Block {i}: {last_error}")
                    if note:
                        result.notes.append(f"block {i}: {note}")

            if not new.endswith("\n") and (base is None or base.endswith("\n")):
                new += "\n"
            if eol == "\r\n":
                new = new.replace("\n", "\r\n")
            diff = unified_diff(edit.path, original, new)
            result.status = "unchanged" if not diff else ("new" if original is None else "modified")
            if diff:
                patches.append(diff)
        except PatchError as err:
            result.error = str(err)
    return PatchResult("".join(patches), results)


def patch_paths(patch: str) -> list[str]:
    """All file paths a patch touches (for validation before applying it)."""
    paths = set()
    for m in re.finditer(r"^(?:---|\+\+\+) (?:a/|b/)?(.+?)\r?$", patch, re.MULTILINE):
        if m.group(1) != "/dev/null":
            paths.add(m.group(1))
    for m in re.finditer(r"^diff --git a/(\S+) b/(\S+)", patch, re.MULTILINE):
        paths.update(m.groups())
    return sorted(paths)


def git_apply(patch: str, cwd: Path, *, check_only: bool) -> tuple[bool, str]:
    args = ["git", "apply", "--verbose"] + (["--check"] if check_only else [])
    try:
        proc = subprocess.run(args, input=patch.encode("utf-8"), cwd=cwd, capture_output=True, timeout=60)
    except FileNotFoundError:
        return False, "git not found on PATH"
    except subprocess.TimeoutExpired:
        return False, "git apply timed out"
    output = (proc.stdout + proc.stderr).decode("utf-8", errors="replace").strip()
    return proc.returncode == 0, output or ("OK" if proc.returncode == 0 else f"git apply failed ({proc.returncode})")


def file_reader(root: Path) -> Reader:
    root = root.resolve()

    def read(rel: str) -> str | None:
        path = (root / rel).resolve()
        if path != root and root not in path.parents:
            raise PatchError(f"Path escapes the project root: {rel}")
        if not path.exists():
            return None
        if not path.is_file():
            raise PatchError(f"Not a file: {rel}")
        if path.stat().st_size > MAX_FILE_BYTES:
            raise PatchError(f"File too large: {rel}")
        try:
            return path.read_bytes().decode("utf-8")  # bytes: keep CRLF exactly
        except UnicodeDecodeError as err:
            raise PatchError(f"Not a UTF-8 text file: {rel}") from err

    return read


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a git patch from a Copilot answer.")
    parser.add_argument("answer", type=Path, help="text file with the Copilot answer ('-' for stdin)")
    parser.add_argument("--root", type=Path, default=Path("."), help="project root (default: current dir)")
    parser.add_argument("--file", default="", help="target path when the answer has no FILE: labels")
    parser.add_argument("-o", "--output", type=Path, help="write the patch here (default: stdout)")
    parser.add_argument("--apply", action="store_true", help="run git apply after building the patch")
    parser.add_argument("--no-clean", action="store_true", help="don't run the code cleaner on the answer")
    args = parser.parse_args(argv)

    text = sys.stdin.read() if str(args.answer) == "-" else args.answer.read_text(encoding="utf-8")
    try:
        result = build_patch(text, file_reader(args.root), default_path=args.file, clean=not args.no_clean)
    except PatchError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    failed = False
    for f in result.files:
        print(f"{f.status:>9}  {f.path}" + (f"\n           {f.error}" if f.error else ""), file=sys.stderr)
        for note in f.notes:
            print(f"           - {note}", file=sys.stderr)
        failed |= f.status == "error"
    if args.output:
        with args.output.open("w", encoding="utf-8", newline="") as fh:
            fh.write(result.patch)
    elif not args.apply:
        sys.stdout.buffer.write(result.patch.encode("utf-8"))
    if args.apply and result.patch:
        ok, output = git_apply(result.patch, args.root, check_only=False)
        print(output, file=sys.stderr)
        failed |= not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
