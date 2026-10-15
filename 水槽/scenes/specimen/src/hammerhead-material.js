import * as THREE from "three";
import { chameleonOrgans } from "./chameleon-material.js";

// The path materials for specimen_hammerhead.glb (blender/ct_hammerhead/a6a_export_gltf.py): each part is a
// closed solid, and its path along the view ray is the depth of the faces turned away minus the depth of the
// faces turned toward the camera (as chameleon-material.js). Parts are named by the node extra `hh_part`.
// The head's cartilage (the cranium; since A7 the jaws and gill arches are parts of their own) takes the fourth
// channel, drawn with the stain's `viscera` spectrum and gain (chameleon-material.js's composite): the shark has no separate viscera yet.
// 2026-10-14: 歯は椎骨と同じ赤（石灰化）、顎はひれの軟骨と同じ青。頭骨だけを濃い青緑にする
// 数のときはその組織の通り道 1 つ。配列のときは 4 つの通り道（骨・軟骨・膜・頭の軟骨）への重みで、組織の色を混ぜた色になる。
// 2026-10-15 エラの骨: 胚の鰓弓（Eames et al. 2007 Fig. 2A、x 58〜100・y 22〜40 px の帯の暗い半分の中央値 0.05 / 0.24 / 0.44、
//  濃い紺）に合わせ、骨と軟骨の色を混ぜる（骨 1.67・軟骨 1.518。骨の利得 166 のとき画面で約 0.05 / 0.26 / 0.40。青は使える組織の色では目標まで上げられない）。前の目標 0.50 / 0.73 / 0.83（点 72, 28）は鰓弓の棒の間のすき間だった（計画書 第 9 節 A7）
const GILL_MIX = [Number(new URLSearchParams(location.search).get("gillbone") ?? 1.67), Number(new URLSearchParams(location.search).get("gillcart") ?? 1.518), 0, 0];
// 顎: 既定はひれの軟骨と同じ淡い青。?jawbone= で骨の色を混ぜる（2026-10-15、顎の色の案を見比べるため）
const JAW_BONE = Number(new URLSearchParams(location.search).get("jawbone") ?? 0);
const CHANNEL = { Bone: 0, Teeth: 0, Cartilage: 1, Jaw: JAW_BONE > 0 ? [JAW_BONE, 1, 0, 0] : 1, Gill: GILL_MIX, Skin: 2, HeadCartilage: 3 };
// 歯は 1 本が 2〜4 mm と小さく、椎骨と同じ吸い方では色が出ないので、道のりを WEIGHT 倍に数える（実物の透明標本では歯は濃く赤く染まる）
const WEIGHT = { Teeth: Number(new URLSearchParams(location.search).get("teeth") ?? 3) };

const vertex = `
varying vec3 vViewPosition;
void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.);
  vViewPosition = mv.xyz;
  gl_Position = projectionMatrix * mv;
}`;
const fragment = `
uniform vec4 channel;
uniform float reference;
varying vec3 vViewPosition;
void main() {
  float d = -vViewPosition.z - reference;
  gl_FragColor = channel * (gl_FrontFacing ? -d : d);
}`;
const ADD = {
  transparent: true, depthTest: false, depthWrite: false, side: THREE.DoubleSide,
  blending: THREE.CustomBlending, blendEquation: THREE.AddEquation,
  blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor, blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneFactor,
};

// A8 皮歯（皮膚の小さな歯）: 膜の表面に、体に貼り付いた細かい点として描く（chameleon-material.js の膜の層の通り道を使う）。
//  胚（Eames et al. 2007 Fig. 2A・2E）では皮歯はアリザリンで赤紫に染まり、体の表面に点として並ぶ。シロシュモクザメの皮歯の
//  大きさの数は見つかっていない（一般に 1 mm よりずっと小さい）ので、点の間隔は画面で見える最小として決めた（出典なし、2026-10-15）。
//  点は、体の座標（glb のメートル）の 3 次元の格子のそれぞれの箱に 1 つ、決まった乱数でずらして置く（毎回同じ）。
//  膜の表面を横切るたびに、点の上なら 1 / |cos|（表面と視線の角）を足す。強さは ?dent=（既定 1、2026-10-15 決定）、間隔は ?dentcell= mm（既定 1.2）
const DENT_Q = new URLSearchParams(location.search);
export const denticleLook = {
  cell: { value: Number(DENT_Q.get("dentcell") ?? 1.2) / 1000 },
  radius: { value: Number(DENT_Q.get("dentsize") ?? 0.28) },   // 点の半径 ÷ 間隔
};
const denticleVertex = `
varying vec3 vRest;
varying vec3 vViewPosition;
varying vec3 vViewNormal;
void main() {
  vRest = position;
  vec4 mv = modelViewMatrix * vec4(position, 1.);
  vViewPosition = mv.xyz;
  vViewNormal = normalMatrix * normal;
  gl_Position = projectionMatrix * mv;
}`;
const denticleFragment = `
uniform float cell;
uniform float radius;
uniform float filmMinCos;
varying vec3 vRest;
varying vec3 vViewPosition;
varying vec3 vViewNormal;
vec3 hash3(vec3 p) {
  p = vec3(dot(p, vec3(127.1, 311.7, 74.7)), dot(p, vec3(269.5, 183.3, 246.1)), dot(p, vec3(113.5, 271.9, 124.6)));
  return fract(sin(p) * 43758.5453123);
}
void main() {
  vec3 q = vRest / cell; vec3 b = floor(q); float dmin = 9.;
  for (int i = -1; i <= 1; i++) for (int j = -1; j <= 1; j++) for (int k = -1; k <= 1; k++) {
    vec3 c = b + vec3(float(i), float(j), float(k));
    dmin = min(dmin, length(q - (c + hash3(c))));
  }
  float dot_ = 1. - smoothstep(radius * .7, radius, dmin);
  float cs = abs(dot(normalize(vViewNormal), normalize(-vViewPosition)));
  gl_FragColor = vec4(dot_ / max(cs, filmMinCos), 0., 0., 0.);
}`;
function denticleMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: { cell: denticleLook.cell, radius: denticleLook.radius, filmMinCos: { value: 0.2 } },
    vertexShader: denticleVertex, fragmentShader: denticleFragment, ...ADD,
  });
}

// A8 まだら: 体の膜の表面に、体に貼り付いた大きなむら（数 cm）を足す。chameleon-material.js の内臓の通り道（organ、色を自由に
//  決められる RGB の吸い方）を使い、膜の表面を横切るたびに「むら × 1 / |cos|」× 色を足す（皮歯と同じ考え方）。
//  むらは体の座標の 3 次元のなめらかな乱数（2 段、決まった種）。色は hammerhead-stain.js の organs.mottle。強さは ?mottle=（既定 0）、
//  むらの大きさは ?mottlecell= mm（既定 40）
// 輪郭（表面を斜めに見る所）で色がたまらないよう、1 / |cos| の上限を ?mottlecos=（既定 0.6 = 最大 1.7 倍）で抑える（0.2 では輪郭が茶色く縁取られた）
export const mottleLook = { cell: { value: Number(DENT_Q.get("mottlecell") ?? 40) / 1000 }, minCos: { value: Number(DENT_Q.get("mottlecos") ?? 0.6) } };
const mottleFragment = `
uniform float cell;
uniform vec3 organAbs;
uniform float filmMinCos;
varying vec3 vRest;
varying vec3 vViewPosition;
varying vec3 vViewNormal;
float h(vec3 p) { return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453); }
float vnoise(vec3 p) {
  vec3 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  return mix(mix(mix(h(i), h(i + vec3(1, 0, 0)), f.x), mix(h(i + vec3(0, 1, 0)), h(i + vec3(1, 1, 0)), f.x), f.y),
             mix(mix(h(i + vec3(0, 0, 1)), h(i + vec3(1, 0, 1)), f.x), mix(h(i + vec3(0, 1, 1)), h(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}
void main() {
  vec3 q = vRest / cell + 17.3;
  float n = .65 * vnoise(q) + .35 * vnoise(q * 2.7 + 5.1);
  float m = smoothstep(.45, .75, n);
  float cs = abs(dot(normalize(vViewNormal), normalize(-vViewPosition)));
  gl_FragColor = vec4(organAbs * m / max(cs, filmMinCos), 0.);
}`;
function mottleMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: { cell: mottleLook.cell, organAbs: (chameleonOrgans.mottle ??= { value: new THREE.Vector3() }), filmMinCos: mottleLook.minCos },
    vertexShader: denticleVertex, fragmentShader: mottleFragment, ...ADD,
  });
}

export function applyHammerheadTissue(model, reference) {
  const found = new Set();
  model.traverse((o) => {
    if (!o.isMesh) return;
    const part = o.userData.hh_part;
    if (!(part in CHANNEL)) throw new Error(`specimen_hammerhead.glb の部位 ${part ?? o.name} に組織の設定がありません`);
    found.add(part);
    o.frustumCulled = false;
    const channel = new THREE.Vector4(0, 0, 0, 0);
    if (Array.isArray(CHANNEL[part])) channel.set(...CHANNEL[part]); else channel.setComponent(CHANNEL[part], WEIGHT[part] ?? 1);
    o.material = new THREE.ShaderMaterial({ uniforms: { channel: { value: channel }, reference }, vertexShader: vertex, fragmentShader: fragment, ...ADD });
    o.userData.pathMaterial = o.material;
    if (part === "Skin") { o.userData.filmMaterial = denticleMaterial(); o.userData.organMaterial = mottleMaterial(); }
  });
  const missing = Object.keys(CHANNEL).filter((p) => !found.has(p));
  if (missing.length) throw new Error(`specimen_hammerhead.glb に部位がありません: ${missing.join(", ")}`);
}
