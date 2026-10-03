# Bash scripting

## Language block (paste after the session primer)

```text
BASH CONVENTIONS for this conversation:
- Target: bash {{4.4+ / 5.x}} on {{Linux / macOS (bash 3.2!) / Git Bash on Windows / WSL}}. If something isn't
  portable to my target, say so. If I ask for POSIX sh, use no bashisms.
- Start scripts with `#!/usr/bin/env bash` and `set -euo pipefail`. Know their pitfalls: commands in
  `if`/`&&`/`||` don't trigger -e; `local x=$(cmd)` hides failures, so declare and assign separately.
- Quote every expansion: "$var", "$@", "${arr[@]}". Use [[ ]] for tests and $(...) instead of backticks.
  Use arrays for lists of arguments; never build commands in strings, and never use eval.
- Must pass `shellcheck` with no warnings (explain any `# shellcheck disable=` you add).
- Structure: functions for each step, a `main "$@"` at the bottom, `local` variables in functions, UPPER_CASE
  only for exported/environment variables.
- Errors: messages to stderr (`>&2`) with a useful prefix; meaningful exit codes; `usage()` for -h/--help and on
  bad arguments; validate inputs and required commands (`command -v jq >/dev/null || die "jq required"`).
- Temp files: `mktemp`, cleaned up by `trap 'rm -rf "$tmp"' EXIT`.
- Filenames: handle spaces and newlines (find -print0 | xargs -0, or `while IFS= read -r -d ''`). Never parse `ls`.
- Destructive operations (rm, mv over, overwrites, remote calls) get a --dry-run option and guard
  against empty variables (`rm -rf "${dir:?}/"`).
- Prefer simple tools that are already installed (grep, sed, awk, jq if available) over new dependencies.
  If the script grows beyond ~150 lines or needs data structures, suggest Python instead.
```

---

## Bash prompts

### Write a script

```text
Write a bash script that {{task}}.
- Arguments/options: {{list, e.g. -n/--dry-run, -v/--verbose, positional input dir}}, parsed with a
  `while case` loop (or getopts for short options only), with usage() and -h.
- Target: {{Linux / Git Bash on Windows / macOS}}. Required tools: {{...}}. Check that they exist.
- Exit codes: 0 ok, 1 runtime error, 2 usage error.
- Must be shellcheck-clean. Explain the non-obvious parts with short comments.
Show 3 example invocations, including a dry run.
```

### Review / harden an existing script

```text
Review this bash script as a strict reviewer:
- Quoting bugs and word-splitting/globbing, unsafe `rm`/`mv` with possibly empty variables, parsing `ls`,
  `for f in $(...)` loops, missing `set -euo pipefail` (and the cases where -e won't save you),
  `cd` without error handling, temp files without cleanup, race conditions, and unvalidated input.
- Portability problems for {{target}}.
- What shellcheck would flag (give the SC codes).
List the issues by severity, then give the hardened script.
{{script}}
```

### Explain a one-liner or script

```text
Explain this shell code piece by piece: each command, flag, redirection and expansion, in order. Then say
what it does overall, and any dangerous or non-portable parts.
{{code}}
```

### Process files safely

```text
Write a bash snippet that {{operation, e.g. renames all *.JPG under a dir to lowercase .jpg}}.
- Handle names with spaces, newlines, leading dashes and unicode (use find -print0 / read -d '' / --).
- Dry-run by default: print what would happen; act only with --apply.
- Stop at the first error, or collect failures and report them at the end: {{choose}}.
```

### Text processing (grep/sed/awk/jq)

```text
Input sample (first ~20 lines):
{{sample}}
Goal: {{e.g. sum column 3 per unique value in column 1, sorted descending}}.
Give a solution with {{awk / sed / jq / plain bash}}, and explain each part. Note any differences between GNU and
BSD/macOS versions of the tools ({{sed -i, date, grep -P}}) if my target needs them.
```

### Convert between shells

```text
Convert this {{bash script -> PowerShell / PowerShell -> bash / bash -> POSIX sh}}:
{{script}}
Use the target's idioms (PowerShell: objects and pipelines, not text parsing; parameter attributes;
$ErrorActionPreference = 'Stop'). List the behavior differences, especially in quoting, error
handling and paths.
```

### Make it a cron / CI step

```text
Adapt this script to run unattended in {{cron / systemd timer / GitHub Actions / GitLab CI / Jenkins}}:
- No interactive prompts; all configuration from env vars or arguments, with validation.
- Logs with timestamps to {{stdout / a file with rotation}}; non-zero exit on failure.
- A lock to prevent overlapping runs (flock), and a timeout.
Give the scheduler/CI config snippet as well.
{{script}}
```

### Debug a failing script

````text
This script fails:
```
{{output, ideally from `bash -x script.sh args` (trace)}}
```
Script:
{{script}}
Environment: {{OS, bash --version, how it's invoked (cron? CI? sudo?)}}.
Find the root cause. Common suspects: different PATH/env under cron or sudo, CRLF line endings
(`$'\r': command not found`), unquoted variables, set -e side effects, a subshell losing variables (pipe into while).
````
