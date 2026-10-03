# Copilot Coding Toolkit

Ready-made prompts and instructions that make **Microsoft 365 Copilot** (chat) feel more like an
agent-mode coding assistant. Copilot can't read your repo, run commands or edit files, so **you**
do those parts. These prompts keep that loop short and predictable.

## Files

| File | What it is | When to use |
|------|-----------|-------------|
| [00-session-primer.md](00-session-primer.md) | Paste-first instructions that set Copilot's working rules | Start of **every** coding chat |
| [01-agent-loop-workflow.md](01-agent-loop-workflow.md) | Plan → step → verify loop that copies agent mode by hand | Any task larger than one function |
| [02-context-packing.md](02-context-packing.md) | How to give Copilot code, errors and project structure | Before asking anything about existing code |
| [03-output-formats.md](03-output-formats.md) | Contracts for full files, search/replace blocks, diffs | Paste after the primer, or use inline |
| [05-gotchas.md](05-gotchas.md) | Known Copilot pitfalls (`\[` escapes, mangled HTML, cut-off answers, invented APIs...) with prevention and fixes | When something looks off |
| [10-prompts-general.md](10-prompts-general.md) | Implement, refactor, debug, review, test, explain, document | Daily work, any language |
| [20-python.md](20-python.md) | Python conventions and Python-specific prompts | Python projects |
| [21-javascript.md](21-javascript.md) | JavaScript conventions, plus framework prompts (React, Express, async, tests) | JS projects (framework prompts: TS too) |
| [22-rust.md](22-rust.md) | Rust conventions and prompts | Rust projects |
| [23-c.md](23-c.md) | C conventions and prompts (memory safety, UB, build) | C projects |
| [24-cpp.md](24-cpp.md) | C++ conventions and prompts (RAII, lifetimes, CMake) | C++ projects |
| [25-typescript.md](25-typescript.md) | TypeScript conventions and prompts (type errors, zod, unions, tsconfig) | TS projects |
| [26-java.md](26-java.md) | Java conventions and prompts (modern Java, Spring, JPA, concurrency) | Java projects |
| [27-kotlin.md](27-kotlin.md) | Kotlin conventions and prompts (idioms, coroutines, Compose, Gradle) | Kotlin projects |
| [28-bash.md](28-bash.md) | Bash conventions and prompts (safe scripts, shellcheck, text processing) | Shell scripts |
| [90-copilot-agent-instructions.md](90-copilot-agent-instructions.md) | Instruction block for a custom Copilot agent (Agent Builder) | If your tenant lets you create agents |

## Quick start

1. Open a **new** Copilot chat (old context causes drift).
2. Paste the primer from `00-session-primer.md`. Add the language block from `2x-*.md` if it applies.
3. Paste the context: the relevant files, the error, the goal (see `02-context-packing.md`).
4. Pick a prompt from `10-prompts-general.md` or a language file and fill in the `{{placeholders}}`.
5. Apply the changes, run tests or the linter, and paste the **real output** back. Repeat.

## Conventions used in prompts

- `{{PLACEHOLDER}}` is something you replace before sending.
- `[optional: ...]` is a part you can delete if it doesn't apply.
- Each prompt is in a fenced code block, so you can copy it with one click in VS Code's Markdown preview.

## General tips for M365 Copilot

- **One task per chat.** Long chats lose earlier context without warning. When answers degrade, ask for a
  handoff summary (prompt in `01-agent-loop-workflow.md`) and continue in a fresh chat.
- **Paste, don't describe.** Real code, real errors and real output beat paraphrases every time.
- **Ask for small outputs.** Ask for one file or one step per answer. Long answers get cut off or lose detail.
- **Make it ask first.** The primer tells Copilot to ask questions when something is ambiguous instead of guessing.
- **Verify everything.** Copilot can't run code. Treat each answer as an untested PR.
- **Copy code with the code block's Copy button**, never by selecting rendered text. That avoids most of the
  artifacts in `05-gotchas.md`. For whatever slips through, use the wizard's *Code cleaner*.
- **Never paste secrets** (keys, tokens, passwords, customer data), even in an internal tool.
