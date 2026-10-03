# Java

## Language block (paste after the session primer)

```text
JAVA CONVENTIONS for this conversation:
- Java {{17 / 21}} (LTS). Use only features available in my version; say when something needs a newer one.
  Build: {{Maven / Gradle (Kotlin DSL)}}. Framework: {{Spring Boot 3 / Quarkus / Jakarta EE / none}}.
- Modern Java: records for immutable data, sealed interfaces + pattern matching for closed hierarchies,
  switch expressions, `var` for local variables when the type is obvious, text blocks for multi-line strings.
- Immutability by default: final fields, List.of / Map.of / Collectors.toUnmodifiableList(), defensive copies of
  mutable inputs.
- Null handling: don't return null from collections or Optional-returning methods; use Optional only as a
  return type (never for fields or parameters); validate parameters with Objects.requireNonNull at
  the public API boundary. Use {{JSpecify / Jakarta}} @Nullable annotations where the project does.
- Exceptions: specific exception types, with the cause attached when wrapping. Never swallow exceptions.
  Checked exceptions only where the caller can recover. try-with-resources for every AutoCloseable.
- Streams where they read better than loops, but no side effects inside stream operations.
- Concurrency: java.util.concurrent (ExecutorService, CompletableFuture{{, virtual threads on 21}}); document
  thread-safety; no manual Thread management; no synchronized on public objects.
- Logging: SLF4J with parameterized messages ("id={}"), never string concatenation; no System.out.
- equals/hashCode/toString: records, or generate all of them consistently.
- Tests: JUnit 5 + AssertJ{{ + Mockito}}; @ParameterizedTest for tables of cases; mock only at external boundaries.
- Follow the existing formatting ({{google-java-format / Spotless / IDE defaults}}). Don't add dependencies without asking.
```

---

## Java prompts

### Modernize legacy Java

```text
Modernize this Java code to Java {{17/21}} without changing the behavior:
- POJOs that only hold data -> records; type-code switches -> sealed interfaces + pattern matching.
- Old switch statements -> switch expressions; instanceof + cast -> pattern matching for instanceof.
- Anonymous classes -> lambdas/method references; manual loops -> streams only where clearer.
- Raw types -> generics; Date/Calendar -> java.time; manual resource closing -> try-with-resources.
Do it in reviewable steps, and point out any change that could affect serialization, reflection or frameworks
(JPA entities, Jackson, Spring proxies).
{{code}}
```

### NullPointerException / stack trace

````text
Stack trace:
```
{{full stack trace, including "Caused by" sections}}
```
Java {{version}}, framework {{...}}. Code for the frames in MY packages:
{{code}}
Find the root cause. Read the "Caused by" chain to its deepest cause; the top frame is often not the bug.
For an NPE, use the helpful NPE message to say which reference was null and why. Then give the fix,
and say how to prevent this class of bug (validation, Optional, annotations).
````

### Spring Boot endpoint

```text
Add a REST endpoint {{METHOD /path}} to this Spring Boot {{3.x}} app:
- Request/response DTOs as records, with Bean Validation (@Valid, @NotNull, @Size...); 400 with field errors
  through the existing @ControllerAdvice (or create one: ProblemDetail responses).
- Thin controller, logic in a @Service, data access through {{Spring Data JPA repository / JdbcClient}}.
- Transactions only on the service methods that need them.
- Tests: @WebMvcTest for the controller (MockMvc), and a unit test for the service.
Existing code for style:
{{controller / service / entity}}
```

### JPA / Hibernate problem

```text
I have a JPA problem: {{N+1 queries / LazyInitializationException / slow query / wrong results / unexpected
updates}}.
Entities:
{{entity classes with their mappings}}
Repository/query and the calling code:
{{code}}
SQL log (spring.jpa.show-sql / hibernate.SQL):
{{log}}
Explain what Hibernate is doing and why, then fix it (fetch join, @EntityGraph, a DTO projection, batch
size, transaction boundaries...). State the trade-offs.
```

### Concurrency review

```text
Review this Java code for thread-safety: shared mutable state, check-then-act races, visibility (missing
volatile/synchronization), non-thread-safe collections, deadlock risk from lock ordering, misuse of
CompletableFuture (blocking join/get in async chains, lost exceptions), and executor lifecycle (shutdown).
For each issue: an interleaving that triggers it, and the fix. {{optional: Java 21: say whether virtual threads
would simplify it, and watch for pinning in synchronized blocks.}}
{{code}}
```

### JUnit 5 tests

```text
Write JUnit 5 tests with AssertJ for this class:
- @Nested classes per method, and @DisplayName or descriptive method names (shouldXWhenY).
- @ParameterizedTest with @CsvSource / @MethodSource for tables of cases.
- assertThatThrownBy(...).isInstanceOf(...).hasMessageContaining(...) for errors.
- Mockito only for external collaborators ({{repository, HTTP client, clock}}); use a fixed Clock for time.
{{code}}
```

### Maven / Gradle build problem

````text
The build fails:
```
{{full output of mvn -e / gradle --stacktrace (the relevant part)}}
```
Build file:
{{pom.xml or build.gradle.kts}}
JDK {{version}}, {{Maven/Gradle}} {{version}}.
Diagnose it (dependency conflict: show how to inspect it with `mvn dependency:tree` / `gradle dependencies`;
JDK/target mismatch; plugin versions; annotation processing) and fix it.
````
