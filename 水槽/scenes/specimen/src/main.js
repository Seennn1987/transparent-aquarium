import * as THREE from "three";
import { installControls, reportSceneError, preferredQuality } from "../../shared/controls.js";
import { createFrameLoop } from "../../shared/frame-loop.js";
import { frameRate, qualityName, renderScale } from "../../shared/render-policy.js";
import { createOrbit } from "./orbit.js";
import { createJar } from "./jar.js";
import { createSpecimen } from "./specimen.js";
import { createChameleonSpecimen } from "./specimen-chameleon.js";
import { createHammerheadSpecimen, setHammerheadSpeed } from "./specimen-hammerhead.js";
import { pickerPanel } from "./picker-panel.js";
import { swimLook } from "./hammerhead-swim.js";
import { specimenLook } from "./specimen-material.js";
import { createSpecimenPost, LENS } from "./postprocess.js";
import {
  DEFAULT_VIEW,
  ROOM_YAW,
  ROOM_DARK,
  KEY_DIRECTION,
  RIM_DIRECTION,
  GALLERY_COLORS,
  GALLERY_LOOK,
  FLOOR_LOOK,
  STAGE_NAMES,
  WALL_NAMES,
  stageName,
  wallName,
  createGallery,
  createGalleryEnvironment,
} from "./gallery.js";
import { createGalleryJars } from "./gallery-jars.js";
import { slotCount } from "./gallery-layout.js";
import { installTunePanel } from "./tune-panel.js";
import { createMirrorPass } from "./table-reflection.js";

const STAGE_KEY = "specimen-stage";
const WALL_KEY = "specimen-wall";

function saved(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}

function preferredLook(params) {
  return {
    table: stageName(params.get("stage") || saved(STAGE_KEY)),
    wall: wallName(params.get("wall") || saved(WALL_KEY)),
  };
}

// The jars behind are traced copies of the front one except at the lightest quality; the
// thick glass of their lids and feet is traced only at the highest.
const jarQuality = (profile) => ({ traced: profile !== "eco", detail: profile === "detail" });

const canvas = document.querySelector("#scene");
const habitat = document.querySelector("#habitat");
const loading = document.querySelector("#loading");

let paused =
  document.documentElement.dataset.motion !== "host" &&
  matchMedia("(prefers-reduced-motion: reduce)").matches;
const query = new URLSearchParams(location.search);
const wallpaper = document.documentElement.dataset.motion === "host";
let profile = preferredQuality(query, "detail");
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

const CAMERA = DEFAULT_VIEW;
// How far the orbit may turn from the default view before the room's edge would show.
const ORBIT_TURN = 0.7;

async function start() {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: false,
    alpha: false,
    powerPreference: "high-performance",
  });
  if (!renderer.capabilities.isWebGL2) throw new Error("WebGL2 が使えないため標本ケースを表示できません");
  renderer.setPixelRatio(1);
  // Applied once, in the final pass: the scene itself is rendered linear.
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.toneMappingExposure = 1.34;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  scene.background = ROOM_DARK.clone();

  const camera = new THREE.PerspectiveCamera(CAMERA.fov, 1, 0.1, 40);
  camera.position.copy(CAMERA.position);

  // The room and the blocks draw their own light; these only give the glass its highlights.
  scene.add(new THREE.HemisphereLight(GALLERY_COLORS.key, GALLERY_COLORS.dark, 0.3));
  const key = new THREE.DirectionalLight(GALLERY_COLORS.key, 1.1);
  key.position.copy(KEY_DIRECTION).multiplyScalar(10);
  scene.add(key);
  const rim = new THREE.DirectionalLight(GALLERY_COLORS.key, 0.6);
  rim.position.copy(RIM_DIRECTION).multiplyScalar(10);
  scene.add(rim);

  // Scene fog must stay off: it veils transmissive glass.
  // The room as the glass reflects it, one per table and walls, baked when first shown.
  let look = preferredLook(query);
  const envMaps = new Map();
  const envFor = ({ table, wall }) => {
    const key = `${table}/${wall}`;
    if (!envMaps.has(key)) envMaps.set(key, createGalleryEnvironment(renderer, { table, wall }));
    return envMaps.get(key);
  };
  const envMap = envFor(look);
  scene.environment = envMap;
  scene.environmentIntensity = 0.6;
  // `?specimen=chameleon`: the cleared-and-stained chameleon (specimen-chameleon.js) instead of the squid.
  // `?specimen=hammerhead`: シロシュモクザメ（specimen-hammerhead.js）を、前の台だけ低い円柱の器（dish.glb）に入れる。後ろの台はいまの液だけの瓶（2026-10-15）
  const specimenKind = ["chameleon", "hammerhead"].includes(query.get("specimen")) ? query.get("specimen") : "squid";
  const jar = await createJar({ envMap, lens: LENS, specimen: specimenKind, vessel: specimenKind === "hammerhead" ? "dish" : "jar" });
  // 後ろの台の瓶の形（gallery-jars.js が写す）。シュモクザメのときも、前の器ではなくいつもの瓶
  const rowJar = specimenKind === "hammerhead" ? await createJar({ envMap, lens: LENS, specimen: "squid" }) : jar;
  // The chameleon's label hid its face; left off for now (2026-10-13, at the user's request).
  if (specimenKind !== "squid") jar.label.visible = false;
  scene.add(jar.root);
  const gallery = createGallery({
    jarRadius: jar.dims.bodyRadius,
    footRadius: jar.dims.footRadius,
    glassTop: jar.bounds.max.y,
    liquidBottom: jar.liquidBounds.min.y,
    liquidTop: jar.liquidBounds.max.y,
  });
  scene.add(gallery.root);
  // The specimen is only ever seen through the liquid, so it has a scene of its own, drawn
  // over white into the image the jar's optics look up.
  const specimenOptions = {
    envMap,
    liquidBounds: jar.liquidBounds,
    facing: CAMERA.position.clone().sub(CAMERA.target).setY(0).normalize(),
  };
  const specimen = specimenKind === "chameleon"
    ? await createChameleonSpecimen({ ...specimenOptions, stain: query.get("stain") === "01" ? "01" : "06" })
    : specimenKind === "hammerhead" ? await createHammerheadSpecimen(specimenOptions)
    : await createSpecimen(specimenOptions);
  // ?specimen=hammerhead&pick=dish: 器の直径（サメに対して）の案を、回したまま切り替える（C2・C3、2026-10-15）
  const picks = (query.get("pick") ?? "").split(",");
  if (specimenKind === "hammerhead" && picks.includes("dish")) {
    pickerPanel([
      ["器の直径", [["1 倍", 1], ["1.5 倍", 1.5], ["2 倍（決定）", 2], ["2.5 倍", 2.5]], () => specimen.dishRatio, (v) => specimen.setDishRatio(v)],
    ], "器はこのままで、サメを小さく描く（器の直径がサメに対して何倍か）。1 倍は回れないので真ん中でその場の泳ぎ。回る円の半径は、体のどこも壁から 0.12 より近づかない、いちばん大きい円");
  }
  // ?pick=speed: 泳ぐ速さの案（2026-10-15、プロデューサー「泳ぐスピードが速いのでもう少し遅いパターンを何パターンか提案して」）。
  //  1 回の尾の振りで進む長さ（0.64 L、Webb & Keyes 1982）はそのままで、尾の振りの回数を速さに合わせて下げる（遅く泳ぐほど尾の振りは少ない、Webb & Keyes 1982・Lowe 1996）。
  //  口は「尾と同じ回数」（B5 の決定）なので、尾に合わせる
  if (specimenKind === "hammerhead" && picks.includes("speed")) {
    const speeds = [0.8, 0.6, 0.4, 0.25];   // L/s
    pickerPanel([
      ["泳ぐ速さ", speeds.map((v) => [`${v} L/s（尾 ${(v / 0.64).toFixed(2)} Hz）`, v]), () => +(swimLook.frequency * 0.64).toFixed(2),
        (v) => setHammerheadSpeed(v)],
    ], "既定は 0.4 L/s（2026-10-15 決定）。0.8 L/s は出典のボンネットヘッドの水槽での速さ（尾 1.25 Hz）。遅いほど 1 周が長い。アドレスの ?speed= でも変えられる");
  }
  const specimenScene = new THREE.Scene();
  specimenScene.background = new THREE.Color(1, 1, 1);
  specimenScene.add(specimen.object);

  // The row of jars behind; the specimen's pose is baked for the front jar's mirror image
  // before it starts to move.
  const galleryJars = createGalleryJars({ jar: rowJar, specimen, envMap, lens: LENS });
  scene.add(galleryJars.root);
  galleryJars.setQuality(jarQuality(profile));
  // Turned further than ORBIT_TURN from the default view (the chameleon's full orbit), the row of
  // jars behind would stand between the camera and the front jar: the row is then left out.
  let wantedJars = 0;
  let rowHidden = false;
  function setJarCount(count) {
    wantedJars = count;
    gallery.setBlocks(galleryJars.setCount(rowHidden ? 0 : count));
    loop?.invalidate();
  }
  setJarCount(slotCount(profile));

  // What the jars stand on and the walls. The glass reflects the room as it now is, so the
  // environment map is swapped along with them.
  const mirror = createMirrorPass(gallery.reflection);
  function setLook(next) {
    look = { table: stageName(next.table ?? look.table), wall: wallName(next.wall ?? look.wall) };
    const to = envFor(look);
    gallery.setLook(look);
    const blocks = look.table === "blocks";
    galleryJars.setBlocks(blocks);
    jar.optics.setBlocks(blocks);
    scene.background.copy(ROOM_DARK);
    const baked = new Set(envMaps.values());
    scene.environment = to;
    for (const root of [scene, specimenScene]) {
      root.traverse((object) => {
        for (const material of [object.material].flat()) {
          if (material?.envMap && baked.has(material.envMap)) material.envMap = to;
        }
      });
    }
    loop?.invalidate();
  }
  setLook(look);

  // The room without any jar, for the traced jars behind to look through. The lens blurs it
  // deeply there, so half the size will do.
  const roomImage = new THREE.WebGLRenderTarget(1, 1, {
    type: THREE.HalfFloatType,
    generateMipmaps: true,
    minFilter: THREE.LinearMipmapLinearFilter,
  });

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
  window.specimenDebug = {
    scene, camera, renderer, jar, specimen, gallery, galleryJars, setJarCount, setLook, get stageLook() { return look; },
    look: specimenLook, lens: LENS, optics: jar.optics, floor: FLOOR_LOOK, galleryLook: GALLERY_LOOK,
    get post() { return post; }, get specimenImage() { return specimenImage; },
  };

  const orbit = createOrbit(camera, canvas, {
    target: CAMERA.target.clone(),
    minDistance: 3.6,
    maxDistance: 14,
    // The chameleon may be walked all the way round (the room's edge then shows; 2026-10-13, at the user's request).
    ...(specimenKind === "chameleon" ? {} : { minAzimuth: ROOM_YAW - ORBIT_TURN, maxAzimuth: ROOM_YAW + ORBIT_TURN }),
    onChange() {
      const turn = Math.atan2(camera.position.x - CAMERA.target.x, camera.position.z - CAMERA.target.z) - ROOM_YAW;
      const hide = Math.abs(THREE.MathUtils.euclideanModulo(turn + Math.PI, Math.PI * 2) - Math.PI) > ORBIT_TURN;
      if (hide !== rowHidden) {
        rowHidden = hide;
        setJarCount(wantedJars);
      }
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
    post.setSize(w, h);
    backgroundImage.setSize(w, h);
    const rw = Math.max(1, Math.round(w / 2));
    const rh = Math.max(1, Math.round(h / 2));
    roomImage.setSize(rw, rh);
    galleryJars.setImage(roomImage.texture, rw, rh);
    // The mirror image is blurred by the polish and the lens anyway.
    const mirrorScale = profile === "eco" ? 0.35 : 0.5;
    mirror.setSize(Math.round(w * mirrorScale), Math.round(h * mirrorScale));
    specimenImage.setSize(w, h);
    jar.optics.setSize(w, h);
    loop?.invalidate();
  }
  resize();
  window.addEventListener("resize", resize);

  function setQuality(name) {
    profile = qualityName(name);
    galleryJars.setQuality(jarQuality(profile));
    setJarCount(slotCount(profile));
    post.dispose();
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

  const stageSelect = document.querySelector("#stage");
  const wallSelect = document.querySelector("#wall");
  function chooseLook(next) {
    setLook(next);
    if (stageSelect) stageSelect.value = look.table;
    if (wallSelect) wallSelect.value = look.wall;
    try {
      localStorage.setItem(STAGE_KEY, look.table);
      localStorage.setItem(WALL_KEY, look.wall);
    } catch {}
  }
  if (stageSelect) {
    stageSelect.value = look.table;
    stageSelect.addEventListener("change", () => chooseLook({ table: stageSelect.value }));
  }
  if (wallSelect) {
    wallSelect.value = look.wall;
    wallSelect.addEventListener("change", () => chooseLook({ wall: wallSelect.value }));
  }
  const nextOf = (names, name) => names[(names.indexOf(name) + 1) % names.length];
  document.addEventListener("keydown", (event) => {
    if (event.repeat || event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.target.closest?.("button,select,input,textarea,a,[contenteditable]")) return;
    const key = event.key.toLowerCase();
    if (key === "t") chooseLook({ table: nextOf(STAGE_NAMES, look.table) });
    else if (key === "w") chooseLook({ wall: nextOf(WALL_NAMES, look.wall) });
  });

  const tune = installTunePanel({
    habitat,
    renderer,
    specimen,
    jarCount: () => galleryJars.shown.length,
    setJarCount,
    onChange() { loop?.invalidate(); },
  });
  window.specimenDebug.tune = tune;

  const focusPoint = new THREE.Vector3();
  let frame = 0;
  loop = createFrameLoop((dt) => {
    specimen.update(dt);
    galleryJars.advance(dt);
    // Autofocus on the specimen, as a photographer would.
    specimen.object.getWorldPosition(focusPoint);
    LENS.focus.value = camera.position.distanceTo(focusPoint) + LENS.focusShift.value;
    jar.optics.setSpecimen(focusPoint);
    jar.optics.advance(dt);
    post.post.uniforms.frame.value = frame++ % 997;

    jar.root.visible = false;
    if (look.table !== "blocks") {
      galleryJars.followSpecimen(specimen.object);
      gallery.table.visible = false;
      galleryJars.setPass("mirror");
      mirror.render(renderer, scene, camera);
      gallery.table.visible = true;
    }
    if (galleryJars.traced && galleryJars.shown.length) {
      galleryJars.setPass("room");
      renderer.setRenderTarget(roomImage);
      renderer.render(scene, camera);
    }
    galleryJars.setPass("scene");
    renderer.setRenderTarget(backgroundImage);
    renderer.render(scene, camera);
    jar.root.visible = true;
    if (specimen.renderImage) specimen.renderImage(renderer, specimenImage, camera, specimenScene);
    else {
      renderer.setRenderTarget(specimenImage);
      renderer.render(specimenScene, camera);
    }

    renderer.setRenderTarget(post.target);
    renderer.render(scene, camera);
    post.prepare(renderer);
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
