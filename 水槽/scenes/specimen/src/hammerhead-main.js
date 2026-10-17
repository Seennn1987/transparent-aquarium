import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { createOrbit } from "./orbit.js";
import { chameleonLook } from "./chameleon-material.js";
import { createHammerheadLightbox } from "./hammerhead-lightbox.js";
import { installHammerheadTune } from "./hammerhead-tune.js";
import { HH_BONE_T0 } from "./hammerhead-stain.js";   // registers STAINS.hammerhead
import { applyHammerheadTissue } from "./hammerhead-material.js";
import { createSwim, swimLook, mouthLook, heartLook, gillLook } from "./hammerhead-swim.js";
import { pickerPanel } from "./picker-panel.js";

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
  // 2026-10-15 色の層を 8 つにしたシュモクザメ専用のライトボックス（hammerhead-lightbox.js）
  const lightbox = createHammerheadLightbox(renderer, { supersample: ss });
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
  // ?pick=look: 頭の幅（glb を読み直す）とエラの骨の色（?gillbone= ?gillcart=）の案（2026-10-15、プロデューサー「鰓骨の色が他の色対比で濃すぎないでしょうか？」
  //  「頭の大きさが体のサイズに比べて小さくないでしょうか？」）。頭の幅の案の glb は試しのページだけに置く
  if (query.get("pick") === "look") {
    const reload = (set) => { const q = new URLSearchParams(location.search); set(q); location.search = q.toString(); };
    const head = { specimen_hammerhead: 33, specimen_hammerhead_h29: 29, specimen_hammerhead_h26: 26 }[GLB_NAME] ?? 33;
    const gill = `${query.get("gillbone") ?? 0},${query.get("gillcart") ?? 1}`;
    pickerPanel([
      ["頭の幅", [["全長の 26%（前）", 26], ["29%", 29], ["33%（決定、CT の個体）", 33]], () => head,
        (v) => reload((q) => { if (v === 33) q.delete("glb"); else q.set("glb", `specimen_hammerhead_h${v}`); })],
      ["エラの骨", [["濃い紺（前）", "1.67,1.518"], ["半分", "0.84,0.76"], ["顎に近い淡い青", "0,0.5"], ["青緑（決定）", "0,1"]], () => gill,
        (v) => reload((q) => { const [b, c] = v.split(","); if (v === "0,1") { q.delete("gillbone"); q.delete("gillcart"); } else { q.set("gillbone", b); q.set("gillcart", c); } })],
    ], "頭の幅: 資料（ICCAT）では全長の 26〜29%、CT の個体は 33%。胴の幅（102 mm）は変えず、頭だけ広げる。エラの骨: いまは胚の鰓弓の濃い紺。鰓条の縞も同じ色に合わせて変わる");
  }
  // ?pick=body: 胴の幅・長さの案と尾の骨の案（glb を読み直す）、弓の色（?archbone= ?arch=）（2026-10-16、プロデューサー「胴の幅（第 1 背びれのあたりを一番太く）と
  //  後ろ半分の長さの案、尾の骨（血道弓・尾びれの鰭条・肋骨）の案を両方作って、ブラウザで並べて見せて」）。案の glb は試しのページだけに置く
  if (query.get("pick") === "body") {
    const reload = (set) => { const q = new URLSearchParams(location.search); set(q); location.search = q.toString(); };
    const arch = `${query.get("archbone") ?? 0},${query.get("arch") ?? 0.5}`;
    pickerPanel([
      // 2026-10-16 参考の図（FMIB の幅・Raver の高さ）に合わせた案を足した。前の「幅を写真に」の 3 案は、幅が高さを超えて文献と逆の形なので外した（glb は試しのページに残る）
      // 2026-10-16 胴の形は案 2 に決定（プロデューサー「胴の形は案 2 に決めて、既定にしてください」）。前の形の glb は試しのページに specimen_hammerhead_prev として残す
      ["案", [["いま（決定）", "specimen_hammerhead"], ["ひれ: 背びれ・臀びれを参考の外形に", "specimen_hammerhead_f1p0"], ["ひれ: ＋胸びれ・腹びれを下へ 15°", "specimen_hammerhead_f1p1"],
        ["ひれ: ＋胸びれ下へ 30°・腹びれ下へ 25°", "specimen_hammerhead_f1p2"], ["胸びれ・腹びれだけ下へ 15°", "specimen_hammerhead_f0p1"], ["尾の骨なし", "specimen_hammerhead_notail"], ["胴: 前の形", "specimen_hammerhead_prev"]], () => GLB_NAME,
        (v) => reload((q) => { if (v === "specimen_hammerhead") q.delete("glb"); else q.set("glb", v); })],
      ["弓の色", [["ひれの軟骨の半分の青（決定）", "0,0.5"], ["ひれの軟骨と同じ青", "0,1"], ["前（骨 0.3・軟骨 0.08）", "0.3,0.08"]], () => arch,
        (v) => reload((q) => { const [b, c] = v.split(","); if (v === "0,0.5") { q.delete("archbone"); q.delete("arch"); } else { q.set("archbone", b); q.set("arch", c); } })],
    ], "ひれ: 背びれ 2 つと臀びれを、横からの参考の図 2 枚（Duane Raver・FMIB 45527、パブリックドメイン）の外形と大きさに。胸びれ・腹びれは 2026-10-14 に決めた姿勢から下へ回す。胴は案 2、尾の骨あり");
  }
  // ?pick=tissue: 胴の色の案（hammerhead-stain.js の ?tissue=）を読み直して切り替える（2026-10-15）
  if (query.get("pick") === "tissue") pickerPanel([
    ["胴の色", [["A 前の色", "A"], ["B 胴の真ん中", "B"], ["C 胴全体", "C"], ["D 胴全体（画面で合わせる、決定）", "D"]], () => query.get("tissue") ?? "D",
      (v) => { const q = new URLSearchParams(location.search); if (v === "D") q.delete("tissue"); else q.set("tissue", v); location.search = q.toString(); }],
  ], "参考の胚の体の組織: 前に測った 1 点 0.79 / 0.66 / 0.57（A）、胴の真ん中 0.81 / 0.76 / 0.69（B）、胴全体 0.80 / 0.81 / 0.75（C）。D は皮歯・まだら・内臓の分を差し引いて、画面で C の値になるようにした");
  // 色と濃さの調整の欄（右上の「調整」。?tune=1 で開いて始める、?tune=0 で出さない）。撮る道具は ?tune=0 を付けなくても欄は閉じている
  const tune = query.get("tune") !== "0" ? installHammerheadTune({ open: query.get("tune") === "1" }) : null;
  document.body.dataset.ready = "1";
  window.hammerheadPage = {
    look: chameleonLook, renderer, lightbox, camera, model, swim, swimLook,
    setPaused(v) { paused = Boolean(v); }, get paused() { return paused; }, tune,
    // 測る道具（measure-hammerhead.mjs）のために、前の 4 層の並び（r 骨＋歯、g 軟骨＋顎＋エラ＋腹びれの軟骨、b 肉、a 頭骨）にまとめて返す
    paths() {
      const t = lightbox.target, t2 = lightbox.target2, n = t.width * t.height * 4;
      const out = new Float32Array(n), b = new Float32Array(n);
      renderer.readRenderTargetPixels(t, 0, 0, t.width, t.height, out);
      renderer.readRenderTargetPixels(t2, 0, 0, t2.width, t2.height, b);
      for (let i = 0; i < n; i += 4) { out[i] += b[i + 3]; out[i + 1] += b[i] + b[i + 1] + b[i + 2]; }
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
// ?pick=organs: 心臓（BIODIDAC の図から作った部品）の案と拍動の回数、エラの動きの案を、動かしたまま切り替える（B5）。心臓の案は ?glb=specimen_hammerhead_heart
function organPicker() {
  pickerPanel([
    ["心臓", [["実物に近い大きさ", "large"], ["小さく骨に当てない", "small"], ["なし", "none"]], () => heartLook.show, (v) => { heartLook.show = v; }],
    ["拍動", [["毎分 37", 37], ["毎分 52", 52], ["止める", 0]], () => heartLook.bpm, (v) => { heartLook.bpm = v; }],
    ["エラ", [["止める（出典どおり）", 0], ["口と同じ 1.25 Hz", 1.25], ["毎分 36", 0.6]], () => gillLook.hz, (v) => { gillLook.hz = v; }],
  ], "心臓は形を BIODIDAC の Squalus の図から、置き場所を骨格から決めた部品。拍動は近い種の安静時（ドチザメ類 37、レモンザメ 52 回/分）。泳いでいる間エラは開いたまま、が出典で、動かすのは創作");
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
