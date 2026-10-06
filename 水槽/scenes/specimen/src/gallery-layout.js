// Where everything in the gallery stands, in the room's own frame: the front jar at the
// origin, the camera out along +z, the back wall toward -z. The room is turned as a whole so
// that its back wall faces the default camera. No three.js here, so the tests can read it.

export const ROOM = {
  halfWidth: 13,
  back: 10,       // back wall at z = -back
  front: 18,      // wall behind the camera, seen only in the glass
  ceiling: 7,
};

// On the blocks every jar stands on its own acrylic block, so all jar bases sit at y = 0 and
// the table beneath them is at y = -PEDESTAL.height. On a glass table its top is y = 0.
export const PEDESTAL = {
  height: 0.32,
  frontRadius: 1.15,   // corner radius of the front jar's octagonal block
  radius: 0.85,        // the others', times the jar's scale
};

// The jars behind stand in one straight row across the room, evenly spaced and centred on
// the front jar, all the front jar's size. They hold only the liquid, no specimen.
export const ROW = {
  z: -3.6,
  spacing: 1.9,
  length: 7,
};

export const SLOTS = Array.from({ length: ROW.length }, (_, i) => ({
  x: (i - (ROW.length - 1) / 2) * ROW.spacing,
  z: ROW.z,
  scale: 1,
}));

// Which slots are filled at each quality: from the middle outward, so the row stays centred.
const ORDER = SLOTS.map((slot, i) => i).sort((a, b) => Math.abs(SLOTS[a].x) - Math.abs(SLOTS[b].x) || SLOTS[a].x - SLOTS[b].x);
const COUNT = { eco: 3, balanced: 5, detail: 5 };

export function slotCount(quality) {
  return COUNT[quality] ?? COUNT.balanced;
}

export function slotsFor(count) {
  return ORDER.slice(0, Math.max(0, Math.min(SLOTS.length, Math.round(count)))).map((i) => SLOTS[i]);
}

export function pedestalRadius(slot) {
  return PEDESTAL.radius * slot.scale;
}
