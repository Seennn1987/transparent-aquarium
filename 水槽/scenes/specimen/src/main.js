import * as THREE from "three";
import { installControls, reportSceneError, preferredQuality } from "../../shared/controls.js";
import { createFrameLoop } from "../../shared/frame-loop.js";
import { frameRate, qualityName, renderScale } from "../../shared/render-policy.js";
import { createOrbit } from "./orbit.js";
import { createJar } from "./jar.js";
import { createSpecimen } from "./specimen.js";
import { specimenLook } from "./specimen-material.js";
import { createSpecimenPost, LENS } from "./postprocess.js";
import {
  STUDIO_BACKGROUND,
  KEY_DIRECTION,
  FLOOR_LOOK,
  createStudioEnvironment,
  createBackdrop,
  createStudioFloor,
} from "./studio.js";

const canvas = document.querySelector("#scene");
const habitat = document.querySelector("#habitat");
const loading = document.querySelector("#loading");

let paused =
  document.documentElement.dataset.motion !== "host" &&
  matchMedia("(prefers-reduced-motion: reduce)").matches;
const query = new URLSearchParams(location.search);
const wallpaper = document.documentElement.dataset.motion === "host";
let profile = preferredQuality(query);
if (query.get("still") === "1") paused = true;

let onBattery = false;
let requestedRate = wallpaper ? 0 : 60;
let loop = null;
let updateControls = () => {};

window.habitatPause = (value) => {
  paused = Boolean(value);
  loop?.setPaused(paused);
  updateControls();
};
window.habitatRate = (fps) => {
  requestedRate = Number.isFinite(fps) && fps > 0 ? Math.min(120, fps) : 0;
  loop?.setRate(frameRate(profile, requestedRate, onBattery));
  updateControls();
};
window.habitatPower = (battery) => {
  const next = Boolean(battery);
  if (next === onBattery) return;
  onBattery = next;
  loop?.setRate(frameRate(profile, requestedRate, onBattery));
  updateControls();
};

// Product-shot framing: a long lens from slightly above the jar's middle.
const CAMERA = { fov: 20, position: new THREE.Vector3(3.1, 3.2, 11.0), target: new THREE.Vector3(0, 1.4, 0) };

async function start() {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: false,
    alpha: false,
    powerPreference: "high-performance",
  });
  if (!renderer.capabilities.isWebGL2) throw new Error("WebGL2 が使えないため標本ケースを表示できません");
  renderer.setPixelRatio(1);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  // Applied once, in the final pass: the scene itself is rendered linear.
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(STUDIO_BACKGROUND);

  const camera = new THREE.PerspectiveCamera(CAMERA.fov, 1, 0.1, 40);
  camera.position.copy(CAMERA.position);

  scene.add(new THREE.HemisphereLight(0xffffff, 0xd8d4cc, 0.45));

  const key = new THREE.DirectionalLight(0xfffaf4, 0.9);
  key.position.copy(KEY_DIRECTION).multiplyScalar(10);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  Object.assign(key.shadow.camera, {
    left: -3,
    right: 3,
    top: 4,
    bottom: -1,
    near: 1,
    far: 16,
  });
  key.shadow.bias = -0.0002;
  key.shadow.normalBias = 0.02;
  scene.add(key);

  const fill = new THREE.DirectionalLight(0xe8eef4, 0.45);
  fill.position.set(-2.5, 2.5, 3.5);
  scene.add(fill);

  // Scene fog must stay off: it veils transmissive glass. The floor fades into the backdrop itself.
  scene.add(createBackdrop(24));

  const envMap = createStudioEnvironment(renderer);
  scene.environment = envMap;
  scene.environmentIntensity = 0.6;
  const jar = await createJar({ envMap, lens: LENS });
  scene.add(jar.root);
  scene.add(createStudioFloor(23.5, {
    jarRadius: jar.dims.bodyRadius,
    footRadius: jar.dims.footRadius,
    glassTop: jar.bounds.max.y,
    liquidBottom: jar.liquidBounds.min.y,
    liquidTop: jar.liquidBounds.max.y,
  }));
  // The specimen is only ever seen through the liquid, so it has a scene of its own, drawn
  // over white into the image the jar's optics look up.
  const specimen = await createSpecimen({ envMap, liquidBounds: jar.liquidBounds });
  const specimenScene = new THREE.Scene();
  specimenScene.background = new THREE.Color(1, 1, 1);
  specimenScene.add(specimen.object);

  // Background mips stand in for the lens blur of what is seen far behind the glass.
  const backgroundImage = new THREE.WebGLRenderTarget(1, 1, {
    type: THREE.HalfFloatType,
    generateMipmaps: true,
    minFilter: THREE.LinearMipmapLinearFilter,
  });
  let specimenImage = null;
  function createSpecimenImage() {
    specimenImage?.dispose();
    specimenImage = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: profile === "eco" ? 0 : 4 });
    jar.optics.setImages(backgroundImage.texture, specimenImage.texture);
  }
  createSpecimenImage();

  let post = createSpecimenPost(camera, profile);
  window.specimenDebug = { scene, camera, renderer, jar, specimen, look: specimenLook, lens: LENS, optics: jar.optics, floor: FLOOR_LOOK, get post() { return post; } };

  const orbit = createOrbit(camera, canvas, {
    target: CAMERA.target.clone(),
    minDistance: 3.6,
    maxDistance: 16,
    onChange() {
      loop?.invalidate();
    },
  });

  function resize() {
    const width = Math.max(1, habitat.clientWidth);
    const height = Math.max(1, habitat.clientHeight);
    const scale = renderScale(profile, devicePixelRatio, onBattery);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
    const w = Math.round(width * scale);
    const h = Math.round(height * scale);
    renderer.setDrawingBufferSize(w, h, 1);
    post.target.setSize(w, h);
    backgroundImage.setSize(w, h);
    specimenImage.setSize(w, h);
    jar.optics.setSize(w, h);
    post.post.uniforms.size.value.set(w, h);
    loop?.invalidate();
  }
  resize();
  window.addEventListener("resize", resize);

  function setQuality(name) {
    profile = qualityName(name);
    const mapSize = profile === "eco" ? 512 : profile === "detail" ? 2048 : 1024;
    key.shadow.mapSize.set(mapSize, mapSize);
    key.shadow.map?.dispose();
    key.shadow.map = null;
    post.target.dispose();
    post.post.dispose();
    post = createSpecimenPost(camera, profile);
    createSpecimenImage();
    resize();
    loop?.setRate(frameRate(profile, requestedRate, onBattery));
    loop?.invalidate();
  }

  updateControls = installControls({
    habitat,
    isPaused: () => paused,
    isRunning: () => Boolean(loop?.state.running),
    pause: (value) => window.habitatPause(value),
    feed: () => {},
    quality: () => profile,
    setQuality,
  });

  const focusPoint = new THREE.Vector3();
  let frame = 0;
  loop = createFrameLoop((dt) => {
    specimen.update(dt);
    // Autofocus on the specimen, as a photographer would.
    specimen.object.getWorldPosition(focusPoint);
    LENS.focus.value = camera.position.distanceTo(focusPoint);
    jar.optics.setSpecimen(focusPoint);
    post.post.uniforms.frame.value = frame++ % 997;

    jar.root.visible = false;
    renderer.setRenderTarget(backgroundImage);
    renderer.render(scene, camera);
    jar.root.visible = true;
    renderer.setRenderTarget(specimenImage);
    renderer.render(specimenScene, camera);

    renderer.setRenderTarget(post.target);
    renderer.render(scene, camera);
    renderer.setRenderTarget(null);
    renderer.render(post.postScene, post.postCamera);
  }, {
    fps: frameRate(profile, requestedRate, onBattery),
    paused,
    hidden: document.hidden,
  });

  document.addEventListener("visibilitychange", () => {
    loop.setHidden(document.hidden);
  });

  if (loading) {
    loading.hidden = true;
    loading.style.opacity = "0";
  }
  canvas.focus({ preventScroll: true });
}

start().catch(reportSceneError);
