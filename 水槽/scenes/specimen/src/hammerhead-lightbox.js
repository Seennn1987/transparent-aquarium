import * as THREE from "three";
import { chameleonLook, chameleonOrgans } from "./chameleon-material.js";
import { STAINS } from "./chameleon-stain.js";
import "./hammerhead-stain.js";   // registers STAINS.hammerhead

// シロシュモクザメのライトボックス（2026-10-15、プロデューサー「骨、内臓、軟骨、肉など、パーツ種別ごとに色や濃さを調整できるようにしたい」）。
//  chameleon-material.js の createLightbox と同じ考え方（部品の表と裏の深さの差＝通り道を色の層に足し、合わせて吸わせる）で、色の層を 4 から 8 に増やした。
//  カメレオンのファイルは変えない（CLAUDE.md）ので、シュモクザメ専用に分けた。
//  層 A（path）: 背骨（骨、飽和あり）・ひれの軟骨・肉・頭骨。層 B（path2）: 顎・エラの骨・腹びれの軟骨・歯（飽和あり）。
//  それぞれの層に色（吸い方の比 spectrum、いちばん吸う成分を 1）と利得（gain、1 m あたり）があり、調整の欄が動かす（hhColorLook）。
//  既定の値は hammerhead-stain.js（前の 4 層のときの色）から作るので、既定では前と同じ見た目になる。
const K = STAINS.hammerhead;
const mix = (parts) => {   // [[利得, 色], ...] → { spectrum, gain }（足し合わせた吸い方）
  const a = [0, 1, 2].map((i) => parts.reduce((s, [g, sp]) => s + g * sp[i], 0)), top = Math.max(...a, 1e-9);
  return { spectrum: a.map((v) => v / top), gain: top };
};
const Q = new URLSearchParams(typeof location !== "undefined" ? location.search : "");
const GILL_BONE = Number(Q.get("gillbone") ?? 0), GILL_CART = Number(Q.get("gillcart") ?? 1);   // hammerhead-material.js の GILL_MIX と同じ既定（青緑）
const JAW_BONE = Number(Q.get("jawbone") ?? 0);
// 層の定義。ref: 色見本の厚み（m、標本ページを背中から測った、その部位のふつうの通り道。measure_colors.py）。sat: 骨と同じ飽和（t0）
export const HH_CHANNELS = [
  { key: "spine", label: "背骨", layer: 0, index: 0, sat: true, ref: 0.012, ...K.bone },
  { key: "fin", label: "ひれ・肩帯の軟骨", layer: 0, index: 1, ref: 0.00225, ...K.cartilage },
  { key: "skin", label: "肉（体の組織）", layer: 0, index: 2, ref: 0.080, ...K.skin },
  { key: "head", label: "頭骨", layer: 0, index: 3, ref: 0.0031, ...K.viscera },
  { key: "jaw", label: "顎", layer: 1, index: 0, ref: 0.0027, ...mix([[K.cartilage.gain, K.cartilage.spectrum], [K.bone.gain * JAW_BONE, K.bone.spectrum]]) },
  { key: "gill", label: "エラの骨", layer: 1, index: 1, ref: 0.0033, ...mix([[K.cartilage.gain * GILL_CART, K.cartilage.spectrum], [K.bone.gain * GILL_BONE, K.bone.spectrum]]) },
  { key: "pelvic", label: "腹びれの軟骨", layer: 1, index: 2, ref: 0.002, ...K.cartilage },
  { key: "teeth", label: "歯", layer: 1, index: 3, sat: true, ref: 0.009, ...K.bone },
];
/** 調整の欄が動かす値（uniform の形）。spectrum は vec3、gain は 1 m あたり、density は濃さの倍率。 */
export const hhColorLook = Object.fromEntries(HH_CHANNELS.map((c) => [c.key, {
  spectrum: { value: new THREE.Vector3(...c.spectrum) }, gain: { value: c.gain }, density: { value: 1 },
  defaults: { spectrum: [...c.spectrum], gain: c.gain },
}]));

const compositeFragment = `
uniform sampler2D tPath, tPath2, tFilm, tOrgan;
uniform float organGain, filmGain, boneT0, linearOut, alphaScale, pathScale;
uniform vec3 filmSpectrum, lightbox;
uniform vec4 gainA, gainB;
uniform vec3 specA0, specA1, specA2, specA3, specB0, specB1, specB2, specB3;
uniform vec2 tap;
varying vec2 vUv;
vec4 signedAt(sampler2D t) {
  return .25 * (texture2D(t, vUv + vec2(-tap.x, -tap.y)) + texture2D(t, vUv + vec2(tap.x, -tap.y))
    + texture2D(t, vUv + vec2(-tap.x, tap.y)) + texture2D(t, vUv + vec2(tap.x, tap.y)));
}
float sat(float m) { return boneT0 * (1. - exp(-m / boneT0)); }
void main() {
  vec4 p = max(signedAt(tPath), 0.), q = max(signedAt(tPath2), 0.);
  vec4 m = p * pathScale, n = q * pathScale;
  vec3 a = gainA.x * sat(m.r) * specA0 + gainA.y * m.g * specA1 + gainA.z * m.b * specA2 + gainA.w * m.a * specA3
    + gainB.x * n.r * specB0 + gainB.y * n.g * specB1 + gainB.z * n.b * specB2 + gainB.w * sat(n.a) * specB3
    + filmGain * max(signedAt(tFilm).r, 0.) * filmSpectrum
    + organGain * max(signedAt(tOrgan).rgb * pathScale, 0.);
  if (linearOut > .5) gl_FragColor = vec4(pow(exp(-a), vec3(2.2)), alphaScale * (p.r + p.g + p.b + p.a + q.r + q.g + q.b + q.a));
  else gl_FragColor = vec4(lightbox * exp(-a), 1.);
}`;

/** createLightbox（chameleon-material.js）と同じ使い方。部品は pathMaterial（層 A）・path2Material（層 B）・filmMaterial・organMaterial を持つ。 */
export function createHammerheadLightbox(renderer, { linear = false, alphaScale = 0, pathScale = 1, supersample = 2 } = {}) {
  const float = renderer.extensions.has("EXT_color_buffer_float") && renderer.extensions.has("EXT_float_blend");
  const rt = () => new THREE.WebGLRenderTarget(1, 1, { type: float ? THREE.FloatType : THREE.HalfFloatType, format: THREE.RGBAFormat, depthBuffer: false, samples: 4 });
  const target = rt(), target2 = rt(), filmTarget = rt(), organTarget = rt();
  for (const [name, abs] of Object.entries(K.organs ?? {})) (chameleonOrgans[name] ??= { value: new THREE.Vector3() }).value.set(...abs);
  const spec = (c) => hhColorLook[c.key].spectrum;
  const byLayer = (l) => HH_CHANNELS.filter((c) => c.layer === l).sort((x, y) => x.index - y.index);
  const [A, B] = [byLayer(0), byLayer(1)];
  const material = new THREE.ShaderMaterial({
    uniforms: {
      tPath: { value: target.texture }, tPath2: { value: target2.texture }, tFilm: { value: filmTarget.texture }, tOrgan: { value: organTarget.texture },
      organGain: { value: 1 }, filmGain: { value: K.film.gain }, filmSpectrum: { value: new THREE.Vector3(...K.film.spectrum) },
      lightbox: { value: new THREE.Vector3(...K.lightbox) }, boneT0: chameleonLook.boneT0,
      gainA: { value: new THREE.Vector4() }, gainB: { value: new THREE.Vector4() },
      ...Object.fromEntries(A.map((c, i) => [`specA${i}`, spec(c)])), ...Object.fromEntries(B.map((c, i) => [`specB${i}`, spec(c)])),
      linearOut: { value: linear ? 1 : 0 }, alphaScale: { value: alphaScale }, pathScale: { value: pathScale }, tap: { value: new THREE.Vector2() },
    },
    vertexShader: "varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0., 1.); }",
    fragmentShader: compositeFragment, depthTest: false, depthWrite: false,
  });
  const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material); quad.frustumCulled = false;
  const screen = new THREE.Scene(); screen.add(quad);
  const flat = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const g = (c) => hhColorLook[c.key].gain.value * hhColorLook[c.key].density.value;
  return {
    precision: float ? "float32" : "float16",
    target, target2, filmTarget, organTarget, organs: true,
    size: { width: 1, height: 1 }, supersample, material,
    setSize(w, h) {
      this.size.width = w; this.size.height = h;
      const W = Math.max(1, Math.round(w * supersample)), H = Math.max(1, Math.round(h * supersample));
      for (const t of [target, target2, filmTarget, organTarget]) t.setSize(W, H);
      if (supersample > 1) material.uniforms.tap.value.set(0.75 / W, 0.75 / H); else material.uniforms.tap.value.set(0, 0);
    },
    render(scene, camera, output = null) {
      material.uniforms.gainA.value.set(...A.map(g)); material.uniforms.gainB.value.set(...B.map(g));
      material.uniforms.filmGain.value = K.film.gain * chameleonLook.film.value;
      material.uniforms.organGain.value = chameleonLook.organs.value;
      const clear = renderer.getClearColor(new THREE.Color()), clearAlpha = renderer.getClearAlpha();
      const background = scene.background; scene.background = null;
      renderer.setClearColor(0x000000, 0);
      const pass = (key, into) => {
        const swapped = [];
        scene.traverse((o) => {
          if (!o.isMesh || !o.userData.pathMaterial) return;
          swapped.push([o, o.visible]);
          if (o.userData[key]) o.material = o.userData[key]; else o.visible = false;
        });
        renderer.setRenderTarget(into); renderer.clear(); renderer.render(scene, camera);
        for (const [o, v] of swapped) { o.material = o.userData.pathMaterial; o.visible = v; }
      };
      pass("pathMaterial", target);
      pass("path2Material", target2);
      pass("filmMaterial", filmTarget);
      pass("organMaterial", organTarget);
      scene.background = background;
      renderer.setClearColor(clear, clearAlpha);
      renderer.setRenderTarget(output);
      renderer.render(screen, flat);
    },
  };
}
