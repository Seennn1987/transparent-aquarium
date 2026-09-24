// The column trace of jar-optics.js, step for step, on plain arrays so it can be tested
// outside the browser. Vectors are [x, y, z]; the jar's axis is the y axis.

const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const add = (a, b, s = 1) => [a[0] + b[0] * s, a[1] + b[1] * s, a[2] + b[2] * s];
const normalize = (a) => { const l = Math.hypot(...a); return a.map((v) => v / l); };
const radial = (p) => normalize([p[0], 0, p[2]]);
const neg = (a) => a.map((v) => -v);

export function cylinder(o, d, r) {
  const a = d[0] * d[0] + d[2] * d[2];
  const b = o[0] * d[0] + o[2] * d[2];
  const h = b * b - a * (o[0] * o[0] + o[2] * o[2] - r * r);
  if (h < 0 || a < 1e-8) return null;
  const s = Math.sqrt(h);
  return [(-b - s) / a, (-b + s) / a];
}

/**
 * Snell's law through a surface whose normal n faces the ray, with the share of light let
 * through (Schlick). Null when fully reflected.
 */
export function bend(d, n, eta) {
  const ci = -dot(n, d);
  const k = 1 - eta * eta * (1 - ci * ci);
  if (k < 0) return null;
  const ct = Math.sqrt(k);
  const r0 = ((1 - eta) / (1 + eta)) ** 2;
  const through = 1 - (r0 + (1 - r0) * (1 - (eta > 1 ? ct : ci)) ** 5);
  return { d: normalize(add(d.map((v) => v * eta), n, eta * ci - ct)), through };
}

/**
 * Follows one camera ray through the side of the filled column. Returns where and in which
 * direction it leaves and how much light the four surfaces let through, or
 * `reflected: true` where a surface turns it back completely.
 */
export function traceColumn(o, dir, { outer, inner, glassIor = 1.52, liquidIor = 1.47 }) {
  let d = normalize(dir);
  const hit = cylinder(o, d, outer);
  if (!hit || hit[0] <= 0) return { missed: true };
  let p = add(o, d, hit[0]);
  let through = 1;
  const pass = (n, eta) => {
    const bent = bend(d, n, eta);
    if (!bent) return false;
    d = bent.d;
    through *= bent.through;
    return true;
  };
  pass(radial(p), 1 / glassIor);
  const toLiquid = cylinder(p, d, inner);
  let inLiquid = false;
  if (toLiquid && toLiquid[0] > 0) {
    p = add(p, d, toLiquid[0]);
    pass(radial(p), glassIor / liquidIor);
    p = add(p, d, cylinder(p, d, inner)[1]);
    if (!pass(neg(radial(p)), liquidIor / glassIor)) return { reflected: true, inLiquid: true };
    inLiquid = true;
  }
  p = add(p, d, cylinder(p, d, outer)[1]);
  if (!pass(neg(radial(p)), glassIor)) return { reflected: true, inLiquid };
  return { point: p, direction: d, through, inLiquid };
}
