# JavaScript

For TypeScript projects, use the language block from [25-typescript.md](25-typescript.md). The
framework prompts below (React, Express, async, testing, tooling) work for both JS and TS.

## Language block (paste after the session primer)

```text
JAVASCRIPT CONVENTIONS for this conversation:
- Runtime: {{Node 20 / browser / both}}. Language: modern JavaScript ({{ES2022}}).
- Modules: {{ESM (import/export) / CommonJS}}. Package manager: {{npm / pnpm / yarn}}.
- Use const by default, let when you must reassign, never var. Use ===. Use optional chaining and ??.
- Async: async/await, no raw .then chains. Always handle rejections; never leave floating promises.
  Use Promise.all / allSettled for independent work.
- Types without TypeScript: JSDoc type annotations on exported functions, and `// @ts-check` at the top
  of files {{if the project uses it}}. Validate external data at the boundaries.
- Errors: throw Error (or subclasses) with useful messages; don't throw strings. Use `cause` when wrapping.
- Code must pass {{eslint + prettier}}.
- Framework: {{React 18 with function components + hooks / Vue 3 / Express / Fastify / none}}.
- Tests: {{vitest / jest}}, plus {{@testing-library/react / supertest}} where relevant.
- Prefer the platform and standard library (fetch, URL, structuredClone, Array methods) over adding
  dependencies.
```

---

## JavaScript prompts

### React component

```text
Write a React {{18}} function component in TypeScript: {{component description}}.
- Props interface: {{props}}
- State and behavior: {{...}}
- Accessibility: semantic HTML, labels, keyboard support, aria attributes only where needed.
- Styling: {{CSS modules / Tailwind / styled-components / plain CSS}}.
- No unnecessary useEffect: derive values during render where possible; memoize only if justified.
- Include a test with @testing-library/react that checks the user-visible behavior.
```

### Fix a React re-render / hooks problem

```text
This component {{re-renders too often / has a stale value / loops infinitely / shows an
exhaustive-deps warning}}.
{{component code}}
Explain exactly which state/prop/dependency causes it, using React's render model. Then give the
minimal fix. Don't just silence the lint rule.
```

### Express/Fastify endpoint

```text
Add an endpoint {{METHOD /path}} to this {{Express / Fastify}} app:
- Input: {{body/query/params}}. Validate it with {{zod / JSON schema}}; return 400 with field errors.
- Behavior: {{...}}
- Responses: {{status codes + shapes}}
- Errors go through the existing error handler; no stack traces leak to clients.
- Tests with {{supertest / fastify.inject}} covering success, validation errors and not-found.
Existing app setup and one existing route, for style:
{{code}}
```

### Async bug hunt

```text
This async code sometimes {{hangs / returns stale data / throws an unhandled rejection / runs out of order}}.
{{code}}
Analyze: unawaited promises, missing error handling, race conditions, shared mutable state across
awaits, and sequential awaits that should run in parallel (or the reverse). Give a timeline of how the
bug happens, then the fix.
```

### Modernize legacy JS

```text
Modernize this legacy JavaScript (callbacks / var / prototype classes / jQuery) to modern
{{ESM + async/await + classes or functions}}. Keep the behavior and the public API identical.
Do it in reviewable steps, listing each one before applying it.
{{code}}
```

### Write vitest/jest tests

```text
Write {{vitest}} tests for this module:
- Use describe blocks per function, and it("does X when Y") names.
- Mock modules with vi.mock / jest.mock only at external boundaries (fetch, fs, timers via fake timers).
- Test async errors with `await expect(...).rejects.toThrow(...)`.
- Use test.each for tables of cases.
{{code}}
```

### package.json scripts / tooling

```text
Set up {{eslint (flat config) + prettier + vitest + tsc}} for this project. Package type: {{module}}.
Give: the devDependencies to install (one npm command), the config files (complete), and package.json
scripts for lint, format, typecheck, test and check (runs all). Keep the configs minimal.
```

### Bundle / build error

````text
`{{npm run build}}` fails with:
```
{{output}}
```
Tooling: {{Vite 5 / webpack 5 / tsc / esbuild}}, config:
{{config file}}
package.json (dependencies + scripts):
{{paste}}
Diagnose the cause (ESM/CJS interop, paths, types, missing deps, ...) and fix it.
````
