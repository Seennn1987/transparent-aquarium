import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { createOrbit } from "./orbit.js";
import { applyChameleonTissue, createLightbox, chameleonLook, chameleonClock, chameleonOrgans, calibrateOrgans } from "./chameleon-material.js";
import { stainOf } from "./chameleon-stain.js";
import { installChameleonTune } from "./chameleon-tune.js";
import { installChameleonRotate } from "./chameleon-rotate.js";
import { createChameleonFps } from "./chameleon-fps.js";
import { createChameleonWalk } from "./chameleon-walk.js";

// The chameleon as a finished cleared-and-stained specimen, on a lightbox, without its jar.
// The mesh comes from the MorphoSource CT (non-commercial, not redistributed), so the file is
// kept out of git: blender/export_chameleon_gltf.py writes it to assets/private/.
const CHAMELEON_URL = new URL("../assets/private/specimen_chameleon.glb", import.meta.url).href;
const CLIP = "CH_Hover";
const PHOTO01_TURN = [0, 0, 20];

const canvas = document.querySelector("#scene");
const status = document.querySelector("#status");
const query = new URLSearchParams(location.search);
let paused = query.get("still") === "1";

async function start() {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, preserveDrawingBuffer: true });
  if (!renderer.capabilities.isWebGL2) throw new Error("WebGL2 が使えないため表示できません");
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  // `stain=01`: the colour pattern measured on the user's jar photo 01 (chameleon-stain.js STAINS).
  const stain = query.get("stain") === "01" ? "01" : "06";
  // ?ss=1 draws the passes at the screen's own size (the calibrations read the buffers pixel for pixel).
  const ss = Number(new URLSearchParams(location.search).get("ss")) || 2;
  const lightbox = createLightbox(renderer, { stain, supersample: ss });
  // ?skin=3: the skin (its path and its surface layer) this many times darker, to check the skin's shape by
  // eye (C record 30, 2026-10-18: the producer found the skin too pale to see). Not the photo's colour.
  // Pattern 01's blue skin is 3 times darker by default for now (the producer, 2026-10-18: 「一旦、青の濃さ3倍で」);
  // ?skin=1 gives photo 01's colour.
  const skinView = Number(query.get("skin")) || (stain === "01" ? 3 : 0);
  if (skinView > 0) { chameleonLook.skin.value = skinView; if (stain === "01") chameleonLook.film.value = skinView; }
  document.body.style.background = `rgb(${stainOf(stain).lightbox.map((v) => Math.round(v * 255)).join(",")})`;

  const gltf = await new GLTFLoader().loadAsync(CHAMELEON_URL);
  const model = gltf.scene;
  const reference = { value: 0 };
  applyChameleonTissue(model, reference);
  const clip = gltf.animations.find((a) => a.name === CLIP);
  if (!clip) throw new Error(`specimen_chameleon.glb に ${CLIP} がありません`);

  // `view=photo06`: the head to the right and the back up, the animal's other side toward the
  // camera, as it lies in 06-lightbox-calyptratus-2.jpg (the pose is still the jar's).
  const holder = new THREE.Group();
  holder.add(model);
  // The start is this orientation, with the rotation bars at 0 (C record 56, 2026-10-24, the producer: 「添付画像の向き規定にして。
  // そしてそれを各軸の０度にして。」, with a picture of it). `view=photo01` gives the jar photo's orientation (C record 55) instead.
  const photo06 = query.get("view") !== "photo01";
  if (photo06) holder.rotation.set(0, Math.PI, -Math.PI / 2);
  const scene = new THREE.Scene();
  scene.add(holder);

  const walking = query.get("walk") === "1";
  const mixer = new THREE.AnimationMixer(model);
  const action = mixer.clipAction(clip);
  action.play();
  mixer.update(Number(query.get("t") ?? 0));
  scene.updateMatrixWorld(true);

  const box = new THREE.Box3().setFromObject(model, true);
  const centre = box.getCenter(new THREE.Vector3());
  const radius = box.getSize(new THREE.Vector3()).length() / 2;
  // The specimen hangs from a pivot at its centre, so the rotation bars (chameleon-rotate.js) turn it in place.
  const pivot = new THREE.Group(); pivot.position.copy(centre);
  // `view=photo01`: turned to lie as in the jar photo 01 (C record 55, 2026-10-24): degrees about the screen's X, Y, Z (Rz · Ry · Rx),
  // on top of the jar pose. `?rot=x,y,z` tries others. Either way the bars start at 0.
  const rot = (query.get("rot") ?? (photo06 ? "0,0,0" : PHOTO01_TURN.join(","))).split(",").map((v) => THREE.MathUtils.degToRad(Number(v) || 0));
  pivot.quaternion.setFromEuler(new THREE.Euler(rot[0], rot[1], rot[2], "ZYX"));
  const inner = new THREE.Group(); inner.position.copy(centre).negate();
  scene.remove(holder); inner.add(holder); pivot.add(inner); scene.add(pivot);
  scene.updateMatrixWorld(true);
  // ?walk=1: walking along a branch (chameleon-walk.js, C record 59), from CH_Hover's pose at t = 0.
  const walk = walking ? createChameleonWalk(model, holder) : null;
  if (walk) { walk.branchFrame.matrixAutoUpdate = false; walk.update(0); scene.updateMatrixWorld(true); }
  const camera = new THREE.PerspectiveCamera(20, 1, radius * 0.1, radius * 20);
  // In the photo the animal spans about 0.75 of the frame's width.
  const size = box.getSize(new THREE.Vector3());
  const distance = photo06
    ? size.x / 0.75 / 2 / Math.tan(THREE.MathUtils.degToRad(10)) / (canvas.clientWidth / canvas.clientHeight)
    : radius / Math.tan(THREE.MathUtils.degToRad(10)) * 1.05;
  camera.position.copy(centre).add(new THREE.Vector3(0, 0, distance));
  const orbit = createOrbit(camera, canvas, {
    target: centre.clone(),
    // Dragging turns the specimen (chameleon-rotate.js), not the camera; the wheel still zooms.
    rotateSpeed: 0,
    minDistance: distance * 0.15,
    maxDistance: distance * 2,
    minPolar: 0.05,
    maxPolar: Math.PI - 0.05,
  });

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    const size = renderer.getDrawingBufferSize(new THREE.Vector2());
    lightbox.setSize(size.x, size.y);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  resize();
  addEventListener("resize", resize);
  addEventListener("keydown", (e) => {
    if (e.code === "Space") { paused = !paused; e.preventDefault(); }
  });

  // ?fps=1: the frame rate at the top left (chameleon-fps.js, C record 57).
  const fpsBox = query.get("fps") === "1" ? createChameleonFps(renderer, model, lightbox) : null;
  const clock = new THREE.Clock();
  let walkTime = Number(query.get("t") ?? 0);
  const view = new THREE.Vector3();
  function frame() {
    const dt = clock.getDelta();
    if (walk) { if (!paused) walkTime += dt; walk.update(walkTime); chameleonClock.value = walkTime; }
    else { if (!paused) mixer.update(dt); chameleonClock.value = action.time; }
    // The plane the solid paths are measured from: through the body's centre.
    view.copy(centre).applyMatrix4(camera.matrixWorldInverse);
    reference.value = -view.z;
    const t0 = performance.now();
    if (walk) { scene.updateMatrixWorld(); walk.branchFrame.matrix.copy(holder.matrixWorld); }
    lightbox.render(scene, camera, null, walk?.backdrop ?? null);
    fpsBox?.tick(t0, performance.now() - t0);
    requestAnimationFrame(frame);
  }
  orbit.update();
  frame();
  status.textContent = `${lightbox.precision} · stain ${stain}`;
  installChameleonTune(stain);
  installChameleonRotate(pivot, canvas);
  document.body.dataset.ready = "1";

  // For measuring the screen against the photo: sRGB 0–255 at canvas pixels (from the top-left).
  window.chameleonPage = {
    look: chameleonLook,
    renderer, lightbox, camera, model, orbit, pivot,
    /** Path lengths (bone, cartilage, skin films) over the whole canvas, bottom row first. */
    paths() {
      const t = lightbox.target;
      const out = new Float32Array(t.width * t.height * 4);
      renderer.readRenderTargetPixels(t, 0, 0, t.width, t.height, out);
      return { width: t.width, height: t.height, data: out };
    },
    sample(points) {
      const gl = renderer.getContext();
      const h = gl.drawingBufferHeight;
      const px = new Uint8Array(4);
      return points.map(([x, y]) => {
        gl.readPixels(x, h - 1 - y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
        return [px[0], px[1], px[2]];
      });
    },
    organs: chameleonOrgans, calibrateOrgans,
    /** The organ buffer (each organ's absorbance × path, model units), bottom row first. */
    organ() {
      const t = lightbox.organTarget;
      const out = new Float32Array(t.width * t.height * 4);
      renderer.readRenderTargetPixels(t, 0, 0, t.width, t.height, out);
      return { width: t.width, height: t.height, data: out };
    },
    /** The "01" pattern's film buffer (slant crossings of the skin's surface), bottom row first. */
    film() {
      const t = lightbox.filmTarget;
      const out = new Float32Array(t.width * t.height * 4);
      renderer.readRenderTargetPixels(t, 0, 0, t.width, t.height, out);
      return { width: t.width, height: t.height, data: out };
    },
    setPaused(v) { paused = Boolean(v); },
    /** ?walk=1: jump the walk to `t` seconds. */
    walkTo(t) { walkTime = t; },
    seek(t) { mixer.setTime(t); },
  };
}

start().catch((error) => {
  status.textContent = String(error.message ?? error);
  document.body.dataset.error = "1";
  console.error(error);
});
