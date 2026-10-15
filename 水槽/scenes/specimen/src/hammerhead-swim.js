import * as THREE from "three";

// B3 うねり（2026-10-15、プロデューサー「標本ページを骨組みで動かし、B2 のボンネットヘッドの値（尾の振り 1.25 Hz・片側 0.09 L・波長 0.91 L）でうねらせてください」）
//  骨組みは blender/ct_hammerhead/b1_rig.py（頭・背骨 38・尾の鎖と、胸びれ・腹びれ）。B1 の試しのうねり（HH_RIG_TEST=1）と同じ式で骨を回す:
//   体軸 s（吻端から、m）の横のずれ y(s, t) = A(s) sin(2π(s/λ − f t))、A(s) = A尾 (0.15 + 0.85 (s/L)²)
//   鎖の骨は、骨の中点でのずれの傾き atan(dy/ds) の向きに、背の軸（glTF の +Y）のまわりに回す（親との差だけ回すので、鎖の先ほど足し合わさる）。
//   吻端は y(0) だけ横へずらす（頭の付け根で回すだけだと、吻端が止まり尾だけが振れる）
//  数の出典（計画書 第 10 節 B2）: f 1.25 Hz、片側の振れ A尾 0.09 L（Webb & Keyes 1982 の 0.18 L を山から谷とみた半分）、λ 0.91 L（ボンネットヘッド 0.93 m）
//  ?swim=0 で止める（休みの形）。?tbf= Hz、?amp= L（片側）、?wave= L、?phase= で位相を止める（撮るとき）
const Q = new URLSearchParams(location.search);
export const swimLook = {
  on: Q.get("swim") !== "0",
  frequency: Number(Q.get("tbf") ?? 1.25),
  amplitude: Number(Q.get("amp") ?? 0.09),
  wavelength: Number(Q.get("wave") ?? 0.91),
  phase: Q.has("phase") ? Number(Q.get("phase")) : null,
};
const L = 1.024;   // 全長（m）。b1_rig.py の尾の骨の終わり

export function createSwim(model) {
  let skeleton = null;
  model.traverse((o) => { if (o.isSkinnedMesh && !skeleton) skeleton = o.skeleton; });
  if (!skeleton) return null;
  const byName = new Map(skeleton.bones.map((b) => [b.name, b]));
  const chainNames = ["head", ...skeleton.bones.map((b) => b.name).filter((n) => /^spine_\d+$/.test(n)).sort(), "tail"];
  const chain = chainNames.map((n) => byName.get(n));
  if (chain.some((b) => !b)) throw new Error(`骨組みに骨がありません: ${chainNames.filter((n) => !byName.get(n)).join(", ")}`);
  model.updateMatrixWorld(true);
  const toModel = new THREE.Matrix4().copy(model.matrixWorld).invert();
  const up = new THREE.Vector3(0, 1, 0);
  const rest = chain.map((b, i) => {
    const head = b.getWorldPosition(new THREE.Vector3()).applyMatrix4(toModel);
    const next = i + 1 < chain.length ? chain[i + 1].getWorldPosition(new THREE.Vector3()).applyMatrix4(toModel) : new THREE.Vector3(L, head.y, head.z);
    const wq = b.getWorldQuaternion(new THREE.Quaternion());
    return { q0: b.quaternion.clone(), mid: (head.x + next.x) / 2, axis: up.clone().applyQuaternion(wq.invert()).normalize() };
  });
  const basePos = model.position.clone();
  const tmp = new THREE.Quaternion();
  const slope = (s, t) => {
    const At = swimLook.amplitude * L, k = 2 * Math.PI / (swimLook.wavelength * L);
    const A = At * (0.15 + 0.85 * (s / L) ** 2), dA = At * 0.85 * 2 * s / (L * L);
    const ph = k * s - 2 * Math.PI * t;
    return Math.atan(dA * Math.sin(ph) + A * k * Math.cos(ph));
  };
  return {
    bones: chain.length,
    /** cycles: 尾の振りの回数で数えた時刻（f × 秒）。 */
    pose(cycles) {
      let prev = 0;
      chain.forEach((b, i) => {
        const a = slope(rest[i].mid, cycles);
        b.quaternion.copy(rest[i].q0).multiply(tmp.setFromAxisAngle(rest[i].axis, a - prev));
        prev = a;
      });
      // 吻端の横のずれ。+Y まわりに回すと体の向き（+x）は −z へ傾くので、ずれ y は −z に置く
      const y0 = swimLook.amplitude * L * 0.15 * Math.sin(-2 * Math.PI * cycles);
      model.position.set(basePos.x, basePos.y, basePos.z - y0);
    },
    update(seconds) {
      if (!swimLook.on) return;
      this.pose(swimLook.phase ?? seconds * swimLook.frequency);
    },
  };
}
