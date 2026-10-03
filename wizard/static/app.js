"use strict";

// Prompt Wizard frontend. Rendering happens on the Python backend (/api/render);
// this file only builds the form, remembers drafts, and talks to the API.

const SIZE_WARNING_CHARS = 15000; // roughly where M365 Copilot starts to truncate/reject; varies by tenant
const STORE_KEY = "promptWizard.v1";

const $ = (sel) => document.querySelector(sel);

const state = {
  data: null,       // { blocks, tasks, default_root }
  task: null,       // currently selected task
  store: loadStore(),
};

// ---------------------------------------------------------------------------
// Persistence (per-browser convenience only; failures are ignored)
// ---------------------------------------------------------------------------

function loadStore() {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY)) || {};
  } catch {
    return {};
  }
}

function saveStore() {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(state.store));
  } catch {
    /* storage unavailable: nothing to do */
  }
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

async function api(path, body) {
  const res = await fetch(path, body === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
  if (!res.ok) throw new Error(payload.error || `HTTP ${res.status}`);
  return payload;
}

function setStatus(message, isError = false) {
  const el = $("#status");
  el.textContent = message;
  el.classList.toggle("error", isError);
}

// ---------------------------------------------------------------------------
// Top-bar block selectors
// ---------------------------------------------------------------------------

function fillBlockSelects() {
  const defaults = { primer: "primer_full", language: "", format: "" };
  for (const select of document.querySelectorAll("select[data-kind]")) {
    const kind = select.dataset.kind;
    select.append(new Option("— none —", ""));
    for (const [id, block] of Object.entries(state.data.blocks)) {
      if (block.kind === kind) select.append(new Option(block.label, id));
    }
    const saved = state.store.options?.[kind];
    select.value = saved !== undefined && [...select.options].some((o) => o.value === saved)
      ? saved
      : defaults[kind];
    select.addEventListener("change", () => {
      state.store.options = { ...state.store.options, [kind]: select.value };
      saveStore();
    });
  }
}

// ---------------------------------------------------------------------------
// Task list
// ---------------------------------------------------------------------------

function renderTaskList(filter = "") {
  const list = $("#task-list");
  list.replaceChildren();
  const needle = filter.trim().toLowerCase();
  let currentCategory = null;

  for (const task of state.data.tasks) {
    const haystack = `${task.title} ${task.description} ${task.category}`.toLowerCase();
    if (needle && !haystack.includes(needle)) continue;
    if (task.category !== currentCategory) {
      currentCategory = task.category;
      const heading = document.createElement("div");
      heading.className = "category";
      heading.textContent = currentCategory;
      list.append(heading);
    }
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "task-btn";
    btn.textContent = task.title;
    btn.title = task.description;
    btn.dataset.id = task.id;
    btn.classList.toggle("active", state.task?.id === task.id);
    btn.addEventListener("click", () => selectTask(task.id));
    list.append(btn);
  }
}

function selectTask(id) {
  const task = state.data.tasks.find((t) => t.id === id);
  if (!task) return;
  state.task = task;
  state.store.lastTask = id;
  saveStore();

  for (const btn of document.querySelectorAll(".task-btn")) {
    btn.classList.toggle("active", btn.dataset.id === id);
  }
  $("#task-title").textContent = task.title;
  $("#task-desc").textContent = task.description;
  renderForm(task);
  setStatus("");
}

// ---------------------------------------------------------------------------
// Dynamic form
// ---------------------------------------------------------------------------

function draftFor(taskId) {
  state.store.drafts ??= {};
  state.store.drafts[taskId] ??= {};
  return state.store.drafts[taskId];
}

function renderForm(task) {
  const form = $("#task-form");
  form.replaceChildren();
  const draft = draftFor(task.id);

  if (task.fields.length === 0) {
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "No fields: just generate and paste.";
    form.append(p);
  }

  for (const field of task.fields) {
    const label = document.createElement("label");
    label.textContent = field.label;
    if (field.required) {
      const star = document.createElement("span");
      star.className = "req";
      star.textContent = "*";
      label.append(star);
    }

    let input;
    if (field.type === "select") {
      input = document.createElement("select");
      if (!field.required) input.append(new Option("—", ""));
      for (const opt of field.options) input.append(new Option(opt, opt));
    } else if (field.type === "textarea" || field.type === "code") {
      input = document.createElement("textarea");
      input.rows = field.type === "code" ? 8 : 3;
      if (field.type === "code") {
        input.classList.add("code");
        input.spellcheck = false;
      }
    } else {
      input = document.createElement("input");
      input.type = "text";
    }
    input.name = field.name;
    if (field.placeholder) input.placeholder = field.placeholder;
    if (draft[field.name] !== undefined) input.value = draft[field.name];
    input.addEventListener("input", () => {
      draft[field.name] = input.value;
      saveStore();
    });

    label.append(input);
    form.append(label);
  }
}

function collectValues() {
  const values = {};
  for (const el of $("#task-form").elements) {
    if (el.name) values[el.name] = el.value;
  }
  return values;
}

// ---------------------------------------------------------------------------
// Project context
// ---------------------------------------------------------------------------

function selectedFiles() {
  return $("#project-files").value.split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
}

function setSelectedFiles(files) {
  $("#project-files").value = files.join("\n");
  persistProject();
}

function persistProject() {
  state.store.project = {
    root: $("#project-root").value,
    files: $("#project-files").value,
    includeTree: $("#include-tree").checked,
  };
  saveStore();
  updateProjectBadge();
}

function updateProjectBadge() {
  const n = selectedFiles().length;
  const parts = [];
  if (n) parts.push(`${n} file${n === 1 ? "" : "s"}`);
  if ($("#include-tree").checked) parts.push("tree");
  $("#project-badge").textContent = parts.join(" + ");
}

let scannedFiles = [];

function renderFileList() {
  const list = $("#file-list");
  list.replaceChildren();
  const needle = $("#file-filter").value.trim().toLowerCase();
  const chosen = new Set(selectedFiles());
  const shown = scannedFiles.filter((f) => !needle || f.toLowerCase().includes(needle)).slice(0, 500);

  for (const file of shown) {
    const label = document.createElement("label");
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = chosen.has(file);
    box.addEventListener("change", () => {
      const current = selectedFiles().filter((f) => f !== file);
      if (box.checked) current.push(file);
      setSelectedFiles(current);
    });
    label.append(box, document.createTextNode(file));
    list.append(label);
  }
  if (shown.length === 0) {
    list.textContent = "No matching files.";
  }
}

async function scanProject() {
  setStatus("Scanning…");
  try {
    const result = await api("/api/tree", { root: $("#project-root").value });
    scannedFiles = result.files;
    $("#file-picker").hidden = false;
    renderFileList();
    persistProject();
    setStatus(`Found ${result.files.length} files.`);
  } catch (err) {
    setStatus(err.message, true);
  }
}

// ---------------------------------------------------------------------------
// Generate / copy
// ---------------------------------------------------------------------------

async function generate() {
  if (!state.task) {
    setStatus("Pick a task first.", true);
    return;
  }
  setStatus("Generating…");
  try {
    const result = await api("/api/render", {
      task_id: state.task.id,
      values: collectValues(),
      options: {
        primer: $("#opt-primer").value,
        language: $("#opt-language").value,
        format: $("#opt-format").value,
      },
      project: {
        root: $("#project-root").value,
        files: selectedFiles(),
        include_tree: $("#include-tree").checked,
      },
    });
    $("#output-card").hidden = false;
    $("#output").value = result.prompt;
    updateCharCount();
    $("#output-card").scrollIntoView({ behavior: "smooth", block: "start" });
    setStatus("");
  } catch (err) {
    setStatus(err.message, true);
  }
}

function updateCharCount() {
  const chars = $("#output").value.length;
  const badge = $("#char-count");
  badge.textContent = `${chars.toLocaleString()} chars`;
  const tooLong = chars > SIZE_WARNING_CHARS;
  badge.classList.toggle("warn", tooLong);
  $("#size-warning").hidden = !tooLong;
}

async function copyOutput() {
  const text = $("#output").value;
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    // Fallback for browsers that block the async clipboard API.
    $("#output").select();
    document.execCommand("copy");
  }
  setStatus("Copied to clipboard. Paste it into Copilot.");
}

function resetFields() {
  if (!state.task) return;
  state.store.drafts[state.task.id] = {};
  saveStore();
  renderForm(state.task);
  setStatus("Fields cleared.");
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

async function init() {
  try {
    state.data = await api("/api/templates");
  } catch (err) {
    setStatus(`Could not load templates: ${err.message}`, true);
    return;
  }

  fillBlockSelects();
  renderTaskList();

  const project = state.store.project || {};
  $("#project-root").value = project.root || state.data.default_root || "";
  $("#project-files").value = project.files || "";
  $("#include-tree").checked = Boolean(project.includeTree);
  updateProjectBadge();

  $("#task-search").addEventListener("input", (e) => renderTaskList(e.target.value));
  $("#btn-scan").addEventListener("click", scanProject);
  $("#project-root").addEventListener("keydown", (e) => {
    if (e.key === "Enter") scanProject();
  });
  $("#project-root").addEventListener("change", persistProject);
  $("#project-files").addEventListener("input", () => {
    persistProject();
    if (scannedFiles.length) renderFileList();
  });
  $("#include-tree").addEventListener("change", persistProject);
  $("#file-filter").addEventListener("input", renderFileList);
  $("#btn-generate").addEventListener("click", generate);
  $("#btn-reset").addEventListener("click", resetFields);
  $("#btn-copy").addEventListener("click", copyOutput);
  $("#output").addEventListener("input", updateCharCount);
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") generate();
  });

  const last = state.store.lastTask;
  selectTask(state.data.tasks.some((t) => t.id === last) ? last : state.data.tasks[0].id);
}

init();
