// Takes stills of the real hammerhead page (水槽/scenes/specimen/hammerhead.html) from fixed views.
//
//   node shoot-hammerhead.mjs <out dir> [tag]     writes <tag>_top.png, <tag>_side.png, <tag>_display.png
//
// The page must be served first (cd 水槽 && npm start). The page has no motion, so no stepped clock:
// it waits for body[data-ready], lets a few frames draw, and takes the canvas only (no status text).
// Env: VIEWS (default "top,side,display"; "display" = the page with no ?view=), SIZE (default 1600x800,
// the 2:1 of docs/hammerhead_ct/a6_*.jpg), BASE (default http://127.0.0.1:8080), EXTRA (more query, e.g. "focus=head"),
// PLAYWRIGHT points at a playwright module, CHROME_CHANNEL (default "chrome").
import { mkdir, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join, resolve } from "node:path";

const PLAYWRIGHT = process.env.PLAYWRIGHT
  || join(homedir(), ".npm/_npx/9833c18b2d85bc59/node_modules/playwright/index.mjs");
const { chromium } = await import(PLAYWRIGHT);

const [outArg, tagArg] = process.argv.slice(2);
if (!outArg) throw new Error("usage: node shoot-hammerhead.mjs <out dir> [tag]");
const outDir = resolve(outArg);
const tag = tagArg || "hammerhead";
const views = (process.env.VIEWS || "top,side,display").split(",");
const [width, height] = (process.env.SIZE || "1600x800").split("x").map(Number);
const base = process.env.BASE || "http://127.0.0.1:8080";
const FRAMES = 8;

const browser = await chromium.launch({
  channel: process.env.CHROME_CHANNEL || "chrome",
  headless: process.env.HEADED !== "1",
  args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist", "--hide-scrollbars"],
});
try {
  await mkdir(outDir, { recursive: true });
  for (const view of views) {
    const query = new URLSearchParams(process.env.EXTRA || "");
    if (view !== "display") query.set("view", view);
    const url = `${base}/scenes/specimen/hammerhead.html${query.size ? `?${query}` : ""}`;
    const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(url, { waitUntil: "load" });
    await page.waitForFunction(() => document.body.dataset.ready === "1" || document.body.dataset.error === "1", null, { timeout: 120000 });
    if (await page.evaluate(() => document.body.dataset.error === "1")) {
      throw new Error(`${view}: ${await page.textContent("#status")} ${errors.join(" ")}`);
    }
    await page.evaluate((n) => new Promise((done) => {
      let left = n;
      const tick = () => (--left > 0 ? requestAnimationFrame(tick) : done());
      requestAnimationFrame(tick);
    }), FRAMES);
    const info = await page.evaluate(() => {
      const { renderer, camera } = window.hammerheadPage;
      const gl = renderer.getContext();
      const ext = gl.getExtension("WEBGL_debug_renderer_info");
      return {
        gpu: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
        status: document.querySelector("#status").textContent,
        camera: camera.position.toArray().map((v) => +v.toFixed(4)),
      };
    });
    await page.addStyleTag({ content: "#status { display: none !important; }" });
    await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
    const file = join(outDir, `${tag}_${view}.png`);
    await writeFile(file, await page.locator("#scene").screenshot({ type: "png" }));
    console.log(JSON.stringify({ view, url, file, ...info, errors }));
    await page.close();
  }
} finally {
  await browser.close();
}
