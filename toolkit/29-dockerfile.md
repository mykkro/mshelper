# Dockerfile

For multi-container setups, see [30-docker-compose.md](30-docker-compose.md).

## Language block (paste after the session primer)

```text
DOCKERFILE CONVENTIONS for this conversation:
- Engine: Docker {{24+}} with BuildKit. Target platform(s): {{linux/amd64 / linux/arm64 / both}}. Registry/base
  image policy: {{e.g. only internal mirror registry.company.local, approved bases}}.
- Pin base images to a specific version tag ({{and digest @sha256 for production}}); never `latest`. Prefer
  slim/distroless/alpine variants only when compatible (musl vs glibc matters for Python wheels, Node native
  modules and Rust binaries; say so).
- Multi-stage builds: build tools only in the builder stage, a minimal runtime stage. COPY --from only the
  artifacts the runtime needs.
- Layer caching: copy dependency manifests first (requirements.txt / package*.json / Cargo.toml + lock files),
  install dependencies, then copy the source. Use BuildKit cache mounts (RUN --mount=type=cache) for package
  caches. Every project gets a .dockerignore (.git, node_modules, target, .venv, secrets, build output).
- RUN: combine related commands with && and clean package-manager caches in the same layer
  (apt-get update && apt-get install -y --no-install-recommends ... && rm -rf /var/lib/apt/lists/*).
  Pin package versions where reproducibility matters. Use `set -eux` or SHELL ["/bin/bash", "-o", "pipefail", "-c"]
  for pipes.
- Security: run as a non-root USER with a fixed UID; no secrets in ENV/ARG/layers (use RUN --mount=type=secret);
  no curl | sh without checksum verification; minimal installed packages.
- Runtime: exec-form CMD/ENTRYPOINT (JSON array) so signals reach the process; a proper init (tini or
  --init) if the app spawns children; HEALTHCHECK where the orchestrator uses it; EXPOSE documents the ports;
  logs to stdout/stderr; config via environment variables.
- WORKDIR instead of `cd`; COPY instead of ADD (ADD only for remote checksummed files or tar extraction);
  LABEL org.opencontainers.image.* metadata.
- Must pass `hadolint` (explain any ignore). Line continuations: a backslash must be the LAST character on the
  line (no trailing spaces).
```

---

## Dockerfile prompts

### Write a Dockerfile

```text
Write a production Dockerfile and .dockerignore for this {{Python FastAPI / Node Express / Rust axum / Java Spring Boot / C++ CMake}} app.
- Build: {{build command}}; run: {{run command}}; port {{port}}; config via env vars: {{list}}.
- Dependency files: {{requirements.txt / package-lock.json / Cargo.lock / pom.xml}}.
- Multi-stage, non-root user, pinned base images ({{base image constraints}}), cache-friendly layer order,
  BuildKit cache mounts, HEALTHCHECK on {{/health}}.
- Target image size: as small as practical; tell me the expected size.
Give the build and run commands, and explain each stage in one line.
Project layout:
{{tree}}
```

### Review / harden a Dockerfile

```text
Review this Dockerfile as a strict reviewer. Check:
- Base image pinning, unnecessary packages, root user, secrets in ENV/ARG/layers, ADD vs COPY, curl | sh.
- Layer cache order (do source changes reinstall dependencies?), missing .dockerignore entries, missing
  cleanup in the same RUN layer.
- Shell-form vs exec-form CMD/ENTRYPOINT (signal handling, PID 1), missing pipefail.
- What hadolint would flag (DL/SC codes).
List the issues by severity, then give the improved Dockerfile.
{{Dockerfile}}
{{optional: .dockerignore}}
```

### Shrink the image

```text
This image is {{size}}. Make it smaller without breaking it.
{{Dockerfile}}
`docker history --no-trunc {{image}}` output:
{{paste}}
Find which layers are big and why. Propose changes ranked by the size saved: multi-stage, slimmer base
(warn about musl/glibc issues), removing build deps, --no-install-recommends, cleaning caches in the same
layer, copying only the runtime artifacts. Give the new Dockerfile and the expected size.
```

### Speed up builds (cache)

```text
Every build reinstalls all dependencies and takes {{time}}. Dockerfile:
{{Dockerfile}}
.dockerignore:
{{paste or "none"}}
Explain why the cache is invalidated, and fix the layer order. Add BuildKit cache mounts for
{{pip / npm / cargo / maven}} and a .dockerignore. Say how to verify the cache hits (docker build --progress=plain).
```

### Build failure

````text
`docker build` fails:
```
{{output with --progress=plain (the failing step and ~30 lines before it)}}
```
Dockerfile:
{{Dockerfile}}
Docker version {{docker version}}, host {{Windows + Docker Desktop (WSL2) / Linux}}, build platform {{...}}.
Diagnose it. Common suspects: files missing from the build context or excluded by .dockerignore, CRLF line
endings in shell scripts (`/bin/sh^M: bad interpreter`), musl vs glibc, an arch mismatch (arm64 vs amd64),
a corporate proxy or TLS interception (certificates), and network access during the build.
````

### Container starts then exits / won't respond

```text
The container {{exits immediately with code N / restarts in a loop / runs but the port doesn't respond}}.
Dockerfile:
{{Dockerfile}}
Run command: {{docker run ...}}
`docker logs` output:
{{paste}}
`docker inspect` (State, Config.Cmd/Entrypoint, NetworkSettings.Ports):
{{paste}}
Find the cause. Check: the app listening on 127.0.0.1 instead of 0.0.0.0, a wrong CMD/ENTRYPOINT combination,
a missing env var, file permissions for the non-root user, and the wrong working directory.
```

### Corporate proxy / custom CA certificates

```text
Builds and containers must work behind our corporate proxy {{proxy URL}}, which uses a custom root CA
({{certificate file name}}). Show how to:
- Pass the proxy settings at build time (build args HTTP_PROXY/HTTPS_PROXY/NO_PROXY) without baking them into
  the final image.
- Install the CA certificate in {{Debian/Ubuntu / Alpine / UBI}} images, and make {{pip / npm / cargo / Java}}
  trust it.
- Keep the Dockerfile working outside the corporate network too.
```
