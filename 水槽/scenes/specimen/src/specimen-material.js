import * as THREE from "three";
import { SQUID_TISSUE } from "../../riverscape/src/squid-material.js";

// In the white studio the backdrop is the lightbox: each tissue surface multiplies what is
// already drawn behind it by exp(-(1 - tint) * absorption * path), as Blender's volume
// absorption does, with no light added and no tank-specific stain boost.
//
// The squid is blended, so the liquid's transmission image never contains it. The lens the
// liquid column forms is applied to the squid directly instead: around the jar's axis, its
// vertices are spread sideways in view space, the way a filled cylinder magnifies what is
// inside it across its axis but not along it.
const REAL_MANTLE_LENGTH = 0.1;

export const specimenLook = {
  // Mantle red/green ≈ 0.56 in the studio, inside the 0.5–0.65 target (1.0 gives 0.46).
  stain: { value: 0.65 },
  lens: { value: 1.3 },
  jarAxis: { value: new THREE.Vector2(0, 0) },
  sheen: { value: 1 },
};

export const ABSORB_ORDER = 10;
export const SURFACE_ORDER = 11;

const LENS_UNIFORMS = "uniform float uLens;\nuniform vec2 uJarAxis;";
const LENS_VERTEX = `
  {
    vec4 lensWorld = modelMatrix * vec4(transformed, 1.0);
    vec4 lensAxis = viewMatrix * vec4(uJarAxis.x, lensWorld.y, uJarAxis.y, 1.0);
    mvPosition.x = lensAxis.x + (mvPosition.x - lensAxis.x) * uLens;
    gl_Position = projectionMatrix * mvPosition;
  }`;

const absorbVertex = `
#include <common>
#include <skinning_pars_vertex>
${LENS_UNIFORMS}
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
  ${LENS_VERTEX}
  vTint = tint;
  vDepth = tissueDepth;
  vViewNormal = transformedNormal;
  vViewPosition = mvPosition.xyz;
}`;

const absorbFragment = `
uniform float absorption;
uniform float film;
uniform float stain;
varying vec4 vTint;
varying float vDepth;
varying vec3 vViewNormal;
varying vec3 vViewPosition;
void main() {
  float c = abs(dot(normalize(vViewNormal), normalize(-vViewPosition)));
  float path = mix(vDepth * c, vDepth / max(c, .12), film);
  vec3 transmit = exp(-(1. - vTint.rgb) * absorption * vTint.a * ${REAL_MANTLE_LENGTH.toFixed(3)} * stain * path);
  // The canvas holds sRGB values, so the linear transmittance is encoded before it multiplies.
  gl_FragColor = vec4(pow(transmit, vec3(1. / 2.2)), 1.);
}`;

function absorbMaterial({ mode, absorption }) {
  return new THREE.ShaderMaterial({
    uniforms: {
      absorption: { value: absorption },
      film: { value: mode === "film" ? 1 : 0 },
      stain: specimenLook.stain,
      uLens: specimenLook.lens,
      uJarAxis: specimenLook.jarAxis,
    },
    vertexShader: absorbVertex,
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
    shader.uniforms.uLens = specimenLook.lens;
    shader.uniforms.uJarAxis = specimenLook.jarAxis;
    shader.uniforms.uSheen = specimenLook.sheen;
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", `#include <common>\n${LENS_UNIFORMS}`)
      .replace("#include <project_vertex>", `#include <project_vertex>\n${LENS_VERTEX}`);
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

/** Absorption plus sheen for every part; the white studio behind it supplies the light. */
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
    mesh.material = absorbMaterial(tissue);
    mesh.renderOrder = ABSORB_ORDER;
    mesh.frustumCulled = false;
    if (tissue.sheen > 0) addPass(mesh, `${part}Surface`, surfaceMaterial(tissue, envMap), SURFACE_ORDER);
  }
}
