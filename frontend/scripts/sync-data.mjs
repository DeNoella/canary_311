// Copies the pipeline's outputs/ JSON into frontend/public/data/ so the site can
// be served as a fully static bundle (no backend). Runs before dev and build.
// On a machine with no ../outputs (e.g. Vercel), the committed public/data/ is
// used as-is.
import { existsSync, cpSync, mkdirSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../outputs");
const dest = resolve(here, "../public/data");

if (existsSync(src) && readdirSync(src).some((f) => f.endsWith(".json"))) {
  mkdirSync(dest, { recursive: true });
  cpSync(src, dest, { recursive: true });
  console.log("[sync-data] copied outputs/ -> public/data/");
} else if (existsSync(dest)) {
  console.log("[sync-data] no ../outputs; using committed public/data/");
} else {
  console.warn(
    "[sync-data] WARNING: no ../outputs and no public/data/ — the site will have no data.\n" +
      "            Run the pipeline (uv run canary) or commit a public/data/ snapshot.",
  );
}
