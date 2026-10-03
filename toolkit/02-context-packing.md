# Context Packing

Copilot only knows what you paste. Good context is the biggest quality lever you have.

## Rules of thumb

1. **Start with the goal**, then the code. Copilot reads top-down.
2. **Label every snippet** with its path and, for partial files, its line range.
3. **Include the interfaces it touches**: callers, called functions, types/models, config.
   Leave out unrelated files.
4. **Paste errors in full**: the whole traceback / compiler error, not a summary.
5. **Give versions**: language, framework and key libraries. APIs change between versions.
6. **Stay under the limit.** If one message is too large, split it: "Part 1/3, reply only OK", and so on.
   Prefer several focused files over one giant dump.
7. **Redact secrets and personal data** before pasting.

## Snippet template

````text
FILE: src/orders/service.py  (lines 40–95, rest of file not relevant)
```python
{{code}}
```
````

## Multi-part paste

```text
I'm going to paste context in {{N}} parts. After each part reply only "OK {{n}}/{{N}}".
Don't analyze anything until I send "END OF CONTEXT".
```

## Project structure

Give Copilot the layout so its paths and imports match your repo.

```text
Here is the project layout (generated, build/vendor dirs excluded):
{{paste tree}}
```

To generate the tree:

- **PowerShell:** `tree /F /A | Select-String -NotMatch "node_modules|target|\.venv|__pycache__|\.git"`
- **Git (tracked files only, cleanest):** `git ls-files`
- **Bash:** `find . -type f -not -path '*/node_modules/*' -not -path '*/target/*' -not -path '*/.git/*' | sort`

## Bundle several files into one paste

PowerShell, from the repo root. Edit the file list, and the result lands in your clipboard:

```powershell
$files = @("src/a.py", "src/b.py", "tests/test_a.py")
$files | ForEach-Object { "FILE: $_`n``````n$(Get-Content $_ -Raw)`n``````n" } | Set-Clipboard
```

Bash equivalent:

````bash
for f in src/a.py src/b.py; do printf 'FILE: %s\n```\n' "$f"; cat "$f"; printf '```\n\n'; done | clip
````

## Diff instead of whole files

For review or "what did I break" questions, a diff is compact and precise:

````text
Here's my current uncommitted diff (`git diff`):
```diff
{{paste}}
```
{{question}}
````

## Errors

````text
Running `{{command}}` gives:
```
{{full output}}
```
Relevant code:
{{snippets}}
Environment: {{OS, language version, key lib versions}}
What I already tried: {{...}}
````

## Ask Copilot what it needs

When you're not sure what to include:

```text
Before answering, list exactly which files, functions or outputs you need to see to answer accurately.
Rank them by importance. Don't guess at their contents.
```
