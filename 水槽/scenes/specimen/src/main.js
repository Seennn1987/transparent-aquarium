import * as THREE from "three";
import { installControls, reportSceneError, preferredQuality } from "../../shared/controls.js";
import { createFrameLoop } from "../../shared/frame-loop.js";
import { frameRate, qualityName } from "../../shared/render-policy.js";
import { createOrbit } from "./orbit.js";
import { createJar } from "./jar.js";
import { createSpecimen } from "./specimen.js";
import { specimenLook } from "./specimen-material.js";
import {
  STUDIO_BACKGROUND,
  createStudioEnvironment,
  createBackdrop,
  createStudioFloor,
  createContactShadow,
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

async function start() {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: false,
    powerPreference: "default",
  });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.NoToneMapping;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(STUDIO_BACKGROUND);

  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 40);
  camera.position.set(1.8, 2.1, 5.6);

  scene.add(new THREE.HemisphereLight(0xffffff, 0xd8d4cc, 0.45));

  const key = new THREE.DirectionalLight(0xfffaf4, 0.9);
  key.position.set(3.2, 6.5, 2.8);
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
  scene.add(createStudioFloor(23.5));

  const envMap = createStudioEnvironment(renderer);
  scene.environment = envMap;
  scene.environmentIntensity = 0.6;
  const jar = await createJar({ envMap });
  scene.add(jar.root);
  scene.add(createContactShadow(1.1));
  const specimen = await createSpecimen({ envMap, liquidBounds: jar.liquidBounds });
  scene.add(specimen.object);
  window.specimenDebug = { scene, camera, renderer, jar, specimen, look: specimenLook };

  const orbit = createOrbit(camera, canvas, {
    target: new THREE.Vector3(0, 1.25, 0),
    minDistance: 2.2,
    maxDistance: 11,
    onChange() {
      loop?.invalidate();
    },
  });

  function resize() {
    const width = Math.max(1, habitat.clientWidth);
    const height = Math.max(1, habitat.clientHeight);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
    loop?.invalidate();
  }
  resize();
  window.addEventListener("resize", resize);

  function setQuality(name) {
    profile = qualityName(name);
    const ratio =
      profile === "eco" ? 1 : Math.min(devicePixelRatio, profile === "detail" ? 2 : 1.5);
    renderer.setPixelRatio(ratio);
    const mapSize = profile === "eco" ? 512 : profile === "detail" ? 2048 : 1024;
    key.shadow.mapSize.set(mapSize, mapSize);
    key.shadow.map?.dispose();
    key.shadow.map = null;
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

  loop = createFrameLoop((dt) => {
    specimen.update(dt);
    renderer.render(scene, camera);
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
