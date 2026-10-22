import * as THREE from "three";
import { chameleonOrgans } from "./chameleon-material.js";
import { stainAbsorb, HH_YELLOW, HH_CHANNELS, hhStainMix, hhColorLook } from "./hammerhead-lightbox.js";

// The path materials for specimen_hammerhead.glb (blender/ct_hammerhead/a6a_export_gltf.py): each part is a
// closed solid, and its path along the view ray is the depth of the faces turned away minus the depth of the
// faces turned toward the camera (as chameleon-material.js). Parts are named by the node extra `hh_part`.
// The head's cartilage (the cranium; since A7 the jaws and gill arches are parts of their own) takes the fourth
// channel, drawn with the stain's `viscera` spectrum and gain (chameleon-material.js's composite): the shark has no separate viscera yet.
// 2026-10-14: 歯は椎骨と同じ赤（石灰化）、顎はひれの軟骨と同じ青。頭骨だけを濃い青緑にする
// 数のときはその組織の通り道 1 つ。配列のときは 4 つの通り道（骨・軟骨・膜・頭の軟骨）への重みで、組織の色を混ぜた色になる。
// 2026-10-15 エラの骨: 胚の鰓弓（Eames et al. 2007 Fig. 2A、x 58〜100・y 22〜40 px の帯の暗い半分の中央値 0.05 / 0.24 / 0.44、
//  濃い紺）に合わせ、骨と軟骨の色を混ぜる（骨 1.67・軟骨 1.518。骨の利得 166 のとき画面で約 0.05 / 0.26 / 0.40。青は使える組織の色では目標まで上げられない）。前の目標 0.50 / 0.73 / 0.83（点 72, 28）は鰓弓の棒の間のすき間だった（計画書 第 9 節 A7）
// 2026-10-15 プロデューサー決定「３３％、青緑」（「鰓骨の色が他の色対比で濃すぎないでしょうか？」から）: エラの骨は青緑（骨 0・軟骨 1、画面で 0.12 / 0.84 / 0.68）。
//  前の濃い紺（骨 1.67・軟骨 1.518）は ?gillbone=1.67&gillcart=1.518
const GILL_MIX = [Number(new URLSearchParams(location.search).get("gillbone") ?? 0), Number(new URLSearchParams(location.search).get("gillcart") ?? 1), 0, 0];
// 顎: 既定はひれの軟骨と同じ淡い青。?jawbone= で骨の色を混ぜる（2026-10-15、顎の色の案を見比べるため）
const JAW_BONE = Number(new URLSearchParams(location.search).get("jawbone") ?? 0);
const CHANNEL = { Bone: 0, Teeth: 0, Cartilage: 1, Jaw: JAW_BONE > 0 ? [JAW_BONE, 1, 0, 0] : 1, Gill: GILL_MIX, Skin: 2, HeadCartilage: 3, Viscera: [0, 0, 0, 0], Liver: [0, 0, 0, 0], Gut: [0, 0, 0, 0], Spiral: [0, 0, 0, 0],   // 内臓は内臓の通り道で描く（下の visceraMaterial）
  // 2026-10-15 背骨の案 E: 椎体の外側の軟骨（a8c_vertebrae.py の椎体）を軟骨の色で淡く。中の石灰化した砂時計形（CT の殻）は Bone のまま
  // 案 H: ?centrumbone= ?archbone= で骨の色（アリザリン）を混ぜる（胚の 15 cm では軟骨の多くも表面がアリザリンで染まる、計画書 第 8.3 節）
  Centrum: [Number(new URLSearchParams(location.search).get("centrumbone") ?? 0.1), Number(new URLSearchParams(location.search).get("centrum") ?? 0.02), 0, 0],   // 既定 骨 0.1・軟骨 0.02（2026-10-15 プロデューサー決定「H1」）
  Arch: [Number(new URLSearchParams(location.search).get("archbone") ?? 0), Number(new URLSearchParams(location.search).get("arch") ?? 0.5), 0, 0] };   // 既定 骨 0・軟骨 0.5（ひれの軟骨の半分の青。2026-10-17 プロデューサー「弓の色はひれの軟骨の半分の青で既定にしてください」。前は H1 の骨 0.3・軟骨 0.08）   // 背骨の弓（別の部品にしたとき。2026-10-15 案 G）
const HEARTS = ["Heart", "HeartLarge", "HeartSmall"];   // B5 心臓（b5b_heart.py）。Large・Small は見比べの案（試しの glb だけ）
for (const h of HEARTS) CHANNEL[h] = [0, 0, 0, 0];   // 内臓の通り道で描く
// 2026-10-16 案: 肋骨と尾びれの鰭条（推定、a8c_vertebrae.py）。ひれの軟骨と同じ層に、?rib= ?ray= 倍（既定 1、ひれの放射軟骨と同じ青）
CHANNEL.Rib = [0, Number(new URLSearchParams(location.search).get("rib") ?? 1), 0, 0];
CHANNEL.CaudalRay = [0, Number(new URLSearchParams(location.search).get("ray") ?? 1), 0, 0];
const FIN_CART = ["PectCartilage", "Dorsal1Cartilage", "Dorsal2Cartilage", "AnalCartilage"], FIN_SKIN = ["PectSkin", "Dorsal1Skin", "Dorsal2Skin", "AnalSkin"];
const OPTIONAL = new Set([...FIN_CART, ...FIN_SKIN, "Dorsal1Ray", "Viscera", "Liver", "Gut", "Spiral", "Centrum", "Arch", "PelvicCartilage", "PelvicSkin", "Rib", "CaudalRay", ...HEARTS]);   // 2026-10-15 前の glb には無い
// 歯は 1 本が 2〜4 mm と小さく、椎骨と同じ吸い方では色が出ないので、道のりを WEIGHT 倍に数える（実物の透明標本では歯は濃く赤く染まる）
const WEIGHT = { Teeth: Number(new URLSearchParams(location.search).get("teeth") ?? 3) };
// 2026-10-15 色の層を 8 つにした（hammerhead-lightbox.js）。部品ごとの、層 A（背骨・ひれの軟骨・肉・頭骨）と層 B（顎・エラの骨・腹びれの軟骨・歯）への重み。
//  顎・エラの骨の色の混ぜ方（?jawbone=・?gillbone=・?gillcart=）は、層の色（HH_CHANNELS）の方に入る。腹びれの軟骨と膜は別の部品にした（a6a_export_gltf.py）
CHANNEL.PelvicCartilage = 1; CHANNEL.PelvicSkin = 2;
// 2026-10-17 プロデューサー「今、ヒレごとの色の濃さを調整できません。特に背鰭がずっと透明です。」: ひれごとの軟骨と膜の部品（a6a_export_gltf.py の HH_FIN_PARTS）。
//  色はひれの軟骨・肉の層のまま、濃さとにごり度を部品ごとに変える
for (const k of FIN_CART) CHANNEL[k] = 1;
for (const k of FIN_SKIN) CHANNEL[k] = 2;
export const HH_SKIN_PARTS = ["Skin", "PelvicSkin", ...FIN_SKIN];
// 2026-10-20 プロデューサー「強で規定にした上で後で色を調整できるように編集パネルに機能追加して」: 第 1 背びれの鰭条（ceratotrichia、a5h_dfin1_photo.py の
//  HH_DFIN1_RAYS。膜の板の中の細い帯）を別の部品にする。色は 膜の色（肉の層）と 軟骨の青（ひれの軟骨の層）を、調整の欄の「鰭条の色」（?rayblue=、既定 0 = 膜の色）で混ぜる。
//  透明標本で鰭条が青く染まるかは文献で確かめられていない（計画書「ひれの先の鰭条を薄く描く案」）
CHANNEL.Dorsal1Ray = 2;
export const hhRayLook = { blue: { value: Number(new URLSearchParams(location.search).get("rayblue") ?? 0) } };
const _rayVec = new THREE.Vector4();
const rayChannel = { get value() { const k = Math.min(1, Math.max(0, hhRayLook.blue.value)); return _rayVec.set(0, k, 1 - k, 0); } };   // three.js は描くたびに value を読む
const LAYERS = {
  Bone: { a: [1, 0, 0, 0] }, Centrum: { a: CHANNEL.Centrum }, Arch: { a: [CHANNEL.Arch[0], 0, 0, 0], b: [CHANNEL.Arch[1], 0, 0, 0] },
  Rib: { b: [CHANNEL.Rib[1], 0, 0, 0] }, CaudalRay: { b: [CHANNEL.CaudalRay[1], 0, 0, 0] }, Cartilage: { a: [0, 1, 0, 0] },
  Skin: { a: [0, 0, 1, 0] }, PelvicSkin: { a: [0, 0, 1, 0] }, HeadCartilage: { a: [0, 0, 0, 1] },
  // 2026-10-17: 顎は頭骨と同じ層（同じ組織）。弓・肋骨・尾びれの鰭条は「石灰化していない軟骨」の層（層 B の 1 つ目）。
  //  弓の骨の色の混ぜ（?archbone=）は層 A の背骨へ、軟骨の分（?arch=、既定 0.5）は石灰化していない軟骨の層へ
  Jaw: { a: [0, 0, 0, 1] }, Gill: { b: [0, 1, 0, 0] }, PelvicCartilage: { b: [0, 0, 1, 0] }, Teeth: { b: [0, 0, 0, WEIGHT.Teeth] },
  ...Object.fromEntries(FIN_CART.map((k) => [k, { a: [0, 1, 0, 0] }])), ...Object.fromEntries(FIN_SKIN.map((k) => [k, { a: [0, 0, 1, 0] }])),
  Dorsal1Ray: { a: [0, 0, 1, 0] },   // 実際の重みは rayChannel（鰭条の色）
};
/** 部品ごとの濃さの倍率（調整の欄。既定 1）。 */
//  既定（2026-10-17 プロデューサーが調整の欄で決めた値（「一旦、以下を規定値にして下さい」））: 顎 0.227（hammerhead-lightbox.js の tuned）、弓 1.32、肋骨 1.36、尾びれの鰭条 0、腹びれの膜 8.39、らせん弁 1.98、心臓 2.02。
//  ひれの膜（胸びれ・背びれ 2 つ・臀びれ）は、腹びれの膜と同じ厚さ（約 3 mm）なので同じ 8.39 から（前は胸びれの膜は体の膜と同じ 1、背びれの板は体の膜の中で 1）
// 2026-10-18 プロデューサー「一旦これを規定値にして。」（調整の欄の「値をコピー」）。前の既定（2026-10-17）は 顎 0.227、弓 1.32、肋骨 1.36、尾びれの鰭条 0、膜 8.39、らせん弁 1.98、心臓 2.02
const PART_DEFAULT = { Bone: 2.31, Centrum: 1.39, Arch: 4.08, Rib: 1.36, CaudalRay: 1.34, Cartilage: 2.32, Skin: 2.92, PelvicSkin: 17.94, HeadCartilage: 2.38, Jaw: 1.29, Gill: 3.57,
  PelvicCartilage: 0.98, Teeth: 4.06, PectCartilage: 1.27, Dorsal1Cartilage: 1.93, Dorsal2Cartilage: 2.54, AnalCartilage: 2.22, PectSkin: 19.76, Dorsal1Skin: 21.87, Dorsal2Skin: 20.26, AnalSkin: 21.11,
  Liver: 1, Gut: 1.52, Spiral: 1.09, Heart: 3.07,
  Dorsal1Ray: 13.1 };   // 2026-10-20: 膜を鰭条に沿って左右 0.6 mm 厚くした版（「強」）と同じ見え方: 膜の濃さ 21.87 × 足した厚さ 1.2 mm ÷ 鰭条の帯の厚さ 2 mm
export const hhPartLook = Object.fromEntries([...Object.keys(LAYERS), "Liver", "Gut", "Spiral", "Heart", "HeartLarge", "HeartSmall", "Viscera"].map((k) => [k, { value: PART_DEFAULT[k] ?? 1 }]));
/** 部品ごとのにごり度（調整の欄。既定 0）。2026-10-17 プロデューサー「各パーツごとににごり度を調整できるようにして」:
 *  その部品の通り道を、体の組織（肉の層、hammerhead-lightbox.js の skin）と同じ吸い方で、にごり度 × 通り道だけ足す。1 で体の組織と同じ濁り */
const HAZE_DEFAULT = { Bone: 6.56, Arch: 6.31, CaudalRay: 13.87, Cartilage: 24.33, PelvicCartilage: 29.51, PectCartilage: 9.15, Dorsal1Cartilage: 35.69, Dorsal2Cartilage: 35.24, AnalCartilage: 37.19, Gut: 3.95 };   // 2026-10-18 プロデューサー「一旦これを規定値にして。」（調整の欄の「値をコピー」）
export const hhPartHaze = Object.fromEntries(Object.keys(hhPartLook).map((k) => [k, { value: HAZE_DEFAULT[k] ?? 0 }]));

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
// B5 エラ（2026-10-15）: エラの範囲（吻端から 135〜240 mm、エラの骨は 139〜215 mm）の体の横を、正中から外へ breath 倍だけ押し広げる。
//  骨・膜・内臓すべてに同じ式なので、ずれない。breath は hammerhead-swim.js が時刻で決める（0 で止まる）
uniform float breath;
vec3 breathWarp(vec3 p) {
  if (breath == 0.) return p;
  float wx = smoothstep(.13, .15, p.x) * (1. - smoothstep(.215, .24, p.x));
  float az = abs(p.z), wz = smoothstep(.008, .025, az) * (1. - smoothstep(.055, .07, az));
  p.z += breath * p.z * wx * wz;
  return p;
}
vec3 restWarp(vec3 p) { return breathWarp(asymWarp(p)); }
`;
// B3 骨組み（2026-10-15）: glb に骨組み（blender/ct_hammerhead/b1_rig.py）があれば、左右差で曲げた休みの形を骨組みで動かす（three.js の skinning）。
//  骨組みの無い glb では USE_SKINNING が付かず、前と同じ
const vertex = `
#include <common>
#include <skinning_pars_vertex>
varying vec3 vViewPosition;
${ASYM_GLSL}
void main() {
  vec3 transformed = restWarp(position);
  #include <skinbase_vertex>
  #include <skinning_vertex>
  vec4 mv = modelViewMatrix * vec4(transformed, 1.);
  vViewPosition = mv.xyz;
  gl_Position = projectionMatrix * mv;
}`;
const fragment = `
uniform vec4 channel;
uniform float reference;
uniform float partGain;
uniform float haze;
varying vec3 vViewPosition;
void main() {
  float d = -vViewPosition.z - reference;
  gl_FragColor = (partGain * channel + vec4(0., 0., haze, 0.)) * (gl_FrontFacing ? -d : d);   // haze: 層 A の 3 つ目（肉）へ。層 B では 0
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
// 皮歯・まだら・鰓条の模様は休みの形の座標（vRest）で決めるので、うねっても体に貼り付いたまま
const denticleVertex = `
#include <common>
#include <skinning_pars_vertex>
varying vec3 vRest;
varying vec3 vViewPosition;
varying vec3 vViewNormal;
${ASYM_GLSL}
void main() {
  vRest = position;
  vec3 transformed = restWarp(position);
  vec3 objectNormal = normal;
  #include <skinbase_vertex>
  #include <skinnormal_vertex>
  #include <skinning_vertex>
  vec4 mv = modelViewMatrix * vec4(transformed, 1.);
  vViewPosition = mv.xyz;
  vViewNormal = normalMatrix * objectNormal;
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
    uniforms: { cell: denticleLook.cell, radius: denticleLook.radius, filmMinCos: { value: 0.2 }, asym: asymLook.amount, breath: organClock.breath, asymWingMM: asymLook.wingMM, asymFinDeg: asymLook.finDeg },
    vertexShader: denticleVertex, fragmentShader: denticleFragment, ...ADD,
  });
}

// A8 まだら: 体の膜の表面に、体に貼り付いた大きなむら（数 cm）を足す。chameleon-material.js の内臓の通り道（organ、色を自由に
//  決められる RGB の吸い方）を使い、膜の表面を横切るたびに「むら × 1 / |cos|」× 色を足す（皮歯と同じ考え方）。
//  むらは体の座標の 3 次元のなめらかな乱数（2 段、決まった種）。色は hammerhead-stain.js の organs.mottle。強さは ?mottle=（既定 0.5、2026-10-15 決定）、
//  むらの大きさは ?mottlecell= mm（既定 40）
// 輪郭（表面を斜めに見る所）で色がたまらないよう、1 / |cos| の上限を ?mottlecos=（既定 0.6 = 最大 1.7 倍）で抑える（0.2 では輪郭が茶色く縁取られた）
export const HH_DENT_DEFAULT = 0.19;   // 皮歯の強さの既定（2026-10-18 プロデューサー「一旦これを規定値にして。」（調整の欄の「値をコピー」）。前は 0.46、その前は 1）。hammerhead-main.js・specimen-hammerhead.js
export const mottleLook = { amount: { value: Number(DENT_Q.get("mottle") ?? 0.39) }, cell: { value: Number(DENT_Q.get("mottlecell") ?? 40) / 1000 }, minCos: { value: Number(DENT_Q.get("mottlecos") ?? 0.6) } };   // 強さ ?mottle=（既定 0.5、2026-10-15 決定）
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
    uniforms: { cell: mottleLook.cell, amount: mottleLook.amount, organAbs: (chameleonOrgans.mottle ??= { value: new THREE.Vector3() }), filmMinCos: mottleLook.minCos, asym: asymLook.amount, breath: organClock.breath, asymWingMM: asymLook.wingMM, asymFinDeg: asymLook.finDeg },
    vertexShader: denticleVertex, fragmentShader: mottleFragment, ...ADD,
  });
}

// A8 鰓条（2026-10-15、プロデューサー「鰓条は今は入れず、A8 で質感として扱ってください」）: エラの骨の表面に、体に貼り付いた細い縞を足す。
//  エラの骨は咽頭のまわりを輪のように回るので、輪の中心（背腹 25 mm 腹側、正中）のまわりの角度で縞を作ると、骨の輪に直角な線（鰓条の向き）になる。
//  出典の図（BIODIDAC の Squalus）では鰓条は角鰓・上鰓の後ろのふちに並ぶ。間隔は ?rayspace= mm（既定 1.8、出典なし）。
//  色はエラの骨と同じ（hammerhead-stain.js の organs.gillray）。強さ ?rays=（既定 2、2026-10-15 決定）
export const gillRayLook = { amount: { value: Number(DENT_Q.get("rays") ?? 0) },   // 既定 0（2026-10-18 プロデューサー「一旦これを規定値にして。」（調整の欄の「値をコピー」）。前は 1.06、その前は 2）
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
      filmMinCos: { value: 0.4 }, asym: asymLook.amount, breath: organClock.breath, asymWingMM: asymLook.wingMM, asymFinDeg: asymLook.finDeg },
    vertexShader: denticleVertex, fragmentShader: gillRayFragment, ...ADD,
  });
}

// A8 内臓（2026-10-15）: 閉じた面の通り道（表と裏の深さの差）× 色（RGB の吸い方、1 m あたり）を、内臓の通り道に足す。
//  透明標本の内臓の色の出典はまだ無い。案: ?visccol=cream（体の組織と同じ色）・yellow（黄み、肝臓の油）・blue（青み、消化管の粘液のアルシアン、推定）
//  強さ ?visc=（既定 2、2026-10-15 決定）。1 で 40 mm 通ると、いちばん吸う色で約 0.3 吸う
const VISC_COLORS = { cream: [0.42, 0.74, 1], yellow: [0.25, 0.45, 1], blue: [1, 0.5, 0.42] };
// 案 2 の部品ごとの色（仮、出典なし）: 肝臓は黄みのクリーム、消化管は淡い青、らせん弁の仕切りは濃い青（強さ 3 倍）
// 2026-10-17 色の既定（写真の透明標本、hammerhead-lightbox.js の PALETTE）: 消化管とらせん弁は、写真の腹の青い塊（粘液がアルシアンで青く染まる）に合わせて
//  色見本の厚み 40 mm・強さ 2 で 透過 0.55 / 0.88 / 0.95 の青緑（らせん弁はその 1.5 倍）。肝臓と心臓は前のまま。前の色は ?palette=embryo
const ORGAN_PALETTE = new URLSearchParams(location.search).get("palette") ?? "tuned";
const ORGAN_PHOTO = ORGAN_PALETTE === "photo";
// 2026-10-17 内臓は軟骨ではないので染まらない（透明にした組織、ほぼ無色）。calcified・double・juvenile では、無色の濁りの量（色見本 40 mm）で
//  肝臓 1.5・消化管 1・らせん弁 1.5・心臓 1.2（量は目で見た仮の値）。値は [赤紫, 青, 無色, 黄ばみ] の量（hammerhead-lightbox.js の HH_STAIN_A）。
//  黄ばみ: 2026-10-17 プロデューサー「内臓は黄ばませて」。内臓は脱色が届きにくく脂も多いので、肉の黄ばみ（?yellow=）に足して ?visy=（既定 1）。脂の多い肝臓は 2 倍
const OY = HH_YELLOW + Number(new URLSearchParams(location.search).get("visy") ?? 1);
//  tuned（既定、2026-10-17 プロデューサーが調整の欄で決めた値（「一旦、以下を規定値にして下さい」））: 前の欄で選んだ色を 4 つの量に直した（ぴったり同じ色。強さ 2.07）
// 2026-10-18 プロデューサー「一旦これを規定値にして。」（調整の欄の「値をコピー」）: 内臓の色の値はそのままで、内臓ぜんぶの強さが 2.07 → 0.88 になったので、量を 0.88 / 2.07 倍にした（同じ色の値になる）
const ORGAN_TUNED = { Liver: [0.0846, 0.411, 0, 1.6027], Gut: [0.0604, 0.1921, 0, 0.7686], Spiral: [0.0927, 0.1029, 0, 3.6185], Heart: [0.1343, 0.0548, 0, 0.5909], HeartLarge: [0.1343, 0.0548, 0, 0.5909], HeartSmall: [0.1343, 0.0548, 0, 0.5909] };
export const HH_ORGAN_MIX = ORGAN_PALETTE === "tuned" ? ORGAN_TUNED : ["calcified", "double", "juvenile", "photo", "ct"].includes(ORGAN_PALETTE) ? { Liver: [0, 0, 1.5, 2 * OY], Gut: [0, 0, 1, OY], Spiral: [0, 0, 1.5, OY], Heart: [0, 0, 1.2, OY], HeartLarge: [0, 0, 1.2, OY], HeartSmall: [0, 0, 1.2, OY] } : null;
/** 染料の量 → 内臓の色の値（visceraMaterial の color。強さ visceraLook.amount × 7.5 × 色見本 40 mm で割る） */
export function organMixToColor(m, amount) { const k = amount * 7.5 * 0.04; return stainAbsorb(m).map((v) => v / k); }
//  肝臓は写真に黄色い臓器が見えないので、ほとんど色の無い淡い膜に（透過 0.90 / 0.91 / 0.93、色見本の厚み 40 mm・強さ 2）
const ORGAN_COLORS_BASE = { Liver: ORGAN_PHOTO ? [0.176, 0.157, 0.121] : [0.25, 0.45, 1], Gut: ORGAN_PHOTO ? [1, 0.213, 0.085] : [1, 0.5, 0.42], Spiral: ORGAN_PHOTO ? [1.5, 0.32, 0.13] : [3, 1.5, 1.2],
  // 心臓: 体の組織と同じクリームの吸い方（visccol=cream）。心室は筋肉が厚いので、通り道が長いぶん濃く見える（色の出典なし）
  Heart: [0.42, 0.74, 1], HeartLarge: [0.42, 0.74, 1], HeartSmall: [0.42, 0.74, 1] };
const ORGAN_VISC_AMOUNT = Number(new URLSearchParams(location.search).get("visc") ?? 0.88);
const ORGAN_COLORS = HH_ORGAN_MIX ? Object.fromEntries(Object.keys(ORGAN_COLORS_BASE).map((k) => [k, organMixToColor(HH_ORGAN_MIX[k], ORGAN_VISC_AMOUNT)])) : ORGAN_COLORS_BASE;
export const visceraLook = { amount: { value: Number(DENT_Q.get("visc") ?? 0.88) },   // 既定 0.88（2026-10-18 プロデューサー「一旦これを規定値にして。」（調整の欄の「値をコピー」）。前は 2.07、その前は 2）
 
  color: { value: new THREE.Vector3(...(VISC_COLORS[DENT_Q.get("visccol") ?? "cream"] ?? VISC_COLORS.cream)) } };
// B5 心臓の拍動: 心臓の中心（読み込んだ心臓の面の箱の中心）へ beat 倍だけ縮める。左右差・呼吸の変形と骨組みの変形の間
export const organClock = { breath: { value: 0 }, beat: { value: 0 } };
const heartVertex = vertex.replace("vec3 transformed = restWarp(position);",
  "vec3 transformed = restWarp(position); transformed = heartC + (transformed - heartC) * (1. - beat);").replace("varying vec3 vViewPosition;", "varying vec3 vViewPosition;\nuniform vec3 heartC;\nuniform float beat;");
const visceraFragment = `
uniform float amount;
uniform float partGain;
uniform vec3 color;
uniform float reference;
varying vec3 vViewPosition;
void main() {
  float d = -vViewPosition.z - reference;
  gl_FragColor = vec4(partGain * amount * 7.5 * color * (gl_FrontFacing ? -d : d), 0.);
}`;
/** 内臓の色（部品ごと、調整の欄が動かす。既定は ORGAN_COLORS）。 */
export const hhOrganColor = {};
function visceraMaterial(reference, part, heartCentre) {
  const heart = HEARTS.includes(part);
  return new THREE.ShaderMaterial({
    uniforms: { amount: visceraLook.amount, partGain: hhPartLook[part] ?? { value: 1 },
      color: ORGAN_COLORS[part] ? (hhOrganColor[part] ??= { value: new THREE.Vector3(...ORGAN_COLORS[part]), defaults: [...ORGAN_COLORS[part]] }) : visceraLook.color, reference, asym: asymLook.amount, breath: organClock.breath, asymWingMM: asymLook.wingMM, asymFinDeg: asymLook.finDeg,
      ...(heart ? { heartC: { value: heartCentre }, beat: organClock.beat } : {}) },
    vertexShader: heart ? heartVertex : vertex, fragmentShader: visceraFragment, ...ADD,
  });
}

// 2026-10-22 プロデューサー「案１を規定にするが、他のヒレ含めて、軟骨の色・濃さは編集パネルで調整できるようにして下さい」: ひれごとの軟骨の色。
//  色の層（8 つ）はひれごとに分けられないので、ひれの軟骨は内臓と同じ「色をそのまま足す」描き方（organMaterial、合わせるときに吸い方として足す）で描く。
//  吸い方 = その部品の染料の量（hhFinStain、null なら元の色の層の染料の量に従う）から、元の色の層と同じ式（hammerhead-lightbox.js の stainToChannel）で。
//  染料の量が元の色の層と同じなら、前と同じ色になる。濃さは「部品ごとの濃さ」（hhPartLook）、にごり度は前と同じ（層 A の肉へ）
export const FIN_COLOR_PARTS = { PectCartilage: "fin", Dorsal1Cartilage: "fin", Dorsal2Cartilage: "fin", AnalCartilage: "fin", PelvicCartilage: "pelvic", Cartilage: "fin", CaudalRay: "uncal" };
export const hhFinStain = Object.fromEntries(Object.keys(FIN_COLOR_PARTS).map((k) => [k, null]));
export const finStainOf = (part) => hhFinStain[part] ?? hhStainMix[FIN_COLOR_PARTS[part]] ?? [0, 1, 0, 0];
function finAbsorb(part) {
  const ch = HH_CHANNELS.find((c) => c.key === FIN_COLOR_PARTS[part]), w = part === "CaudalRay" ? CHANNEL.CaudalRay[1] : 1;
  const k = w * hhColorLook[ch.key].density.value / ch.ref;
  return stainAbsorb(finStainOf(part)).map((v) => v * k);
}
const finColorFragment = `
uniform float partGain;
uniform vec3 absorb;
uniform float reference;
varying vec3 vViewPosition;
void main() {
  float d = -vViewPosition.z - reference;
  gl_FragColor = vec4(partGain * absorb * (gl_FrontFacing ? -d : d), 0.);
}`;
function finColorMaterial(reference, part) {
  const v = new THREE.Vector3(); const absorb = { get value() { return v.set(...finAbsorb(part)); } };   // three.js は描くたびに value を読む
  return new THREE.ShaderMaterial({ uniforms: { partGain: hhPartLook[part] ?? { value: 1 }, absorb, reference, asym: asymLook.amount, breath: organClock.breath, asymWingMM: asymLook.wingMM, asymFinDeg: asymLook.finDeg },
    vertexShader: vertex, fragmentShader: finColorFragment, ...ADD });
}

export function applyHammerheadTissue(model, reference) {
  const found = new Set();
  model.traverse((o) => {
    if (!o.isMesh) return;
    const part = o.userData.hh_part;
    if (!(part in CHANNEL)) throw new Error(`specimen_hammerhead.glb の部位 ${part ?? o.name} に組織の設定がありません`);
    found.add(part);
    o.frustumCulled = false;
    const layer = LAYERS[part] ?? {};
    const partGain = hhPartLook[part] ?? { value: 1 };
    const pathMat = (w, haze = { value: 0 }, chan = null) => new THREE.ShaderMaterial({ uniforms: { channel: chan ?? { value: new THREE.Vector4(...(w ?? [0, 0, 0, 0])) }, partGain, haze, reference, asym: asymLook.amount, breath: organClock.breath, asymWingMM: asymLook.wingMM, asymFinDeg: asymLook.finDeg }, vertexShader: vertex, fragmentShader: fragment, ...ADD });
    const finColor = part in FIN_COLOR_PARTS;
    o.material = pathMat(finColor ? [0, 0, 0, 0] : layer.a, hhPartHaze[part], part === "Dorsal1Ray" ? rayChannel : null);   // ひれの軟骨は色の層に書かない（にごり度だけ）
    o.userData.pathMaterial = o.material;
    o.userData.path2Material = layer.b && !finColor ? pathMat(layer.b) : null;
    if (finColor) o.userData.organMaterial = finColorMaterial(reference, part);
    if (HH_SKIN_PARTS.includes(part)) { o.userData.filmMaterial = denticleMaterial(); o.userData.organMaterial = mottleMaterial(); }
    if (part === "Gill") o.userData.organMaterial = gillRayMaterial();
    if (["Viscera", "Liver", "Gut", "Spiral"].includes(part)) o.userData.organMaterial = visceraMaterial(reference, part);
    if (HEARTS.includes(part)) {
      o.geometry.computeBoundingBox();
      o.userData.organMaterial = visceraMaterial(reference, part, o.geometry.boundingBox.getCenter(new THREE.Vector3()));
    }
  });
  const missing = Object.keys(CHANNEL).filter((p) => !found.has(p) && !OPTIONAL.has(p));
  if (missing.length) throw new Error(`specimen_hammerhead.glb に部位がありません: ${missing.join(", ")}`);
}
