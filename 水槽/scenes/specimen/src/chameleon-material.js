import * as THREE from "three";
import {
  BONE_T0, stainOf,
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
  film: { value: 1 },
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

// The blue film of the "01" pattern (chameleon-stain.js STAINS["01"].film): a thin stained layer at the
// skin's surface. Each crossing of the skin's surface adds the layer's slant path, 1 / |cos| of the angle
// between the surface and the view, counted in layer thicknesses (the gain holds the thickness). The cos is
// kept above filmMinCos: a layer d thick on a body R in radius is crossed at most 2·sqrt(2Rd) at the outline.
const filmFragment = `
uniform float filmMinCos;
varying vec3 vViewPosition;
varying vec3 vViewNormal;
void main() {
  float c = abs(dot(normalize(vViewNormal), normalize(-vViewPosition)));
  gl_FragColor = vec4(1. / max(c, filmMinCos), 0., 0., 0.);
}`;
// 0.2 (at most 5 thicknesses per crossing): at 0.1 the creases where the skin's tubes meet (tail base,
// elbows, knees) showed as dark rings; the colours fitted on photo 01 are the same at either (chameleon-stain.js).
export const chameleonFilm = { minCos: { value: 0.2 } };

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
    object.userData.pathMaterial = object.material;
    object.userData.filmMaterial = part === "Skin" ? new THREE.ShaderMaterial({
      uniforms: { filmMinCos: chameleonFilm.minCos, uTime: chameleonClock, uHeart: { value: new THREE.Vector3() },
        uHeartRadius: { value: 1 }, uHeartAmp: { value: 0 }, uHeartPeriod: { value: 1 } },
      vertexShader: pathVertex, fragmentShader: filmFragment, ...ADD,
    }) : null;
  });
  const missing = Object.keys(CHANNEL).filter((p) => !found.has(p));
  if (missing.length) throw new Error(`specimen_chameleon.glb に部位がありません: ${missing.join(", ")}`);
}

const compositeFragment = `
uniform sampler2D tPath;
uniform sampler2D tFilm;
uniform float filmGain;
uniform vec3 filmSpectrum;
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
    + visceraGain * m.a * visceraSpectrum
    + filmGain * max(texture2D(tFilm, vUv).r, 0.) * filmSpectrum;
  // In the jar the image is a linear light let through over white (jar-optics.js looks it up and the
  // final pass tone-maps it); the ratios measured on the photo are in display (sRGB) values.
  if (linearOut > .5) gl_FragColor = vec4(pow(exp(-a), vec3(2.2)), alphaScale * (p.r + p.g + p.b + p.a));
  else gl_FragColor = vec4(lightbox * exp(-a), 1.);
}`;

/**
 * The path buffer and the pass that turns it into the lightbox image. `linear`: write the light
 * let through (over white, linear) for the jar's optics, with the tissue crossed × alphaScale in alpha.
 * `pathScale`: model units per world unit, when the model is drawn scaled (the jar).
 * `stain`: the colour pattern (chameleon-stain.js STAINS, "06" or "01").
 */
export function createLightbox(renderer, { linear = false, alphaScale = 0, pathScale = 1, stain = "06" } = {}) {
  const k = stainOf(stain);
  const float = renderer.extensions.has("EXT_color_buffer_float") && renderer.extensions.has("EXT_float_blend");
  const target = new THREE.WebGLRenderTarget(1, 1, {
    type: float ? THREE.FloatType : THREE.HalfFloatType,
    format: THREE.RGBAFormat,
    depthBuffer: false,
    samples: 4,
  });
  const film = k.film && k.film.gain > 0 ? k.film : null;
  const filmTarget = new THREE.WebGLRenderTarget(1, 1, {
    type: float ? THREE.FloatType : THREE.HalfFloatType, format: THREE.RGBAFormat, depthBuffer: false, samples: 4,
  });
  const material = new THREE.ShaderMaterial({
    uniforms: {
      tPath: { value: target.texture },
      tFilm: { value: filmTarget.texture },
      filmGain: { value: film ? film.gain : 0 },
      filmSpectrum: { value: new THREE.Vector3(...(film ? film.spectrum : [0, 0, 0])) },
      lightbox: { value: new THREE.Vector3(...k.lightbox) },
      boneGain: { value: k.bone.gain },
      boneT0: chameleonLook.boneT0,
      cartGain: { value: k.cartilage.gain },
      skinGain: { value: k.skin.gain },
      boneSpectrum: { value: new THREE.Vector3(...k.bone.spectrum) },
      cartSpectrum: { value: new THREE.Vector3(...k.cartilage.spectrum) },
      skinSpectrum: { value: new THREE.Vector3(...k.skin.spectrum) },
      visceraGain: { value: k.viscera.gain },
      visceraSpectrum: { value: new THREE.Vector3(...k.viscera.spectrum) },
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
    filmTarget,
    setSize(w, h) { target.setSize(w, h); filmTarget.setSize(w, h); },
    material,
    render(scene, camera, output = null) {
      material.uniforms.boneGain.value = k.bone.gain * chameleonLook.bone.value;
      material.uniforms.cartGain.value = k.cartilage.gain * chameleonLook.cartilage.value;
      material.uniforms.skinGain.value = k.skin.gain * chameleonLook.skin.value;
      material.uniforms.visceraGain.value = k.viscera.gain * chameleonLook.viscera.value;
      material.uniforms.filmGain.value = film ? film.gain * chameleonLook.film.value : 0;
      const clear = renderer.getClearColor(new THREE.Color()), clearAlpha = renderer.getClearAlpha();
      const background = scene.background; scene.background = null;
      renderer.setRenderTarget(target);
      renderer.setClearColor(0x000000, 0);
      renderer.clear();
      renderer.render(scene, camera);
      if (film) {
        // The film pass: only the skin, with its film material.
        const swapped = [];
        scene.traverse((o) => {
          if (!o.isMesh || !o.userData.pathMaterial) return;
          swapped.push([o, o.visible]);
          if (o.userData.filmMaterial) o.material = o.userData.filmMaterial; else o.visible = false;
        });
        renderer.setRenderTarget(filmTarget);
        renderer.clear();
        renderer.render(scene, camera);
        for (const [o, v] of swapped) { o.material = o.userData.pathMaterial; o.visible = v; }
      }
      scene.background = background;
      renderer.setClearColor(clear, clearAlpha);
      renderer.setRenderTarget(output);
      renderer.render(screen, flat);
    },
  };
}
