import assert from "node:assert/strict";
import { ROOM, PEDESTAL, ROW, SLOTS, slotCount, slotsFor, pedestalRadius } from "../src/gallery-layout.js";

// Room frame: the front jar at the origin, the default camera out along +z.
const JAR_BODY = 0.62;

// Every jar stands wholly inside the room, with space to the walls.
for (const slot of SLOTS) {
  const r = pedestalRadius(slot);
  assert.ok(Math.abs(slot.x) + r < ROOM.halfWidth - 1, `slot (${slot.x}, ${slot.z}) inside the side walls`);
  assert.ok(slot.z - r > -ROOM.back + 0.5, `slot (${slot.x}, ${slot.z}) clear of the back wall`);
  assert.ok(slot.z < -PEDESTAL.frontRadius - r, `slot (${slot.x}, ${slot.z}) stands behind the front block`);
}

// One straight row, evenly spaced and centred on the front jar.
assert.ok(SLOTS.every((s) => s.z === ROW.z && s.scale === 1), "one row, all one size");
const xs = SLOTS.map((s) => s.x).sort((a, b) => a - b);
for (let i = 1; i < xs.length; i++) assert.ok(Math.abs(xs[i] - xs[i - 1] - ROW.spacing) < 1e-9, "even spacing");
assert.ok(Math.abs(xs[0] + xs[xs.length - 1]) < 1e-9, "centred");

// Neighbouring blocks do not touch; neither do the jars.
assert.ok(ROW.spacing - 2 * PEDESTAL.radius > 0.15, "blocks clear of each other");
assert.ok(ROW.spacing - 2 * JAR_BODY > 0.5, "jars clear of each other");

// Each quality fills the middle of the row outward, so what is shown stays centred.
const counts = { eco: slotCount("eco"), balanced: slotCount("balanced"), detail: slotCount("detail") };
assert.deepEqual(counts, { eco: 3, balanced: 5, detail: 5 });
assert.ok(slotsFor(counts.detail).length <= SLOTS.length);
for (const name of ["eco", "balanced", "detail"]) {
  const shown = slotsFor(counts[name]);
  assert.ok(Math.abs(shown.reduce((sum, s) => sum + s.x, 0)) < 1e-9, `${name} row is centred`);
}
assert.deepEqual(slotsFor(counts.eco), slotsFor(counts.balanced).slice(0, counts.eco), "lighter settings keep a prefix");

console.log(`gallery-layout: ok (${SLOTS.length} slots; eco ${counts.eco}, balanced ${counts.balanced}, detail ${counts.detail})`);
