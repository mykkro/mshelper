# Rust

## Language block (paste after the session primer)

```text
RUST CONVENTIONS for this conversation:
- Rust {{1.79}}, edition {{2021}}. Code must compile without warnings and pass `cargo clippy -- -D warnings`
  and `cargo fmt --check`.
- Errors: no unwrap()/expect() in library code or non-test paths, except where an invariant really
  makes failure impossible (add a comment saying why). Use `?`. Libraries use {{thiserror}} error enums;
  binaries use {{anyhow}} with .context("...") at the I/O boundaries.
- Ownership: borrow (&T, &str, &[T]) in parameters where you can. Avoid needless .clone(); if you clone,
  it should be a deliberate choice. Avoid Rc<RefCell<>> or Arc<Mutex<>> unless shared mutation is
  really needed.
- Prefer iterators and combinators where they stay readable; plain loops are fine when clearer.
- Prefer enums and the type system to make invalid states unrepresentable. Derive Debug (and Clone,
  PartialEq where it makes sense) on public types.
- No `unsafe` unless I ask for it. If you need it, explain the safety invariants in a // SAFETY: comment.
- Async: {{tokio}} runtime. Never block inside async code (use spawn_blocking for blocking work).
- Tests: unit tests in a #[cfg(test)] mod tests in the same file; integration tests in tests/.
  Doc examples on public items.
- Crates: ask before adding a new dependency, and pin a version you are confident exists.
- If you are not sure a crate API or a feature flag exists in the version I use, SAY SO.
```

---

## Rust prompts

### Fix a borrow checker error

````text
Borrow checker error:
```
{{full `cargo build` output for this error, including the help/note lines}}
```
Code:
{{the function(s) involved, plus the relevant struct definitions}}

1) Explain in plain terms what conflict the compiler sees (who borrows what, and for how long).
2) Give the idiomatic fix. Restructure the code instead of reaching for clone() or RefCell unless they're
   really the right tool, and say why.
3) If there are multiple valid fixes, briefly compare them.
````

### Lifetime / trait bound help

```text
I'm struggling with {{lifetimes / trait bounds / generics / impl Trait vs dyn Trait}} here:
{{code + error}}
Explain what the compiler needs and why, then give the simplest signature that works.
Note any case where an owned type (String, Vec, Box) would make this much simpler.
```

### Design types for a domain

```text
Design Rust types for {{domain description}}.
Rules/invariants: {{e.g. an order has at least one item; status moves only Draft → Paid → Shipped}}.
- Make invalid states unrepresentable (enums, newtypes, private fields + constructors).
- Show the constructors and the key methods with their signatures.
- Add serde derives if needed: {{yes/no}}.
- Explain the design trade-offs briefly.
```

### Error handling setup

```text
Set up error handling for this {{library / binary / workspace}}:
- A {{thiserror}} enum for the library errors, with variants for {{io, parse, validation, ...}}, using
  #[from] where it fits.
- {{anyhow}} in main with context messages.
- Convert the code below to use it, replacing the unwraps.
{{code}}
```

### Make it idiomatic

```text
Review this Rust code for idiom and clippy-level issues, and rewrite it:
- Unnecessary clones/allocations, &String/&Vec parameters (→ &str/&[T]), manual loops that should be
  iterators, match → if let / let-else, Option/Result combinators, missing derives, needless
  lifetimes, non-snake_case names.
Keep the behavior identical. List the changes as bullets.
{{code}}
```

### Async with tokio

```text
Implement {{task}} with tokio:
- Concurrency limit of {{N}} (Semaphore or buffer_unordered).
- Timeouts per operation (tokio::time::timeout) and a graceful shutdown on Ctrl+C.
- No blocking calls in async context.
- Error propagation: {{collect all / fail fast}}.
Cargo.toml dependency lines with the features you need, and a short explanation of the task structure.
```

### CLI with clap

```text
Create a CLI using clap {{4}} (derive API): {{tool description}}.
Commands/args: {{list}}
- Use anyhow for errors and a proper exit code.
- Put the logic in lib.rs so it's testable; keep main.rs thin.
- Add tests for the argument parsing and the core logic.
Give Cargo.toml, src/main.rs and src/lib.rs in full.
```

### Write tests

```text
Write tests for this Rust code:
- Unit tests in a #[cfg(test)] module, named <behavior>_when_<condition>.
- Cover the Ok and Err paths. Match on specific error variants instead of just is_err().
- Use table-driven cases (arrays of (input, expected)) for many cases.
- [optional: property tests with proptest for {{invariant}}]
- Doc-test examples for the public functions.
{{code}}
```

### Performance

```text
This Rust code is slower than expected: {{measurement}}. Built with --release: {{yes/no}}.
{{code}}
Look for: allocations in hot loops, cloning, String building, the hashing algorithm, bounds checks, poor
iterator chains, needless collect(), Box<dyn> in hot paths, and locking contention.
Rank the fixes by impact. Give a criterion benchmark skeleton to measure them.
```

### Cargo / build / linker problems

````text
`{{cargo build}}` fails:
```
{{full output}}
```
Cargo.toml:
{{paste}}
Platform: {{Windows 10, MSVC toolchain / GNU}}, rustc {{version}}.
Diagnose it (feature flags, version conflicts, missing system libs, linker, build.rs) and fix it.
````
