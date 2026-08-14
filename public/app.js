const listEl = document.getElementById("task-list");
const formEl = document.getElementById("task-form");
const inputEl = document.getElementById("task-input");
const emptyEl = document.getElementById("empty-state");
const countTotalEl = document.getElementById("count-total");
const countDoneEl = document.getElementById("count-done");

async function api(path, options) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok && res.status !== 204) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed: ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}

function render(tasks) {
  listEl.innerHTML = "";
  emptyEl.hidden = tasks.length > 0;

  const doneCount = tasks.filter((task) => task.done).length;
  countTotalEl.textContent = `${tasks.length} task${tasks.length === 1 ? "" : "s"}`;
  countDoneEl.textContent = `${doneCount} done`;

  for (const task of tasks) {
    const li = document.createElement("li");
    li.className = `task-item${task.done ? " done" : ""}`;
    li.dataset.id = task.id;

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "task-checkbox";
    checkbox.checked = task.done;
    checkbox.addEventListener("change", () => toggle(task, checkbox.checked));

    const title = document.createElement("span");
    title.className = "task-title";
    title.textContent = task.title;

    const del = document.createElement("button");
    del.className = "task-delete";
    del.setAttribute("aria-label", `Delete ${task.title}`);
    del.textContent = "\u00d7";
    del.addEventListener("click", () => remove(task));

    li.append(checkbox, title, del);
    listEl.append(li);
  }
}

async function load() {
  render(await api("/api/tasks"));
}

async function toggle(task, done) {
  await api(`/api/tasks/${task.id}`, {
    method: "PATCH",
    body: JSON.stringify({ done }),
  });
  await load();
}

async function remove(task) {
  await api(`/api/tasks/${task.id}`, { method: "DELETE" });
  await load();
}

formEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const title = inputEl.value.trim();
  if (!title) return;
  await api("/api/tasks", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
  inputEl.value = "";
  inputEl.focus();
  await load();
});

load().catch((err) => {
  emptyEl.hidden = false;
  emptyEl.textContent = `Failed to load tasks: ${err.message}`;
});
