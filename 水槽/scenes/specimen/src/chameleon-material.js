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
  organs: { value: 1 },
  heartAmp: { value: HEART_AMP },
};

// Where each part's path goes in the path buffer. Organ (the organs of the body cavity, one mesh each,
// blender/ct_body_pipeline/organs.py) has a buffer of its own: each organ adds its own colour of absorbance.
const CHANNEL = { Bone: 0, Cartilage: 1, Skin: 2, Viscera: 3, Organ: -1 };
const REQUIRED = ["Bone", "Cartilage", "Skin", "Viscera"];
// Each organ's absorbance per model unit (red, green, blue), by the organ's name (node extra chameleon_organ).
// Set from the colour pattern (chameleon-stain.js STAINS[...].organs) by createLightbox.
export const chameleonOrgans = {};
const organUniform = (name) => (chameleonOrgans[name] ??= { value: new THREE.Vector3() });

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
// For measuring: render the organ pass even when the pattern draws no organs (chameleon-main.js organ()).
export const calibrateOrgans = { on: false };

const organFragment = `
uniform vec3 organAbs;
uniform float reference;
varying vec3 vViewPosition;
void main() {
  float d = -vViewPosition.z - reference;
  gl_FragColor = vec4(organAbs * (gl_FrontFacing ? -d : d), 0.);
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
  if (CHANNEL[part] >= 0) v.setComponent(CHANNEL[part], 1);
  return v;
}

// The organ heart's beat: about its own middle, over half its short axis (Melero et al. 2023 Table 3: 9.1 mm,
// × 0.82 for this animal, ct_body_pipeline/organs.py).
const ORGAN_HEART_RADIUS_MM = 9.1 * 0.82 / 2;
function meshCentre(mesh) {
  const pos = mesh.geometry.getAttribute("position"), p = new THREE.Vector3(), c = new THREE.Vector3();
  for (let k = 0; k < pos.count; k++) c.add(p.fromBufferAttribute(pos, k));
  return c.divideScalar(Math.max(pos.count, 1));
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
    const organ = part === "Organ" ? object.userData.chameleon_organ : null;
    if (part === "Organ" && !organ) throw new Error(`specimen_chameleon.glb の臓器 ${object.name} に名前（chameleon_organ）がありません`);
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
    const organHeart = organ === "heart" ? meshCentre(object) : null;
    object.userData.organMaterial = organ ? new THREE.ShaderMaterial({
      uniforms: {
        organAbs: organUniform(organ), reference,
        uTime: chameleonClock,
        uHeart: { value: organHeart ?? new THREE.Vector3() },
        uHeartRadius: { value: ORGAN_HEART_RADIUS_MM * MODEL_UNITS_PER_MM },
        uHeartAmp: organHeart ? chameleonLook.heartAmp : { value: 0 },
        uHeartPeriod: { value: HEART_PERIOD },
      },
      vertexShader: pathVertex, fragmentShader: organFragment, ...ADD,
    }) : null;
    object.userData.filmMaterial = part === "Skin" ? new THREE.ShaderMaterial({
      uniforms: { filmMinCos: chameleonFilm.minCos, uTime: chameleonClock, uHeart: { value: new THREE.Vector3() },
        uHeartRadius: { value: 1 }, uHeartAmp: { value: 0 }, uHeartPeriod: { value: 1 } },
      vertexShader: pathVertex, fragmentShader: filmFragment, ...ADD,
    }) : null;
  });
  const missing = REQUIRED.filter((p) => !found.has(p));
  if (missing.length) throw new Error(`specimen_chameleon.glb に部位がありません: ${missing.join(", ")}`);
}

const compositeFragment = `
uniform sampler2D tPath;
uniform sampler2D tFilm;
uniform sampler2D tOrgan;
uniform float organGain;
uniform float filmGain;
uniform vec3 filmSpectrum;
uniform vec3 lightbox;
uniform float linearOut;
uniform float alphaScale;
uniform float pathScale;
uniform float boneGain, boneT0, cartGain, skinGain;
uniform float visceraGain;
uniform vec3 boneSpectrum, cartSpectrum, skinSpectrum, visceraSpectrum;
uniform vec2 tap;
varying vec2 vUv;
// The signed paths, averaged over the output pixel's fine texels and the ring round them
// (weights 1-3-3-1), before anything is clamped.
vec4 signedAt(sampler2D t) {
  return .25 * (texture2D(t, vUv + vec2(-tap.x, -tap.y)) + texture2D(t, vUv + vec2(tap.x, -tap.y))
    + texture2D(t, vUv + vec2(-tap.x, tap.y)) + texture2D(t, vUv + vec2(tap.x, tap.y)));
}
void main() {
  vec4 p = max(signedAt(tPath), 0.);
  // The gains are per model unit; a scaled model's paths are given back in model units.
  vec4 m = p * pathScale;
  vec3 a = boneGain * boneT0 * (1. - exp(-m.r / boneT0)) * boneSpectrum
    + cartGain * m.g * cartSpectrum
    + skinGain * m.b * skinSpectrum
    + visceraGain * m.a * visceraSpectrum
    + filmGain * max(signedAt(tFilm).r, 0.) * filmSpectrum
    + organGain * max(signedAt(tOrgan).rgb * pathScale, 0.);
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
 * `supersample`: the passes are drawn at this many times the output's width and height. Ribs and
 * the casque's edges are thinner than a pixel; there the faces turned toward and away from the
 * camera do not land in the same pixel, so a pixel's path came out negative (taken as 0: a white
 * dot) next to one too large. The composite reads the finer buffers with linear filtering at the
 * output pixel's centre, which averages the 2 × 2 signed paths before anything is clamped, so the
 * two cancel (measured on chameleon.html?stain=01, ct_body_pipeline/README.md).
 */
export function createLightbox(renderer, { linear = false, alphaScale = 0, pathScale = 1, stain = "06", supersample = 2 } = {}) {
  const k = stainOf(stain);
  const float = renderer.extensions.has("EXT_color_buffer_float") && renderer.extensions.has("EXT_float_blend");
  const target = new THREE.WebGLRenderTarget(1, 1, {
    type: float ? THREE.FloatType : THREE.HalfFloatType,
    format: THREE.RGBAFormat,
    depthBuffer: false,
    samples: 4,
  });
  const film = k.film && k.film.gain > 0 ? k.film : null;
  for (const [name, abs] of Object.entries(k.organs ?? {})) organUniform(name).value.set(...abs);
  const organs = Object.keys(k.organs ?? {}).length > 0;
  const organTarget = new THREE.WebGLRenderTarget(1, 1, {
    type: float ? THREE.FloatType : THREE.HalfFloatType, format: THREE.RGBAFormat, depthBuffer: false, samples: 4,
  });
  const filmTarget = new THREE.WebGLRenderTarget(1, 1, {
    type: float ? THREE.FloatType : THREE.HalfFloatType, format: THREE.RGBAFormat, depthBuffer: false, samples: 4,
  });
  const material = new THREE.ShaderMaterial({
    uniforms: {
      tPath: { value: target.texture },
      tFilm: { value: filmTarget.texture },
      tOrgan: { value: organTarget.texture },
      organGain: { value: organs ? 1 : 0 },
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
      tap: { value: new THREE.Vector2() },
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
    organTarget,
    /** Whether this pattern draws the organs (and so renders their pass). */
    organs,
    /** The output's size; the passes are `supersample` times finer. */
    size: { width: 1, height: 1 },
    supersample,
    setSize(w, h) {
      this.size.width = w; this.size.height = h;
      const W = Math.max(1, Math.round(w * supersample)), H = Math.max(1, Math.round(h * supersample));
      target.setSize(W, H); filmTarget.setSize(W, H); organTarget.setSize(W, H);
      // Four bilinear taps 0.75 fine texel either side of the output pixel's centre (a texel corner):
      // 4 × 4 fine texels, weights 1-3-3-1 along each axis.
      if (supersample > 1) material.uniforms.tap.value.set(0.75 / W, 0.75 / H); else material.uniforms.tap.value.set(0, 0);
    },
    material,
    render(scene, camera, output = null) {
      material.uniforms.boneGain.value = k.bone.gain * chameleonLook.bone.value;
      material.uniforms.cartGain.value = k.cartilage.gain * chameleonLook.cartilage.value;
      material.uniforms.skinGain.value = k.skin.gain * chameleonLook.skin.value;
      material.uniforms.visceraGain.value = k.viscera.gain * chameleonLook.viscera.value;
      material.uniforms.filmGain.value = film ? film.gain * chameleonLook.film.value : 0;
      material.uniforms.organGain.value = organs ? chameleonLook.organs.value : 0;
      const clear = renderer.getClearColor(new THREE.Color()), clearAlpha = renderer.getClearAlpha();
      const background = scene.background; scene.background = null;
      renderer.setRenderTarget(target);
      renderer.setClearColor(0x000000, 0);
      renderer.clear();
      renderer.render(scene, camera);
      // Passes of their own: only the meshes that have that material (the skin's film, the organs).
      const pass = (key, into) => {
        const swapped = [];
        scene.traverse((o) => {
          if (!o.isMesh || !o.userData.pathMaterial) return;
          swapped.push([o, o.visible]);
          if (o.userData[key]) o.material = o.userData[key]; else o.visible = false;
        });
        renderer.setRenderTarget(into);
        renderer.clear();
        renderer.render(scene, camera);
        for (const [o, v] of swapped) { o.material = o.userData.pathMaterial; o.visible = v; }
      };
      if (film) pass("filmMaterial", filmTarget);
      if (organs || calibrateOrgans.on) pass("organMaterial", organTarget);
      scene.background = background;
      renderer.setClearColor(clear, clearAlpha);
      renderer.setRenderTarget(output);
      renderer.render(screen, flat);
    },
  };
}
