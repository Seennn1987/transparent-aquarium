import * as THREE from "three";

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
  });
  const missing = Object.keys(CHANNEL).filter((p) => !found.has(p));
  if (missing.length) throw new Error(`specimen_hammerhead.glb に部位がありません: ${missing.join(", ")}`);
}
