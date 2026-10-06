// Solid glass turned on a lathe (the lid with its knob, the jar's foot), described by its
// cross-section: points [r, y] from the axis round the outline and back to the axis. The
// field below holds, for each point of the (r, y) half-plane, how far it is from the glass,
// negative inside, so a ray can be marched through the solid in a shader.

/** [r0, y0, r1, y1, ...] as a list of points. */
export function profilePoints(flat) {
  if (!Array.isArray(flat) || flat.length < 6 || flat.length % 2) throw new Error("断面の点列が不正です");
  const points = [];
  for (let i = 0; i < flat.length; i += 2) points.push([flat[i], flat[i + 1]]);
  return points;
}

const ON_AXIS = 1e-6;

/**
 * Signed distance from (r, y) to the outline (negative inside the glass) and the outward
 * direction of the surface nearest to it, [distance, dr, dy].
 */
export function profileField(points, r, y) {
  // Kept off the axis itself, where the closing stretch lies and would count as a crossing.
  r = Math.max(Math.abs(r), 1e-5);
  let best = Infinity, gr = 0, gy = 1;
  let inside = false;
  for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
    const [ar, ay] = points[j];
    const [br, by] = points[i];
    if ((ay > y) !== (by > y) && r < ar + ((y - ay) / (by - ay)) * (br - ar)) inside = !inside;
    // The closing stretch along the axis is not a surface: the solid carries on across it.
    if (ar < ON_AXIS && br < ON_AXIS) continue;
    const er = br - ar, ey = by - ay;
    const t = Math.min(Math.max(((r - ar) * er + (y - ay) * ey) / (er * er + ey * ey), 0), 1);
    const dr = r - ar - er * t, dy = y - ay - ey * t;
    const dist = Math.hypot(dr, dy);
    if (dist < best) {
      best = dist;
      // Exactly on the surface: across the segment, whichever way (a texel centre seldom is).
      if (dist > 1e-9) { gr = dr / dist; gy = dy / dist; } else { const l = Math.hypot(er, ey); gr = ey / l; gy = -er / l; }
    }
  }
  return inside ? [-best, -gr, -gy] : [best, gr, gy];
}

/** Signed distance from (r, y) to the outline: negative inside the glass. */
export function profileDistance(points, r, y) {
  return profileField(points, r, y)[0];
}

/**
 * The field sampled on a grid over the outline's bounds plus a margin (outward, below and
 * above), texel centres at r = (i + 0.5) / width * rMax and
 * y = yMin + (j + 0.5) / height * (yMax - yMin).
 */
export function bakeProfileField(points, { width = 256, margin = {} } = {}) {
  const { r: out = 0.04, below = 0.04, above = 0.04 } = margin;
  const rMax = Math.max(...points.map(([r]) => r)) + out;
  const yMin = Math.min(...points.map(([, y]) => y)) - below;
  const yMax = Math.max(...points.map(([, y]) => y)) + above;
  const height = Math.max(8, Math.round((width * (yMax - yMin)) / rMax));
  // Four values a texel: the distance, the outward direction (r, y), and a spare.
  const data = new Float32Array(width * height * 4);
  for (let j = 0; j < height; j++) {
    const y = yMin + ((j + 0.5) / height) * (yMax - yMin);
    for (let i = 0; i < width; i++) {
      const [d, gr, gy] = profileField(points, ((i + 0.5) / width) * rMax, y);
      data.set([d, gr, gy, 1], (j * width + i) * 4);
    }
  }
  return { data, width, height, rMax, yMin, yMax };
}
