import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { createJarOptics } from "./jar-optics.js";
import { profilePoints } from "./solid-glass.js";
import { GLASS_EDGE, GLASS_DIFFUSE, MENISCUS_DIFFUSE } from "./gallery.js";

export const JAR_PARTS = ["Jar_Glass", "Jar_Lid", "Jar_Liquid", "Jar_Meniscus"];

export const glassEdge = {
  darkness: { value: 0.55 },
  power: { value: 2.6 },
  tint: { value: GLASS_EDGE },
};

// The glass surfaces themselves: reflections of the softbox room, and a grey outline where
// the thin wall is seen edge-on. What is seen through the filled part is jar-optics.js.
const EDGE_UNIFORMS = "uniform float uEdgeDarkness;\nuniform float uEdgePower;\nuniform vec3 uEdgeTint;";
const EDGE_FACTOR =
  "pow(1.0 - abs(dot(normalize(normal), normalize(vViewPosition))), uEdgePower) * uEdgeDarkness";

// The thick glass of the lid and the foot is traced with its own dark bands; its surface
// only needs a trace of the outline.
export const thickGlassEdge = { ...glassEdge, darkness: { value: 0.12 } };

export function glassSurface(envMap, key, edge = glassEdge) {
  const material = new THREE.MeshPhysicalMaterial({
    color: "#f7fbf9",
    metalness: 0,
    roughness: 0.01,
    ior: 1.52,
    specularIntensity: 1,
    envMap,
    envMapIntensity: 1.6,
    transparent: true,
    opacity: 0.06,
    depthWrite: false,
    premultipliedAlpha: false,
    // Lies on the traced glass's own depth: drawn a hair nearer so it is not lost to it.
    polygonOffset: true,
    polygonOffsetFactor: -1,
    polygonOffsetUnits: -4,
  });
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uEdgeDarkness = edge.darkness;
    shader.uniforms.uEdgePower = edge.power;
    shader.uniforms.uEdgeTint = edge.tint;
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", `#include <common>\n${EDGE_UNIFORMS}`)
      .replace(
        "#include <opaque_fragment>",
        `{
          float edge = ${EDGE_FACTOR};
          outgoingLight = mix(outgoingLight, uEdgeTint * 0.9, edge);
          diffuseColor.a = mix(diffuseColor.a, 1.0, edge * 0.85);
        }
        #include <opaque_fragment>`,
      );
  };
  material.customProgramCacheKey = () => key;
  // Shared, so the surfaces follow the room's walls.
  material.color = GLASS_DIFFUSE;
  return material;
}

// The meniscus is the one part of the surface seen from above at a steep angle: a bright
// line of reflected room along the wall.
export function meniscusMaterial(envMap) {
  const material = new THREE.MeshPhysicalMaterial({
    roughness: 0.05,
    transparent: true,
    opacity: 0.45,
    depthWrite: false,
    envMap,
    envMapIntensity: 1.4,
    side: THREE.DoubleSide,
  });
  material.color = MENISCUS_DIFFUSE;
  return material;
}

// The collection's paper label, written by hand and yellowed with the years.
export const labelLook = { opacity: { value: 1 } };
// Where it is stuck on: to the left of the default view, low down, clear of most of the squid.
// The chameleon hangs head down at the left of the jar, so its label is mirrored about the
// default view (gallery.js ROOM_YAW 0.274 rad) to the right, below the hind feet.
const LABEL = { angle: 1.9, arc: 0.72, height: 0.36, lift: 0.3 };
const LABEL_AT = { squid: LABEL, chameleon: { ...LABEL, angle: Math.PI / 2 - (2 * 0.274 - (Math.PI / 2 - LABEL.angle)) } };

function labelTexture(specimen = "squid") {
  const canvas = document.createElement("canvas");
  canvas.width = 1024;
  canvas.height = 512;
  const g = canvas.getContext("2d");
  const paper = g.createRadialGradient(512, 256, 80, 512, 256, 620);
  paper.addColorStop(0, "#efe6c8");
  paper.addColorStop(1, "#d9c595");
  g.fillStyle = paper;
  g.fillRect(0, 0, 1024, 512);
  // Foxing: small brown spots where the paper has aged.
  let seed = 7;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 70; i++) {
    const r = 2 + rnd() * 9;
    g.fillStyle = `rgba(150, 105, 50, ${0.04 + rnd() * 0.1})`;
    g.beginPath();
    g.arc(rnd() * 1024, rnd() * 512, r, 0, Math.PI * 2);
    g.fill();
  }
  g.strokeStyle = "rgba(60, 45, 40, 0.75)";
  g.lineWidth = 5;
  g.strokeRect(26, 26, 972, 460);
  g.lineWidth = 2;
  g.strokeRect(40, 40, 944, 432);

  // Ink that has bled a little into the paper: a soft wide pass, then the stroke itself.
  const write = (text, x, y, font, size, style = "") => {
    g.font = `${style} ${size}px ${font}`;
    g.fillStyle = "rgba(40, 32, 70, 0.25)";
    g.shadowColor = "rgba(40, 32, 70, 0.5)";
    g.shadowBlur = 4;
    g.fillText(text, x + 1, y + 1);
    g.shadowBlur = 0;
    g.fillStyle = "rgba(35, 28, 62, 0.88)";
    g.fillText(text, x, y);
  };
  const hand = `"Bradley Hand", "Noteworthy", "Segoe Print", cursive`;
  const handJa = `"Klee", "Klee One", "Hiragino Mincho ProN", serif`;
  const underline = () => {
    g.strokeStyle = "rgba(35, 28, 62, 0.7)";
    g.lineWidth = 3;
    g.beginPath();
    g.moveTo(90, 228);
    g.bezierCurveTo(300, 236, 520, 222, 900, 232);
    g.stroke();
  };
  if (specimen === "chameleon") {
    // Only what is known of this animal: the species of the CT (MorphoSource, see
    // docs/references/chameleon/SOURCES.md) and the two stains the model draws (chameleon-stain.js).
    // No collection number, date or place is written, since none is known.
    write("Chamaeleo calyptratus", 90, 196, hand, 80, "italic");
    underline();
    write("エボシカメレオン", 90, 318, handJa, 56);
    write("透明骨格標本  Alizarin red / Alcian blue", 90, 404, `${hand}, ${handJa}`, 42);
  } else {
    write("No. 0417", 760, 108, hand, 44);
    write("Loligo sp.", 90, 200, hand, 96, "italic");
    write("ヤリイカ属", 610, 196, handJa, 56);
    underline();
    write("採集  1987 . 6 . 12   三崎", 90, 318, handJa, 52);
    write("透明骨格標本  Alcian blue / KOH", 90, 404, `${hand}, ${handJa}`, 46);
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 8;
  return texture;
}

function createLabel(dims, specimen) {
  const at = LABEL_AT[specimen] ?? LABEL;
  const theta = Math.PI / 2 - at.angle;
  const geometry = new THREE.CylinderGeometry(
    dims.bodyRadius * 1.004, dims.bodyRadius * 1.004, at.height, 48, 1, true,
    theta - at.arc / 2, at.arc,
  );
  const material = new THREE.MeshStandardMaterial({
    map: labelTexture(specimen),
    roughness: 0.85,
    metalness: 0,
    transparent: true,
    opacity: labelLook.opacity.value,
  });
  const label = new THREE.Mesh(geometry, material);
  label.name = "specimen-label";
  label.position.y = dims.floorHeight + at.lift;
  label.onBeforeRender = () => {
    material.opacity = labelLook.opacity.value;
    material.depthWrite = material.opacity > 0.5;
  };
  return label;
}

function readDims(glass) {
  const extras = glass.userData;
  const dims = {
    bodyRadius: extras.jar_body_radius,
    innerRadius: extras.jar_inner_radius,
    footRadius: extras.jar_foot_radius,
    rimHeight: extras.jar_rim_height,
    floorHeight: extras.jar_floor_height,
    liquidTop: extras.jar_liquid_top,
    knobCentre: extras.jar_knob_centre,
    knobRadius: extras.jar_knob_radius,
  };
  const unknown = Object.entries(dims).filter(([, value]) => !Number.isFinite(value)).map(([key]) => key);
  if (!Array.isArray(extras.jar_lid_profile)) unknown.push("jar_lid_profile");
  if (!Array.isArray(extras.jar_base_profile)) unknown.push("jar_base_profile");
  if (unknown.length) throw new Error(`jar.glb に寸法がありません: ${unknown.join(", ")}（generate_specimen_jar.py で書き出し直してください）`);
  // 蓋の無い器（dish.glb、generate_specimen_dish.py）: 屈折の計算（jar-optics.js）は蓋の断面を使うので、口より上に小さな仮の円盤を渡し、
  // その面は描かない（createJar が隠す）
  dims.hasLid = extras.jar_lid_profile.length > 0;
  if (!dims.hasLid) extras.jar_lid_profile = [0, dims.rimHeight + 1, 0.01, dims.rimHeight + 1, 0.01, dims.rimHeight + 1.01, 0, dims.rimHeight + 1.01];
  dims.lidProfile = profilePoints(extras.jar_lid_profile);
  dims.baseProfile = profilePoints(extras.jar_base_profile);
  return dims;
}

/** `specimen`: whose label the jar carries ("squid" or "chameleon"). `vessel`: "jar"（イカ・カメレオンの瓶）または "dish"（シュモクザメの蓋の無い低い器、C1） */
export async function createJar({ envMap, lens, specimen = "squid", vessel = "jar" }) {
  const gltf = await new GLTFLoader().loadAsync(new URL(vessel === "dish" ? "../assets/dish.glb" : "../assets/jar.glb", import.meta.url).href);
  const root = gltf.scene;
  root.name = "specimen-jar";
  const parts = {};
  root.traverse((object) => {
    const name = object.userData?.jar_part;
    if (object.isMesh && name) parts[name] = object;
  });
  const missing = JAR_PARTS.filter((name) => !parts[name] && !(vessel === "dish" && name === "Jar_Lid"));
  if (missing.length) throw new Error(`jar.glb に部位がありません: ${missing.join(", ")}`);
  const dims = readDims(parts.Jar_Glass);

  const liquidBounds = new THREE.Box3().setFromObject(parts.Jar_Liquid);
  // The liquid is traced by the optics column; its mesh only gives the bounds.
  parts.Jar_Liquid.visible = false;
  parts.Jar_Glass.material = glassSurface(envMap, "specimen-glass-wall");
  if (parts.Jar_Lid) parts.Jar_Lid.material = glassSurface(envMap, "specimen-glass-lid", thickGlassEdge);
  parts.Jar_Meniscus.material = meniscusMaterial(envMap);

  // Blended layers over the opaque optics: the meniscus, then the glass surfaces.
  parts.Jar_Meniscus.renderOrder = 19;
  parts.Jar_Glass.renderOrder = 20;
  if (parts.Jar_Lid) parts.Jar_Lid.renderOrder = 21;
  for (const mesh of Object.values(parts)) {
    mesh.castShadow = false;
    mesh.receiveShadow = false;
  }

  const optics = createJarOptics({ dims, lens });
  for (const mesh of optics.meshes) root.add(mesh);
  if (!dims.hasLid) for (const mesh of optics.meshes) if (mesh.name === "jar-optics-lid") mesh.visible = false;   // 仮の蓋は描かない
  const label = createLabel(dims, specimen);
  root.add(label);

  // Blended glass leaves no depth, so the depth of field would blur the lid and the foot as if
  // they were the far wall. Drawn last and depth only, they keep their distance.
  const depthOnly = new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: true, transparent: true });
  for (const name of ["Jar_Glass", "Jar_Lid"]) {
    const source = parts[name];
    if (!source) continue;
    const proxy = new THREE.Mesh(source.geometry, depthOnly);
    proxy.name = `${name}-depth`;
    proxy.renderOrder = 100;
    source.add(proxy);
  }

  const bounds = new THREE.Box3().setFromObject(root);
  return { root, parts, bounds, liquidBounds, dims, optics, label };
}
