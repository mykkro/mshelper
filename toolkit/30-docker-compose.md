# Docker Compose

Use this together with [29-dockerfile.md](29-dockerfile.md) for the images themselves.

## Language block (paste after the session primer)

```text
DOCKER COMPOSE CONVENTIONS for this conversation:
- Docker Compose v2 (`docker compose`, not the old `docker-compose` v1). Follow the Compose Specification:
  no top-level `version:` key (it is obsolete). File: compose.yaml {{+ compose.override.yaml for dev}}.
- Services: pin image tags (never `latest`); `build:` with context/dockerfile/target for local images.
  Container names only if really needed (they prevent scaling).
- Configuration: environment variables via `environment:` or `env_file:`, with defaults in .env
  (${VAR:-default}, ${VAR:?error} for required ones). No secrets committed in compose files; use `secrets:`
  or untracked .env files, and give a .env.example.
- Startup order: `depends_on` with `condition: service_healthy`, backed by real `healthcheck:` definitions.
  The app must still retry its connections (health at startup isn't health forever).
- Networking: services talk to each other by service name on user-defined networks; publish ports to the host
  only for what must be reached from outside, bound to 127.0.0.1 for dev-only access
  ("127.0.0.1:5432:5432"). Separate frontend/backend networks when it helps.
- Data: named volumes for databases and state; bind mounts only for source code in development. Note
  Windows/WSL2 bind-mount performance and file-permission issues when they're relevant.
- Restart policy: `restart: unless-stopped` for long-running services in prod-like setups. Resource limits
  where they matter (deploy.resources or mem_limit).
- Dev vs prod: a base compose.yaml plus override files or profiles (`profiles:`), instead of duplicated files.
- YAML: 2-space indentation, no tabs; quote port mappings and strings that YAML could misread
  ("yes", "no", "on", "08", "1:2").
- Verify with `docker compose config` (renders and validates the final configuration).
```

---

## Docker Compose prompts

### Create a compose project

```text
Create a Docker Compose setup for this project:
- Services: {{e.g. api (built from ./api), worker (same image, different command), postgres 16, redis 7,
  nginx reverse proxy}}.
- Dev mode: hot reload via a bind mount for {{service}}; ports published on 127.0.0.1 only.
- Prod-like mode: no bind mounts, restart policies, resource limits. Use an override file or profiles.
- Health checks for every service, and depends_on with condition: service_healthy.
- Config through .env, with a committed .env.example; secrets via {{secrets: / env file not in git}}.
- Named volumes for the database data. One-off tasks (migrations, seeding) as a separate service or profile.
Give compose.yaml, the override/profile files, .env.example, and the commands for: start dev, start prod-like,
run migrations, view logs, reset data.
```

### Review a compose file

```text
Review this compose file as a strict reviewer:
- Obsolete syntax (top-level version:, links:, docker-compose v1 behavior), unpinned images, secrets in the file.
- depends_on without health checks; health checks that don't test readiness.
- Ports published to 0.0.0.0 that should be internal or bound to 127.0.0.1; services on the default network that
  should be isolated.
- Bind mounts vs named volumes, data that would be lost on `docker compose down -v`.
- YAML pitfalls: tabs, unquoted ports/booleans/octal-looking values, anchors used incorrectly.
List the issues by severity, then give the improved file.
{{compose.yaml}}
```

### Services can't reach each other

```text
Service {{A}} can't connect to {{B}}: {{error, e.g. "connection refused" / "could not resolve host" / timeout}}.
compose.yaml:
{{paste}}
`docker compose ps` and the logs of both services:
{{paste}}
Connection settings that {{A}} uses: {{host/port/URL}}.
Diagnose it. Common causes: using localhost/127.0.0.1 inside a container instead of the service name, the
container port vs the published host port, B listening on 127.0.0.1 instead of 0.0.0.0, B not ready yet (no health
check), different networks, and DNS caching in the client.
```

### Dev environment with hot reload

```text
Set up a development compose environment for {{stack}} with hot reload:
- Source is bind-mounted; dependencies stay inside the container (anonymous volume for node_modules / .venv)
  so host and container don't clash.
- File watching works on {{Windows + Docker Desktop (WSL2) / macOS / Linux}}: say whether polling is needed and
  how to enable it for {{tool}}, or use `docker compose watch` (develop.watch) if it fits better.
- The debugger port for {{language}} is exposed on 127.0.0.1.
Give the compose file(s) and the dev Dockerfile target.
```

### Database with init, backup and restore

```text
Add {{PostgreSQL 16 / MySQL 8 / MongoDB 7}} to this compose project:
- A named volume for data, init scripts from ./db/init, a health check that tests real readiness.
- Credentials from .env / secrets, with an app user separate from the admin user.
- Commands (or a small script) for backup (dump to ./backups with a timestamp) and restore.
- How to reset the database completely, with a warning about data loss.
Existing compose.yaml:
{{paste}}
```

### Convert `docker run` commands to compose

```text
Convert these docker run commands into a compose.yaml, keeping every option (ports, volumes, env, networks,
restart, user, command, labels):
{{commands}}
Point out any options that behave differently in compose, and improve obvious problems (unpinned images,
missing health checks) in a separate, clearly marked step.
```

### Startup / ordering problems

```text
On `docker compose up`, {{service}} fails because {{dependency}} isn't ready:
{{logs}}
compose.yaml:
{{paste}}
Fix it properly: a real health check on {{dependency}}, depends_on: condition: service_healthy, and retry with
backoff in the app's connection code (show where). Explain why depends_on alone (service_started) isn't enough.
```
