import * as THREE from "three";
import {
  LIGHTBOX, BONE_SPECTRUM, BONE_T0, BONE_GAIN, CARTILAGE_SPECTRUM, CARTILAGE_GAIN,
  SKIN_SPECTRUM, SKIN_GAIN,
} from "./chameleon-stain.js";

// The cleared-and-stained chameleon on a lightbox (no jar yet). Each tissue's absorbance and
// where its numbers were measured: chameleon-stain.js.

export const chameleonLook = {
  bone: { value: 1 },
  boneT0: { value: BONE_T0 },
  cartilage: { value: 1 },
  skin: { value: 1 },
};

// Where each part's path goes in the path buffer.
const CHANNEL = { Bone: 0, Cartilage: 1, Skin: 2 };
const SOLID = new Set(["Bone", "Cartilage"]);

const pathVertex = `
#include <common>
#include <skinning_pars_vertex>
attribute float tissueDepth;
varying vec3 vViewPosition;
varying vec3 vViewNormal;
varying float vDepth;
void main() {
  vDepth = tissueDepth;
  #include <skinbase_vertex>
  #include <beginnormal_vertex>
  #include <skinnormal_vertex>
  #include <defaultnormal_vertex>
  #include <begin_vertex>
  #include <skinning_vertex>
  #include <project_vertex>
  vViewPosition = mvPosition.xyz;
  vViewNormal = transformedNormal;
}`;

// A closed solid: the path through it is the depth of the faces turned away minus the depth
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

// The open skin: the tissue under each face, half at the face it enters by and half at the
// face it leaves by (blender/export_chameleon_gltf.py bakes the depth).
const filmFragment = `
uniform vec4 channel;
varying float vDepth;
void main() {
  gl_FragColor = channel * .5 * vDepth;
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
  const v = new THREE.Vector4();
  v.setComponent(CHANNEL[part], 1);
  return v;
}

/**
 * Gives every part of specimen_chameleon.glb its path material. Parts are named by the
 * node extra `chameleon_part` (blender/export_chameleon_gltf.py).
 */
export function applyChameleonTissue(model, reference) {
  const found = new Set();
  model.traverse((object) => {
    if (!object.isMesh) return;
    const part = object.userData.chameleon_part;
    if (!(part in CHANNEL)) throw new Error(`specimen_chameleon.glb の部位 ${part ?? object.name} に組織の設定がありません`);
    found.add(part);
    object.frustumCulled = false;
    object.material = SOLID.has(part)
      ? new THREE.ShaderMaterial({ uniforms: { channel: { value: channelVector(part) }, reference }, vertexShader: pathVertex, fragmentShader: solidFragment, ...ADD })
      : new THREE.ShaderMaterial({ uniforms: { channel: { value: channelVector(part) } }, vertexShader: pathVertex, fragmentShader: filmFragment, ...ADD });
    const depth = object.geometry.getAttribute("_depth");
    if (!SOLID.has(part) && !depth) throw new Error("specimen_chameleon.glb の膜に厚み（_depth）がありません");
    object.geometry.setAttribute("tissueDepth", depth ?? new THREE.BufferAttribute(new Float32Array(object.geometry.getAttribute("position").count), 1));
  });
  const missing = Object.keys(CHANNEL).filter((p) => !found.has(p));
  if (missing.length) throw new Error(`specimen_chameleon.glb に部位がありません: ${missing.join(", ")}`);
}

const compositeFragment = `
uniform sampler2D tPath;
uniform vec3 lightbox;
uniform float boneGain, boneT0, cartGain, skinGain;
uniform vec3 boneSpectrum, cartSpectrum, skinSpectrum;
varying vec2 vUv;
void main() {
  vec4 p = max(texture2D(tPath, vUv), 0.);
  vec3 a = boneGain * boneT0 * (1. - exp(-p.r / boneT0)) * boneSpectrum
    + cartGain * p.g * cartSpectrum
    + skinGain * p.b * skinSpectrum;
  gl_FragColor = vec4(lightbox * exp(-a), 1.);
}`;

/** The path buffer and the pass that turns it into the lightbox image. */
export function createLightbox(renderer) {
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
    render(scene, camera) {
      material.uniforms.boneGain.value = BONE_GAIN * chameleonLook.bone.value;
      material.uniforms.cartGain.value = CARTILAGE_GAIN * chameleonLook.cartilage.value;
      material.uniforms.skinGain.value = SKIN_GAIN * chameleonLook.skin.value;
      renderer.setRenderTarget(target);
      renderer.setClearColor(0x000000, 0);
      renderer.clear();
      renderer.render(scene, camera);
      renderer.setRenderTarget(null);
      renderer.render(screen, flat);
    },
  };
}
