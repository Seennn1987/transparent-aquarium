import * as THREE from "three";

// The cleared-and-stained squid is seen by the light that comes through it: tissue soaked
// in alcian blue absorbs red and a little green, so whatever is behind the animal shows
// through tinted, and the tint deepens with the length of tissue the ray crosses. Blender
// renders that as volume absorption; here each surface multiplies what is already drawn
// by exp(-(1 - tint) * absorption * path). A second, additive pass adds what the tissue
// sends back toward the eye (see surfaceMaterial).
//
// Per vertex, blender/export_squid_gltf.py bakes the transmitted colour (RGB) with a
// density factor (A), and `_depth` in mantle lengths:
//   solid parts: the local radius. A ray through a round body crosses r·cosθ inside it
//     at each of its two surfaces, which is exact for a sphere and thickest face-on.
//   film parts: half the sheet's thickness. A sheet is crossed as t/cosθ, so the hollow
//     mantle's walls and the fins darken where the eye grazes them, as in the specimen.
// Absorption is in 1/m of the real animal (Blender's values), whatever size it is drawn.
const REAL_MANTLE_LENGTH = 0.1;
// sheen: strength of the wet reflection. glow: strength of the scattered lamp light.
export const SQUID_TISSUE = {
  Mantle: { mode: "film", absorption: 460, sheen: 1, glow: 0.45 },
  Fins: { mode: "film", absorption: 460, sheen: 1, glow: 0.5 },
  Funnel: { mode: "solid", absorption: 460, sheen: 1, glow: 0.45 },
  Head: { mode: "solid", absorption: 250, sheen: 1, glow: 0.45 },
  Arms: { mode: "solid", absorption: 550, sheen: 1, glow: 0.5 },
  Eyes: { mode: "solid", absorption: 110, sheen: 0.6, glow: 0.8 },
  BuccalMass: { mode: "solid", absorption: 260, sheen: 0, glow: 0.7 },
  Beak: { mode: "solid", absorption: 3000, sheen: 0.5, glow: 0 },
  DigestiveGland: { mode: "solid", absorption: 250, sheen: 0, glow: 0.7 },
  Caecum: { mode: "solid", absorption: 180, sheen: 0, glow: 0.7 },
  Gonad: { mode: "solid", absorption: 150, sheen: 0, glow: 0.7 },
  InkSac: { mode: "solid", absorption: 800, sheen: 0, glow: 0 },
  Gladius: { mode: "film", absorption: 400, sheen: 0, glow: 0.5 },
  Gills: { mode: "solid", absorption: 800, sheen: 0, glow: 0.6 },
  SuckerRings: { mode: "solid", absorption: 6000, sheen: 0.4, glow: 0.6 },
};
// Multiplying passes all go before anything added, so the order among parts never matters.
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
  vec3 transmit = exp(-(1. - vTint.rgb) * absorption * vTint.a * ${REAL_MANTLE_LENGTH} * path);
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

// What the squid gives back, added over the tinted water: the wet sheen, and the lamp's
// light scattered by the tissue. On the lightbox the tint alone draws the animal, but a
// blue-green filter over green planting barely shows, and in a dark tank a cleared animal
// is seen by that scattered light, brightest where the eye looks through the most tissue.
function surfaceMaterial({ mode, absorption, sheen, glow }) {
  const material = new THREE.MeshPhysicalMaterial({
    color: 0xffffff,
    roughness: 0.12,
    ior: 1.38,
    clearcoat: 0.6 * sheen,
    clearcoatRoughness: 0.04,
    envMapIntensity: sheen,
    specularIntensity: sheen,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  material.onBeforeCompile = (shader) => {
    shader.uniforms.absorption = { value: absorption };
    shader.uniforms.film = { value: mode === "film" ? 1 : 0 };
    shader.uniforms.glow = { value: glow };
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", `#include <common>
        attribute vec4 tint;attribute float tissueDepth;varying vec4 vTint;varying float vDepth;`)
      .replace("#include <begin_vertex>", `#include <begin_vertex>
        vTint = tint;vDepth = tissueDepth;`);
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", `#include <common>
        uniform float absorption;uniform float film;uniform float glow;varying vec4 vTint;varying float vDepth;`)
      .replace("#include <normal_fragment_maps>", `#include <normal_fragment_maps>
        {
          float c = abs(dot(normal, normalize(vViewPosition)));
          float path = mix(vDepth * c, vDepth / max(c, .12), film);
          // The share of light the crossed tissue takes out is the share it can scatter.
          vec3 taken = 1. - exp(-(1. - vTint.rgb) * absorption * vTint.a * ${REAL_MANTLE_LENGTH} * path);
          diffuseColor.rgb = vTint.rgb * glow * max(max(taken.r, taken.g), taken.b);
        }`)
      // Standard fog would add the fog colour on top of the scene; added light fades instead.
      .replace("#include <fog_fragment>", `#if defined(USE_FOG) && defined(FOG_EXP2)
          gl_FragColor.rgb *= exp(-fogDensity * fogDensity * vFogDepth * vFogDepth);
        #endif`);
  };
  return material;
}

/** Replaces each part's mesh with an absorbing pass and, where it has one, a sheen pass. */
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
    if (tissue.sheen > 0 || tissue.glow > 0) {
      const surface = new THREE.SkinnedMesh(geometry, surfaceMaterial(tissue));
      surface.name = `${part}Surface`;
      surface.renderOrder = SURFACE_ORDER;
      surface.frustumCulled = false;
      surface.position.copy(mesh.position);
      surface.quaternion.copy(mesh.quaternion);
      surface.scale.copy(mesh.scale);
      surface.bind(mesh.skeleton, mesh.bindMatrix);
      mesh.parent.add(surface);
    }
  }
}
