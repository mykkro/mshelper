# CMake

For C/C++ code itself, see [23-c.md](23-c.md) and [24-cpp.md](24-cpp.md).

## Language block (paste after the session primer)

```text
CMAKE CONVENTIONS for this conversation:
- CMake >= {{3.21}} (use only features of my minimum version; say when something needs a newer one).
  Generators: {{Ninja / Visual Studio 17 2022 / Unix Makefiles}}. Compilers: {{MSVC / gcc / clang}}.
  Dependencies via {{FetchContent / find_package + vcpkg / Conan / system packages}}.
- Modern, target-based CMake: everything per target with target_sources, target_include_directories,
  target_compile_features, target_compile_options, target_compile_definitions and target_link_libraries, each with
  PRIVATE / PUBLIC / INTERFACE chosen deliberately. No global include_directories, add_definitions,
  link_libraries or CMAKE_CXX_FLAGS edits.
- Language standard via target_compile_features (cxx_std_20) or CMAKE_CXX_STANDARD + CMAKE_CXX_STANDARD_REQUIRED ON
  + CMAKE_CXX_EXTENSIONS OFF.
- Warnings per target, compiler-aware: MSVC /W4 (/permissive-), others -Wall -Wextra -Wpedantic; an option to turn
  them into errors. Use generator expressions ($<CXX_COMPILER_ID:MSVC>, $<CONFIG:Debug>) instead of if() where
  it's clearer.
- List source files explicitly; no file(GLOB) for sources (or CONFIGURE_DEPENDS if unavoidable, with the caveat).
- Out-of-source builds only. Provide CMakePresets.json for the common configurations (debug, release, ci).
- Libraries: an alias target (MyLib::MyLib); install() and export with a package config file when the library is
  consumed by others; $<BUILD_INTERFACE:...> / $<INSTALL_INTERFACE:...> for include directories.
- Tests: enable_testing() + add_test (or gtest_discover_tests / catch_discover_tests); run them with ctest.
- Options: option() with a project prefix (MYPROJ_BUILD_TESTS); don't override cache variables the user set.
- Multi-config generators (Visual Studio, Ninja Multi-Config): don't rely on CMAKE_BUILD_TYPE there; use
  $<CONFIG>.
- Explain any non-obvious line with a short comment.
```

---

## CMake prompts

### New project setup

```text
Create a modern CMake setup for this project:
- Targets: {{e.g. library core (src/core/*.cpp), executable app (src/main.cpp) linking core, tests}}.
- Standard: {{C++20 / C17}}. Minimum CMake: {{3.21}}.
- Dependencies: {{e.g. fmt, spdlog, GoogleTest}} via {{FetchContent / find_package (vcpkg)}}.
- Per-target warnings with a MYPROJ_WARNINGS_AS_ERRORS option; an ASan+UBSan option for non-MSVC builds.
- Tests with CTest; CMakePresets.json with debug, release and ci presets.
Give every CMakeLists.txt in full, CMakePresets.json, and the configure/build/test commands for
{{Windows (Visual Studio / Ninja) and Linux}}.
Layout:
{{tree}}
```

### Modernize an old CMakeLists.txt

```text
Modernize this CMake code to target-based CMake (minimum {{3.21}}) without changing what gets built:
- Global include_directories/add_definitions/link_libraries/CMAKE_CXX_FLAGS -> per-target commands with the
  correct PRIVATE/PUBLIC/INTERFACE.
- file(GLOB) sources -> explicit lists; hard-coded paths and compiler flags -> generator expressions and
  target_compile_features.
- find_package results used as variables (${FOO_LIBRARIES}) -> imported targets (Foo::Foo) where they exist.
Do it in reviewable steps, and list anything whose behavior might change (e.g. usage requirements now
propagate to dependents).
{{CMakeLists.txt files}}
```

### Add a dependency

```text
Add {{library}} (version {{version}}) to this CMake project using {{FetchContent / find_package with vcpkg /
Conan / a system package}}.
- Link it to {{target}} with the correct visibility (PRIVATE unless it's in our public headers).
- It must work {{offline / behind a corporate proxy / in CI}}: say how (FETCHCONTENT_TRY_FIND_PACKAGE_MODE, a local
  mirror, FETCHCONTENT_SOURCE_DIR_<NAME>, vcpkg binary caching).
- If the library doesn't provide a CMake config, write a minimal Find module or IMPORTED target.
Current CMakeLists.txt:
{{paste}}
```

### Configure or find_package error

````text
CMake configure fails:
```
{{full output of cmake -S . -B build ... (from the first error), optionally with --debug-find}}
```
CMakeLists.txt (relevant parts):
{{paste}}
CMake {{version}}, generator {{...}}, platform {{...}}, package manager {{vcpkg / Conan / none}}, toolchain file {{...}}.
Explain why CMake can't find or configure it (search paths, CMAKE_PREFIX_PATH, <Pkg>_DIR, toolchain file
order, config vs module mode, architecture/triplet mismatch), and fix it, preferring a fix in presets or the
command line over hard-coded paths.
````

### Link errors from a CMake build

````text
The build fails at link time:
```
{{linker output}}
```
CMakeLists.txt files:
{{paste}}
Explain which symbol is missing and why from CMake's point of view (missing target_link_libraries, wrong
visibility so the dependency doesn't propagate, a static/shared mix-up, link order for static libs, a missing
source in target_sources, MSVC runtime mismatch: CMAKE_MSVC_RUNTIME_LIBRARY), and fix it.
````

### Presets and toolchains

```text
Write CMakePresets.json (schema version {{6}}) for this project:
- Configure presets: {{windows-msvc-debug, windows-msvc-release, linux-gcc-debug, linux-clang-asan, ci}}, using
  {{Ninja / Visual Studio}} with a binary dir under out/build/<preset>.
- vcpkg toolchain integration {{if used}}; cache variables for our options ({{list}}).
- Matching build and test presets (test output on failure), and a workflow preset for CI.
Explain how to use them from the command line and from VS Code (CMake Tools).
```

### Install and export a library

```text
Make the library target {{name}} installable and consumable with find_package({{Name}} CONFIG):
- install(TARGETS ... EXPORT ...), install the public headers, generate {{Name}}Config.cmake and
  {{Name}}ConfigVersion.cmake (CMakePackageConfigHelpers), with the namespace {{Name}}::.
- Correct $<BUILD_INTERFACE>/$<INSTALL_INTERFACE> include directories and transitive dependencies
  (find_dependency in the config file).
- A minimal consumer project to test it.
Current CMakeLists.txt:
{{paste}}
```
