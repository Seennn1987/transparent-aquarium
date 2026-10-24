import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { createOrbit } from "./orbit.js";
import { applyMendakoTissue, createMendakoLightbox, mdLook } from "./mendako-material.js";

// メンダコの透明標本を、器なしでライトボックスの上に描く（2026-10-24、手順 A4）。
// 形: blender/mendako/（b0〜b4。外の形は第 12 版、2026-10-24 プロデューサー「外の形はこの第 12 版でよい」）。
// glTF: +Y が背、+Z が前、+X が体の左。メートル（横幅 約 0.138 m）。
// ?view=front（生体の正面の写真 Sunshine2 と同じ低い前から）・oblique（斜め前の上から）・top（背中から、前が上）・oral（口側から、前が上）・side（体の左から）。
//  指定なしは斜め前の上から（display）。?ss=<n> 細かさ（既定 2）
const query = new URLSearchParams(location.search);
const URL_GLB = new URL("../assets/specimen_mendako.glb", import.meta.url).href;
const canvas = document.querySelector("#scene");
const status = document.querySelector("#status");

async function start() {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, preserveDrawingBuffer: true });
  if (!renderer.capabilities.isWebGL2) throw new Error("WebGL2 が使えないため表示できません");
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  const lightbox = createMendakoLightbox(renderer, { supersample: Number(query.get("ss")) || 2 });
  const gltf = await new GLTFLoader().loadAsync(URL_GLB);
  const model = gltf.scene;
  const reference = { value: 0 };
  applyMendakoTissue(model, reference);
  const scene = new THREE.Scene();
  scene.add(model);
  scene.updateMatrixWorld(true);

  const box = new THREE.Box3().setFromObject(model, true);
  const centre = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const radius = size.length() / 2;
  const camera = new THREE.PerspectiveCamera(20, 1, radius * 0.05, radius * 30);
  const view = query.get("view") ?? "display";
  const dirs = {
    front: new THREE.Vector3(0, 0.08, 1),
    oblique: new THREE.Vector3(-0.55, 0.3, 0.8),
    top: new THREE.Vector3(0, 1, 0.0001),
    oral: new THREE.Vector3(0, -1, 0.0001),
    side: new THREE.Vector3(1, 0.02, 0.0001),     // 体の左から（前が画面の左）
    display: new THREE.Vector3(-0.45, 0.6, 0.75),
  };
  const dir = (dirs[view] ?? dirs.display).clone().normalize();
  await canvasShown(canvas);
  const aspect0 = canvas.clientWidth / canvas.clientHeight;
  const fitW = Math.max(size.x, size.z);
  const distance = fitW / 2 / Math.tan(THREE.MathUtils.degToRad(10)) / Math.min(aspect0, 1) * 1.15;
  camera.position.copy(centre).addScaledVector(dir, distance);
  if (view === "top" || view === "oral") camera.up.set(0, 0, 1);   // 前（+Z）を画面の上に
  camera.lookAt(centre);
  const orbit = createOrbit(camera, canvas, { target: centre.clone(), minDistance: distance * 0.2, maxDistance: distance * 2.5, minPolar: 0.02, maxPolar: Math.PI - 0.02 });

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    const s = renderer.getDrawingBufferSize(new THREE.Vector2());
    lightbox.setSize(s.x, s.y);
    camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  resize();
  addEventListener("resize", resize);
  new ResizeObserver(resize).observe(canvas);
  const v = new THREE.Vector3();
  function frame() {
    v.copy(centre).applyMatrix4(camera.matrixWorldInverse);
    reference.value = -v.z;
    lightbox.render(scene, camera);
    requestAnimationFrame(frame);
  }
  if (view !== "top" && view !== "oral" && view !== "side") orbit.update();
  frame();
  status.textContent = `${lightbox.precision} · ${view}`;
  document.body.dataset.ready = "1";
  window.mendakoPage = { renderer, lightbox, camera, model, look: mdLook };
}
function canvasShown(el) {
  if (el.clientWidth > 0 && el.clientHeight > 0) return Promise.resolve();
  return new Promise((done) => {
    const ro = new ResizeObserver(() => { if (el.clientWidth > 0 && el.clientHeight > 0) { ro.disconnect(); done(); } });
    ro.observe(el);
  });
}
start().catch((error) => { status.textContent = String(error.message ?? error); document.body.dataset.error = "1"; console.error(error); });
