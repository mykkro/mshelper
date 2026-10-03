# General Coding Prompts

These prompts work in any language. Paste the session primer first (`00-session-primer.md`).
Replace each `{{placeholder}}`. Delete any `[optional: ...]` part you don't need.

**Contents:** [Implement](#implement-a-feature) · [Write a function](#write-a-function-from-a-spec) ·
[Debug](#debug-an-error) · [Flaky or wrong behavior](#wrong-behavior-no-error) · [Refactor](#refactor) ·
[Code review](#code-review) · [Write tests](#write-tests) · [Explain code](#explain-unfamiliar-code) ·
[Performance](#performance) · [Documentation](#documentation) · [Naming](#naming--api-design) ·
[Regex / SQL / shell one-offs](#one-off-snippets) · [Translate between languages](#translate-between-languages) ·
[Dependency upgrade](#dependency--api-migration) · [Security check](#security-check) · [Learn a concept](#learn-a-concept)

---

## Implement a feature

```text
Implement: {{feature description}}

Context:
{{relevant code / interfaces / models}}

Requirements:
- {{req 1}}
- {{req 2}}
- Handle errors: {{e.g. invalid input → raise/return error X; network failure → retry N times}}
[optional: Performance/size constraints: {{...}}]

Follow the existing code style. First give a short plan (files + changes). Then, after I say go,
implement it with tests.
```

## Write a function from a spec

```text
Write a {{language}} function:
- Name / signature: {{e.g. parse_duration(text: str) -> timedelta}}
- Purpose: {{one sentence}}
- Inputs and constraints: {{types, ranges, allowed formats}}
- Output: {{type and meaning}}
- Errors: {{when and how it fails}}
- Examples:
  {{input}} -> {{output}}
  {{input}} -> {{output}}
  {{bad input}} -> {{error}}

Include a docstring/doc comment and unit tests that cover the examples plus edge cases (empty, boundary,
unicode, very large). Don't use libraries beyond {{allowed libs / "the standard library"}}.
```

## Debug an error

````text
I get this error:
```
{{full error / traceback / compiler output}}
```
When I run: `{{command}}`
Code involved:
{{snippets, with file paths}}
Expected: {{what should happen}}
What I already tried: {{...}}

1) Explain the root cause in 1–3 sentences, pointing to specific lines.
2) Give the minimal fix.
3) If you're not certain, list the alternative causes and a quick check for each instead of guessing.
````

## Wrong behavior (no error)

```text
This code runs but gives the wrong result.
Input: {{input}}
Expected: {{expected}}
Actual: {{actual}}
[optional: Happens only when: {{condition / intermittently / only in prod}}]

Code:
{{snippets}}

Don't fix anything yet. Walk through the code with this input step by step, showing the key variable
values, and find where the actual behavior diverges from the expected. Then propose the fix.
```

## Refactor

```text
Refactor the code below to {{goal: e.g. remove duplication / split this 200-line function / make it testable
/ replace callbacks with async}}.

Constraints:
- Behavior must stay EXACTLY the same, including error cases and the public API.
- Keep the change small and reviewable. No unrelated cleanups.
- {{other constraints}}

Code:
{{code}}

First list the refactoring steps you plan (each one should keep the behavior). Then apply them.
Point out any spot where preserving the behavior is ambiguous.
```

## Code review

```text
Review this code as a strict senior reviewer. Focus on, in this order:
1. Correctness bugs and unhandled edge cases
2. Error handling and resource cleanup
3. Security issues (injection, unsafe deserialization, path traversal, secrets)
4. Concurrency / race conditions [optional: if relevant]
5. Readability and maintainability
6. Test gaps

For each finding: severity (blocker/should-fix/nit), location, the problem, a concrete fix.
Don't report pure style preferences that a formatter would handle. If the code is fine, say so.

Context: {{what the code is for, who calls it}}
Code / diff:
{{paste}}
```

## Write tests

```text
Write tests for the code below using {{pytest / vitest / jest / cargo test / ...}}.

- Cover: the happy path, boundaries, invalid input, error paths, and {{specific risky case}}.
- Use descriptive test names that state the behavior (e.g. test_returns_empty_list_when_no_orders).
- Use the arrange/act/assert structure. Each test checks one behavior.
- Mock only external I/O ({{network, filesystem, time, DB}}). Don't mock the code under test.
- Match the existing test style:
{{paste an existing test file or example}}

Code under test:
{{code}}

Start with a list of the test cases (name + one line each) so I can approve it, then write them.
```

### Reproduce a bug as a failing test first

```text
Before fixing anything, write ONE minimal test that reproduces this bug and fails for the
right reason: {{bug description}}. Tell me what failure message I should expect when I run it.
```

## Explain unfamiliar code

```text
Explain this code to me. I'm an experienced developer, but new to this codebase.
1. Purpose in 2 sentences.
2. Flow: the main steps in order, as numbered bullets.
3. Key data structures and what they hold.
4. Non-obvious parts: tricky logic, hidden side effects, assumptions.
5. Possible bugs or smells you notice (briefly).
{{code}}
```

## Performance

```text
This code is too slow: {{measurement, e.g. 12 s for 100k rows; target < 1 s}}.
[optional: Profiler output:
{{paste}}]
Code:
{{code}}

1) Find the likely bottlenecks and give the complexity (big-O) of each.
2) Propose optimizations, ranked by expected gain vs effort. Keep the behavior identical.
3) Implement the top one, and tell me how to measure the improvement.
Don't micro-optimize at the cost of readability unless the gain is large.
```

## Documentation

```text
Write {{docstrings / doc comments / a README section / module docs}} for the code below.
- Style: {{Google / NumPy / JSDoc / TSDoc / rustdoc}}
- For each public item: purpose, parameters, return value, errors raised, and a short example.
- Document behavior and contracts, not the implementation details.
- Don't change any code.
{{code}}
```

### README for a project or module

```text
Write a README.md for {{project/module}}: a one-line description, features, install, a quick-start
example, configuration (as a table), development (build/test/lint commands), and the project structure.
Use only facts from the info below. Mark anything you'd have to guess with TODO.
{{info: purpose, commands, config, tree}}
```

## Naming & API design

```text
Suggest better names for these identifiers. They should be clear, consistent with the codebase, and in
{{language}} conventions. Give a table: current | suggested | why.
{{code or list}}
```

```text
I'm designing the API for {{component}}. Here's the draft:
{{signatures / endpoints}}
Critique it for consistency, error handling, extensibility and ease of use. Propose an improved version.
```

## One-off snippets

```text
Write a regex ({{flavor: Python re / JS / Rust regex crate}}) that matches {{description}}.
Should match: {{examples}}
Should NOT match: {{examples}}
Explain each part, and give a small test that checks all the examples.
```

```text
Write a {{PowerShell / bash}} command that {{task}}. Target: {{Windows 10 PowerShell 5.1 / Git Bash / Linux}}.
Explain the flags briefly. Make it safe: no destructive action without a dry-run option.
```

```text
Write a SQL query ({{dialect: PostgreSQL / SQLite / MSSQL}}) for: {{goal}}.
Schema:
{{CREATE TABLE statements}}
Explain the joins and indexes that would help.
```

## Translate between languages

```text
Port this {{source language}} code to idiomatic {{target language}}.
- Keep the behavior identical, including the edge cases and errors.
- Use the target language's idioms (error handling, iterators, naming); don't transliterate line by line.
- Map the dependencies: {{e.g. requests → reqwest}}. Ask if there's no obvious equivalent.
- List every behavior difference you couldn't avoid.
{{code}}
```

## Dependency / API migration

```text
I'm upgrading {{library}} from {{old version}} to {{new version}}.
Here's code that uses it:
{{code}}
List the breaking changes that affect this code, and give the updated code. If you're unsure about a
specific change in the new version, say so explicitly and tell me where in the changelog or docs to check.
```

## Security check

```text
Do a security review of this code. Assume an attacker controls {{inputs: e.g. HTTP params, uploaded files, env}}.
Check: injection (SQL/command/template), path traversal, deserialization, authn/authz gaps,
secrets in code/logs, unsafe crypto/randomness, SSRF, DoS via unbounded input, dependency risks.
For each issue: a concrete exploit scenario, the severity, and the fix.
{{code}}
```

## Learn a concept

```text
Teach me {{concept, e.g. Rust lifetimes / Python descriptors / JS event loop}} for practical use.
1. A one-paragraph intuition.
2. A minimal runnable example.
3. The 3 most common mistakes, each with a broken and a fixed snippet.
4. When NOT to use it.
I already know {{related things you know}}.
```
