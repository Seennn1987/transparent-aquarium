import * as THREE from "three";

// The path materials for specimen_hammerhead.glb (blender/ct_hammerhead/a6a_export_gltf.py): each part is a
// closed solid, and its path along the view ray is the depth of the faces turned away minus the depth of the
// faces turned toward the camera (as chameleon-material.js). Parts are named by the node extra `hh_part`.
// The head's cartilage (cranium, jaws, gill arches) takes the fourth channel, drawn with the stain's
// `viscera` spectrum and gain (chameleon-material.js's composite): the shark has no separate viscera yet.
// 2026-10-14: 歯は椎骨と同じ赤（石灰化）、顎とエラの骨はひれの軟骨と同じ青。頭骨だけを濃い青緑にする
const CHANNEL = { Bone: 0, Teeth: 0, Cartilage: 1, Jaw: 1, Gill: 1, Skin: 2, HeadCartilage: 3 };
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
    const channel = new THREE.Vector4(0, 0, 0, 0); channel.setComponent(CHANNEL[part], WEIGHT[part] ?? 1);
    o.material = new THREE.ShaderMaterial({ uniforms: { channel: { value: channel }, reference }, vertexShader: vertex, fragmentShader: fragment, ...ADD });
    o.userData.pathMaterial = o.material;
  });
  const missing = Object.keys(CHANNEL).filter((p) => !found.has(p));
  if (missing.length) throw new Error(`specimen_hammerhead.glb に部位がありません: ${missing.join(", ")}`);
}
