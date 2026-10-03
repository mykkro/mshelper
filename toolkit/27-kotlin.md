# Kotlin

## Language block (paste after the session primer)

```text
KOTLIN CONVENTIONS for this conversation:
- Kotlin {{2.0}}, targeting {{JVM 17 / Android / Multiplatform}}. Build: Gradle Kotlin DSL. Framework:
  {{Spring Boot / Ktor / Android (Jetpack Compose) / none}}.
- Idiomatic Kotlin, not Java written in Kotlin: val over var, expression bodies where short, data classes,
  sealed interfaces/classes for closed hierarchies with exhaustive `when`, extension functions for
  helpers, named and default arguments instead of overloads/builders.
- Null safety: no `!!` (use ?., ?:, let, requireNotNull/checkNotNull with a message). Platform types from
  Java APIs: decide nullability explicitly at the boundary.
- Immutability: read-only collections (List, Map) in public APIs; mutable ones only locally.
- Errors: exceptions for programming errors (require/check); {{Result / sealed result types}} for expected
  failures. Never catch Throwable/CancellationException blindly.
- Coroutines: structured concurrency only (no GlobalScope); suspend functions for async work; the right
  dispatcher for blocking I/O (Dispatchers.IO); Flow for streams; cancellation-aware code (don't swallow
  CancellationException).
- Scope functions (let/run/apply/also/with) only when they make the code clearer; no deep nesting of them.
- Formatting: {{ktlint / detekt}} clean; follow the official Kotlin coding conventions.
- Tests: {{JUnit 5 / kotest}} + {{MockK}}; kotlinx-coroutines-test (runTest) for coroutines.
- Don't add dependencies without asking.
```

---

## Kotlin prompts

### Java to idiomatic Kotlin

```text
Convert this Java code to idiomatic Kotlin. Don't transliterate it line by line.
- POJOs -> data classes; static helpers -> top-level or extension functions; builders -> named/default args.
- Decide the nullability of every type explicitly; no `!!`.
- Streams -> Kotlin collection operations; switch/if chains -> `when`.
- Keep the public API usable from Java if needed ({{yes/no}}): @JvmStatic, @JvmOverloads, @JvmName.
List any behavior differences (e.g. nullability now enforced, equality semantics of data classes).
{{code}}
```

### Coroutines review

```text
Review this coroutine code for: GlobalScope or unstructured launches, blocking calls on the wrong dispatcher,
swallowed CancellationException (catch (e: Exception) around suspend calls), leaking scopes/jobs,
runBlocking in production code, shared mutable state without Mutex/atomic, and Flow collection on the wrong
context or lifecycle. For each one: what can go wrong, and the fix.
{{code}}
```

### Convert callbacks / futures to coroutines

```text
Convert this {{callback-based / CompletableFuture / RxJava}} code to coroutines:
- Wrap callback APIs with suspendCancellableCoroutine (and unregister on cancellation).
- Run independent calls concurrently with async/awaitAll inside coroutineScope.
- Use timeouts (withTimeout) where needed; the caller's cancellation must propagate.
{{code}}
```

### Sealed hierarchy for state

```text
Model {{UI state / domain state / API result}} as a sealed interface:
{{description or current code}}
- One subtype per state, carrying only that state's data (data class / data object).
- Exhaustive `when` at the use sites, with no else branch.
- Show how the code that produces and consumes it changes.
```

### Ktor / Spring endpoint

```text
Add an endpoint {{METHOD /path}} to this {{Ktor / Spring Boot}} app (Kotlin):
- Request/response as @Serializable data classes (kotlinx.serialization) {{or Jackson}}, with validation and
  400 responses on bad input.
- Suspend handlers; the service layer is separate from routing.
- Tests: {{testApplication (Ktor) / WebTestClient or MockMvc (Spring)}}.
Existing code for style:
{{code}}
```

### Android / Compose issue

```text
This Compose screen {{recomposes too often / loses state on rotation / shows stale data / leaks}}.
{{composable + ViewModel code}}
Explain the cause in terms of state hoisting, remember/rememberSaveable, stable types, and
collectAsStateWithLifecycle. Then give the minimal fix.
```

### Tests with MockK and runTest

```text
Write tests for this Kotlin class with {{JUnit 5 / kotest}} + MockK:
- Use runTest for suspend functions (no Thread.sleep or runBlocking); inject the dispatchers for testability.
- coEvery/coVerify for suspend mocks; mock only external collaborators.
- Test names in backticks describing the behavior: `returns cached value when fresh`.
{{code}}
```

### Gradle (Kotlin DSL) problem

````text
Gradle build fails:
```
{{output with --stacktrace (the relevant part)}}
```
build.gradle.kts / settings.gradle.kts / libs.versions.toml:
{{paste}}
Kotlin {{version}}, Gradle {{version}}, JDK {{version}}, AGP {{version if Android}}.
Diagnose it (Kotlin/JVM target mismatch, plugin vs Kotlin version, KSP/kapt, version catalog errors,
dependency conflicts) and fix it.
````
