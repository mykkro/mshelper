"""Prompt Wizard: a tiny local web app that builds prompts for Microsoft 365 Copilot.

Standard library only (Python 3.11+). Run:  python server.py  [--port 8765] [--root C:/path/to/project]
Then open http://127.0.0.1:8765
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import tomllib
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_FILE = BASE_DIR / "templates.toml"

MAX_FILE_BYTES = 200_000
MAX_TREE_ENTRIES = 400
EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "target", ".venv", "venv", "env", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build", ".next", ".idea", ".vscode",
    "coverage", ".tox",
}
EXT_LANG = {
    ".py": "python", ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "tsx", ".jsx": "jsx", ".rs": "rust", ".toml": "toml",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".md": "markdown", ".html": "html",
    ".css": "css", ".sql": "sql", ".sh": "bash", ".ps1": "powershell", ".txt": "text",
}
PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


class WizardError(Exception):
    """A user-facing error returned to the browser as HTTP 400."""


# ---------------------------------------------------------------------------
# Templates & rendering
# ---------------------------------------------------------------------------

def load_templates(path: Path = TEMPLATES_FILE) -> dict[str, Any]:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _all_empty(text: str, values: dict[str, str]) -> bool:
    names = PLACEHOLDER.findall(text)
    return bool(names) and all(not values.get(n, "").strip() for n in names)


def fill(template: str, values: dict[str, str]) -> str:
    """Substitute {{name}} placeholders, dropping parts whose optional fields are empty.

    A paragraph (blank-line separated) whose placeholders are all empty is dropped with its
    label; inside a kept paragraph, a line whose placeholders are all empty is dropped.
    """
    paragraphs: list[str] = []
    for para in re.split(r"\n[ \t]*\n", template.strip()):
        if _all_empty(para, values):
            continue
        lines = [line for line in para.splitlines() if not _all_empty(line, values)]
        text = "\n".join(lines)
        paragraphs.append(PLACEHOLDER.sub(lambda m: values.get(m.group(1), "").strip("\n"), text))
    return "\n\n".join(p for p in paragraphs if p.strip())


def fence(text: str, lang: str = "") -> str:
    """Wrap text in a code fence that is longer than any backtick run inside it."""
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    ticks = "`" * max(3, longest + 1)
    return f"{ticks}{lang}\n{text.rstrip()}\n{ticks}"


def render_prompt(data: dict[str, Any], templates: dict[str, Any]) -> str:
    tasks = {t["id"]: t for t in templates["tasks"]}
    task = tasks.get(data.get("task_id", ""))
    if task is None:
        raise WizardError(f"Unknown task: {data.get('task_id')!r}")

    values: dict[str, str] = {k: str(v) for k, v in (data.get("values") or {}).items()}
    missing = [f["label"] for f in task["fields"]
               if f.get("required") and not values.get(f["name"], "").strip()]
    if missing:
        raise WizardError("Missing required fields: " + ", ".join(missing))

    # Code-type fields get fenced automatically so users can paste raw code.
    for field in task["fields"]:
        if field.get("type") == "code" and values.get(field["name"], "").strip():
            values[field["name"]] = fence(values[field["name"]], field.get("lang", ""))

    blocks = templates["blocks"]
    options = data.get("options") or {}
    parts: list[str] = []
    for key in ("primer", "language", "format"):
        block_id = options.get(key) or ""
        if block_id:
            block = blocks.get(block_id)
            if block is None or block["kind"] != key:
                raise WizardError(f"Unknown {key} block: {block_id!r}")
            parts.append(block["text"].strip())

    context = build_context(data.get("project") or {})
    if context:
        parts.append(context)

    parts.append(fill(task["template"], values))
    return "\n\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Project context (file bundling + tree)
# ---------------------------------------------------------------------------

def resolve_root(root: str) -> Path:
    if not root.strip():
        raise WizardError("Project root is empty.")
    path = Path(root.strip()).expanduser().resolve()
    if not path.is_dir():
        raise WizardError(f"Project root is not a directory: {path}")
    return path


def safe_join(root: Path, rel: str) -> Path:
    """Resolve rel inside root, refusing anything that escapes it."""
    candidate = (root / rel.strip().lstrip("/\\")).resolve()
    if candidate != root and root not in candidate.parents:
        raise WizardError(f"Path escapes project root: {rel}")
    return candidate


def project_tree(root: Path, max_entries: int = MAX_TREE_ENTRIES) -> str:
    lines = [root.name + "/"]
    count = 0

    def walk(directory: Path, prefix: str) -> None:
        nonlocal count
        try:
            entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except OSError:
            return
        entries = [e for e in entries if not (e.is_dir() and e.name in EXCLUDED_DIRS)]
        for i, entry in enumerate(entries):
            if count >= max_entries:
                if count == max_entries:
                    lines.append(prefix + "... (truncated)")
                    count += 1
                return
            last = i == len(entries) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{entry.name}{'/' if entry.is_dir() else ''}")
            count += 1
            if entry.is_dir():
                walk(entry, prefix + ("    " if last else "│   "))

    walk(root, "")
    return "\n".join(lines)


def project_files(root: Path, limit: int = 2000) -> list[str]:
    """Relative paths of files under root (POSIX style), skipping excluded directories."""
    found: list[str] = []
    stack = [root]
    while stack and len(found) < limit:
        directory = stack.pop()
        try:
            entries = sorted(directory.iterdir(), key=lambda p: p.name.lower(), reverse=True)
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name not in EXCLUDED_DIRS:
                    stack.append(entry)
            elif len(found) < limit:
                found.append(entry.relative_to(root).as_posix())
    return sorted(found, key=str.lower)


def read_project_file(root: Path, rel: str) -> str:
    path = safe_join(root, rel)
    if not path.is_file():
        raise WizardError(f"File not found: {rel}")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise WizardError(f"File too large (> {MAX_FILE_BYTES // 1000} kB): {rel}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as err:
        raise WizardError(f"Not a UTF-8 text file: {rel}") from err


def build_context(project: dict[str, Any]) -> str:
    files = [f.strip() for f in project.get("files", []) if f.strip()]
    include_tree = bool(project.get("include_tree"))
    if not files and not include_tree:
        return ""

    root = resolve_root(str(project.get("root", "")))
    sections: list[str] = []
    if include_tree:
        sections.append("PROJECT LAYOUT\n" + fence(project_tree(root)))
    for rel in files:
        content = read_project_file(root, rel)
        lang = EXT_LANG.get(Path(rel).suffix.lower(), "")
        sections.append(f"FILE: {rel.replace(chr(92), '/')}\n" + fence(content, lang))
    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "PromptWizard/1.0"
    default_root = ""

    def log_message(self, fmt: str, *args: Any) -> None:  # route through logging
        logger.debug("%s - %s", self.address_string(), fmt % args)

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        self._send(status, json.dumps(payload).encode("utf-8"), CONTENT_TYPES[".json"])

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as err:
            raise WizardError("Request body is not valid JSON.") from err
        if not isinstance(data, dict):
            raise WizardError("Request body must be a JSON object.")
        return data

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/templates":
            payload = load_templates()
            payload["default_root"] = self.default_root
            self._json(payload)
            return
        self._serve_static(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            data = self._read_json()
            if path == "/api/render":
                prompt = render_prompt(data, load_templates())
                self._json({"prompt": prompt, "chars": len(prompt)})
            elif path == "/api/tree":
                root = resolve_root(str(data.get("root", "")))
                self._json({"root": str(root), "tree": project_tree(root),
                            "files": project_files(root)})
            else:
                self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except WizardError as err:
            self._json({"error": str(err)}, HTTPStatus.BAD_REQUEST)
        except Exception:
            logger.exception("Unhandled error on %s", path)
            self._json({"error": "Internal error, see server log."}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _serve_static(self, path: str) -> None:
        rel = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (STATIC_DIR / rel).resolve()
        if STATIC_DIR not in target.parents or not target.is_file():
            self._send(HTTPStatus.NOT_FOUND, b"Not found", "text/plain; charset=utf-8")
            return
        content_type = CONTENT_TYPES.get(target.suffix, "application/octet-stream")
        self._send(HTTPStatus.OK, target.read_bytes(), content_type)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prompt Wizard for Microsoft 365 Copilot")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--root", default="", help="default project root for file bundling")
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")
    Handler.default_root = args.root
    # Bind to localhost only: the server can read files from disk.
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}"
    logger.info("Prompt Wizard running at %s  (Ctrl+C to stop)", url)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
