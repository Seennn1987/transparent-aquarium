import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { createOrbit } from "./orbit.js";
import { createLightbox, chameleonLook } from "./chameleon-material.js";
import { HH_BONE_T0 } from "./hammerhead-stain.js";   // registers STAINS.hammerhead
import { applyHammerheadTissue } from "./hammerhead-material.js";

// The smooth hammerhead as a cleared-and-stained specimen on a lightbox, without its dish (A6).
// The mesh: blender/ct_hammerhead (CT of ZMA.PISC.108725, Kamminga et al. 2017, CC0).
const URL_GLB = new URL("../assets/specimen_hammerhead.glb", import.meta.url).href;
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
  // A8 まだらの強さ（内臓の通り道。hammerhead-material.js の mottleMaterial）。既定 0 = まだらなし
  chameleonLook.organs.value = Number(query.get("mottle") ?? 0);
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
  const aspect0 = canvas.clientWidth / canvas.clientHeight;
  // focus=head: 頭（吻端から 0.3 m）を画面いっぱいに（顎・歯・エラの骨を見る）
  const focusHead = query.get("focus") === "head";
  if (focusHead) centre.set(box.min.x + 0.13, centre.y, centre.z);
  const distance = fit(focusHead ? 0.3 : size.x) / (focusHead ? Math.min(aspect0, 1) : aspect0) * 1.1;
  camera.position.copy(centre).addScaledVector(dir, distance);
  if (view === "top" || view === "below") camera.up.set(0, 0, -1);
  camera.lookAt(centre);
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
  const v = new THREE.Vector3();
  function frame() {
    v.copy(centre).applyMatrix4(camera.matrixWorldInverse);
    reference.value = -v.z;
    lightbox.render(scene, camera);
    requestAnimationFrame(frame);
  }
  if (view !== "top" && view !== "below") orbit.update();
  frame();
  status.textContent = `${lightbox.precision} · ${view}`;
  document.body.dataset.ready = "1";
  window.hammerheadPage = {
    look: chameleonLook, renderer, lightbox, camera, model,
    paths() {
      const t = lightbox.target; const out = new Float32Array(t.width * t.height * 4);
      renderer.readRenderTargetPixels(t, 0, 0, t.width, t.height, out);
      return { width: t.width, height: t.height, data: out };
    },
  };
}
start().catch((error) => { status.textContent = String(error.message ?? error); document.body.dataset.error = "1"; console.error(error); });
