# Prompt Wizard

A small local web app that builds well-structured prompts for **Microsoft 365 Copilot**.
Pick a task, fill in the form, optionally bundle files from your project, then copy the result
into Copilot.

- **No dependencies.** It uses only the Python standard library (Python 3.11+), plus plain HTML/JS.
- **Local only.** The server binds to `127.0.0.1` and nothing is sent anywhere. The prompt goes
  only where you paste it.

## Run

```powershell
cd wizard
python server.py                              # opens http://127.0.0.1:8765
python server.py --root C:\Work\myproject     # pre-fill the project root
python server.py --port 9000 --no-browser
```

## Use

1. **Top bar:** choose a primer, a language block and an output format. These are prepended to the
   prompt. The primer only needs to go in the first message of a chat.
2. **Sidebar:** pick a task (search with the box at the top). Tasks are grouped by category: the
   *Agent loop* tasks walk you through brief → plan → step → feedback → handoff.
3. **Form:** fill in the fields (`*` = required). Code fields are wrapped in code fences
   automatically. Empty optional fields disappear from the prompt, labels included.
4. **Project context** (optional): enter the project root and click **Scan**. Tick the files to
   include and/or *Include project layout*. Their contents are read from disk at generation time,
   so you always send the current version.
5. **Generate** (or Ctrl+Enter) → check the preview, edit it if needed → **Copy**.

Your options, project selection and per-task drafts are remembered in the browser's localStorage.

The character counter turns orange above ~15,000 characters, around where Copilot starts to
truncate or reject long prompts (the exact limit varies by tenant). If you hit it, deselect files or
split the context across messages (see `toolkit/02-context-packing.md`).

## Add or edit templates

Everything lives in [templates.toml](templates.toml). No code changes are needed. Reload the page
after editing.

```toml
[[tasks]]
id = "my_task"                 # unique
category = "Fix"               # sidebar group (tasks are listed in file order)
title = "My task"
description = "Shown under the title."
fields = [
  { name = "error", label = "Error output", type = "code", required = true },
  { name = "notes", label = "Notes", type = "textarea" },
  { name = "lang",  label = "Language", type = "select", options = ["Python", "Rust"] },
]
template = '''
Fix this error:
{{error}}

Notes:
{{notes}}
'''
```

- Field types: `text`, `textarea`, `code` (auto-fenced; optional `lang`), `select` (needs `options`).
- Template rules: `{{name}}` is substituted. **Paragraphs** are separated by blank lines. A paragraph whose
  placeholders are all empty is dropped. Inside a kept paragraph, a line whose placeholders are all
  empty is dropped. Put a label and its optional field in their own paragraph so both disappear
  together.
- Reusable blocks go under `[blocks.<id>]` with `kind = "primer" | "language" | "format"`, `label` and `text`.
- Use `'''` literal strings so backslashes and quotes need no escaping.

Run the tests after editing. One test checks that every template uses exactly its declared fields:

```powershell
python -m unittest -v
```

## Files

| File | Purpose |
|------|---------|
| `server.py` | HTTP server, template rendering, file bundling (stdlib only) |
| `templates.toml` | All tasks and blocks |
| `static/` | UI (`index.html`, `app.js`, `style.css`) |
| `test_server.py` | Unit tests |

## Safety notes

- The server can read any file **under the project root you give it**. Paths that escape the root
  (`..`) are rejected, and files over 200 kB or non-UTF-8 files are refused.
- Common build/vendor folders (`node_modules`, `target`, `.venv`, `.git`, ...) are skipped when scanning.
- Check the preview for secrets (keys, tokens, `.env` contents) before you paste it into Copilot.
