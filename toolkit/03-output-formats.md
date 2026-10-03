# Output Formats

Tell Copilot exactly what shape the answer should take. Shapes you can apply mechanically save
the most time. Paste one of these contracts after the primer, or add it to any prompt.

---

## A. SEARCH/REPLACE blocks (default for edits)

Best for targeted edits to larger files. You find the SEARCH text and replace it.

```text
Return edits ONLY as SEARCH/REPLACE blocks:

FILE: path/to/file.ext
<<<<<<< SEARCH
exact existing lines, copied verbatim, including indentation; enough lines to be unique
=======
replacement lines
>>>>>>> REPLACE

Rules: one block per contiguous change; the SEARCH text must match my code exactly; to insert, use the
neighbouring line as the anchor; to delete, leave REPLACE empty; for new files, give the complete file under
"FILE: path (new)".
```

## B. Complete file

Best for new files, small files (under ~150 lines), or heavy rewrites.

```text
Return the COMPLETE contents of {{path}}, ready to save over the existing file. Include every line,
with no placeholders, ellipses or "unchanged" comments.
```

> **Want a patch you can `git apply`?** Don't ask Copilot for a diff. Ask for format A or B, then paste the
> answer into the wizard's **Patch builder** tab (or run `python wizard/patcher.py answer.md --root .`). It computes
> an exact patch against your current files and can run `git apply` for you.

## C. Unified diff

Use this only when you can't use the Patch builder. Copilot often miscounts hunk headers and uses stale
context lines, so these diffs frequently fail to apply.

```text
Return a unified diff (git format, paths a/ and b/ relative to the repo root) that I can apply with
`git apply`. Use 3 lines of context. Hunk headers must be accurate.
```

Apply it with: save the diff as `change.patch`, then `git apply --check change.patch` and `git apply change.patch`.
If that fails, try `git apply --3way change.patch`, or fall back to format A.

## D. Function-level replacement

A middle ground that works well in Python, JS and Rust.

```text
Return only the full new versions of the functions/methods/types you changed, each preceded by
"FILE: path — replaces `name`". List any new imports separately at the top.
```

## E. Plan only (no code)

```text
Don't write code. Answer as: 1) approach in 3–5 bullets, 2) files to touch, 3) risks and open questions,
4) verification plan.
```

## F. Options to compare

```text
Give {{2–3}} alternative approaches. For each: a short description, pros, cons, complexity (S/M/L),
and when you'd pick it. End with your recommendation and why. No code yet.
```

---

## Fixing a malformed answer

```text
Your last answer didn't follow the format: {{what was wrong, e.g. "used '...rest unchanged'" /
"SEARCH text doesn't match my file"}}. Resend it in the exact format I asked for.
```

```text
Your SEARCH block for {{file}} doesn't match. Here is the current exact content of that region:
{{paste}}
Regenerate the block against this text.
```

```text
Your answer was cut off. Continue exactly where you stopped, starting with the last complete line.
Don't repeat earlier content.
```
