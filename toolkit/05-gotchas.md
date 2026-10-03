# Gotchas

Known ways that Microsoft 365 Copilot chat output goes wrong, how to prevent each one, and how to recover.
Most of them come from two facts:

1. The chat window **renders** answers as Markdown + LaTeX + HTML. Anything not inside a fenced code
   block gets escaped, auto-linked, sanitized, or typographically "prettified".
2. Copilot **can't see or run** your code. It works from what you pasted, which may be partial or out of date.

**Golden rules:** use the session primer (it includes a code-hygiene rule). Copy code only with a code block's
**Copy** button, never by selecting rendered text. Run pasted code through the wizard's **Code cleaner**
(`python wizard/server.py` → *Code cleaner* tab), or from the command line:

```powershell
python wizard\cleaner.py path\to\file.py            # report only
python wizard\cleaner.py path\to\file.py --write    # apply the safe fixes
```

---

## Rendering artifacts

### 1. Stray backslashes: `arr\[0\]`, `\_\_init\_\_`, `a \* b`

- **Cause:** Markdown escaping, plus LaTeX math delimiters `\[ … \]` and `\( … \)`. This happens when code was
  outside a code fence, or was copied from the rendered text.
- **Prevent:** the primer rule "ALL code in fenced code blocks, no Markdown escapes, no LaTeX".
- **Fix:** the Code cleaner removes them where they can't be legitimate (outside strings and comments), and
  reports the ones inside strings. Inside strings, `\[` might be a real regex escape, so check by hand.

### 2. Lost backslashes: `"\d+"` instead of `"\\d+"`, `C:\Users` paths broken

- **Cause:** the opposite of #1: Markdown treats `\\` as an escaped backslash and shows only one.
- **Prevent:** fenced code blocks. Prefer raw strings for regexes and paths (`r"\d+"` in Python,
  `r"..."` in Rust, `String.raw` in JS) and forward slashes in paths.
- **Fix:** the cleaner reports invalid escape sequences in Python, C, C++, Rust, Java and Kotlin strings
  (`"\d"`, `"\["`). Turn them into raw strings or double the backslash.

### 3. Mangled HTML: `<script>` / `<link>` with mixed-up attributes

- **Cause:** URLs and file names in attributes get auto-linked
  (`href="[style.css](http://style.css)"`, `src="<a href="…">…</a>"`), and the HTML sanitizer strips
  or rearranges tags that weren't in a code fence.
- **Prevent:** ask for HTML in a ```` ```html ```` fenced block. For larger pages, ask for HTML, CSS and JS as
  separate files.
- **Fix:** the cleaner (language *HTML*) removes the auto-links, cleans inline `<script>` bodies as JavaScript,
  and reports damage: attribute text outside tags, `<script src>` with inline code, `</link>`, unclosed
  `<script>`/`<style>`, duplicate or malformed attributes.

### 4. `SyntaxError: invalid character '“'` / `invalid non-printable character U+00A0`

- **Cause:** smart quotes, non-breaking spaces and zero-width characters from typographic rendering.
- **Fix:** the cleaner replaces them (turn off *Fix smart quotes* if your strings really contain curly quotes).

### 5. `&lt;`, `&gt;`, `&amp;` in code

- **Cause:** HTML-escaped output copied from the rendered view.
- **Fix:** the cleaner's *Decode HTML entities* option (it's off by default, because entities can be legitimate in HTML).

### 6. Lost indentation, or tabs turned into spaces

- **Cause:** copying rendered text collapses whitespace. Some answers convert tabs to spaces.
- **Symptoms:** Python `IndentationError`; Makefile `*** missing separator`; Go/YAML formatting errors.
- **Prevent:** use the Copy button. For Makefiles, say "recipe lines MUST start with a real TAB character".
- **Fix:** run a formatter (`ruff format`, `prettier`, `rustfmt`, `clang-format`). For Makefiles, use
  VS Code's *Convert Indentation to Tabs* command (Ctrl+Shift+P).

### 7. Emoji and Unicode in output (`✓ Done`, `→`)

- **Symptom:** `UnicodeEncodeError: 'charmap' codec can't encode character` on Windows consoles.
- **Prevent:** add to the project context: "ASCII only in print/log output and in source files."
- **Fix:** ask Copilot to replace them, or set `PYTHONIOENCODING=utf-8`.

---

## Incomplete or invented answers

### 8. The answer is cut off mid-code

- **Prevent:** ask for one file or one step per answer.
- **Fix:** "Continue exactly where you stopped, starting with the last complete line. Don't repeat."
  If it's still a mess, ask for the rest of the file split into parts.

### 9. Placeholders: `# ... rest of the code unchanged ...`

- **Danger:** if you save it as a complete file, you delete real code.
- **Prevent:** the primer forbids placeholders; ask for SEARCH/REPLACE blocks for big files.
- **Fix:** "Your answer contains placeholders. Give the COMPLETE file with no omissions."

### 10. Invented APIs, flags, config keys or package versions

- **Symptom:** `AttributeError`, `unknown option`, `no matching version`, or code that compiles but
  calls something that doesn't exist.
- **Prevent:** state your versions in the project context. The primer says "say so when unsure".
- **Fix:** paste the real error. Ask "Does `X` exist in `lib` version `N`? How can I verify it?" Check the
  docs, `help(obj)`, `dir(obj)`, `cargo doc --open`, or the type definitions in `node_modules/`.

### 11. "Fixing" a failing test by weakening the test

- **Prevent:** "Don't modify tests unless I ask. The tests describe the required behavior."
- **Fix:** reject the change and repeat the constraint.

---

## Context problems

### 12. Edits based on an old version of your file

- **Cause:** you changed the file (applied steps, fixed something by hand) but Copilot remembers an earlier version.
- **Symptom:** SEARCH blocks don't match, or reverted changes reappear.
- **Fix:** paste the current file and say "This is the current version. Discard all earlier versions."

### 13. Long chats drift: forgotten rules, repeated mistakes

- **Fix:** ask for a handoff note (`01-agent-loop-workflow.md`), start a new chat, paste the primer + handoff.

### 14. Attached files are only partly read

- **Cause:** large attachments may be summarized or truncated rather than read in full.
- **Prevent:** paste the relevant parts as text (the wizard's file bundling does this), or ask
  "Quote the first and last lines of the attached file" to check what it actually sees.

### 15. Unrelated "improvements": renames, reformatting, reordered imports

- **Prevent:** the primer says "change only what the task needs".
- **Fix:** "Revert every change not needed for the task. Give only the minimal diff."

### 16. Answers mixed up between files

- **Prevent:** require a `FILE: path` label on every code block (the primer does this).

### 17. Refusals on security-related code

- **Cause:** content filters on keywords (exploit, bypass, payload...).
- **Fix:** state the defensive context ("I'm hardening our own service; review this input validation").
