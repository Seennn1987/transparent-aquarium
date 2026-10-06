import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { profilePoints, profileDistance, profileField, bakeProfileField } from "../src/solid-glass.js";

// A unit square beside the axis: inside is negative, the axis side is not a surface.
const square = [[0, 0], [1, 0], [1, 1], [0, 1]];
assert.ok(Math.abs(profileDistance(square, 0.5, 0.5) + 0.5) < 1e-9, "middle: 0.5 inside");
assert.ok(Math.abs(profileDistance(square, 0, 0.5) + 0.5) < 1e-9, "on the axis the solid carries on");
assert.ok(Math.abs(profileDistance(square, -0.5, 0.5) + 0.5) < 1e-9, "mirrored across the axis");
assert.ok(Math.abs(profileDistance(square, 1.5, 0.5) - 0.5) < 1e-9, "outside: 0.5 away");
assert.ok(Math.abs(profileDistance(square, 0.2, 1.3) - 0.3) < 1e-9, "above the top");

// The jar's own sections (blender/generate_specimen_jar.py).
const glb = readFileSync(new URL("../assets/jar.glb", import.meta.url));
const json = JSON.parse(glb.subarray(20, 20 + glb.readUInt32LE(12)).toString());
const extras = json.nodes.find((n) => n.extras?.jar_part === "Jar_Glass").extras;
const lid = profilePoints(extras.jar_lid_profile);
const base = profilePoints(extras.jar_base_profile);
const rim = extras.jar_rim_height;

// The lid is thick glass: the knob solid, the top and the band round the mouth ~0.1 thick,
// and hollow under the top.
assert.ok(profileDistance(lid, 0, extras.jar_knob_centre) < -0.15, "the knob is a solid ball");
assert.ok(profileDistance(lid, 0, rim + 0.2) > 0.02, "hollow under the top");
const thickness = (r0, r1, y) => {
  let inside = 0;
  for (let i = 0; i <= 400; i++) if (profileDistance(lid, r0 + ((r1 - r0) * i) / 400, y) < 0) inside++;
  return (inside / 401) * (r1 - r0);
};
const band = thickness(0.3, 0.8, rim + 0.08);
assert.ok(band > 0.1, `the band round the mouth is thick (${band.toFixed(3)})`);
// Up through the top off the axis, clear of the neck.
let top = 0;
for (let i = 0; i <= 400; i++) if (profileDistance(lid, 0.2, rim + 0.15 + (0.3 * i) / 400) < 0) top++;
top *= 0.3 / 401;
assert.ok(top > 0.09 && top < 0.2, `the top is thick (${top.toFixed(3)})`);

// The foot: solid glass up to the liquid's floor, wider than the body.
assert.ok(profileDistance(base, 0, extras.jar_floor_height / 2) < -0.1, "the floor is solid");
assert.ok(profileDistance(base, extras.jar_foot_radius - 0.01, 0.05) < 0, "the foot reaches its radius");
assert.ok(profileDistance(base, extras.jar_body_radius + 0.02, extras.jar_floor_height - 0.01) > 0, "the foot curves in to the body");

// The baked field agrees with the exact distance at its texel centres, and its direction is
// the way the distance grows.
const field = bakeProfileField(lid, { width: 64 });
for (const [i, j] of [[5, 5], [30, 40], [60, field.height - 3], [40, 20]]) {
  const r = ((i + 0.5) / field.width) * field.rMax;
  const y = field.yMin + ((j + 0.5) / field.height) * (field.yMax - field.yMin);
  const k = (j * field.width + i) * 4;
  assert.equal(field.data[k], Math.fround(profileDistance(lid, r, y)));
  const e = 1e-4;
  const slope = (profileDistance(lid, r + field.data[k + 1] * e, y + field.data[k + 2] * e) - profileDistance(lid, r, y)) / e;
  assert.ok(Math.abs(slope - 1) < 0.02, `texel ${i},${j}: the direction points up the distance (${slope.toFixed(3)})`);
}
// Just outside the knob's top the surface faces up.
const [, upR, upY] = profileField(lid, 0.02, extras.jar_knob_centre + extras.jar_knob_radius + 0.01);
assert.ok(upY > 0.95 && Math.abs(upR) < 0.2, `the knob's top faces up (${upR.toFixed(2)}, ${upY.toFixed(2)})`);

console.log(`solid-glass: ok (band ${band.toFixed(3)}, top ${top.toFixed(3)}, field ${field.width}x${field.height})`);
