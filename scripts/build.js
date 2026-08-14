// Minimal build step: copy the static frontend into dist/ so the app has a
// reproducible, deployable artifact. Kept dependency-free on purpose.
import { cp, rm, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(fileURLToPath(import.meta.url)) + "/..";
const dist = path.join(root, "dist");

await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });
await cp(path.join(root, "public"), path.join(dist, "public"), { recursive: true });
await cp(path.join(root, "src"), path.join(dist, "src"), { recursive: true });

console.log("Build complete -> dist/");
