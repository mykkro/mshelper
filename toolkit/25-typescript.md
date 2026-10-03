# TypeScript

Framework prompts (React, Express/Fastify, async bugs, vitest/jest, build errors) are in
[21-javascript.md](21-javascript.md) and work for TypeScript too. This page covers the type system,
compiler configuration and migration.

## Language block (paste after the session primer)

```text
TYPESCRIPT CONVENTIONS for this conversation:
- TypeScript {{5.x}} with "strict": true {{plus noUncheckedIndexedAccess, exactOptionalPropertyTypes}}.
  Runtime: {{Node 20 / browser / Deno / Bun}}. Modules: {{ESM}}. Code must pass `tsc --noEmit` and
  {{eslint (typescript-eslint) + prettier}}.
- No `any`. Use `unknown` + narrowing (typeof, instanceof, `in`, discriminant checks, type guard functions).
  No non-null assertions (`!`) and no `as` casts unless you explain why they're safe. Never use
  `as unknown as T`.
- Model data with type aliases/interfaces. Use discriminated unions for variants, with an exhaustive `switch`
  and a `never` check. Prefer union literal types or `as const` objects over `enum`.
- Explicit return types on exported functions. `readonly` for data that shouldn't change. Use
  `satisfies` to check object literals without widening them.
- Validate external data (HTTP, JSON, env, files) at the boundary with {{zod / valibot / a hand-written guard}},
  and derive the static types from the schema (z.infer) instead of declaring them twice.
- Generics only when they remove duplication or keep a relationship between types. Keep them simple and
  readable; explain any conditional/mapped type.
- Use `import type` for type-only imports. No `namespace`; no `declare` unless writing .d.ts files.
- Async: async/await; no floating promises (use @typescript-eslint/no-floating-promises).
- Errors: throw Error subclasses; in catch blocks, treat the error as `unknown` and narrow it.
- Tests: {{vitest / jest}}; type-level tests with `expectTypeOf` or `// @ts-expect-error`.
- If something depends on a newer TS version than mine, say so.
```

---

## TypeScript prompts

### Convert JS to TypeScript

```text
Convert this JavaScript file to strict TypeScript.
- Infer precise types from usage. Create interfaces/types for the data shapes.
- No `any`. Where the type is really unknown, use `unknown` and narrow it.
- Mark places where the conversion exposed potential runtime bugs (null access, wrong arity, etc.).
- Keep the runtime behavior identical.
{{code}}
```

### Incremental migration plan

```text
Plan a gradual migration of this JavaScript project to TypeScript:
- Project size/layout: {{tree or summary}}. Build: {{Vite / webpack / tsc / none}}. Tests: {{...}}.
- Phase 1: tsconfig with allowJs + checkJs off, build still working. Phase 2: convert leaf modules first.
  Phase 3: turn on strict flags one at a time.
- For each phase: the config changes, the order of files, and how to keep main shippable.
Give the initial tsconfig.json and the package.json script changes.
```

### Fix a type error

````text
`tsc` reports:
```
{{full error, including the "Type X is not assignable to type Y" elaboration chain}}
```
Code:
{{code + the relevant type definitions}}
TypeScript {{version}}, relevant tsconfig flags: {{strict, noUncheckedIndexedAccess, ...}}.

1) Explain in plain words which types the compiler compared and where exactly they differ.
2) Say whether the error found a real bug, or the types are just imprecise.
3) Fix it properly. Don't use `any`, `as` or `!` to silence it unless you justify it.
````

### Type a tricky value

```text
I need a TypeScript type for {{description}}. Example values:
{{examples}}
It should reject: {{invalid examples}}
Give the type, explain any advanced features you used (generics, conditional/mapped/template literal types),
and show compile-time tests using `// @ts-expect-error` lines.
```

### Runtime validation with derived types

```text
Write a {{zod}} schema for this external data and derive the TypeScript type from it:
Sample payload(s):
{{json}}
Rules: {{required fields, formats, ranges, enums}}.
- Give a `parseX(input: unknown): X` function that throws (or returns a Result) with readable error messages.
- Show how to use it at the boundary ({{fetch response / request handler / env vars}}).
- Tests for one valid sample and the most important invalid cases.
```

### Discriminated union + exhaustive handling

```text
Refactor this code to model {{concept}} as a discriminated union, with `kind` as the discriminant:
{{code}}
- One variant per case, carrying only the data that case needs.
- Handle the variants with exhaustive `switch` statements, with an `assertNever(x: never)` default.
- Point out the bugs or impossible states this removes.
```

### Generic utility

```text
Write a generic, fully typed TypeScript function: {{description, e.g. groupBy(items, keyFn) -> Record<K, T[]>}}.
- The inferred types must be precise at the call site: show 3 example calls with their inferred result types.
- No overload unless it's needed. No `any` inside the implementation either (a narrow `as` is OK, with a comment).
- Type tests with expectTypeOf or @ts-expect-error.
```

### tsconfig review

```text
Review this tsconfig.json for a {{Node library / Node service / browser app with Vite / monorepo package}}:
{{tsconfig}}
Check: strictness flags, module/moduleResolution/target consistency with my runtime and bundler,
declaration output for libraries, paths/baseUrl pitfalls, isolatedModules/verbatimModuleSyntax, and
skipLibCheck trade-offs. Give a corrected config, with a one-line comment per changed option.
```

### Typing a third-party module

```text
The package {{name}}@{{version}} has no types (or wrong types). Here's how I use it:
{{usage code}}
Write a minimal `{{name}}.d.ts` declaration that covers exactly my usage, with accurate types. Tell me where to
put it and how to include it in tsconfig. If @types/{{name}} exists, say so instead.
```
