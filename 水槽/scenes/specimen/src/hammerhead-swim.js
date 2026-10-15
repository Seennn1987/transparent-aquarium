import * as THREE from "three";

// B3 うねり（2026-10-15、プロデューサー「標本ページを骨組みで動かし、B2 のボンネットヘッドの値（尾の振り 1.25 Hz・片側 0.09 L・波長 0.91 L）でうねらせてください」）
//  骨組みは blender/ct_hammerhead/b1_rig.py（頭・背骨 38・尾の鎖と、胸びれ・腹びれ）。B1 の試しのうねり（HH_RIG_TEST=1）と同じ式で骨を回す:
//   体軸 s（吻端から、m）の横のずれ y(s, t) = A(s) sin(2π(s/λ − f t))、A(s) = A尾 (0.15 + 0.85 (s/L)²)
//   鎖の骨は、骨の中点でのずれの傾き atan(dy/ds) の向きに、背の軸（glTF の +Y）のまわりに回す（親との差だけ回すので、鎖の先ほど足し合わさる）。
//   吻端は y(0) だけ横へずらす（頭の付け根で回すだけだと、吻端が止まり尾だけが振れる）
//  数の出典（計画書 第 10 節 B2）: f 1.25 Hz、片側の振れ A尾 0.09 L（Webb & Keyes 1982 の 0.18 L を山から谷とみた半分）、λ 0.91 L（ボンネットヘッド 0.93 m）
//  ?swim=0 で止める（休みの形）。?tbf= Hz、?amp= L（片側）、?wave= L、?phase= で位相を止める（撮るとき）
// B4 ひれ（2026-10-15、プロデューサー「胸びれと腹びれの動きを、B2 の出典（まっすぐ泳ぐときは止めたまま、旋回で内側を引く）に合わせて作ってください」）
//  まっすぐ泳ぐとき: 胸びれは付け根の区間の背骨の骨の子のまま、体に対して動かさない（Kajiura et al. 2003、Wilga & Lauder 2000）。腹びれは背骨の重みのまま
//  旋回（turn、−1〜1、+ で体の右へ。?turn= で止めた値、後で回る道すじが決める）:
//   体: 自分の通り道の円（半径 0.374 L、Hoffmann & Porter 2019 のボンネットヘッドのふだんの旋回）に沿うとして、首（125 mm）から後ろの向きの角に
//    turn × (s − 0.125) / (0.374 L) を足す（体が通り道に沿う、は推定。?turnbend= でその割合）
//   内側の胸びれ: 付け根を中心に、前へ 8.5°・ひれの長さの軸のまわり 5.0°（前のふちを背側へ、向きは推定）・下へ 10.4°（Hoffmann & Porter 2019、
//    ボンネットヘッドの平均。合計 24 ± 2.3°）を |turn| 倍。外側の胸びれと腹びれは動かさない（アカシュモクザメは左右同じ、Kajiura 2003）
const Q = new URLSearchParams(location.search);
export const swimLook = {
  on: Q.get("swim") !== "0",
  frequency: Number(Q.get("tbf") ?? 1.25),
  amplitude: Number(Q.get("amp") ?? 0.09),
  wavelength: Number(Q.get("wave") ?? 0.91),
  phase: Q.has("phase") ? Number(Q.get("phase")) : null,
  turn: Number(Q.get("turn") ?? 0),
  turnBend: Number(Q.get("turnbend") ?? 0.5),   // 旋回で体を曲げる割合（1 で通り道の円に沿う、推定）。既定 0.5（2026-10-15 プロデューサー「旋回の体の曲げは 0.5 にしてください」）
};
const NECK = 0.125, TURN_R = 0.374;   // 首（頭の骨だけの終わり、m）、旋回の半径（L）
const TUCK = { protract: 8.5, roll: 5.0, depress: 10.4 };   // 内側の胸びれ（°）
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
  const fins = Object.fromEntries(["pect_L", "pect_R"].map((n) => {
    const b = byName.get(n); if (!b) return [n, null];
    const inv = b.getWorldQuaternion(new THREE.Quaternion()).invert();
    const ax = (x, y, z) => new THREE.Vector3(x, y, z).applyQuaternion(inv).normalize();
    return [n, { bone: b, q0: b.quaternion.clone(), up: ax(0, 1, 0), along: ax(1, 0, 0), side: ax(0, 0, 1) }];
  }));
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
      const turn = swimLook.turn;
      chain.forEach((b, i) => {
        const a = slope(rest[i].mid, cycles) + turn * swimLook.turnBend * Math.max(rest[i].mid - NECK, 0) / (TURN_R * L);
        b.quaternion.copy(rest[i].q0).multiply(tmp.setFromAxisAngle(rest[i].axis, a - prev));
        prev = a;
      });
      // 内側の胸びれを引く。glTF の軸: +Y 背、+X 尾へ、+Z 体の左。右のひれは −z 側。Blender の試し（b1_rig.py の tuck）と同じ回し方
      for (const [n, f] of Object.entries(fins)) {
        if (!f) continue;
        const inner = (turn > 0 && n === "pect_R") || (turn < 0 && n === "pect_L");
        const sg = n === "pect_R" ? 1 : -1, k = inner ? Math.abs(turn) : 0, r = THREE.MathUtils.degToRad;
        f.bone.quaternion.copy(f.q0)
          .multiply(tmp.setFromAxisAngle(f.up, sg * r(TUCK.protract) * k))
          .multiply(tmp.setFromAxisAngle(f.side, -r(TUCK.roll) * k))
          .multiply(tmp.setFromAxisAngle(f.along, -sg * r(TUCK.depress) * k));
      }
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
