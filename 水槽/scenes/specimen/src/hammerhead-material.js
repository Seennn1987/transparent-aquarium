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
const CHANNEL = { Bone: 0, Teeth: 0, Cartilage: 1, Jaw: JAW_BONE > 0 ? [JAW_BONE, 1, 0, 0] : 1, Gill: GILL_MIX, Skin: 2, HeadCartilage: 3, Viscera: [0, 0, 0, 0], Liver: [0, 0, 0, 0], Gut: [0, 0, 0, 0], Spiral: [0, 0, 0, 0] };   // 内臓は内臓の通り道で描く（下の visceraMaterial）
const OPTIONAL = new Set(["Viscera", "Liver", "Gut", "Spiral"]);   // 2026-10-15 前の glb には無い
// 歯は 1 本が 2〜4 mm と小さく、椎骨と同じ吸い方では色が出ないので、道のりを WEIGHT 倍に数える（実物の透明標本では歯は濃く赤く染まる）
const WEIGHT = { Teeth: Number(new URLSearchParams(location.search).get("teeth") ?? 3) };

const ASYM_GLSL = `
// A8 左右差（2026-10-15）: 鏡映で作った左右を、左側（glTF の z > 0。z = −u）だけ決まった量なめらかに曲げる。すべての部品で同じ式なので、
//  骨・膜・皮歯・まだらはずれない。量は翼の先 asymWingMM（?asymwing=）とひれ asymFinDeg（?asymfin=）、まとめた強さ asym（?asym=）が 1 のとき:
//   頭の翼: 左の翼の先を背側へ 3 mm 上げる（CT では左の翼の先が右より約 15 mm 高かった、計画書 第 9 節 A3。その 2 割）
//   左の胸びれ: 付け根（吻端 232.7 mm、左右 17.9、背腹 38.6）を中心に、背腹の軸のまわりに 4° 後ろへ寝かせる（推定）
//   左の腹びれ: 付け根（464.4、5.5、46.8）を中心に 4° 前へ起こす（推定）
uniform float asym;
uniform float asymWingMM;
uniform float asymFinDeg;
vec3 swingY(vec3 p, vec3 c, float a) {   // c を中心に、背腹の軸（y）のまわりに a ラジアン。+ で外の点が後ろ（+x）へ
  vec3 d = p - c; float cs = cos(a), sn = sin(a);
  return c + vec3(d.x * cs + d.z * sn, d.y, -d.x * sn + d.z * cs);
}
vec3 asymWarp(vec3 p) {
  float wingMM = asymWingMM + 3. * asym, finDeg = asymFinDeg + 4. * asym;
  if (wingMM == 0. && finDeg == 0.) return p;
  float side = smoothstep(.0, .012, p.z);
  float wing = side * smoothstep(.05, .15, p.z) * (1. - smoothstep(.12, .16, p.x));
  p.y += wingMM * .001 * wing;
  vec3 cp = vec3(.2327, -.0386, .0179);
  // 胴の表面（正中から約 50 mm）より外のひれだけを回す（中まで回すと胴の横腹が最大 7 mm 内側へずれた）
  float wp = side * smoothstep(.05, .065, p.z) * (1. - smoothstep(.33, .37, p.x)) * smoothstep(.16, .19, p.x);
  p = mix(p, swingY(p, cp, radians(finDeg)), wp);
  vec3 cv = vec3(.4644, -.0468, .0055);
  float wv = side * smoothstep(.035, .05, p.z) * (1. - smoothstep(.54, .57, p.x)) * smoothstep(.43, .45, p.x) * (1. - smoothstep(-.045, -.035, p.y));
  p = mix(p, swingY(p, cv, -radians(finDeg)), wv);
  return p;
}
`;
const vertex = `
varying vec3 vViewPosition;
${ASYM_GLSL}
void main() {
  vec4 mv = modelViewMatrix * vec4(asymWarp(position), 1.);
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
// A8 左右差（ASYM_GLSL）: 翼の先の高さ ?asymwing= mm、ひれの角度 ?asymfin= °（2026-10-15 に分けた）。?asym= は両方をまとめて（1 で 3 mm・4°）
export const asymLook = { amount: { value: Number(DENT_Q.get("asym") ?? 0) }, wingMM: { value: Number(DENT_Q.get("asymwing") ?? 15) }, finDeg: { value: Number(DENT_Q.get("asymfin") ?? 4) } };   // 既定 翼 15 mm・ひれ 4°（2026-10-15 プロデューサー決定）
export const denticleLook = {
  cell: { value: Number(DENT_Q.get("dentcell") ?? 1.2) / 1000 },
  radius: { value: Number(DENT_Q.get("dentsize") ?? 0.28) },   // 点の半径 ÷ 間隔
};
const denticleVertex = `
varying vec3 vRest;
varying vec3 vViewPosition;
varying vec3 vViewNormal;
${ASYM_GLSL}
void main() {
  vRest = position;
  vec4 mv = modelViewMatrix * vec4(asymWarp(position), 1.);
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
    uniforms: { cell: denticleLook.cell, radius: denticleLook.radius, filmMinCos: { value: 0.2 }, asym: asymLook.amount, asymWingMM: asymLook.wingMM, asymFinDeg: asymLook.finDeg },
    vertexShader: denticleVertex, fragmentShader: denticleFragment, ...ADD,
  });
}

// A8 まだら: 体の膜の表面に、体に貼り付いた大きなむら（数 cm）を足す。chameleon-material.js の内臓の通り道（organ、色を自由に
//  決められる RGB の吸い方）を使い、膜の表面を横切るたびに「むら × 1 / |cos|」× 色を足す（皮歯と同じ考え方）。
//  むらは体の座標の 3 次元のなめらかな乱数（2 段、決まった種）。色は hammerhead-stain.js の organs.mottle。強さは ?mottle=（既定 0.5、2026-10-15 決定）、
//  むらの大きさは ?mottlecell= mm（既定 40）
// 輪郭（表面を斜めに見る所）で色がたまらないよう、1 / |cos| の上限を ?mottlecos=（既定 0.6 = 最大 1.7 倍）で抑える（0.2 では輪郭が茶色く縁取られた）
export const mottleLook = { amount: { value: Number(DENT_Q.get("mottle") ?? 0.5) }, cell: { value: Number(DENT_Q.get("mottlecell") ?? 40) / 1000 }, minCos: { value: Number(DENT_Q.get("mottlecos") ?? 0.6) } };   // 強さ ?mottle=（既定 0.5、2026-10-15 決定）
const mottleFragment = `
uniform float cell;
uniform float amount;
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
  gl_FragColor = vec4(amount * organAbs * m / max(cs, filmMinCos), 0.);
}`;
function mottleMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: { cell: mottleLook.cell, amount: mottleLook.amount, organAbs: (chameleonOrgans.mottle ??= { value: new THREE.Vector3() }), filmMinCos: mottleLook.minCos, asym: asymLook.amount, asymWingMM: asymLook.wingMM, asymFinDeg: asymLook.finDeg },
    vertexShader: denticleVertex, fragmentShader: mottleFragment, ...ADD,
  });
}

// A8 鰓条（2026-10-15、プロデューサー「鰓条は今は入れず、A8 で質感として扱ってください」）: エラの骨の表面に、体に貼り付いた細い縞を足す。
//  エラの骨は咽頭のまわりを輪のように回るので、輪の中心（背腹 25 mm 腹側、正中）のまわりの角度で縞を作ると、骨の輪に直角な線（鰓条の向き）になる。
//  出典の図（BIODIDAC の Squalus）では鰓条は角鰓・上鰓の後ろのふちに並ぶ。間隔は ?rayspace= mm（既定 1.8、出典なし）。
//  色はエラの骨と同じ（hammerhead-stain.js の organs.gillray）。強さ ?rays=（既定 2、2026-10-15 決定）
export const gillRayLook = { amount: { value: Number(DENT_Q.get("rays") ?? 2) },   // 既定 2（2026-10-15 プロデューサー決定）
  space: { value: Number(DENT_Q.get("rayspace") ?? 1.8) / 1000 } };
const gillRayFragment = `
uniform float amount;
uniform float space;
uniform vec3 organAbs;
uniform float filmMinCos;
varying vec3 vRest;
varying vec3 vViewPosition;
varying vec3 vViewNormal;
void main() {
  vec2 q = vec2(vRest.z, vRest.y + .025);
  float s = atan(q.x, q.y) * length(q) / space;          // 輪に沿った長さ ÷ 間隔
  float line = 1. - smoothstep(.12, .22, abs(fract(s) - .5));
  float cs = abs(dot(normalize(vViewNormal), normalize(-vViewPosition)));
  gl_FragColor = vec4(amount * organAbs * line / max(cs, filmMinCos), 0.);
}`;
function gillRayMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: { amount: gillRayLook.amount, space: gillRayLook.space, organAbs: (chameleonOrgans.gillray ??= { value: new THREE.Vector3() }),
      filmMinCos: { value: 0.4 }, asym: asymLook.amount, asymWingMM: asymLook.wingMM, asymFinDeg: asymLook.finDeg },
    vertexShader: denticleVertex, fragmentShader: gillRayFragment, ...ADD,
  });
}

// A8 内臓（2026-10-15）: 閉じた面の通り道（表と裏の深さの差）× 色（RGB の吸い方、1 m あたり）を、内臓の通り道に足す。
//  透明標本の内臓の色の出典はまだ無い。案: ?visccol=cream（体の組織と同じ色）・yellow（黄み、肝臓の油）・blue（青み、消化管の粘液のアルシアン、推定）
//  強さ ?visc=（既定 0）。1 で 40 mm 通ると、いちばん吸う色で約 0.3 吸う
const VISC_COLORS = { cream: [0.42, 0.74, 1], yellow: [0.25, 0.45, 1], blue: [1, 0.5, 0.42] };
// 案 2 の部品ごとの色（仮、出典なし）: 肝臓は黄みのクリーム、消化管は淡い青、らせん弁の仕切りは濃い青（強さ 3 倍）
const ORGAN_COLORS = { Liver: [0.25, 0.45, 1], Gut: [1, 0.5, 0.42], Spiral: [3, 1.5, 1.2] };
export const visceraLook = { amount: { value: Number(DENT_Q.get("visc") ?? 0) },
  color: { value: new THREE.Vector3(...(VISC_COLORS[DENT_Q.get("visccol") ?? "cream"] ?? VISC_COLORS.cream)) } };
const visceraFragment = `
uniform float amount;
uniform vec3 color;
uniform float reference;
varying vec3 vViewPosition;
void main() {
  float d = -vViewPosition.z - reference;
  gl_FragColor = vec4(amount * 7.5 * color * (gl_FrontFacing ? -d : d), 0.);
}`;
function visceraMaterial(reference, part) {
  return new THREE.ShaderMaterial({
    uniforms: { amount: visceraLook.amount, color: ORGAN_COLORS[part] ? { value: new THREE.Vector3(...ORGAN_COLORS[part]) } : visceraLook.color, reference, asym: asymLook.amount, asymWingMM: asymLook.wingMM, asymFinDeg: asymLook.finDeg },
    vertexShader: vertex, fragmentShader: visceraFragment, ...ADD,
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
    o.material = new THREE.ShaderMaterial({ uniforms: { channel: { value: channel }, reference, asym: asymLook.amount, asymWingMM: asymLook.wingMM, asymFinDeg: asymLook.finDeg }, vertexShader: vertex, fragmentShader: fragment, ...ADD });
    o.userData.pathMaterial = o.material;
    if (part === "Skin") { o.userData.filmMaterial = denticleMaterial(); o.userData.organMaterial = mottleMaterial(); }
    if (part === "Gill") o.userData.organMaterial = gillRayMaterial();
    if (["Viscera", "Liver", "Gut", "Spiral"].includes(part)) o.userData.organMaterial = visceraMaterial(reference, part);
  });
  const missing = Object.keys(CHANNEL).filter((p) => !found.has(p) && !OPTIONAL.has(p));
  if (missing.length) throw new Error(`specimen_hammerhead.glb に部位がありません: ${missing.join(", ")}`);
}
