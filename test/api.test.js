import test from "node:test";
import assert from "node:assert/strict";
import { createApp } from "../src/app.js";
import { reset } from "../src/store.js";

async function startServer() {
  reset();
  const app = createApp();
  const server = app.listen(0);
  await new Promise((resolve) => server.once("listening", resolve));
  const { port } = server.address();
  const base = `http://127.0.0.1:${port}`;
  return { server, base };
}

test("health endpoint reports ok", async () => {
  const { server, base } = await startServer();
  try {
    const res = await fetch(`${base}/api/health`);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { status: "ok", service: "mangedong" });
  } finally {
    server.close();
  }
});

test("tasks start empty", async () => {
  const { server, base } = await startServer();
  try {
    const res = await fetch(`${base}/api/tasks`);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), []);
  } finally {
    server.close();
  }
});

test("create, toggle, and delete a task end to end", async () => {
  const { server, base } = await startServer();
  try {
    const createRes = await fetch(`${base}/api/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "Write tests" }),
    });
    assert.equal(createRes.status, 201);
    const created = await createRes.json();
    assert.equal(created.title, "Write tests");
    assert.equal(created.done, false);
    assert.ok(created.id);

    const patchRes = await fetch(`${base}/api/tasks/${created.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ done: true }),
    });
    assert.equal(patchRes.status, 200);
    assert.equal((await patchRes.json()).done, true);

    const listRes = await fetch(`${base}/api/tasks`);
    assert.equal((await listRes.json()).length, 1);

    const delRes = await fetch(`${base}/api/tasks/${created.id}`, {
      method: "DELETE",
    });
    assert.equal(delRes.status, 204);

    const finalRes = await fetch(`${base}/api/tasks`);
    assert.deepEqual(await finalRes.json(), []);
  } finally {
    server.close();
  }
});

test("rejects a task without a title", async () => {
  const { server, base } = await startServer();
  try {
    const res = await fetch(`${base}/api/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "   " }),
    });
    assert.equal(res.status, 400);
    assert.equal((await res.json()).error, "title is required");
  } finally {
    server.close();
  }
});

test("returns 404 when updating a missing task", async () => {
  const { server, base } = await startServer();
  try {
    const res = await fetch(`${base}/api/tasks/999`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ done: true }),
    });
    assert.equal(res.status, 404);
  } finally {
    server.close();
  }
});
