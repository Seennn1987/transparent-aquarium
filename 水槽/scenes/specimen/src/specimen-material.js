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
// only; the golden head and the organs keep their colours.
const SKY_WEIGHTS = new THREE.Vector3(1, 1.36, 0.4);
// 1 − the body tint baked by blender/generate_squid.py (BODY_TINT_STOPS).
const BODY_ABSORBANCE = [0.65, 0.115, 0.1];
const STAINED_PARTS = new Set(["Mantle", "Fins", "Funnel", "Head", "Arms"]);
// Measured against the reference: the arms take the stain more deeply than the tank's
// settings give them, the fins (a thin sheet, deepened face-on below) less.
const PART_STAIN = { Arms: 1.2, Fins: 0.23 };

// Targets, light let through (red/green/blue) on the white-lightbox reference: fin
// 0.58/0.86/0.98, arms 0.05–0.8 red with blue ≈ 1.5× green, mantle red 0–0.19.
export const specimenLook = {
  stain: { value: 0.9 },
  sky: { value: 1 },              // 0: the tank's blue-green, 1: the specimen's sky blue
  dorsal: { value: 0.45 },        // extra stain on the back
  gold: { value: 0.4 },           // how much of the tank's golden head survives the stain
  // Thin sheets (mantle, fins): how deep face-on, and how much more along the outline.
  face: { value: 1.8 },
  rim: { value: 0.7 },
  milk: { value: 0.16 },          // light scattered back by thick tissue
  milkColor: { value: new THREE.Color("#e6f3fa") },
  sheen: { value: 1 },
};

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
centroid varying vec4 vTint;
centroid varying float vDepth;
centroid varying float vDorsal;
centroid varying vec3 vViewNormal;
centroid varying vec3 vViewPosition;
void main() {
  #include <skinbase_vertex>
  #include <beginnormal_vertex>
  #include <skinnormal_vertex>
  #include <defaultnormal_vertex>
  #include <begin_vertex>
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
uniform float gold;
uniform float face;
uniform float rim;
centroid varying vec4 vTint;
centroid varying float vDepth;
centroid varying float vDorsal;
centroid varying vec3 vViewNormal;
centroid varying vec3 vViewPosition;
vec3 absorbance() {
  float c = abs(dot(normalize(vViewNormal), normalize(-vViewPosition)));
  float sheet = vDepth * (face + rim * (1. / max(c, .12) - 1.));
  float path = mix(vDepth * c, sheet, film);
  vec3 a = 1. - vTint.rgb;
  vec3 skyWeights = vec3(${SKY_WEIGHTS.toArray().map((v) => v.toFixed(3)).join(", ")});
  float blue = stained * smoothstep(.7, .85, vTint.b);
  a *= mix(vec3(1.), skyWeights, blue * sky);
  // Golden stained tissue (the head) is taken most of the way to the stain's own colour.
  vec3 stainColour = vec3(${BODY_ABSORBANCE.map((v) => v.toFixed(3)).join(", ")}) * skyWeights;
  a = mix(a, stainColour, (1. - blue) * stained * sky * (1. - gold));
  a *= 1. + dorsal * vDorsal * stained;
  return max(a * absorption * vTint.a * ${REAL_MANTLE_LENGTH.toFixed(3)} * stain * partStain * path, 0.);
}`;

const absorbFragment = `
${tissueAbsorbance}
void main() {
  gl_FragColor = vec4(exp(-absorbance()), 1.);
}`;

// Preserved tissue is not glass-clear: its thick parts send some light back milky, which
// also veils the organs behind them.
const milkFragment = `
${tissueAbsorbance}
uniform float milk;
uniform vec3 milkColor;
void main() {
  float density = dot(absorbance(), vec3(1. / 3.));
  gl_FragColor = vec4(milkColor * milk * (1. - exp(-density * .8)), 1.);
}`;

function tissueUniforms({ mode, absorption }, part) {
  return {
    absorption: { value: absorption },
    film: { value: mode === "film" ? 1 : 0 },
    stained: { value: STAINED_PARTS.has(part) ? 1 : 0 },
    partStain: { value: PART_STAIN[part] ?? 1 },
    stain: specimenLook.stain,
    sky: specimenLook.sky,
    dorsal: specimenLook.dorsal,
    gold: specimenLook.gold,
    face: specimenLook.face,
    rim: specimenLook.rim,
  };
}

function absorbMaterial(tissue, part) {
  return new THREE.ShaderMaterial({
    uniforms: tissueUniforms(tissue, part),
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

function milkMaterial(tissue, part) {
  return new THREE.ShaderMaterial({
    uniforms: {
      ...tissueUniforms(tissue, part),
      milk: specimenLook.milk,
      milkColor: specimenLook.milkColor,
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
function surfaceMaterial({ sheen }, envMap) {
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
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nuniform float uSheen;")
      .replace("#include <opaque_fragment>", "outgoingLight *= uSheen;\n#include <opaque_fragment>");
  };
  material.customProgramCacheKey = () => "specimen-squid-sheen";
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
  const missing = Object.keys(SQUID_TISSUE).filter((name) => !names.has(name));
  if (missing.length) throw new Error(`squid.glb に部位がありません: ${missing.join(", ")}`);
  for (const mesh of meshes) {
    const part = mesh.userData.squid_part;
    const tissue = SQUID_TISSUE[part];
    if (!tissue) throw new Error(`squid.glb の部位 ${part ?? mesh.name} に組織の設定がありません`);
    const geometry = mesh.geometry;
    const tint = geometry.getAttribute("color");
    const depth = geometry.getAttribute("_depth");
    if (!tint || tint.itemSize !== 4 || !depth)
      throw new Error(`squid.glb の部位 ${part} に色または厚みの焼き込みがありません`);
    geometry.setAttribute("tint", tint);
    geometry.setAttribute("tissueDepth", depth);
    geometry.deleteAttribute("color");
    geometry.deleteAttribute("_depth");
    mesh.material = absorbMaterial(tissue, part);
    mesh.renderOrder = ABSORB_ORDER;
    mesh.frustumCulled = false;
    if (STAINED_PARTS.has(part)) addPass(mesh, `${part}Milk`, milkMaterial(tissue, part), SURFACE_ORDER);
    if (tissue.sheen > 0) addPass(mesh, `${part}Surface`, surfaceMaterial(tissue, envMap), SURFACE_ORDER);
  }
}
