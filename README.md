# mshelper

Tools that make coding with **Microsoft 365 Copilot** (chat) less tedious and closer to an
agent-mode workflow.

| Folder | What it is |
|--------|-----------|
| [toolkit/](toolkit/README.md) | Markdown library of ready-made prompts and instructions: session primer, manual agent loop, context packing, output formats, general + Python/JS/TS/Rust/C/C++/Java/Kotlin/Bash prompts, gotchas, custom Copilot agent instructions |
| [wizard/](wizard/README.md) | Local web app (Python stdlib + HTML/JS) that builds prompts from templates, bundles project files into them, and cleans rendering artifacts (`\[`, mangled HTML, smart quotes) out of pasted code. Run `python wizard/server.py` |
