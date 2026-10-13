import * as THREE from "three";
import {
  LIGHTBOX, BONE_SPECTRUM, BONE_T0, BONE_GAIN, CARTILAGE_SPECTRUM, CARTILAGE_GAIN,
  SKIN_SPECTRUM, SKIN_GAIN, VISCERA_SPECTRUM, VISCERA_GAIN,
  HEART_PERIOD, HEART_RADIUS_MM, HEART_AMP, MODEL_UNITS_PER_MM,
} from "./chameleon-stain.js";

// The cleared-and-stained chameleon on a lightbox (no jar yet). Each tissue's absorbance and
// where its numbers were measured: chameleon-stain.js.

// The animation clock (seconds into CH_Hover), set by the page each frame.
export const chameleonClock = { value: 0 };
export const chameleonLook = {
  bone: { value: 1 },
  boneT0: { value: BONE_T0 },
  cartilage: { value: 1 },
  skin: { value: 1 },
  viscera: { value: 1 },
  heartAmp: { value: HEART_AMP },
};

// Where each part's path goes in the path buffer.
const CHANNEL = { Bone: 0, Cartilage: 1, Skin: 2, Viscera: 3 };

const pathVertex = `
#include <common>
#include <skinning_pars_vertex>
uniform float uTime;
uniform vec3 uHeart;
uniform float uHeartRadius;
uniform float uHeartAmp;
uniform float uHeartPeriod;
varying vec3 vViewPosition;
varying vec3 vViewNormal;
void main() {
  #include <skinbase_vertex>
  #include <beginnormal_vertex>
  #include <skinnormal_vertex>
  #include <defaultnormal_vertex>
  #include <begin_vertex>
  // The heart's beat: the viscera squeeze in toward the heart, strongest at it (uHeartAmp 0 elsewhere).
  if (uHeartAmp > 0.) {
    vec3 d = transformed - uHeart;
    float beat = pow(.5 + .5 * sin(6.2831853 * uTime / uHeartPeriod), 4.);
    transformed = uHeart + d * (1. - uHeartAmp * beat * exp(-dot(d, d) / (uHeartRadius * uHeartRadius)));
  }
  #include <skinning_vertex>
  #include <project_vertex>
  vViewPosition = mvPosition.xyz;
  vViewNormal = transformedNormal;
}`;

// Every part is a closed solid (bone, cartilage, and the skin since ct_body_pipeline/softmesh2.py): the path through it is the depth of the faces turned away minus the depth
// of the faces turned toward the camera, summed in any order. Depths are taken from a plane
// through the body's centre so the sums stay small.
const solidFragment = `
uniform vec4 channel;
uniform float reference;
varying vec3 vViewPosition;
void main() {
  float d = -vViewPosition.z - reference;
  gl_FragColor = channel * (gl_FrontFacing ? -d : d);
}`;

const ADD = {
  transparent: true,
  depthTest: false,
  depthWrite: false,
  side: THREE.DoubleSide,
  blending: THREE.CustomBlending,
  blendEquation: THREE.AddEquation,
  blendSrc: THREE.OneFactor,
  blendDst: THREE.OneFactor,
  blendSrcAlpha: THREE.OneFactor,
  blendDstAlpha: THREE.OneFactor,
};

function channelVector(part) {
  const v = new THREE.Vector4(0, 0, 0, 0);   // Vector4() starts with w = 1
  v.setComponent(CHANNEL[part], 1);
  return v;
}

/**
 * Gives every part of specimen_chameleon.glb its path material. Parts are named by the
 * node extra `chameleon_part` (blender/export_chameleon_gltf.py).
 */
// Where the heart is: in the most cranial part of the body cavity, within the rib cage (Melero et al. 2023,
// Open Vet J 13:1071). The viscera mass is not split into organs, so the heart is taken as the part of the
// mass nearest the head: the mean of its vertices within HEART_RADIUS_MM of the vertex closest to the skull.
function heartCentre(mesh) {
  const bones = mesh.skeleton.bones;
  const i = bones.findIndex((b) => b.name === "head");
  if (i < 0) return null;
  const head = new THREE.Vector3().setFromMatrixPosition(mesh.skeleton.boneInverses[i].clone().invert()).applyMatrix4(mesh.bindMatrixInverse);
  const pos = mesh.geometry.getAttribute("position"), p = new THREE.Vector3();
  let best = Infinity, near = new THREE.Vector3();
  for (let k = 0; k < pos.count; k++) {
    p.fromBufferAttribute(pos, k);
    const d = p.distanceToSquared(head);
    if (d < best) { best = d; near.copy(p); }
  }
  const r = HEART_RADIUS_MM * MODEL_UNITS_PER_MM, c = new THREE.Vector3(); let n = 0;
  for (let k = 0; k < pos.count; k++) {
    p.fromBufferAttribute(pos, k);
    if (p.distanceTo(near) < r) { c.add(p); n++; }
  }
  return n ? c.divideScalar(n) : near;
}

export function applyChameleonTissue(model, reference) {
  const found = new Set();
  model.traverse((object) => {
    if (!object.isMesh) return;
    const part = object.userData.chameleon_part;
    if (!(part in CHANNEL)) throw new Error(`specimen_chameleon.glb の部位 ${part ?? object.name} に組織の設定がありません`);
    found.add(part);
    object.frustumCulled = false;
    const heart = part === "Viscera" ? heartCentre(object) : null;
    object.material = new THREE.ShaderMaterial({
      uniforms: {
        channel: { value: channelVector(part) }, reference,
        uTime: chameleonClock,
        uHeart: { value: heart ?? new THREE.Vector3() },
        uHeartRadius: { value: HEART_RADIUS_MM * MODEL_UNITS_PER_MM },
        uHeartAmp: heart ? chameleonLook.heartAmp : { value: 0 },
        uHeartPeriod: { value: HEART_PERIOD },
      },
      vertexShader: pathVertex, fragmentShader: solidFragment, ...ADD,
    });
  });
  const missing = Object.keys(CHANNEL).filter((p) => !found.has(p));
  if (missing.length) throw new Error(`specimen_chameleon.glb に部位がありません: ${missing.join(", ")}`);
}

const compositeFragment = `
uniform sampler2D tPath;
uniform vec3 lightbox;
uniform float linearOut;
uniform float alphaScale;
uniform float pathScale;
uniform float boneGain, boneT0, cartGain, skinGain;
uniform float visceraGain;
uniform vec3 boneSpectrum, cartSpectrum, skinSpectrum, visceraSpectrum;
varying vec2 vUv;
void main() {
  vec4 p = max(texture2D(tPath, vUv), 0.);
  // The gains are per model unit; a scaled model's paths are given back in model units.
  vec4 m = p * pathScale;
  vec3 a = boneGain * boneT0 * (1. - exp(-m.r / boneT0)) * boneSpectrum
    + cartGain * m.g * cartSpectrum
    + skinGain * m.b * skinSpectrum
    + visceraGain * m.a * visceraSpectrum;
  // In the jar the image is a linear light let through over white (jar-optics.js looks it up and the
  // final pass tone-maps it); the ratios measured on the photo are in display (sRGB) values.
  if (linearOut > .5) gl_FragColor = vec4(pow(exp(-a), vec3(2.2)), alphaScale * (p.r + p.g + p.b + p.a));
  else gl_FragColor = vec4(lightbox * exp(-a), 1.);
}`;

/**
 * The path buffer and the pass that turns it into the lightbox image. `linear`: write the light
 * let through (over white, linear) for the jar's optics, with the tissue crossed × alphaScale in alpha.
 * `pathScale`: model units per world unit, when the model is drawn scaled (the jar).
 */
export function createLightbox(renderer, { linear = false, alphaScale = 0, pathScale = 1 } = {}) {
  const float = renderer.extensions.has("EXT_color_buffer_float") && renderer.extensions.has("EXT_float_blend");
  const target = new THREE.WebGLRenderTarget(1, 1, {
    type: float ? THREE.FloatType : THREE.HalfFloatType,
    format: THREE.RGBAFormat,
    depthBuffer: false,
    samples: 4,
  });
  const material = new THREE.ShaderMaterial({
    uniforms: {
      tPath: { value: target.texture },
      lightbox: { value: new THREE.Vector3(...LIGHTBOX) },
      boneGain: { value: BONE_GAIN },
      boneT0: chameleonLook.boneT0,
      cartGain: { value: CARTILAGE_GAIN },
      skinGain: { value: SKIN_GAIN },
      boneSpectrum: { value: new THREE.Vector3(...BONE_SPECTRUM) },
      cartSpectrum: { value: new THREE.Vector3(...CARTILAGE_SPECTRUM) },
      skinSpectrum: { value: new THREE.Vector3(...SKIN_SPECTRUM) },
      visceraGain: { value: VISCERA_GAIN },
      visceraSpectrum: { value: new THREE.Vector3(...VISCERA_SPECTRUM) },
      linearOut: { value: linear ? 1 : 0 },
      alphaScale: { value: alphaScale },
      pathScale: { value: pathScale },
    },
    vertexShader: "varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0., 1.); }",
    fragmentShader: compositeFragment,
    depthTest: false,
    depthWrite: false,
  });
  const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material);
  quad.frustumCulled = false;
  const screen = new THREE.Scene();
  screen.add(quad);
  const flat = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  return {
    precision: float ? "float32" : "float16",
    target,
    setSize(w, h) { target.setSize(w, h); },
    material,
    render(scene, camera, output = null) {
      material.uniforms.boneGain.value = BONE_GAIN * chameleonLook.bone.value;
      material.uniforms.cartGain.value = CARTILAGE_GAIN * chameleonLook.cartilage.value;
      material.uniforms.skinGain.value = SKIN_GAIN * chameleonLook.skin.value;
      material.uniforms.visceraGain.value = VISCERA_GAIN * chameleonLook.viscera.value;
      const clear = renderer.getClearColor(new THREE.Color()), clearAlpha = renderer.getClearAlpha();
      const background = scene.background; scene.background = null;
      renderer.setRenderTarget(target);
      renderer.setClearColor(0x000000, 0);
      renderer.clear();
      renderer.render(scene, camera);
      scene.background = background;
      renderer.setClearColor(clear, clearAlpha);
      renderer.setRenderTarget(output);
      renderer.render(screen, flat);
    },
  };
}
