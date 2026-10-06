import * as THREE from "three";
import { KEY_DIRECTION, RIM_DIRECTION, ROOM_DARK, ROOM_YAW, GALLERY_COLORS, GALLERY_LOOK, STAGE, WALL_LIGHT } from "./gallery.js";
import { ROOM, PEDESTAL } from "./gallery-layout.js";
import { bakeProfileField } from "./solid-glass.js";

// The filled jar is drawn by tracing each pixel's ray through it: into the outer glass, into
// the liquid, past the specimen, out through the far glass, then onto whatever lies behind.
// The background and the specimen are drawn to their own images first and looked up where
// the bent ray meets them, so the jar shows what a real one does: the contents stretched
// across the axis, the room flipped left to right, and dark bands at the edges where the
// glass turns the ray toward the dark room or reflects it completely.
export const OPTICS = {
  glassIor: 1.52,
  liquidIor: 1.47,
  // Light reflected completely inside the glass comes back out elsewhere and mostly sees the
  // white studio; this share of it shows the darker softbox room instead (the edge bands).
  mirror: { value: 0.38 },
  haze: { value: 0 },         // share of light scattered per unit of liquid crossed
  // How much the specimen bends what is seen through it (0: not at all). The ray turns by
  // this times the slope of the tissue crossed, kept ×10 in the specimen image.
  tissueBend: { value: 0 },
  // The lit block below: how much of it the liquid scatters low down, and the tissue.
  underGlow: { value: 0.38 },
  tissueGlow: { value: 0.3 },
  glassGreen: { value: 0.35 },       // the green of soda-lime glass where the light crosses more of it
  meniscus: { value: 1 },         // the surface climbing the glass in the last few millimetres
  swirl: { value: 1.51 },            // streaks of denser glycerin drifting in the liquid
};

// Soda-lime glass reads faintly green-blue through its thick parts; the liquid, barely.
const GLASS_TINT = { color: "#e4f0ec", distance: 1.2 };
const GLASS_GREEN = { color: "#d2e8d4", distance: 0.8 };
const LIQUID_TINT = { color: "#f1f6ef", distance: 6 };

function absorption({ color, distance }) {
  const c = new THREE.Color(color);
  return new THREE.Vector3(-Math.log(c.r), -Math.log(c.g), -Math.log(c.b)).divideScalar(distance);
}

const COMMON = /* glsl */ `
  uniform sampler2D tBackground;
  uniform sampler2D tSpecimen;
  uniform mat4 uViewProj;
  uniform vec2 uSize;
  uniform float uGlassIor, uLiquidIor, uMirror;
  uniform vec3 uGlassAbsorb, uLiquidAbsorb, uGreenAbsorb;
  uniform float uGlassGreen;
  #define GLASS_ABSORB (uGlassAbsorb + uGlassGreen * uGreenAbsorb)
  uniform float uFocus, uAperture, uFocusDepth;
  uniform vec3 uKey, uRim, uFront;
  uniform vec3 uWallLight, uKeyLight, uGlowLight;
  uniform float uGlowK, uRoomYaw;
  uniform float uStageBlocks;   // 1 on the lit blocks, 0 on a glass table
  uniform float uFloorLight;    // how bright what lies below the jar looks
  uniform vec4 uRoomBox;   // half width, back, front, ceiling
  uniform vec2 uBlock;     // the blocks' height, this jar's block's radius
  uniform vec2 uBlockAt;   // where this jar's block stands, in the room frame
  // Where the jar stands. The tracing works about the jar's own axis: positions are relative to
  // uCentre, and behind() and screenOf() are given world positions.
  uniform vec3 uCentre;
  varying vec3 vWorld;

  vec3 cameraForward() { return -vec3(viewMatrix[0][2], viewMatrix[1][2], viewMatrix[2][2]); }

  vec2 screenOf(vec3 p) {
    vec4 c = uViewProj * vec4(p, 1.);
    return c.xy / c.w * .5 + .5;
  }

  // Bends d through a surface whose normal n faces the incoming ray, eta = n1 / n2, and
  // keeps the part of the light the surface lets through. False: reflected completely.
  bool bend(inout vec3 d, vec3 n, float eta, inout vec3 carry) {
    // Rounding can push the cosine past 1 at grazing angles; pow() of a negative is NaN,
    // which the depth of field would spread into a black blot.
    float ci = clamp(-dot(n, d), 0., 1.);
    float k = 1. - eta * eta * (1. - ci * ci);
    if (k < 0.) return false;
    float ct = min(sqrt(k), 1.);
    float r0 = (1. - eta) / (1. + eta);
    r0 *= r0;
    carry *= 1. - (r0 + (1. - r0) * pow(max(1. - (eta > 1. ? ct : ci), 0.), 5.));
    d = normalize(eta * d + (eta * ci - ct) * n);
    return true;
  }

  // The gallery of createGalleryEnvironment, as the glass sees it from inside: the warm walls,
  // the key spot overhead, the rim light behind, and the lit blocks below.
  float softbox(vec3 d, vec3 axis, float size) {
    return smoothstep(cos(size * 1.4), cos(size * .7), dot(d, axis));
  }
  vec3 studio(vec3 d) {
    vec3 c = uWallLight * (d.y < -.02 ? uFloorLight : 1. - .8 * smoothstep(.2, .8, d.y));
    c += uKeyLight * (6. * softbox(d, uKey, .2) + 3. * softbox(d, uRim, .14));
    c += uGlowLight * uGlowK * 1.4 * smoothstep(-.05, -.35, d.y) * uStageBlocks;
    return c;
  }

  // What lies behind: the top of the jar's block (y = 0), the table below it, or the walls of
  // the room, looked up in the background image and blurred by the lens as much as its
  // distance calls for. The room is a box turned by uRoomYaw. p is relative to uCentre.
  vec3 behind(vec3 p, vec3 d) {
    p += uCentre;
    float cy = cos(uRoomYaw), sy = sin(uRoomYaw);
    vec3 lp = vec3(cy * p.x - sy * p.z, p.y, sy * p.x + cy * p.z);
    vec3 ld = vec3(cy * d.x - sy * d.z, d.y, sy * d.x + cy * d.z);
    ld = sign(ld) * max(abs(ld), vec3(1e-5));
    float t = 1e4;
    if (ld.y < 0.) {
      float tTop = -lp.y / ld.y;
      t = tTop > 0. && length(lp.xz + ld.xz * tTop - uBlockAt) < uBlock.y ? tTop : (-uBlock.x - lp.y) / ld.y;
    }
    vec3 lo = vec3(-uRoomBox.x, -uBlock.x, -uRoomBox.y);
    vec3 hi = vec3(uRoomBox.x, uRoomBox.w, uRoomBox.z);
    vec3 exits = max((lo - lp) / ld, (hi - lp) / ld);
    t = min(t, min(exits.x, min(exits.y, exits.z)));
    vec3 hit = p + d * t;
    // Behind the camera: the part of the room the image does not hold.
    if (dot(hit - cameraPosition, cameraForward()) < .1) return uFront;
    float dist = distance(hit, cameraPosition);
    float band = 1. / max(uFocus - uFocusDepth, .1) - 1. / uFocus;
    float coc = max(abs(1. / uFocus - 1. / dist) - band, 0.) * uAperture * uFocus * uFocus * 2.2 * uSize.y / 1080.;
    vec2 uv = clamp(screenOf(hit), vec2(.001), vec2(.999));
    return textureLod(tBackground, uv, clamp(log2(max(coc, 1.)), 0., 6.)).rgb;
  }

  vec3 mirrored(vec3 p, vec3 d) {
    return mix(behind(p, d), studio(d), uMirror);
  }
`;

const VERTEX = /* glsl */ `
  varying vec3 vWorld;
  void main() {
    vec4 world = modelMatrix * vec4(position, 1.);
    vWorld = world.xyz;
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`;

const COLUMN_FRAGMENT = /* glsl */ `
  ${COMMON}
  uniform float uRo, uRi, uFloor, uTop;
  uniform vec3 uSpecimen;
  uniform float uHaze, uTissueBend, uUnderGlow, uTissueGlow, uHasSpecimen, uSpot;

  // The block under the jar shines up through its floor: the liquid glows brightest low down,
  // and the stained tissue scatters some of that light toward the camera in its own colour.
  // On the glass table the light enters from the key spot overhead instead, brightest high up.
  float underLight(float y) {
    return uGlowK * uUnderGlow * mix(.7 * exp(-(uTop - y) / 1.1), exp(-(y - uFloor) / .9), uStageBlocks);
  }
  vec3 hazeLight(float y) { return uWallLight * .9 + uGlowLight * 1.4 * underLight(y); }
  vec3 tissueGlow(vec3 tissue, float y) {
    float taken = 1. - dot(tissue, vec3(1. / 3.));
    return (uGlowLight * uTissueGlow * (.25 + underLight(y)) + uKeyLight * uSpot) * taken * sqrt(max(tissue, 0.));
  }

  // How fast the tissue crossed (the specimen image's alpha) grows across the image, per
  // world unit, as a world direction in the image plane.
  vec3 thicknessSlope(vec3 p, vec2 uv) {
    vec2 px = 1. / uSize;
    float dx = texture2D(tSpecimen, uv + vec2(px.x, 0.)).a - texture2D(tSpecimen, uv - vec2(px.x, 0.)).a;
    float dy = texture2D(tSpecimen, uv + vec2(0., px.y)).a - texture2D(tSpecimen, uv - vec2(0., px.y)).a;
    vec3 right = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
    vec3 up = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
    float worldPerPixel = .01 / max(length((screenOf(p + right * .01) - uv) * uSize), 1e-4);
    return (dx * right + dy * up) / (2. * worldPerPixel);
  }

  vec2 cylinder(vec3 o, vec3 d, float r) {
    float a = dot(d.xz, d.xz);
    float b = dot(o.xz, d.xz);
    float h = b * b - a * (dot(o.xz, o.xz) - r * r);
    if (h < 0. || a < 1e-8) return vec2(-1.);
    h = sqrt(h);
    return vec2(-b - h, -b + h) / a;
  }
  vec3 radial(vec3 p) { return normalize(vec3(p.x, 0., p.z)); }

  uniform float uMeniscus, uSwirl, uTime;

  // Within a few millimetres of the glass the surface climbs it and tilts. side: 1 seen
  // from above, -1 from below.
  vec3 surfaceNormal(vec3 p, float side) {
    float gap = max(uRi - length(p.xz), 0.);
    float slope = uMeniscus * 1.2 * exp(-gap / .012);
    return normalize(vec3(0., side, 0.) - side * slope * radial(p));
  }

  // Streaks of denser glycerin, mostly upright, drifting slowly: the direction they turn a
  // ray, per unit of path.
  vec3 swirl(vec3 p) {
    float t = uTime;
    return vec3(
      sin(p.z * 14. + 2. * sin(p.y * 3. + t * .3) + t * .2),
      0.,
      sin(p.x * 12. + 2. * sin(p.y * 2.5 - t * .25) - t * .15));
  }

  void main() {
    vec3 o = cameraPosition - uCentre;
    vec3 d = normalize(vWorld - cameraPosition);
    vec3 carry = vec3(1.);
    vec3 light = vec3(0.);
    vec3 p;

    vec2 tc = cylinder(o, d, uRo);
    float yHit = o.y + d.y * tc.x;
    if (tc.x > 0. && yHit >= uFloor && yHit <= uTop) {
      p = o + d * tc.x;
      vec3 incoming = d;
      vec3 face = radial(p);
      bend(d, face, 1. / uGlassIor, carry);
      // The front face mirrors the bright studio; the softbox highlights are the wall mesh's.
      light += (1. - carry) * behind(p, reflect(incoming, face));
      vec2 ti = cylinder(p, d, uRi);
      if (ti.x <= 0.) {
        // Only the glass wall, seen edge-on.
        float tOut = cylinder(p, d, uRo).y;
        carry *= exp(-GLASS_ABSORB * tOut);
        p += d * tOut;
        vec3 n = -radial(p);
        vec3 inside = d;
        if (!bend(d, n, uGlassIor, carry)) {
          gl_FragColor = vec4(carry * mirrored(p, reflect(inside, n)), 1.);
          return;
        }
        gl_FragColor = vec4(carry * behind(p, d), 1.);
        return;
      }
      carry *= exp(-GLASS_ABSORB * ti.x);
      p += d * ti.x;
      bend(d, radial(p), uGlassIor / uLiquidIor, carry);
    } else if (d.y < 0. && o.y > uTop) {
      p = o + d * ((uTop - o.y) / d.y);
      if (length(p.xz) > uRi) discard;
      vec3 incoming = d;
      vec3 face = surfaceNormal(p, 1.);
      bend(d, face, 1. / uLiquidIor, carry);
      light += (1. - carry) * behind(p, reflect(incoming, face));
    } else {
      discard;
    }

    // In the liquid. The specimen is thin and hangs facing the viewer, so it is met where the
    // ray crosses the upright plane through its middle.
    vec3 facing = cameraPosition - uSpecimen;
    facing.y = 0.;
    facing = normalize(facing);
    vec3 specimen = uSpecimen - uCentre;
    vec3 tissue = vec3(1.);
    bool met = uHasSpecimen < .5;
    for (int i = 0; i < 4; i++) {
      float tWall = cylinder(p, d, uRi).y;
      float tTop = d.y > 1e-5 ? (uTop - p.y) / d.y : 1e4;
      float tBottom = d.y < -1e-5 ? (uFloor - p.y) / d.y : 1e4;
      float t = min(tWall, min(tTop, tBottom));
      float along = dot(d, facing);
      float tPlane = abs(along) > 1e-4 ? dot(specimen - p, facing) / along : -1.;
      bool atPlane = !met && tPlane > 0. && tPlane < t;
      if (atPlane) t = tPlane;
      // Light scattered by the liquid on the way: it veils what lies deeper.
      float h = 1. - exp(-uHaze * t);
      light += carry * h * hazeLight(p.y + d.y * t * .5);
      carry *= (1. - h) * exp(-uLiquidAbsorb * t);
      p += d * t;
      if (uSwirl > 0.) d = normalize(d + uSwirl * .002 * t * swirl(p - d * t * .5));
      if (atPlane) {
        met = true;
        vec2 uv = screenOf(p + uCentre);
        tissue = texture2D(tSpecimen, uv).rgb;
        light += carry * tissueGlow(tissue, p.y);
        // Tissue refracts a little more than the glycerin, so each body is a faint lens:
        // what lies behind it is bent toward where it is thicker.
        if (uTissueBend > 0.) d = normalize(d + uTissueBend * thicknessSlope(p + uCentre, uv));
        continue;
      }
      if (t == tBottom) {
        // Down through the thick glass floor onto the table.
        carry *= exp(-GLASS_ABSORB * uFloor / max(-d.y, .2));
        break;
      }
      if (t == tTop) {
        // Seen from below, the surface is a mirror past the critical angle.
        vec3 out_ = d;
        vec3 under = surfaceNormal(p, -1.);
        if (bend(out_, under, uLiquidIor, carry)) { d = out_; break; }
        d = reflect(d, under);
        p.y -= 1e-4;
        continue;
      }
      vec3 n = -radial(p);
      if (!bend(d, n, uLiquidIor / uGlassIor, carry)) {
        d = reflect(d, n);
        p -= n * 1e-4;
        continue;
      }
      float tOut = cylinder(p, d, uRo).y;
      carry *= exp(-GLASS_ABSORB * tOut);
      p += d * tOut;
      n = -radial(p);
      vec3 inside = d;
      if (!bend(d, n, uGlassIor, carry)) {
        light += carry * tissue * mirrored(p, reflect(inside, n));
        carry = vec3(0.);
      }
      break;
    }
    gl_FragColor = vec4(light + carry * tissue * behind(p, d), 1.);
  }
`;

// Thick solid glass turned on a lathe: the lid with its knob, and the foot. The ray is
// marched through the distance field of the cross-section (solid-glass.js), bent at every
// surface it meets, reflected inside where the glass turns it back completely, and the
// green of the glass taken along the way. The ball of the knob turns the room upside down;
// the thick band and top of the lid show the bright and dark bands of the room folded in.
const SOLID_FRAGMENT = /* glsl */ `
  ${COMMON}
  uniform sampler2D tShape;
  uniform vec3 uShapeBox;     // rMax, yMin, yMax of the field
  uniform vec2 uShapeTexel;
  // Above this height, leaving the glass upward means entering the liquid (the jar's floor).
  uniform float uLiquidFloor;

  // x: distance to the glass, yz: the outward direction of its nearest surface in (r, y).
  vec3 shapeAt(vec2 q) {
    vec2 size = vec2(uShapeBox.x, uShapeBox.z - uShapeBox.y);
    vec2 uv = vec2(q.x, q.y - uShapeBox.y) / size;
    vec2 c = clamp(uv, .5 * uShapeTexel, 1. - .5 * uShapeTexel);
    vec2 over = (uv - c) * size;
    over.x = max(over.x, 0.);   // the axis side mirrors itself
    vec3 f = texture2D(tShape, c).rgb;
    return vec3(f.x + length(over), f.yz);
  }
  float shape(vec3 p) { return shapeAt(vec2(length(p.xz), p.y)).x; }
  vec3 shapeNormal(vec3 p) {
    float r = length(p.xz);
    vec2 g = shapeAt(vec2(r, p.y)).yz;
    // Where two surfaces are equally near (an inner corner) the baked directions cancel:
    // take the slope of the distance instead.
    if (dot(g, g) < .25) {
      vec2 e = vec2(uShapeBox.x * uShapeTexel.x, (uShapeBox.z - uShapeBox.y) * uShapeTexel.y);
      g = vec2(shapeAt(vec2(r + e.x, p.y)).x - shapeAt(vec2(abs(r - e.x), p.y)).x,
               shapeAt(vec2(r, p.y + e.y)).x - shapeAt(vec2(r, p.y - e.y)).x) / e;
    }
    vec3 out_ = r > 1e-4 ? vec3(p.x, 0., p.z) / r : vec3(0.);
    vec3 n = out_ * g.x + vec3(0., g.y, 0.);
    return dot(n, n) > 1e-8 ? normalize(n) : vec3(0., 1., 0.);
  }

  void main() {
    vec3 view = normalize(vWorld - cameraPosition);
    vec3 d = view;
    vec3 p = vWorld - uCentre;
    vec3 carry = vec3(1.);
    vec3 light = vec3(0.);
    vec3 first = vec3(0.);
    bool inside = false, touched = false;
    int folds = 0;
    vec3 last = p;
    for (int i = 0; i < 200; i++) {
      float s = shape(p);
      // A surface counts only once the ray is really across it; passing close by a rim is
      // not a hit. The crossing is then found exactly between the last two steps.
      if (inside ? s > 0. : s < 0.) {
        vec3 a = last, b = p;
        for (int k = 0; k < 8; k++) {
          vec3 m = (a + b) * .5;
          float sm = shape(m);
          if (inside ? sm > 0. : sm < 0.) b = m; else a = m;
        }
        vec3 n = shapeNormal(b);
        vec3 incoming = d;
        if (!inside) {
          vec3 before = carry;
          bend(d, n, 1. / uGlassIor, carry);
          light += (before - carry) * behind(b, reflect(incoming, n));
          if (!touched) first = b;
          touched = true;
          inside = true;
          p = b - n * 5e-4;
        } else {
          bool toLiquid = b.y > uLiquidFloor - 4e-3 && d.y > 0.;
          if (bend(d, -n, toLiquid ? uGlassIor / uLiquidIor : uGlassIor, carry)) {
            inside = false;
            p = b + n * 5e-4;
            if (toLiquid) {
              carry *= exp(-uLiquidAbsorb * 1.5);
              break;
            }
          } else {
            d = reflect(d, -n);
            p = a - n * 5e-4;
            // Past a few folds the path hangs on the last hair of the surface and would
            // only sparkle from pixel to pixel.
            if (++folds >= 3) break;
          }
        }
        last = p;
        continue;
      }
      float stride = max(abs(s) * .95, 1.5e-3);
      if (inside) carry *= exp(-GLASS_ABSORB * stride);
      last = p;
      p += d * stride;
      if (!inside && (length(p.xz) > uShapeBox.x + .01 || p.y < uShapeBox.y - .01 || p.y > uShapeBox.z + .01)) break;
    }
    if (!touched) discard;
    // Light folded round inside the glass until it is lost: it shows the room's glow evenly,
    // not whichever way the last fold happened to point.
    vec3 seen = inside ? uWallLight * 1.2 + uKeyLight * .6 : behind(p, d);
    vec3 color = light + carry * seen;
    // A stray NaN would be spread into a black blot by the depth of field.
    if (!(color.r >= 0. && color.g >= 0. && color.b >= 0.)) color = uWallLight;
    gl_FragColor = vec4(color, 1.);
    // A few millimetres behind the glass, so its own surface meshes (the highlights) are
    // never lost to this depth.
    vec4 clip = uViewProj * vec4(first + uCentre + view * .004, 1.);
    gl_FragDepth = clip.z / clip.w * .5 + .5;
  }
`;

function solidField(points, margin) {
  const field = bakeProfileField(points, { width: 256, margin });
  const half = new Uint16Array(field.data.length);
  for (let i = 0; i < half.length; i++) half[i] = THREE.DataUtils.toHalfFloat(field.data[i]);
  const texture = new THREE.DataTexture(half, field.width, field.height, THREE.RGBAFormat, THREE.HalfFloatType);
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.needsUpdate = true;
  return { field, texture };
}

// Every jar has the same lid and foot: their fields are baked once.
const fields = new WeakMap();
function sharedField(points, margin) {
  const key = JSON.stringify(margin);
  if (!fields.has(points)) fields.set(points, new Map());
  const byMargin = fields.get(points);
  if (!byMargin.has(key)) byMargin.set(key, solidField(points, margin));
  return byMargin.get(key);
}

/**
 * Opaque stand-ins for the liquid column, the lid and the foot that draw them by ray tracing.
 * `background` and `specimen` are the images drawn from the same camera before the jar.
 * `centre`: where the jar stands (world). `specimen`: false for a jar of liquid only.
 * `block`: the jar's own block, { x, z, radius } in the room frame.
 */
export function createJarOptics({
  dims,
  lens,
  centre = new THREE.Vector3(),
  specimen = true,
  block = { x: 0, z: 0, radius: PEDESTAL.frontRadius },
}) {
  const shared = {
    tBackground: { value: null },
    tSpecimen: { value: null },
    uViewProj: { value: new THREE.Matrix4() },
    uSize: { value: new THREE.Vector2(1, 1) },
    uGlassIor: { value: OPTICS.glassIor },
    uLiquidIor: { value: OPTICS.liquidIor },
    uMirror: OPTICS.mirror,
    uGlassAbsorb: { value: absorption(GLASS_TINT) },
    uGreenAbsorb: { value: absorption(GLASS_GREEN) },
    uGlassGreen: OPTICS.glassGreen,
    uLiquidAbsorb: { value: absorption(LIQUID_TINT) },
    uFocus: lens.focus,
    uAperture: lens.aperture,
    uFocusDepth: lens.focusDepth,
    uKey: { value: KEY_DIRECTION.clone() },
    uRim: { value: RIM_DIRECTION.clone() },
    uFront: { value: ROOM_DARK },
    uWallLight: { value: WALL_LIGHT },
    uKeyLight: { value: GALLERY_COLORS.key },
    uGlowLight: { value: GALLERY_COLORS.glow },
    uGlowK: GALLERY_LOOK.glow,
    uRoomYaw: { value: ROOM_YAW },
    uRoomBox: { value: new THREE.Vector4(ROOM.halfWidth, ROOM.back, ROOM.front, ROOM.ceiling) },
    uBlock: { value: new THREE.Vector2(PEDESTAL.height, block.radius) },
    uBlockAt: { value: new THREE.Vector2(block.x, block.z) },
    uCentre: { value: centre.clone() },
    uStageBlocks: STAGE.blocks,
    uFloorLight: STAGE.floorLight,
  };
  const trackCamera = (renderer, scene, camera) => {
    shared.uViewProj.value.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
  };

  const height = dims.liquidTop - dims.floorHeight;
  const column = new THREE.Mesh(
    new THREE.CylinderGeometry(dims.bodyRadius * 1.002, dims.bodyRadius * 1.002, height, 160, 1, false),
    new THREE.ShaderMaterial({
      uniforms: {
        ...shared,
        uRo: { value: dims.bodyRadius },
        uRi: { value: dims.innerRadius },
        uFloor: { value: dims.floorHeight },
        uTop: { value: dims.liquidTop },
        uSpecimen: { value: new THREE.Vector3(0, (dims.floorHeight + dims.liquidTop) / 2, 0) },
        uHaze: OPTICS.haze,
        uTissueBend: OPTICS.tissueBend,
        uUnderGlow: OPTICS.underGlow,
        uTissueGlow: OPTICS.tissueGlow,
        uHasSpecimen: { value: specimen ? 1 : 0 },
        uSpot: STAGE.spot,
        uMeniscus: OPTICS.meniscus,
        uSwirl: OPTICS.swirl,
        uTime: { value: 0 },
      },
      vertexShader: VERTEX,
      fragmentShader: COLUMN_FRAGMENT,
    }),
  );
  column.name = "jar-optics-column";
  column.position.set(centre.x, dims.floorHeight + height / 2, centre.z);
  column.onBeforeRender = trackCamera;

  // The bounds of each solid stop short of the column, so no pixel is traced twice.
  const solid = (name, points, margin, liquidFloor) => {
    const { field, texture } = sharedField(points, margin);
    const height = field.yMax - field.yMin;
    const mesh = new THREE.Mesh(
      new THREE.CylinderGeometry(field.rMax, field.rMax, height, 128, 1, false),
      new THREE.ShaderMaterial({
        uniforms: {
          ...shared,
          tShape: { value: texture },
          uShapeBox: { value: new THREE.Vector3(field.rMax, field.yMin, field.yMax) },
          uShapeTexel: { value: new THREE.Vector2(1 / field.width, 1 / field.height) },
          uLiquidFloor: { value: liquidFloor },
        },
        vertexShader: VERTEX,
        fragmentShader: SOLID_FRAGMENT,
      }),
    );
    mesh.name = name;
    mesh.position.set(centre.x, field.yMin + height / 2, centre.z);
    mesh.onBeforeRender = trackCamera;
    return mesh;
  };
  const lid = solid("jar-optics-lid", dims.lidProfile, { r: 0.03, below: 0.005, above: 0.03 }, 1e4);
  const foot = solid("jar-optics-foot", dims.baseProfile, { r: 0.03, below: 0.02, above: 0 }, dims.floorHeight);

  return {
    meshes: [column, lid, foot],
    column,
    solids: [lid, foot],
    uniforms: shared,
    setImages(background, specimen) {
      shared.tBackground.value = background;
      shared.tSpecimen.value = specimen;
    },
    setSize(width, height) {
      shared.uSize.value.set(width, height);
    },
    /** What lies below the jar: its block and the table under it, or the glass table at y = 0. */
    setBlocks(on) {
      if (on) shared.uBlock.value.set(PEDESTAL.height, block.radius);
      else shared.uBlock.value.set(1e-3, 1e3);
    },
    setSpecimen(position) {
      column.material.uniforms.uSpecimen.value.copy(position);
    },
    // The liquid's streaks drift only while time runs, so a paused frame stays still.
    advance(dt) {
      column.material.uniforms.uTime.value = (column.material.uniforms.uTime.value + dt) % 1000;
    },
  };
}
