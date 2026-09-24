import * as THREE from "three";

// The cleared-and-stained squid is seen by the light that comes through it: tissue soaked
// in alcian blue absorbs red and a little green, so whatever is behind the animal shows
// through tinted, and the tint deepens with the length of tissue the ray crosses. Blender
// renders that as volume absorption; here each surface multiplies what is already drawn
// by exp(-(1 - tint) * absorption * path). Before that, the lightbox the specimen stood
// on is added behind it (see backlightMaterial); after it, the wet sheen.
//
// Per vertex, blender/export_squid_gltf.py bakes the transmitted colour (RGB) with a
// density factor (A), and `_depth` in mantle lengths:
//   solid parts: the local radius. A ray through a round body crosses r·cosθ inside it
//     at each of its two surfaces, which is exact for a sphere and thickest face-on.
//   film parts: half the sheet's thickness. A sheet is crossed as t/cosθ, so the hollow
//     mantle's walls and the fins darken where the eye grazes them, as in the specimen.
// Absorption is in 1/m of the real animal (Blender's values), whatever size it is drawn.
const REAL_MANTLE_LENGTH = 0.1;
// Blender shows the specimen through its Standard view, because a filmic view washes
// bright transmitted colour out toward white; the tank's ACES does the same, so the stain
// is deepened until the tank shows the colours of renders/blender_side_ref.png.
const ACES_STAIN = 2.5;
const ABSORBANCE_SCALE = REAL_MANTLE_LENGTH * ACES_STAIN;
// layers: for the parts that make the outline, how many of their surfaces a sight line
//   crosses, for judging how much tissue is there. The hollow mantle has a near and a far
//   wall, each with an outer and an inner face; a fin is a single sheet; a solid part is
//   entered once and left once. The other parts lie within that outline (the viscera in
//   the mantle, the eyes and mouth in the head, the suckers on the arms), which already
//   brings the lightbox behind them.
// sheen: strength of the wet reflection. Absorption values are generate_squid.py's.
export const SQUID_TISSUE = {
  Mantle: { mode: "film", absorption: 460, layers: 4, sheen: 1 },
  Fins: { mode: "film", absorption: 460, layers: 2, sheen: 1 },
  Funnel: { mode: "solid", absorption: 460, layers: 2, sheen: 1 },
  Head: { mode: "solid", absorption: 250, layers: 2, sheen: 1 },
  Arms: { mode: "solid", absorption: 550, layers: 2, sheen: 1 },
  Eyes: { mode: "solid", absorption: 110, sheen: 0.6 },
  BuccalMass: { mode: "solid", absorption: 260, sheen: 0 },
  Beak: { mode: "solid", absorption: 3000, sheen: 0.5 },
  DigestiveGland: { mode: "solid", absorption: 250, sheen: 0 },
  Caecum: { mode: "solid", absorption: 180, sheen: 0 },
  Gonad: { mode: "solid", absorption: 150, sheen: 0 },
  InkSac: { mode: "solid", absorption: 800, sheen: 0 },
  Gladius: { mode: "film", absorption: 400, sheen: 0 },
  Gills: { mode: "solid", absorption: 800, sheen: 0 },
  SuckerRings: { mode: "solid", absorption: 6000, sheen: 0.4 },
};
// Brightness of the lightbox brought behind the squid.
const LIGHTBOX = 1.5;
// The lightbox is added once per pixel, the absorbing passes then take out what the whole
// animal absorbs, and the sheen goes on top; within each stage the order never matters.
export const MARK_ORDER = 8;
export const BACKLIGHT_ORDER = 9;
export const ABSORB_ORDER = 10;
export const SURFACE_ORDER = 11;

const absorbVertex = `
#include <common>
#include <skinning_pars_vertex>
#include <fog_pars_vertex>
attribute vec4 tint;
attribute float tissueDepth;
varying vec4 vTint;
varying float vDepth;
varying vec3 vViewNormal;
varying vec3 vViewPosition;
void main() {
  #include <skinbase_vertex>
  #include <beginnormal_vertex>
  #include <skinnormal_vertex>
  #include <defaultnormal_vertex>
  #include <begin_vertex>
  #include <skinning_vertex>
  #include <project_vertex>
  #include <fog_vertex>
  vTint = tint;
  vDepth = tissueDepth;
  vViewNormal = transformedNormal;
  vViewPosition = mvPosition.xyz;
}`;

const absorbFragment = `
#include <common>
#include <fog_pars_fragment>
uniform float absorption;
uniform float film;
varying vec4 vTint;
varying float vDepth;
varying vec3 vViewNormal;
varying vec3 vViewPosition;
void main() {
  float c = abs(dot(normalize(vViewNormal), normalize(-vViewPosition)));
  // A film seen edge-on is limited by the part's own size, not by 1/cos.
  float path = mix(vDepth * c, vDepth / max(c, .12), film);
  vec3 transmit = exp(-(1. - vTint.rgb) * absorption * vTint.a * ${ABSORBANCE_SCALE} * path);
  #if defined(USE_FOG) && defined(FOG_EXP2)
    // Water between the squid and the eye hides it the same way it hides everything else.
    float fogFactor = 1. - exp(-fogDensity * fogDensity * vFogDepth * vFogDepth);
    transmit = mix(transmit, vec3(1.), fogFactor);
  #endif
  gl_FragColor = vec4(transmit, 1.);
}`;

function absorbMaterial({ mode, absorption }) {
  return new THREE.ShaderMaterial({
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, {
      absorption: { value: absorption },
      film: { value: mode === "film" ? 1 : 0 },
    }]),
    vertexShader: absorbVertex,
    fragmentShader: absorbFragment,
    fog: true,
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    blending: THREE.CustomBlending,
    blendEquation: THREE.AddEquation,
    blendSrc: THREE.ZeroFactor,
    blendDst: THREE.SrcColorFactor,
  });
}

// On the lightbox the specimen is drawn by the lightbox's light after the whole animal
// has absorbed it: red is taken again at every wall and organ it crosses, so the thick
// mantle is a deep blue-green and the viscera show through it in their own colours. Over
// dark green planting that light is missing, and a blue-green filter alone barely shows,
// so the lightbox is brought into the tank behind the squid: added here, then absorbed
// by the ordinary absorbing passes exactly as in Blender. It is unlit, as a lightbox is;
// the tank's overhead lamp would bleach the colour toward white.
//
// Every surface in a sight line would add it again, and the sum soon saturates to white,
// so it is added once per pixel: the mark pass clears the target's alpha under the squid,
// the first surface there adds its light and restores the alpha, and the rest add nothing.
// Nothing else in the scene reads the target's alpha. Where the tissue is thin and clear
// the lightbox fades, so the water behind the squid stays visible through it.
const passOnce = {
  transparent: true,
  depthWrite: false,
  side: THREE.DoubleSide,
  blending: THREE.CustomBlending,
  blendEquation: THREE.AddEquation,
  blendEquationAlpha: THREE.AddEquation,
};

function markMaterial() {
  return new THREE.ShaderMaterial({
    ...passOnce,
    vertexShader: absorbVertex,
    fragmentShader: "void main() { gl_FragColor = vec4(0.); }",
    blendSrc: THREE.ZeroFactor,
    blendDst: THREE.OneFactor,
    blendSrcAlpha: THREE.ZeroFactor,
    blendDstAlpha: THREE.ZeroFactor,
  });
}

const backlightFragment = `
#include <common>
#include <fog_pars_fragment>
uniform float absorption;
uniform float film;
uniform float layers;
varying vec4 vTint;
varying float vDepth;
varying vec3 vViewNormal;
varying vec3 vViewPosition;
void main() {
  float c = abs(dot(normalize(vViewNormal), normalize(-vViewPosition)));
  float path = layers * mix(vDepth * c, vDepth / max(c, .12), film);
  vec3 through = exp(-(1. - vTint.rgb) * absorption * vTint.a * ${ABSORBANCE_SCALE} * path);
  // The stain shows first in the red it takes, so thin arms keep their cyan.
  float density = 1. - min(min(through.r, through.g), through.b);
  float light = ${LIGHTBOX.toFixed(3)} * density;
  #if defined(USE_FOG) && defined(FOG_EXP2)
    light *= exp(-fogDensity * fogDensity * vFogDepth * vFogDepth);
  #endif
  gl_FragColor = vec4(vec3(light), 1.);
}`;

function backlightMaterial({ mode, absorption, layers }) {
  return new THREE.ShaderMaterial({
    ...passOnce,
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, {
      absorption: { value: absorption },
      film: { value: mode === "film" ? 1 : 0 },
      layers: { value: layers },
    }]),
    vertexShader: absorbVertex,
    fragmentShader: backlightFragment,
    fog: true,
    blendSrc: THREE.OneMinusDstAlphaFactor,
    blendDst: THREE.OneFactor,
    // Set, not summed: a float target does not clamp, and an alpha past 1 would subtract.
    blendSrcAlpha: THREE.OneFactor,
    blendDstAlpha: THREE.ZeroFactor,
  });
}

// The wet sheen, added last. As in Blender it is faint face-on and lies along the outline.
function surfaceMaterial({ sheen }) {
  const material = new THREE.MeshPhysicalMaterial({
    color: 0x000000,
    roughness: 0.12,
    ior: 1.38,
    envMapIntensity: 0.12 * sheen,
    specularIntensity: 0.12 * sheen,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  material.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader
      // Standard fog would add the fog colour on top of the scene; added light fades instead.
      .replace("#include <fog_fragment>", `#if defined(USE_FOG) && defined(FOG_EXP2)
          gl_FragColor.rgb *= exp(-fogDensity * fogDensity * vFogDepth * vFogDepth);
        #endif`);
  };
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

/** Draws each part in stages: the lightbox behind it, its absorption, then its sheen. */
export function applySquidTissue(model) {
  // Parts are found by their squid_part mark: the loader renames a mesh whose name a bone
  // already uses (the head is both).
  const meshes = [];
  model.traverse((object) => { if (object.isSkinnedMesh) meshes.push(object); });
  const names = new Set(meshes.map((mesh) => mesh.userData.squid_part));
  const missing = Object.keys(SQUID_TISSUE).filter((name) => !names.has(name));
  if (missing.length) throw new Error(`squid.glb has no part named ${missing.join(", ")}`);
  for (const mesh of meshes) {
    const part = mesh.userData.squid_part;
    const tissue = SQUID_TISSUE[part];
    if (!tissue) throw new Error(`squid.glb part ${part ?? mesh.name} has no tissue settings`);
    const geometry = mesh.geometry;
    const tint = geometry.getAttribute("color");
    const depth = geometry.getAttribute("_depth");
    if (!tint || tint.itemSize !== 4 || !depth)
      throw new Error(`squid.glb part ${part} is missing its baked tint or depth`);
    geometry.setAttribute("tint", tint);
    geometry.setAttribute("tissueDepth", depth);
    geometry.deleteAttribute("color");
    geometry.deleteAttribute("_depth");
    mesh.material = absorbMaterial(tissue);
    mesh.renderOrder = ABSORB_ORDER;
    mesh.frustumCulled = false;
    if (tissue.layers) {
      addPass(mesh, `${part}Mark`, markMaterial(), MARK_ORDER);
      addPass(mesh, `${part}Backlight`, backlightMaterial(tissue), BACKLIGHT_ORDER);
    }
    if (tissue.sheen > 0) addPass(mesh, `${part}Surface`, surfaceMaterial(tissue), SURFACE_ORDER);
  }
}
