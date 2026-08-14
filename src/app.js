import express from "express";
import { fileURLToPath } from "node:url";
import path from "node:path";
import {
  listTasks,
  createTask,
  updateTask,
  deleteTask,
} from "./store.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(__dirname, "..", "public");

export function createApp() {
  const app = express();
  app.use(express.json());

  app.get("/api/health", (_req, res) => {
    res.json({ status: "ok", service: "mangedong" });
  });

  app.get("/api/tasks", (_req, res) => {
    res.json(listTasks());
  });

  app.post("/api/tasks", (req, res, next) => {
    try {
      const task = createTask(req.body ?? {});
      res.status(201).json(task);
    } catch (err) {
      next(err);
    }
  });

  app.patch("/api/tasks/:id", (req, res, next) => {
    try {
      const task = updateTask(Number(req.params.id), req.body ?? {});
      res.json(task);
    } catch (err) {
      next(err);
    }
  });

  app.delete("/api/tasks/:id", (req, res, next) => {
    try {
      deleteTask(Number(req.params.id));
      res.status(204).end();
    } catch (err) {
      next(err);
    }
  });

  app.use(express.static(publicDir));

  app.use((err, _req, res, _next) => {
    res.status(err.status ?? 500).json({ error: err.message ?? "internal error" });
  });

  return app;
}
