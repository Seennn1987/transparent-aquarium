import assert from "node:assert/strict";
import { traceColumn } from "../src/optics-trace.js";

// Dimensions of assets/jar.glb (blender/generate_specimen_jar.py).
const JAR = { outer: 0.62, inner: 0.575 };
const camera = [0, 1.2, 11];
const along = (x) => [x, 0, -11];

// Straight through the middle: no bend.
const centre = traceColumn(camera, along(0), JAR);
assert.ok(centre.inLiquid);
assert.ok(Math.abs(centre.direction[0]) < 1e-9, "the central ray must not bend");

// Off the axis the filled column is a converging lens: the ray crosses the axis, so what lies
// behind on one side is seen on the other (the room flipped left to right).
for (const x of [0.1, 0.25, 0.4]) {
  const ray = traceColumn(camera, along(x), JAR);
  assert.ok(ray.inLiquid, `offset ${x}: through the liquid`);
  const behind = ray.point[0] + ray.direction[0] * (10 / -ray.direction[2]);
  assert.ok(behind < 0, `offset ${x}: seen from the other side (x ${behind.toFixed(3)})`);
}

// Concentric surfaces give back the angle they took, so a ray always leaves through the side;
// what darkens the edges is the glass reflecting more and more of the light at grazing angles.
let darkest = 1;
for (let x = 0; x < 0.62; x += 0.002) {
  const ray = traceColumn(camera, along(x), JAR);
  assert.ok(!ray.reflected && !ray.missed, `offset ${x.toFixed(3)}: leaves through the far side`);
  darkest = Math.min(darkest, ray.through);
}
assert.ok(centre.through > 0.9, `face-on the glass lets most light through (${centre.through.toFixed(3)})`);
assert.ok(darkest < 0.5 * centre.through, `the edge must be dark (${darkest.toFixed(3)})`);

console.log(`jar-optics: ok (through face-on ${centre.through.toFixed(3)}, at the edge ${darkest.toFixed(3)})`);
