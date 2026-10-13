import assert from "node:assert/strict";
import { jarEnlargement, CHAMELEON_POSE } from "../src/specimen-chameleon.js";
import { MOTION } from "../src/specimen-motion.js";

// The front jar's liquid (jar.glb: inner radius 0.571, from y 0.264 to 2.288).
const liquid = { min: { x: -0.571, y: 0.264, z: -0.571 }, max: { x: 0.571, y: 2.288, z: 0.571 } };
const c = CHAMELEON_POSE.clearance;
const yaw = CHAMELEON_POSE.maxYawDegrees * Math.PI / 180;
const half = (s) => (s.x * Math.cos(yaw) + s.z * Math.sin(yaw)) / 2;

for (const size of [
  { x: 3.83, y: 6.93, z: 2.0 },   // about the chameleon's box over CH_Hover (model units)
  { x: 0.5, y: 6.93, z: 0.5 },    // a thin one: the height decides
  { x: 9, y: 1, z: 1 },           // a wide one: the wall decides
]) {
  const J = jarEnlargement(size, liquid);
  // In the enlarged jar the animal at its own size clears the wall, the surface and the floor…
  const wall = 0.571 * J - half(size) - MOTION.limitRadius;
  const top = (2.024 * J - size.y) / 2 - MOTION.limitHeight - MOTION.bobHeight;
  assert.ok(wall >= c - 1e-9 && top >= c - 1e-9, "空きが 0.12 より狭い");
  // …and one of them by exactly the clearance (the jar is no larger than it must be).
  assert.ok(Math.min(wall, top) - c < 1e-9, "瓶が必要より大きい");
}
console.log("specimen-chameleon ok");
