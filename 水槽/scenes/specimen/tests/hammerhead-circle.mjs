import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { circlePose, circleSpeed, dishBaseScale, farthestFromAxis, fitCircle, HH_BODY, HH_HEIGHT } from "../src/hammerhead-path.js";

// シロシュモクザメの回遊（C2、2026-10-15）: 器の直径の案ごとに、1 周の間、体のどこも壁・液面・底から空き（0.12）より近づかない。
//  器の液の大きさは dish.glb の Jar_Liquid（ページの liquidBounds と同じ）から読む。体の外形は hammerhead-path.js（中心線 ± 半幅、ページと同じ式）
const glb = readFileSync(new URL("../assets/dish.glb", import.meta.url));
const json = JSON.parse(glb.subarray(20, 20 + glb.readUInt32LE(12)).toString("utf8"));
const liquidNode = json.nodes.find((n) => n.extras?.jar_part === "Jar_Liquid");
const acc = json.accessors[json.meshes[liquidNode.mesh].primitives[0].attributes.POSITION];
const radius = (acc.max[0] - acc.min[0]) / 2, depth = acc.max[1] - acc.min[1];
const CLEARANCE = 0.12;
const swim = { amplitude: 0.09, wavelength: 0.91, turnBend: 0.5, frequency: 1.25 };
const scale1 = dishBaseScale({ radius, depth, clearance: CLEARANCE });

// いまの器（倍率 1）では回れない
assert.equal(fitCircle({ inner: radius, clearance: CLEARANCE, scale: scale1, swim }), null);

for (const ratio of [1.5, 2, 2.5]) {
  const scale = scale1 / ratio;
  const r = fitCircle({ inner: radius, clearance: CLEARANCE, scale, swim });
  assert.ok(r, `${ratio} 倍で回れない`);
  const L = HH_BODY.length * scale;
  const lap = 2 * Math.PI * r / (HH_BODY.stride * L * swim.frequency);
  let far = 0, maxTurn = 0;
  for (let t = 0; t <= lap; t += 1 / 60) {
    const pose = circlePose(circleSpeed(scale, swim) * t / r, t * swim.frequency, { radius: r, scale, swim });
    far = Math.max(far, farthestFromAxis(pose, scale));
    maxTurn = Math.max(maxTurn, pose.turn);
  }
  // 壁
  assert.ok(far <= radius - CLEARANCE + 1e-9, `${ratio} 倍: 体の端が軸から ${far.toFixed(4)}（壁まで ${(radius - far).toFixed(4)}）`);
  // 底と液面（体は液の真ん中の高さ、背腹の端はうねらない）
  const half = scale * (HH_HEIGHT.top - HH_HEIGHT.bottom) / 2;
  assert.ok(half <= depth / 2 - CLEARANCE, `${ratio} 倍: 背腹が底か液面に近い`);
  // 曲がりは出典のふだんの旋回より強くしない
  assert.ok(maxTurn <= 1 + 1e-12);
  // 同じ時刻なら同じ姿（一時停止で止まる時計から決まる）
  const a = circlePose(3.3, 4.1, { radius: r, scale, swim }), b = circlePose(3.3, 4.1, { radius: r, scale, swim });
  assert.deepEqual([a.at, a.yaw], [b.at, b.yaw]);
  console.log(`  ${ratio} 倍: 回る半径 ${(r / L).toFixed(2)} L、1 周 ${lap.toFixed(1)} 秒、壁までの空き ${(radius - far).toFixed(3)}`);
}
// 泳ぐ速さの案（2 倍の器）: 尾の振りの回数を下げても、1 周の間の空きは変わらない（道すじの形は速さによらない）
for (const v of [0.6, 0.4, 0.25]) {
  const f = v / HH_BODY.stride, sw = { ...swim, frequency: f }, scale = scale1 / 2;
  const r = fitCircle({ inner: radius, clearance: CLEARANCE, scale, swim: sw });
  const lap = 2 * Math.PI * r / (HH_BODY.stride * HH_BODY.length * scale * f);
  let far = 0;
  for (let t = 0; t <= lap; t += 1 / 30) far = Math.max(far, farthestFromAxis(circlePose(circleSpeed(scale, sw) * t / r, t * f, { radius: r, scale, swim: sw }), scale));
  assert.ok(far <= radius - CLEARANCE + 1e-9, `${v} L/s: 壁までの空き ${(radius - far).toFixed(4)}`);
  console.log(`  2 倍・${v} L/s（尾 ${f.toFixed(2)} Hz）: 1 周 ${lap.toFixed(1)} 秒、壁までの空き ${(radius - far).toFixed(3)}`);
}
console.log("hammerhead-circle: ok");
