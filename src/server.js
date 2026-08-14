import { createApp } from "./app.js";
import { reset } from "./store.js";

const PORT = Number(process.env.PORT) || 3000;
const HOST = process.env.HOST || "0.0.0.0";

// Seed a couple of example tasks so a fresh boot shows a populated board.
reset([
  { title: "Welcome to Mangedong", done: true },
  { title: "Add your first task", done: false },
]);

const app = createApp();

app.listen(PORT, HOST, () => {
  console.log(`Mangedong running at http://${HOST}:${PORT}`);
});
