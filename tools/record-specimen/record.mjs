// Records the specimen case frame by frame on a stepped clock, with no page UI.
//
//   node record.mjs probe                     scene facts + one still of the default view
//   node record.mjs still <t> [out.png]       one frame of the camera path at t seconds
//   node record.mjs frames <dir>              every frame of the path (FPS x DURATION)
//
// Env: STAGE / WALL pick the room (as ?stage= / ?wall=), URL overrides the page,
// PLAYWRIGHT points at a playwright module, CHROME_CHANNEL (default "chrome").
import { mkdir, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join, resolve } from "node:path";

const FPS = 30;
const DURATION = 20;
const SIZE = 1080;
const SCALE = 1.5;
const WARMUP = 45;

const PLAYWRIGHT = process.env.PLAYWRIGHT
  || join(homedir(), ".npm/_npx/9833c18b2d85bc59/node_modules/playwright/index.mjs");
const { chromium } = await import(PLAYWRIGHT);

const [mode = "probe", arg, out] = process.argv.slice(2);

const params = new URLSearchParams({ quality: "detail", tune: "0" });
if (process.env.STAGE) params.set("stage", process.env.STAGE);
if (process.env.WALL) params.set("wall", process.env.WALL);
const url = process.env.URL || `http://127.0.0.1:8080/scenes/specimen/?${params}`;

// Runs in the page before any of its scripts. Until __rec.manual() the page keeps real time;
// after it, time only moves when __rec.step() is called, one draw per step.
function steppedClock() {
  const realNow = performance.now.bind(performance);
  const realRaf = window.requestAnimationFrame.bind(window);
  let manual = false;
  let now = 0;
  let queue = [];
  performance.now = () => (manual ? now : realNow());
  window.requestAnimationFrame = (fn) => {
    if (manual) { queue.push(fn); return 0; }
    return realRaf((t) => fn(manual ? now : t));
  };
  window.cancelAnimationFrame = () => {};
  const waitForQueue = async () => {
    for (let i = 0; i < 400 && !queue.length; i++) await new Promise((r) => setTimeout(r, 2));
  };
  window.__rec = {
    manual() { now = realNow(); manual = true; },
    async step(ms) {
      now += ms;
      await waitForQueue();
      const run = queue;
      queue = [];
      for (const fn of run) fn(now);
    },
  };
}

const HIDE_UI = `
  body > main > :not(canvas), #tune, #tune-open { display: none !important; }
  canvas { cursor: none !important; outline: none !important; }
`;

// Keyframes of the one-take path, as offsets from the default view: yaw from the room's
// facing (radians, clamped to the orbit's range), distance, height of the camera above the
// look-at point, and the look-at point blended from the jar centre (0) to the squid (1).
// The last key repeats the first so the clip loops. The jar's label faces yaw -0.55, so the
// path stays on the other side. Every key keeps the whole jar in frame, aimed at its middle.
const KEYS = [
  { t: 0.0, yaw: 0.5, dist: 11.5, rise: 0.6, aim: 0, lift: 0.3 },
  { t: 5.0, yaw: 0.28, dist: 10.5, rise: -0.4, aim: 0, lift: 0.3 },
  { t: 10.0, yaw: 0.05, dist: 11.0, rise: 1.2, aim: 0, lift: 0.3 },
  { t: 15.0, yaw: 0.35, dist: 12.5, rise: 3.0, aim: 0, lift: 0.3 },
  { t: 20.0, yaw: 0.5, dist: 11.5, rise: 0.6, aim: 0, lift: 0.3 },
];
const MAX_YAW = 0.66;

// Periodic Catmull-Rom over the keys, eased within each span so the camera never jerks.
function pathAt(time) {
  const n = KEYS.length - 1;
  const t = ((time % DURATION) + DURATION) % DURATION;
  let i = 0;
  while (i < n - 1 && t >= KEYS[i + 1].t) i++;
  const k = (j) => KEYS[((j % n) + n) % n];
  const p0 = k(i - 1), p1 = KEYS[i], p2 = KEYS[i + 1], p3 = k(i + 2);
  const raw = (t - p1.t) / (p2.t - p1.t);
  const u = raw * raw * (3 - 2 * raw) * 0.35 + raw * 0.65;
  const cr = (a, b, c, d) =>
    0.5 * (2 * b + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (-a + 3 * b - 3 * c + d) * u * u * u);
  const pick = (key) => cr(p0[key], p1[key], p2[key], p3[key]);
  return {
    yaw: Math.max(-MAX_YAW, Math.min(MAX_YAW, pick("yaw"))),
    dist: pick("dist"),
    rise: pick("rise"),
    aim: pick("aim"),
    lift: pick("lift"),
  };
}

// Runs in the page: places the camera for one pose of the path.
function placeCamera(pose) {
  const { camera, jar, specimen } = window.specimenDebug;
  const THREE_V = camera.position.constructor;
  const centre = jar.liquidBounds.getCenter(new THREE_V());
  const squid = specimen.object.getWorldPosition(new THREE_V());
  const target = centre.clone().lerp(squid, pose.aim);
  target.y += pose.lift;
  const roomYaw = window.__roomYaw;
  const yaw = roomYaw + pose.yaw;
  camera.position.set(
    target.x + Math.sin(yaw) * pose.dist,
    target.y + pose.rise,
    target.z + Math.cos(yaw) * pose.dist,
  );
  camera.lookAt(target);
  camera.updateMatrixWorld();
}

async function open() {
  const browser = await chromium.launch({
    channel: process.env.CHROME_CHANNEL || "chrome",
    headless: process.env.HEADED !== "1",
    args: ["--use-angle=metal", "--enable-gpu", "--ignore-gpu-blocklist", "--hide-scrollbars"],
  });
  const page = await browser.newPage({ viewport: { width: SIZE, height: SIZE }, deviceScaleFactor: SCALE });
  page.on("pageerror", (e) => console.error("pageerror:", e.message));
  await page.addInitScript(steppedClock);
  await page.goto(url, { waitUntil: "load" });
  await page.addStyleTag({ content: HIDE_UI });
  await page.waitForFunction(() => window.specimenDebug && document.querySelector("#loading")?.hidden, null, { timeout: 120000 });
  await page.evaluate(() => {
    const p = window.specimenDebug.camera.position;
    // DEFAULT_VIEW target is (0, 1.4, 0); the room faces the default camera.
    window.__roomYaw = Math.atan2(p.x, p.z);
    document.activeElement?.blur();
  });
  await page.evaluate(() => window.__rec.manual());
  return { browser, page };
}

async function settle(page, pose) {
  for (let i = 0; i < WARMUP; i++) {
    await page.evaluate(placeCamera, pose);
    await page.evaluate((ms) => window.__rec.step(ms), 1000 / FPS);
  }
}

async function frameAt(page, time) {
  await page.evaluate(placeCamera, pathAt(time));
  await page.evaluate((ms) => window.__rec.step(ms), 1000 / FPS);
  return page.screenshot({ type: "png", animations: "allow", caret: "initial" });
}

const { browser, page } = await open();
try {
  if (mode === "probe") {
    const info = await page.evaluate(() => {
      const { renderer, camera, jar, specimen } = window.specimenDebug;
      const gl = renderer.getContext();
      const ext = gl.getExtension("WEBGL_debug_renderer_info");
      const V = camera.position.constructor;
      return {
        gpu: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
        drawingBuffer: [gl.drawingBufferWidth, gl.drawingBufferHeight],
        camera: camera.position.toArray(),
        roomYaw: window.__roomYaw,
        liquid: [jar.liquidBounds.min.toArray(), jar.liquidBounds.max.toArray()],
        jar: [jar.bounds.min.toArray(), jar.bounds.max.toArray()],
        squid: specimen.object.getWorldPosition(new V()).toArray(),
      };
    });
    console.log(JSON.stringify(info, null, 2));
    for (let i = 0; i < WARMUP; i++) await page.evaluate((ms) => window.__rec.step(ms), 1000 / FPS);
    await writeFile(resolve(out || arg || "probe.png"), await page.screenshot({ type: "png" }));
  } else if (mode === "still") {
    const t = Number(arg || 0);
    await settle(page, pathAt(t));
    await writeFile(resolve(out || `still-${t}.png`), await frameAt(page, t));
  } else if (mode === "frames") {
    const dir = resolve(arg || "/tmp/specimen-frames");
    await mkdir(dir, { recursive: true });
    await settle(page, pathAt(0));
    const total = FPS * DURATION;
    // ONLY="6,271" replays the whole clip but rewrites just those frames.
    const only = process.env.ONLY ? new Set(process.env.ONLY.split(",").map(Number)) : null;
    const started = Date.now();
    for (let f = 0; f < total; f++) {
      if (only && !only.has(f)) {
        await page.evaluate(placeCamera, pathAt(f / FPS));
        await page.evaluate((ms) => window.__rec.step(ms), 1000 / FPS);
        continue;
      }
      const png = await frameAt(page, f / FPS);
      await writeFile(join(dir, `f${String(f).padStart(4, "0")}.png`), png);
      if (f % 30 === 0) console.log(`frame ${f}/${total}  ${((Date.now() - started) / 1000).toFixed(0)}s`);
    }
    console.log(`done: ${total} frames in ${dir}`);
  } else {
    throw new Error(`unknown mode ${mode}`);
  }
} finally {
  await browser.close();
}
