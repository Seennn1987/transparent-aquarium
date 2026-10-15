import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { createOrbit } from "./orbit.js";
import { createLightbox, chameleonLook } from "./chameleon-material.js";
import { HH_BONE_T0 } from "./hammerhead-stain.js";   // registers STAINS.hammerhead
import { applyHammerheadTissue } from "./hammerhead-material.js";
import { createSwim, swimLook, mouthLook, heartLook, gillLook } from "./hammerhead-swim.js";

// The smooth hammerhead as a cleared-and-stained specimen on a lightbox, without its dish (A6).
// The mesh: blender/ct_hammerhead (CT of ZMA.PISC.108725, Kamminga et al. 2017, CC0).
// ?glb=<名前>: assets/<名前>.glb を読む（案の glb を見比べるとき。英数字と _ だけ）
const GLB_NAME = /^[A-Za-z0-9_]+$/.test(new URLSearchParams(location.search).get("glb") ?? "") ? new URLSearchParams(location.search).get("glb") : "specimen_hammerhead";
const URL_GLB = new URL(`../assets/${GLB_NAME}.glb`, import.meta.url).href;
const canvas = document.querySelector("#scene");
const status = document.querySelector("#status");
const query = new URLSearchParams(location.search);

async function start() {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, preserveDrawingBuffer: true });
  if (!renderer.capabilities.isWebGL2) throw new Error("WebGL2 が使えないため表示できません");
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  chameleonLook.boneT0.value = HH_BONE_T0;
  // A8 皮歯の強さ（膜の層の通り道。hammerhead-material.js の denticleMaterial）。既定 1（2026-10-15 プロデューサー決定）。?dent=0 で皮歯なし
  chameleonLook.film.value = Number(query.get("dent") ?? 1);
  // A8 内臓の通り道（まだら・鰓条）。強さはそれぞれの式の中（hammerhead-material.js の mottleLook・gillRayLook）にあるので、ここは 1
  chameleonLook.organs.value = 1;
  const ss = Number(query.get("ss")) || 2;
  const lightbox = createLightbox(renderer, { stain: "hammerhead", supersample: ss });
  document.body.style.background = "rgb(253,247,251)";

  const gltf = await new GLTFLoader().loadAsync(URL_GLB);
  const model = gltf.scene;
  const reference = { value: 0 };
  applyHammerheadTissue(model, reference);
  const scene = new THREE.Scene();
  scene.add(model);
  scene.updateMatrixWorld(true);

  // glTF: +Y is the back; x runs snout → tail (Blender x), so the head is at −x... the snout at the smaller x.
  const box = new THREE.Box3().setFromObject(model, true);
  const centre = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const radius = size.length() / 2;
  const camera = new THREE.PerspectiveCamera(20, 1, radius * 0.1, radius * 20);
  // view=top: from above, the head to the left (as Eames et al. 2007 Fig. 2A, dorsal). view=side: from the side.
  // Default: from above and in front at the side, as on the display table.
  const view = query.get("view") ?? "display";
  const fit = (w) => w / 2 / Math.tan(THREE.MathUtils.degToRad(10));
  let dir;
  if (view === "top") dir = new THREE.Vector3(0, 1, 0.0001);
  else if (view === "side") dir = new THREE.Vector3(0, 0.0001, 1);
  else if (view === "below") dir = new THREE.Vector3(0, -1, 0.0001);
  else if (view === "front") dir = new THREE.Vector3(-1, 0.15, 0.25).normalize();
  else dir = new THREE.Vector3(-0.35, 0.55, 0.85).normalize();
  // 横長の体を画面の幅に収める（縦長の画面では、横の画角が縦より狭い）
  // 描く枠の大きさが 0 のうち（見えない欄やタブで読み込んだとき）は待つ。0 のまま視点を決めると、距離が NaN になって何も描かれなかった（2026-10-15）
  await canvasShown(canvas);
  const aspect0 = canvas.clientWidth / canvas.clientHeight;
  // focus=head: 頭（吻端から 0.3 m）を画面いっぱいに（顎・歯・エラの骨を見る）
  const focusHead = query.get("focus") === "head";
  if (focusHead) centre.set(box.min.x + 0.13, centre.y, centre.z);
  const distance = fit(focusHead ? 0.3 : size.x) / (focusHead ? Math.min(aspect0, 1) : aspect0) * 1.1;
  camera.position.copy(centre).addScaledVector(dir, distance);
  if (view === "top" || view === "below") camera.up.set(0, 0, -1);
  camera.lookAt(centre);
  // B3 うねり（hammerhead-swim.js）。骨組みの無い glb では null。枠と視点は休みの形で決めたあと
  const swim = createSwim(model);
  const orbit = createOrbit(camera, canvas, { target: centre.clone(), minDistance: distance * 0.15, maxDistance: distance * 2, minPolar: 0.02, maxPolar: Math.PI - 0.02 });

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    const s = renderer.getDrawingBufferSize(new THREE.Vector2());
    lightbox.setSize(s.x, s.y);
    camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  resize();
  addEventListener("resize", resize);
  new ResizeObserver(resize).observe(canvas);   // 窓の大きさが変わらずに枠だけが変わるとき（隠れていた欄が開いたときなど）
  const v = new THREE.Vector3();
  // B5 一時停止: スペースキーで止める・動かす（?still=1 で止めて始める）。止めている間は時計が進まず、うねり・口・心臓・エラが全部止まる
  let paused = query.get("still") === "1", last = performance.now();
  addEventListener("keydown", (e) => { if (e.code === "Space" && !e.target.closest?.("button")) { paused = !paused; e.preventDefault(); } });
  function frame() {
    const now = performance.now(), dt = paused ? 0 : Math.min((now - last) / 1000, 0.1); last = now;
    swim?.update(dt);
    v.copy(centre).applyMatrix4(camera.matrixWorldInverse);
    reference.value = -v.z;
    lightbox.render(scene, camera);
    requestAnimationFrame(frame);
  }
  if (view !== "top" && view !== "below") orbit.update();
  frame();
  status.textContent = `${lightbox.precision} · ${view}${swim && swimLook.on ? ` · ${swimLook.frequency} Hz` : ""}`;
  // ?pick=turnbend: 旋回で体を曲げる割合の案を、動かしたまま切り替えて見比べる（2026-10-15、プロデューサー「ブラウザで３つを切り替えてそれぞれの動作を確認できるようにして」）
  if (swim && query.get("pick") === "turnbend") turnBendPicker();
  if (swim && query.get("pick") === "mouth") mouthPicker();
  if (swim && query.get("pick") === "organs") organPicker();
  document.body.dataset.ready = "1";
  window.hammerheadPage = {
    look: chameleonLook, renderer, lightbox, camera, model, swim, swimLook,
    setPaused(v) { paused = Boolean(v); }, get paused() { return paused; },
    paths() {
      const t = lightbox.target; const out = new Float32Array(t.width * t.height * 4);
      renderer.readRenderTargetPixels(t, 0, 0, t.width, t.height, out);
      return { width: t.width, height: t.height, data: out };
    },
  };
}
function turnBendPicker() {
  if (!new URLSearchParams(location.search).has("turn")) swimLook.turn = 1;
  pickerPanel([
    ["体の曲げ", [["1", 1], ["0.5", 0.5], ["0.25", 0.25]], () => swimLook.turnBend, (v) => { swimLook.turnBend = v; }],
    ["向き", [["右へ旋回", 1], ["左へ旋回", -1], ["まっすぐ", 0]], () => swimLook.turn, (v) => { swimLook.turn = v; }],
  ], "1 = 体が通り道の円（半径は体長の 37%）に沿う（推定）。旋回では内側の胸びれを引く");
}
function pickerPanel(rows, noteText) {
  const box = document.createElement("div");
  box.style.cssText = "position:fixed;left:12px;top:12px;display:flex;flex-direction:column;gap:6px;font:14px/1.3 system-ui,sans-serif;color:#333;background:rgba(255,255,255,.85);padding:10px 12px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.15)";
  for (const [title, items, get, set] of rows) {
    const r = document.createElement("div"); r.style.cssText = "display:flex;align-items:center;gap:6px;flex-wrap:wrap";
    const t = document.createElement("span"); t.textContent = title; t.style.minWidth = "5.5em"; r.append(t);
    const buttons = items.map(([label, value]) => {
      const b = document.createElement("button"); b.type = "button"; b.textContent = label;
      b.style.cssText = "font:inherit;padding:4px 10px;border:1px solid #999;border-radius:6px;cursor:pointer";
      b.onclick = () => { set(value); paint(); };
      r.append(b); return [b, value];
    });
    const paint = () => { for (const [b, v] of buttons) { const on = get() === v; b.style.background = on ? "#333" : "#fff"; b.style.color = on ? "#fff" : "#333"; } };
    paint(); box.append(r);
  }
  const note = document.createElement("div"); note.style.cssText = "font-size:12px;color:#666;max-width:28em"; note.textContent = noteText;
  box.append(note); document.body.append(box);
}
// ?pick=organs: 心臓（推定）の案と拍動の回数、エラの動きの案を、動かしたまま切り替える（B5）。心臓の案は ?glb=specimen_hammerhead_heart
function organPicker() {
  pickerPanel([
    ["心臓", [["実物に近い大きさ", "large"], ["小さく骨に当てない", "small"], ["なし", "none"]], () => heartLook.show, (v) => { heartLook.show = v; }],
    ["拍動", [["毎分 37", 37], ["毎分 52", 52], ["止める", 0]], () => heartLook.bpm, (v) => { heartLook.bpm = v; }],
    ["エラ", [["止める（出典どおり）", 0], ["口と同じ 1.25 Hz", 1.25], ["毎分 36", 0.6]], () => gillLook.hz, (v) => { gillLook.hz = v; }],
  ], "心臓は形を BIODIDAC の Squalus の図から、置き場所を骨格から決めた推定の部品。拍動は近い種の安静時（ドチザメ類 37、レモンザメ 52 回/分）。泳いでいる間エラは開いたまま、が出典で、動かすのは創作");
}
// ?pick=mouth: 口の休みの開き・開け閉めの振れと回数の案を、動かしたまま切り替える（B5）
function mouthPicker() {
  // 休みの開きの既定は 15°（2026-10-15 プロデューサー決定）。25°・20° は試しのページにだけ置いた案の glb
  const base = { specimen_hammerhead: 15, specimen_hammerhead_m20: 20, specimen_hammerhead_m25: 25 }[GLB_NAME] ?? 15;
  pickerPanel([
    ["休みの開き", [["15°", 15], ["20°", 20], ["25°", 25]], () => base, (v) => {
      const q = new URLSearchParams(location.search); if (v === 15) q.delete("glb"); else q.set("glb", `specimen_hammerhead_m${v}`);
      location.search = q.toString();   // 開きの違う glb を読み直す
    }],
    ["口の振れ", [["0°", 0], ["±2°", 2], ["±3°", 3], ["±5°", 5]], () => mouthLook.deg, (v) => { mouthLook.deg = v; }],
    ["回数", [["尾と同じ 1.25 Hz", 1.25], ["毎分 36 回", 0.6]], () => mouthLook.hz, (v) => { mouthLook.hz = v; }],
  ], "口は休みの開きを中心に開け閉め（休みの開きを変えると読み直す）。毎分 36 回はドチザメ類の呼吸（ポンプ）の速さ。シュモクザメの口の動きの回数の出典は無い");
}
function canvasShown(el) {
  if (el.clientWidth > 0 && el.clientHeight > 0) return Promise.resolve();
  return new Promise((done) => {
    const ro = new ResizeObserver(() => { if (el.clientWidth > 0 && el.clientHeight > 0) { ro.disconnect(); done(); } });
    ro.observe(el);
  });
}
start().catch((error) => { status.textContent = String(error.message ?? error); document.body.dataset.error = "1"; console.error(error); });
