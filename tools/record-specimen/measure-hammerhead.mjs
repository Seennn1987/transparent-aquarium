// Reads what the hammerhead page draws, for measuring its colours: the light let through (the canvas) and each
// path channel (window.hammerheadPage.paths(): r bone+teeth, g cartilage+jaw+gill, b skin, a head cartilage; metres),
// at the same pixels (?ss=1 so the path buffer is the canvas's size).
//
//   node measure-hammerhead.mjs <out dir> [view]     writes <view>_rgb.png, <view>_paths.f32 (H × W × 4, top row first),
//                                                     <view>_part_<P>.f32 (that part's own path, H × W) for PARTS, <view>.json
// Env: SIZE (default 1000x500, as A6), BASE, EXTRA (more query), PARTS (default "Gill,Jaw,Teeth,Cartilage"): for each, the path
// with only that part drawn (the summed channel of its tissue), PLAYWRIGHT, CHROME_CHANNEL.
// blender/ct_hammerhead/measure_colors.py classifies the pixels (A6's classes) and gives the medians.
import { mkdir, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join, resolve } from "node:path";

const PLAYWRIGHT = process.env.PLAYWRIGHT
  || join(homedir(), ".npm/_npx/9833c18b2d85bc59/node_modules/playwright/index.mjs");
const { chromium } = await import(PLAYWRIGHT);
const [outArg, view = "top"] = process.argv.slice(2);
if (!outArg) throw new Error("usage: node measure-hammerhead.mjs <out dir> [view]");
const out = resolve(outArg);
const [width, height] = (process.env.SIZE || "1000x500").split("x").map(Number);
const base = process.env.BASE || "http://127.0.0.1:8080";
const parts = (process.env.PARTS ?? "Gill,Jaw,Teeth,Cartilage").split(",").filter(Boolean);

const browser = await chromium.launch({
  channel: process.env.CHROME_CHANNEL || "chrome",
  args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist", "--hide-scrollbars"],
});
try {
  await mkdir(out, { recursive: true });
  const query = new URLSearchParams(process.env.EXTRA || ""); query.set("ss", "1");
  if (view !== "display") query.set("view", view);
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  page.on("pageerror", (e) => console.error("pageerror:", e.message));
  await page.goto(`${base}/scenes/specimen/hammerhead.html?${query}`, { waitUntil: "load" });
  await page.waitForFunction(() => document.body.dataset.ready === "1");
  await page.addStyleTag({ content: "#status { display: none !important; }" });
  const frames = (n) => page.evaluate((n) => new Promise((done) => { let k = n; const t = () => (--k > 0 ? requestAnimationFrame(t) : done()); requestAnimationFrame(t); }), n);
  // The path buffer as base64 of a Float32Array, flipped so the top row comes first (as the canvas).
  const readPaths = () => page.evaluate(() => {
    const { width: w, height: h, data } = window.hammerheadPage.paths();
    const flip = new Float32Array(w * h * 4);
    for (let y = 0; y < h; y++) flip.set(data.subarray((h - 1 - y) * w * 4, (h - y) * w * 4), y * w * 4);
    const u8 = new Uint8Array(flip.buffer); let s = "";
    for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode(...u8.subarray(i, i + 0x8000));
    return { w, h, b64: btoa(s) };
  });
  await frames(6);
  await writeFile(join(out, `${view}_rgb.png`), await page.locator("#scene").screenshot({ type: "png" }));
  const all = await readPaths();
  if (all.w !== width || all.h !== height) throw new Error(`path buffer ${all.w}×${all.h} is not the canvas ${width}×${height}`);
  await writeFile(join(out, `${view}_paths.f32`), Buffer.from(all.b64, "base64"));
  const CH = { Bone: 0, Teeth: 0, Cartilage: 1, Jaw: 1, Gill: 1, Skin: 2, HeadCartilage: 3 };
  for (const p of parts) {
    // The part's channel weights (a mixed-colour part writes weight × path into several channels)
    const wsum = await page.evaluate((p) => { let s = 1; window.hammerheadPage.model.traverse((o) => {
      if (!o.isMesh) return; o.visible = o.userData.hh_part === p;
      if (o.visible) { const c = o.material.uniforms.channel.value; s = c.x + c.y + c.z + c.w;
        // 内臓のように通り道に何も書かない部品は、形を測る間だけ骨の通り道に書く（2026-10-15）
        if (s === 0) { o.userData.savedChannel = c.clone(); c.set(1, 0, 0, 0); s = 1; } } }); return s; }, p);
    await frames(4);
    const one = await readPaths();
    // The part's own path: the sum of the channels divided by the sum of its weights
    const f = new Float32Array(Buffer.from(one.b64, "base64").buffer.slice(0)); const m = new Float32Array(width * height);
    for (let i = 0; i < m.length; i++) m[i] = (Math.max(0, f[4 * i]) + Math.max(0, f[4 * i + 1]) + Math.max(0, f[4 * i + 2]) + Math.max(0, f[4 * i + 3])) / wsum;
    await writeFile(join(out, `${view}_part_${p}.f32`), Buffer.from(m.buffer));
  }
  await page.evaluate(() => window.hammerheadPage.model.traverse((o) => {
    if (!o.isMesh) return; o.visible = true;
    if (o.userData.savedChannel) { o.material.uniforms.channel.value.copy(o.userData.savedChannel); delete o.userData.savedChannel; } }));
  const info = await page.evaluate(() => {
    const weights = {};   // each part's channel weights (bone, cartilage, skin, head)
    window.hammerheadPage.model.traverse((o) => { if (o.isMesh) { const c = o.material.uniforms.channel.value; weights[o.userData.hh_part] = [c.x, c.y, c.z, c.w]; } });
    return { status: document.querySelector("#status").textContent, weights };
  });
  await writeFile(join(out, `${view}.json`), JSON.stringify({ view, width, height, parts, channels: CH, ...info }));
  console.log(JSON.stringify({ view, width, height, parts, ...info }));
} finally {
  await browser.close();
}
