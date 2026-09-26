import * as THREE from "three";
import { SQUID_TISSUE } from "../../riverscape/src/squid-material.js";

// In the white studio the backdrop is the lightbox: each tissue surface multiplies what is
// already drawn behind it by exp(-(1 - tint) * absorption * path), as Blender's volume
// absorption does, with no light added and no tank-specific stain boost.
//
// It is drawn on its own over white, so the image holds how much light each point lets
// through (plus its sheen and milkiness); jar-optics.js looks it up where the bent rays
// cross it.
const REAL_MANTLE_LENGTH = 0.1;

// The tank's squid is baked blue-green. Measured on the reference photos (white lightbox),
// the stained tissue absorbs red : green : blue ≈ 1 : 0.24 : 0.08, a sky blue; the baked
// tint absorbs 1 : 0.18 : 0.15. These weights turn one into the other on the stained body
// only; the organs keep their colours.
const SKY_WEIGHTS = new THREE.Vector3(1, 1.36, 0.4);
const STAINED_PARTS = new Set(["Mantle", "Fins", "Funnel", "Head", "Arms"]);
// Measured against the reference: the arms take the stain more deeply than the tank's
// settings give them, the fins (a thin sheet, deepened face-on below) less. The head's skin
// is the same muscle as the arms it grows into.
const PART_STAIN = { Arms: 1.2, Head: 1.2, Fins: 0.23 };
// The specimen squid (blender/generate_specimen_squid.py) replaces the tank's solid head
// with a muscular shell holding the anatomy that shows through it: eye (wall, cornea,
// iris, retina, dissolved lens), cartilage, brain, optic lobes and nerves, statocysts,
// mouth parts and oesophagus.
const SPECIMEN_TISSUE = {
  ...SQUID_TISSUE,
  Head: { mode: "film", absorption: 550, sheen: 1 },
  Eyes: { mode: "film", absorption: 700, sheen: 0.05 },
  Cornea: { mode: "film", absorption: 150, sheen: 0.35 },
  Iris: { mode: "film", absorption: 1500, sheen: 0 },
  Retina: { mode: "film", absorption: 280, sheen: 0 },
  Lens: { mode: "solid", absorption: 600, sheen: 0 },
  OpticNerves: { mode: "solid", absorption: 900, sheen: 0 },
  OpticLobes: { mode: "solid", absorption: 900, sheen: 0 },
  Brain: { mode: "solid", absorption: 900, sheen: 0 },
  Statocysts: { mode: "solid", absorption: 600, sheen: 0 },
  Cartilage: { mode: "film", absorption: 450, sheen: 0 },
  OrbitCartilage: { mode: "film", absorption: 450, sheen: 0 },
  BuccalMass: { mode: "solid", absorption: 180, sheen: 0 },
  Beak: { mode: "film", absorption: 1300, sheen: 0.08 },
  Radula: { mode: "film", absorption: 1800, sheen: 0 },
  Esophagus: { mode: "solid", absorption: 1400, sheen: 0 },
  Rachis: { mode: "film", absorption: 260, sheen: 0 },
  InkSac: { mode: "solid", absorption: 220, sheen: 0 },
  DigestiveGland: { mode: "solid", absorption: 210, sheen: 0 },
  Gladius: { mode: "film", absorption: 180, sheen: 0 },
};
// What each part is made of decides how it takes the stain (alcian blue colours cartilage
// deepest, muscle sky blue; nerve stays pale and cloudy; chitin keeps its amber).
const TISSUE_CLASS = {
  Mantle: "muscle", Fins: "muscle", Funnel: "muscle", Head: "muscle", Arms: "muscle",
  Cartilage: "cartilage", OrbitCartilage: "cartilage", Iris: "cartilage",
  OpticNerves: "nerve", OpticLobes: "nerve", Brain: "nerve",
  Beak: "chitin", Radula: "chitin", SuckerRings: "chitin",
  Lens: "lens",
};
// Screening pigment left after bleaching.
const PIGMENTED = new Set(["Retina", "InkSac"]);
// Parts that scatter light back milky instead of only absorbing it.
const HAZY = new Set(["OpticNerves", "OpticLobes", "Brain", "Statocysts"]);
// Where the chromatophores' remnants show: on the back, the head and the arms.
const PART_SPOTS = { Mantle: 1, Head: 1, Arms: 0.8, Fins: 0.4, Funnel: 0.5 };
// Spacing of the remnant dots in mantle lengths (3 mm on a 10 cm squid).
const SPOT_CELL = 0.03;

// Targets, light let through (red/green/blue) on the white-lightbox reference: fin
// 0.58/0.86/0.98, arms 0.05–0.8 red with blue ≈ 1.5× green, mantle red 0–0.19.
export const specimenLook = {
  stain: { value: 0.9 },
  sky: { value: 1 },              // 0: the tank's blue-green, 1: the specimen's sky blue
  dorsal: { value: 0.45 },        // extra stain on the back
  // Thin sheets (mantle, fins): how deep face-on, and how much more along the outline.
  face: { value: 1.8 },
  rim: { value: 0.7 },
  finRim: { value: 1.8 },         // extra stain toward the fin's outer edge
  spots: { value: 0.5 },          // chromatophore remnants
  milk: { value: 0.16 },          // light scattered back by thick tissue
  milkColor: { value: new THREE.Color("#e6f3fa") },
  sheen: { value: 1 },
  wrinkles: { value: 0.6 },       // unevenness of the sheen
  // How each kind of tissue takes the stain (1 as baked).
  muscle: { value: 1 },
  cartilage: { value: 1 },
  nerve: { value: 1 },
  nerveHaze: { value: 0.05 },     // milky white of brain, optic lobes and nerves
  chitin: { value: 1 },
  pigment: { value: 0.15 },       // 0: bleached, 1: the retina and ink as dark as in life
  lens: { value: 0 },             // the lens dissolves in clearing; >0 leaves some of it
  // Sizes, 1 as baked. Each part grows about its own centre, the eye's parts about the eye.
  headSize: { value: 1 },         // 頭の左右・上下の大きさ
  eyeSize: { value: 1 },
  eyePop: { value: 0 },           // 目の飛び出し。正で外へ、負で頭の中へ
  eyeAspect: { value: 1 },        // 目の前後の長さ
  irisSize: { value: 1 },
  retinaDepth: { value: 1 },      // <1 で網膜が眼の奥へ下がる
  lobeSize: { value: 1 },
  buccalSize: { value: 1 },
  beakSize: { value: 1 },
};
const CLASS_GAIN = {
  muscle: specimenLook.muscle,
  cartilage: specimenLook.cartilage,
  nerve: specimenLook.nerve,
  chitin: specimenLook.chitin,
  lens: specimenLook.lens,
};

// The eye and what moves with it; left and right are fitted as mirror images.
const EYE_GROUP = new Set(["Eyes", "Cornea", "Iris", "Retina", "Lens", "OpticNerves", "OrbitCartilage"]);
const MIRRORED = new Set([...EYE_GROUP, "OpticLobes", "Statocysts"]);
const SIZED_AT_EYE = new Set(["Eyes", "Cornea", "Retina", "OpticNerves", "OrbitCartilage"]);
const HEAD_GROUP = new Set([...MIRRORED, "Brain", "Cartilage", "BuccalMass", "Beak", "Radula", "Esophagus"]);
const PART_SIZE = {
  Iris: specimenLook.irisSize,
  Retina: specimenLook.retinaDepth,
  OpticLobes: specimenLook.lobeSize,
  BuccalMass: specimenLook.buccalSize,
  Beak: specimenLook.beakSize,
};

// Rest-pose model axes: +X the mantle tip, −X the arms, +Y the back, ±Z left and right.
const fitVertex = `
uniform float uHeadSize;
uniform float uEyeSize;
uniform float uEyePop;
uniform float uEyeAspect;
uniform float uPartSize;
uniform vec3 uEyeCenter;
uniform vec3 uFitCenter;
uniform float uFitMirror;
uniform float uFitEye;
uniform float uFitHead;
vec3 specimenFit(vec3 p) {
  float side = uFitMirror > .5 && p.z < 0. ? -1. : 1.;
  vec3 c = uFitCenter * vec3(1., 1., side);
  p = c + (p - c) * uPartSize;
  if (uFitEye > .5) {
    vec3 e = uEyeCenter * vec3(1., 1., side);
    vec3 d = (p - e) * uEyeSize;
    d.x *= uEyeAspect;
    p = e + d + vec3(0., 0., side * uEyePop);
  }
  if (uFitHead > 1.5) p.yz += c.yz * (uHeadSize - 1.);
  else if (uFitHead > .5) p.yz *= uHeadSize;
  return p;
}
`;

function centreOf(geometry, mirrored) {
  const position = geometry.getAttribute("position");
  const box = new THREE.Box3();
  const v = new THREE.Vector3();
  for (let i = 0; i < position.count; i++) {
    v.fromBufferAttribute(position, i);
    if (!mirrored || v.z >= 0) box.expandByPoint(v);
  }
  return box.getCenter(new THREE.Vector3());
}

function fitUniforms(part, fit) {
  return {
    uHeadSize: specimenLook.headSize,
    uEyeSize: specimenLook.eyeSize,
    uEyePop: specimenLook.eyePop,
    uEyeAspect: specimenLook.eyeAspect,
    uPartSize: PART_SIZE[part] ?? { value: 1 },
    uEyeCenter: { value: fit.eye },
    uFitCenter: { value: SIZED_AT_EYE.has(part) ? fit.eye : fit.centres[part] },
    uFitMirror: { value: MIRRORED.has(part) ? 1 : 0 },
    uFitEye: { value: EYE_GROUP.has(part) ? 1 : 0 },
    uFitHead: { value: part === "Head" ? 1 : HEAD_GROUP.has(part) ? 2 : 0 },
  };
}

export const ABSORB_ORDER = 10;
export const SURFACE_ORDER = 11;

// With multisampling a pixel centre can fall outside a thin triangle (arm tips, fin edges)
// and plain varyings are extrapolated past their range: a negative absorbance multiplies
// the light by thousands, a normal through zero turns NaN, and the arms flash white.
// Every tissue varying is sampled inside its triangle (centroid).
function centroidVaryings(shader) {
  for (const stage of ["vertex", "fragment"]) {
    const key = `${stage}Shader`;
    shader[key] = shader[key]
      .replace(`#include <normal_pars_${stage}>`, THREE.ShaderChunk[`normal_pars_${stage}`].replaceAll("varying", "centroid varying"))
      .replaceAll("\nvarying vec3 vViewPosition;", "\ncentroid varying vec3 vViewPosition;");
  }
}

const tissueVertex = `
#include <common>
#include <skinning_pars_vertex>
attribute vec4 tint;
attribute float tissueDepth;
attribute float tissueRim;
centroid varying vec4 vTint;
centroid varying float vDepth;
centroid varying float vDorsal;
centroid varying float vRim;
centroid varying vec3 vRest;
centroid varying vec3 vViewNormal;
centroid varying vec3 vViewPosition;
${fitVertex}
void main() {
  vec3 fitted = specimenFit(position);
  // The pattern is fixed to the body at rest, so it moves with the tissue.
  vRest = fitted;
  vRim = tissueRim;
  #include <skinbase_vertex>
  #include <beginnormal_vertex>
  #include <skinnormal_vertex>
  #include <defaultnormal_vertex>
  #include <begin_vertex>
  transformed = fitted;
  #include <skinning_vertex>
  #include <project_vertex>
  vTint = tint;
  vDepth = tissueDepth;
  // The model's +Y is the animal's back.
  vDorsal = smoothstep(-.2, .8, normalize(objectNormal).y);
  vViewNormal = transformedNormal;
  vViewPosition = mvPosition.xyz;
}`;

// Absorbance along the view ray through this surface, shared by both tissue passes.
const tissueAbsorbance = `
uniform float absorption;
uniform float film;
uniform float stained;
uniform float partStain;
uniform float stain;
uniform float sky;
uniform float dorsal;
uniform float classGain;
uniform float pigment;
uniform float face;
uniform float rim;
uniform float finRim;
uniform float spots;
uniform float spotted;
centroid varying vec4 vTint;
centroid varying float vDepth;
centroid varying float vDorsal;
centroid varying float vRim;
centroid varying vec3 vRest;
centroid varying vec3 vViewNormal;
centroid varying vec3 vViewPosition;
vec3 hash3(vec3 p) {
  p = fract(p * vec3(.1031, .1030, .0973));
  p += dot(p, p.yxz + 33.33);
  return fract((p.xxy + p.yxx) * p.zyx);
}
// Scattered dots of uneven size and strength, about half the cells holding one.
float spotField(vec3 p) {
  vec3 q = p / ${SPOT_CELL.toFixed(3)};
  vec3 i = floor(q), f = fract(q);
  float s = 0.;
  for (int x = -1; x <= 1; x++)
    for (int y = -1; y <= 1; y++)
      for (int z = -1; z <= 1; z++) {
        vec3 o = vec3(x, y, z);
        vec3 h = hash3(i + o + 71.);
        if (h.z > .5) continue;
        float r = .16 + .2 * fract(h.x * 7.13);
        s = max(s, smoothstep(r, r * .35, length(o + h - f)) * (.4 + h.y));
      }
  return s;
}
float tissuePath() {
  float c = abs(dot(normalize(vViewNormal), normalize(-vViewPosition)));
  float sheet = vDepth * (face + rim * (1. / max(c, .12) - 1.));
  return mix(vDepth * c, sheet, film);
}
vec3 absorbance() {
  vec3 a = 1. - vTint.rgb;
  // Dark pigment absorbs all colours almost alike.
  a = mix(a, vec3(.78, .82, .86), pigment);
  vec3 skyWeights = vec3(${SKY_WEIGHTS.toArray().map((v) => v.toFixed(3)).join(", ")});
  float blue = stained * smoothstep(.7, .85, vTint.b);
  a *= mix(vec3(1.), skyWeights, blue * sky);
  a *= (1. + dorsal * vDorsal * stained) * (1. + finRim * vRim);
  a = max(a * absorption * vTint.a * ${REAL_MANTLE_LENGTH.toFixed(3)} * stain * partStain * classGain * tissuePath(), 0.);
  // The remnants are brownish: they take more blue than red.
  float dots = spotted * mix(.25, 1., vDorsal) * vTint.a * spotField(vRest);
  return a + dots * spots * vec3(.35, .6, .9);
}`;

const absorbFragment = `
${tissueAbsorbance}
void main() {
  // At the arm crown the head's shell fades out as the arm roots fade in. What is faded to
  // nothing is not drawn; cutting off any higher leaves a visible edge.
  if (vTint.a < .02) discard;
  gl_FragColor = vec4(exp(-absorbance()), 1.);
}`;

// Preserved tissue is not glass-clear: its thick parts send some light back milky, which
// also veils the organs behind them.
const milkFragment = `
${tissueAbsorbance}
uniform float milk;
uniform vec3 milkColor;
uniform float milky;
uniform float haze;
void main() {
  if (vTint.a < .02) discard;
  float density = dot(absorbance(), vec3(1. / 3.));
  vec3 cloud = vec3(.96, .94, .86) * haze * (1. - exp(-tissuePath() * 120.));
  gl_FragColor = vec4(milkColor * milk * milky * (1. - exp(-density * .8)) + cloud, 1.);
}`;

function tissueUniforms({ mode, absorption }, part, fit) {
  return {
    absorption: { value: absorption },
    film: { value: mode === "film" ? 1 : 0 },
    stained: { value: STAINED_PARTS.has(part) ? 1 : 0 },
    partStain: { value: PART_STAIN[part] ?? 1 },
    classGain: CLASS_GAIN[TISSUE_CLASS[part]] ?? { value: 1 },
    pigment: PIGMENTED.has(part) ? specimenLook.pigment : { value: 0 },
    stain: specimenLook.stain,
    sky: specimenLook.sky,
    dorsal: specimenLook.dorsal,
    face: specimenLook.face,
    rim: specimenLook.rim,
    finRim: specimenLook.finRim,
    spots: specimenLook.spots,
    spotted: { value: PART_SPOTS[part] ?? 0 },
    ...fitUniforms(part, fit),
  };
}

function absorbMaterial(tissue, part, fit) {
  return new THREE.ShaderMaterial({
    uniforms: tissueUniforms(tissue, part, fit),
    vertexShader: tissueVertex,
    fragmentShader: absorbFragment,
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    blending: THREE.CustomBlending,
    blendEquation: THREE.AddEquation,
    blendSrc: THREE.ZeroFactor,
    blendDst: THREE.SrcColorFactor,
  });
}

function milkMaterial(tissue, part, fit) {
  return new THREE.ShaderMaterial({
    uniforms: {
      ...tissueUniforms(tissue, part, fit),
      milk: specimenLook.milk,
      milkColor: specimenLook.milkColor,
      milky: { value: STAINED_PARTS.has(part) ? 1 : 0 },
      haze: HAZY.has(part) ? specimenLook.nerveHaze : { value: 0 },
    },
    vertexShader: tissueVertex,
    fragmentShader: milkFragment,
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending,
  });
}

// The wet sheen of a preserved specimen: faint face-on, stronger along the outline.
function surfaceMaterial({ sheen }, envMap, part, fit) {
  const material = new THREE.MeshPhysicalMaterial({
    color: 0x000000,
    roughness: 0.1,
    ior: 1.38,
    envMap,
    envMapIntensity: 0.35 * sheen,
    specularIntensity: 0.3 * sheen,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  material.onBeforeCompile = (shader) => {
    centroidVaryings(shader);
    shader.uniforms.uSheen = specimenLook.sheen;
    shader.uniforms.uWrinkles = specimenLook.wrinkles;
    Object.assign(shader.uniforms, fitUniforms(part, fit));
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", `#include <common>\nattribute vec4 tint;\ncentroid varying vec3 vRest;\ncentroid varying float vFade;\n${fitVertex}`)
      .replace("#include <begin_vertex>", "#include <begin_vertex>\ntransformed = specimenFit(position);\nvRest = transformed;\nvFade = tint.a;");
    // Fine creases of the preserved skin break the highlight into uneven streaks.
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nuniform float uSheen;\nuniform float uWrinkles;\ncentroid varying vec3 vRest;\ncentroid varying float vFade;")
      .replace("#include <opaque_fragment>", `
if (vFade < .02) discard;
float crease = sin(dot(vRest, vec3(160., 41., 67.)) + 3. * sin(vRest.x * 55. + vRest.z * 38.));
outgoingLight *= uSheen * vFade * (1. + uWrinkles * crease * .5);
#include <opaque_fragment>`);
  };
  material.customProgramCacheKey = () => "specimen-squid-sheen-fit";
  return material;
}

function addPass(mesh, name, material, renderOrder) {
  const pass = new THREE.SkinnedMesh(mesh.geometry, material);
  pass.name = name;
  pass.renderOrder = renderOrder;
  pass.frustumCulled = false;
  pass.position.copy(mesh.position);
  pass.quaternion.copy(mesh.quaternion);
  pass.scale.copy(mesh.scale);
  pass.bind(mesh.skeleton, mesh.bindMatrix);
  mesh.parent.add(pass);
}

/** Absorption, milkiness and sheen for every part; the white studio supplies the light. */
export function applySpecimenTissue(model, { envMap }) {
  const meshes = [];
  model.traverse((object) => { if (object.isSkinnedMesh) meshes.push(object); });
  const names = new Set(meshes.map((mesh) => mesh.userData.squid_part));
  const missing = Object.keys(SPECIMEN_TISSUE).filter((name) => !names.has(name));
  if (missing.length) throw new Error(`specimen_squid.glb に部位がありません: ${missing.join(", ")}`);
  const centres = {};
  for (const mesh of meshes) centres[mesh.userData.squid_part] = centreOf(mesh.geometry, MIRRORED.has(mesh.userData.squid_part));
  const fit = { eye: centres.Eyes, centres };
  for (const mesh of meshes) {
    const part = mesh.userData.squid_part;
    const tissue = SPECIMEN_TISSUE[part];
    if (!tissue) throw new Error(`specimen_squid.glb の部位 ${part ?? mesh.name} に組織の設定がありません`);
    const geometry = mesh.geometry;
    const tint = geometry.getAttribute("color");
    const depth = geometry.getAttribute("_depth");
    const rim = geometry.getAttribute("_rim");
    if (!tint || tint.itemSize !== 4 || !depth || !rim)
      throw new Error(`specimen_squid.glb の部位 ${part} に色・厚み・縁の焼き込みがありません`);
    geometry.setAttribute("tint", tint);
    geometry.setAttribute("tissueDepth", depth);
    geometry.setAttribute("tissueRim", rim);
    geometry.deleteAttribute("color");
    geometry.deleteAttribute("_depth");
    geometry.deleteAttribute("_rim");
    mesh.material = absorbMaterial(tissue, part, fit);
    mesh.renderOrder = ABSORB_ORDER;
    mesh.frustumCulled = false;
    // The arms and the head they grow from are one tissue; neither is veiled.
    const milky = STAINED_PARTS.has(part) && part !== "Arms" && part !== "Head";
    if (milky || HAZY.has(part)) addPass(mesh, `${part}Milk`, milkMaterial(tissue, part, fit), SURFACE_ORDER);
    if (tissue.sheen > 0) addPass(mesh, `${part}Surface`, surfaceMaterial(tissue, envMap, part, fit), SURFACE_ORDER);
  }
}
