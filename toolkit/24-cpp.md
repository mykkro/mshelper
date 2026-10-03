# C++

## Language block (paste after the session primer)

```text
C++ CONVENTIONS for this conversation:
- Standard: {{C++17 / C++20 / C++23}}. Compiler: {{gcc / clang / MSVC}}. Build: {{CMake}}.
  Code must compile cleanly with -Wall -Wextra -Wpedantic (MSVC /W4) and pass {{clang-tidy}}.
- Follow the C++ Core Guidelines. Use modern C++ only for what my standard version supports; if
  something needs a newer standard, say so.
- RAII everywhere: no raw new/delete. Use std::unique_ptr by default, std::shared_ptr only for real
  shared ownership. Raw pointers and references are non-owning.
- Rule of zero; if you must write a destructor or copy/move operation, follow the rule of five.
- Pass cheap types by value, read-only large ones by const&, sinks by value + std::move. Use
  std::string_view / std::span for non-owning views, and make sure they never outlive their data.
- const and constexpr wherever possible. [[nodiscard]] on functions whose result must not be ignored.
  noexcept on move operations and on functions that truly cannot throw.
- Prefer standard containers and <algorithm> / ranges to hand-written loops when it's clearer.
- Errors: {{exceptions / std::expected / error codes}}. Don't mix styles within a module. Exception
  safety: at least the basic guarantee; say when the strong guarantee holds.
- No undefined behavior: dangling references/iterators, iterator invalidation, signed overflow,
  out-of-bounds access, data races.
- Concurrency: std::jthread / std::mutex / std::scoped_lock / std::atomic; document what each mutex protects.
- Headers: #pragma once (or guards), minimal includes, no `using namespace` in headers.
- Tests: {{GoogleTest / Catch2 / doctest}}. Recommend running them under ASan + UBSan (and TSan for threaded code).
- No new dependencies without asking.
```

---

## C++ prompts

### Modernize legacy C++

```text
Modernize this C++ code to {{C++17/20}} without changing the behavior:
- Raw new/delete → smart pointers or values; manual arrays → std::vector/std::array.
- Index loops → range-for / algorithms / ranges where clearer.
- NULL → nullptr, typedef → using, C casts → named casts, macros → constexpr/inline functions.
- Add const, override, final, [[nodiscard]] and noexcept where they're correct.
Do it in reviewable steps, listing each one before applying it. Point out any ownership that is unclear.
{{code}}
```

### Ownership & lifetime review

```text
Review this C++ code for ownership and lifetime bugs:
dangling references/pointers/string_views/spans, iterator invalidation, use-after-move, returning
references to locals or temporaries, lambdas capturing by reference that outlive their scope, shared_ptr
cycles, and missing virtual destructors.
For each one: the line, the scenario that triggers it, and the fix. Then say who owns what in this code,
as a short list.
{{code}}
```

### Decode a template error

````text
This template error is unreadable:
```
{{full compiler output: the first error plus its "required from" / "note" chain}}
```
Compiler: {{gcc / clang / MSVC + version}}, standard {{C++20}}.
Code:
{{code}}
1) Say in plain words what the compiler tried to do and which requirement failed.
2) Point to the line in MY code that causes it.
3) Fix it. If concepts/static_assert would make the error clearer next time, show how.
````

### Design a class

```text
Design a C++ class for {{purpose}}.
- Invariants: {{list}}. Enforce them in the constructor/factory; members private.
- Ownership of resources: {{describe}}. Rule of zero if possible, otherwise rule of five.
- Error handling: {{exceptions / std::expected}}.
- Thread-safety: {{none / internally synchronized}}.
Give the header, the implementation, and {{GoogleTest}} tests. Explain the choices that aren't obvious.
```

### Performance

```text
This C++ code is slower than expected: {{measurement}}, built with {{-O2 / Release}}.
{{code}}
Look for: unnecessary copies (missing move / pass-by-value of large types), allocations in hot loops
(missing reserve), cache-unfriendly layouts, virtual calls / std::function in hot paths, std::map where
std::unordered_map or a sorted vector would do, exceptions used for control flow, and lock contention.
Rank the fixes by impact. Give a Google Benchmark skeleton to measure them.
```

### Concurrency bug

```text
This multithreaded C++ code sometimes {{deadlocks / gives wrong results / crashes}}.
[optional: ThreadSanitizer output:
{{paste}}]
{{code}}
Find the data races, lock-order inversions and missed notifications (condition_variable without a predicate).
Give an interleaving that shows the bug, then the fix. Say what each mutex protects.
```

### CMake project setup

```text
Create a modern CMake (>= {{3.20}}) setup for this C++ project:
- Targets: {{library / executable names and sources}}. Standard {{C++20}} through target_compile_features.
- Warnings per target (MSVC /W4, others -Wall -Wextra -Wpedantic), with an option to turn them into errors.
- Dependencies: {{e.g. fmt, GoogleTest}} through {{FetchContent / find_package / vcpkg}}.
- Tests registered with CTest; a sanitizer option (ASan+UBSan) for non-MSVC builds.
- No global include_directories / add_definitions; everything per target.
Give the complete CMakeLists.txt files and the configure/build/test commands.
```

### Write tests

```text
Write {{GoogleTest / Catch2}} tests for this code:
- Cover: the happy path, boundaries, invalid input, error paths (exceptions or error results), and
  resource cleanup.
- Test names describe the behavior. Use fixtures for shared setup, and parameterized tests for tables of cases.
- No sleeps in tests; inject clocks or other dependencies through interfaces or templates.
{{code}}
```

### Explain a linker error

````text
Linking fails:
```
{{full linker output}}
```
Build setup: {{CMakeLists.txt or command}}. Compiler: {{...}}.
Explain which symbol is missing and why (missing source in the target, a template defined in a .cpp,
missing target_link_libraries, ABI/runtime mismatch such as MSVC /MD vs /MT, name mangling with
C code / extern "C"), and fix it.
````
