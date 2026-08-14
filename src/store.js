// Simple in-memory task store. Kept dependency-free so it is trivial to test.
let tasks = [];
let nextId = 1;

export function reset(seed = []) {
  tasks = [];
  nextId = 1;
  for (const item of seed) {
    createTask(item);
  }
}

export function listTasks() {
  return tasks.map((task) => ({ ...task }));
}

export function createTask({ title, done = false }) {
  const trimmed = typeof title === "string" ? title.trim() : "";
  if (!trimmed) {
    const error = new Error("title is required");
    error.status = 400;
    throw error;
  }
  const task = { id: nextId++, title: trimmed, done: Boolean(done) };
  tasks.push(task);
  return { ...task };
}

export function updateTask(id, patch) {
  const task = tasks.find((item) => item.id === id);
  if (!task) {
    const error = new Error("task not found");
    error.status = 404;
    throw error;
  }
  if (typeof patch.title === "string") {
    const trimmed = patch.title.trim();
    if (!trimmed) {
      const error = new Error("title cannot be empty");
      error.status = 400;
      throw error;
    }
    task.title = trimmed;
  }
  if (typeof patch.done === "boolean") {
    task.done = patch.done;
  }
  return { ...task };
}

export function deleteTask(id) {
  const index = tasks.findIndex((item) => item.id === id);
  if (index === -1) {
    const error = new Error("task not found");
    error.status = 404;
    throw error;
  }
  const [removed] = tasks.splice(index, 1);
  return { ...removed };
}
