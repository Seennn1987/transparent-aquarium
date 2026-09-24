import * as THREE from "three";
import { KEY_DIRECTION, RIM_DIRECTION, STUDIO_BACKGROUND } from "./studio.js";

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
  mirror: { value: 0.5 },
};

// Soda-lime glass reads faintly green-blue through its thick parts; the liquid, barely.
const GLASS_TINT = { color: "#e4f0ec", distance: 1.2 };
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
  uniform vec3 uGlassAbsorb, uLiquidAbsorb;
  uniform float uFocus, uAperture;
  uniform vec3 uKey, uRim, uFront;
  varying vec3 vWorld;

  vec3 cameraForward() { return -vec3(viewMatrix[0][2], viewMatrix[1][2], viewMatrix[2][2]); }

  vec2 screenOf(vec3 p) {
    vec4 c = uViewProj * vec4(p, 1.);
    return c.xy / c.w * .5 + .5;
  }

  // Bends d through a surface whose normal n faces the incoming ray, eta = n1 / n2, and
  // keeps the part of the light the surface lets through. False: reflected completely.
  bool bend(inout vec3 d, vec3 n, float eta, inout vec3 carry) {
    float ci = -dot(n, d);
    float k = 1. - eta * eta * (1. - ci * ci);
    if (k < 0.) return false;
    float ct = sqrt(k);
    float r0 = (1. - eta) / (1. + eta);
    r0 *= r0;
    carry *= 1. - (r0 + (1. - r0) * pow(1. - (eta > 1. ? ct : ci), 5.));
    d = normalize(eta * d + (eta * ci - ct) * n);
    return true;
  }

  // The softbox room of createStudioEnvironment, as the glass sees it from inside.
  float softbox(vec3 d, vec3 axis, float size) {
    return smoothstep(cos(size * 1.4), cos(size * .7), dot(d, axis));
  }
  float strip(vec3 d, vec2 toward, float halfWidth, float centre, float halfHeight) {
    float level = max(length(d.xz), 1e-4);
    float across = abs(d.x * toward.y - d.z * toward.x) / level;
    return (1. - smoothstep(halfWidth, halfWidth * 2.5, across)) * step(0., dot(d.xz, toward))
      * (1. - smoothstep(halfHeight * .8, halfHeight * 1.2, abs(d.y - centre)));
  }
  vec3 studio(vec3 d) {
    float c = d.y < 0. ? .3 : .045;
    c += 4. * softbox(d, uKey, .26) + 4.5 * softbox(d, uRim, .16);
    c += 5.5 * strip(d, normalize(vec2(2.6, 4.2)), .035, .2, .42);
    c += 1.8 * strip(d, normalize(vec2(-3.6, 2.4)), .07, -.05, .4);
    c += 1.4 * smoothstep(.85, .95, d.y);
    return vec3(c);
  }

  // What lies behind: the table (y = 0) or the backdrop sphere, looked up in the background
  // image and blurred by the lens as much as its distance calls for.
  vec3 behind(vec3 p, vec3 d) {
    float t = d.y < -1e-4 ? -p.y / d.y : 1e4;
    float b = dot(p, d);
    t = min(t, -b + sqrt(max(b * b - (dot(p, p) - 576.), 0.)));
    vec3 hit = p + d * t;
    // Behind the camera: the part of the white studio the image does not hold.
    if (dot(hit - cameraPosition, cameraForward()) < .1) return uFront;
    float dist = distance(hit, cameraPosition);
    float coc = abs(1. / uFocus - 1. / dist) * uAperture * uFocus * uFocus * 2.2 * uSize.y / 1080.;
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

  vec2 cylinder(vec3 o, vec3 d, float r) {
    float a = dot(d.xz, d.xz);
    float b = dot(o.xz, d.xz);
    float h = b * b - a * (dot(o.xz, o.xz) - r * r);
    if (h < 0. || a < 1e-8) return vec2(-1.);
    h = sqrt(h);
    return vec2(-b - h, -b + h) / a;
  }
  vec3 radial(vec3 p) { return normalize(vec3(p.x, 0., p.z)); }

  void main() {
    vec3 o = cameraPosition;
    vec3 d = normalize(vWorld - o);
    vec3 carry = vec3(1.);
    vec3 light = vec3(0.);
    vec3 p;

    vec2 tc = cylinder(o, d, uRo);
    float yHit = o.y + d.y * tc.x;
    if (tc.x > 0. && yHit >= uFloor && yHit <= uTop) {
      p = o + d * tc.x;
      vec3 incoming = d;
      bend(d, radial(p), 1. / uGlassIor, carry);
      // The front face mirrors the bright studio; the softbox highlights are the wall mesh's.
      light += (1. - carry) * behind(p, reflect(incoming, radial(p)));
      vec2 ti = cylinder(p, d, uRi);
      if (ti.x <= 0.) {
        // Only the glass wall, seen edge-on.
        float tOut = cylinder(p, d, uRo).y;
        carry *= exp(-uGlassAbsorb * tOut);
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
      carry *= exp(-uGlassAbsorb * ti.x);
      p += d * ti.x;
      bend(d, radial(p), uGlassIor / uLiquidIor, carry);
    } else if (d.y < 0. && o.y > uTop) {
      p = o + d * ((uTop - o.y) / d.y);
      if (length(p.xz) > uRi) discard;
      vec3 incoming = d;
      bend(d, vec3(0., 1., 0.), 1. / uLiquidIor, carry);
      light += (1. - carry) * behind(p, reflect(incoming, vec3(0., 1., 0.)));
    } else {
      discard;
    }

    // In the liquid. The specimen is thin and hangs facing the viewer, so it is met where the
    // ray crosses the upright plane through its middle.
    vec3 facing = cameraPosition - uSpecimen;
    facing.y = 0.;
    facing = normalize(facing);
    vec3 tissue = vec3(1.);
    bool met = false;
    for (int i = 0; i < 3; i++) {
      float tWall = cylinder(p, d, uRi).y;
      float tTop = d.y > 1e-5 ? (uTop - p.y) / d.y : 1e4;
      float tBottom = d.y < -1e-5 ? (uFloor - p.y) / d.y : 1e4;
      float t = min(tWall, min(tTop, tBottom));
      float along = dot(d, facing);
      float tPlane = abs(along) > 1e-4 ? dot(uSpecimen - p, facing) / along : -1.;
      if (!met && tPlane > 0. && tPlane < t) {
        tissue = texture2D(tSpecimen, screenOf(p + d * tPlane)).rgb;
        met = true;
      }
      carry *= exp(-uLiquidAbsorb * t);
      p += d * t;
      if (t == tBottom) {
        // Down through the thick glass floor onto the table.
        carry *= exp(-uGlassAbsorb * uFloor / max(-d.y, .2));
        break;
      }
      if (t == tTop) {
        // Seen from below, the surface is a mirror past the critical angle.
        vec3 out_ = d;
        if (bend(out_, vec3(0., -1., 0.), uLiquidIor, carry)) { d = out_; break; }
        d = reflect(d, vec3(0., -1., 0.));
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
      carry *= exp(-uGlassAbsorb * tOut);
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

// The knob is a solid glass ball: it turns the room upside down.
const KNOB_FRAGMENT = /* glsl */ `
  ${COMMON}
  uniform vec3 uCentre;
  uniform float uRadius;

  void main() {
    vec3 o = cameraPosition;
    vec3 d = normalize(vWorld - o);
    vec3 oc = o - uCentre;
    float b = dot(oc, d);
    float h = b * b - (dot(oc, oc) - uRadius * uRadius);
    if (h < 0.) discard;
    vec3 p = o + d * (-b - sqrt(h));
    vec3 carry = vec3(1.);
    bend(d, normalize(p - uCentre), 1. / uGlassIor, carry);
    float t = -2. * dot(p - uCentre, d);
    carry *= exp(-uGlassAbsorb * t);
    p += d * t;
    vec3 n = -normalize(p - uCentre);
    vec3 inside = d;
    if (!bend(d, n, uGlassIor, carry)) {
      gl_FragColor = vec4(carry * mirrored(p, reflect(inside, n)), 1.);
      return;
    }
    gl_FragColor = vec4(carry * behind(p, d), 1.);
  }
`;

/**
 * Opaque stand-ins for the liquid column and the knob that draw them by ray tracing.
 * `background` and `specimen` are the images drawn from the same camera before the jar.
 */
export function createJarOptics({ dims, lens }) {
  const shared = {
    tBackground: { value: null },
    tSpecimen: { value: null },
    uViewProj: { value: new THREE.Matrix4() },
    uSize: { value: new THREE.Vector2(1, 1) },
    uGlassIor: { value: OPTICS.glassIor },
    uLiquidIor: { value: OPTICS.liquidIor },
    uMirror: OPTICS.mirror,
    uGlassAbsorb: { value: absorption(GLASS_TINT) },
    uLiquidAbsorb: { value: absorption(LIQUID_TINT) },
    uFocus: lens.focus,
    uAperture: lens.aperture,
    uKey: { value: KEY_DIRECTION.clone() },
    uRim: { value: RIM_DIRECTION.clone() },
    uFront: { value: new THREE.Color(STUDIO_BACKGROUND) },
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
      },
      vertexShader: VERTEX,
      fragmentShader: COLUMN_FRAGMENT,
    }),
  );
  column.name = "jar-optics-column";
  column.position.y = dims.floorHeight + height / 2;
  column.onBeforeRender = trackCamera;

  const knob = new THREE.Mesh(
    new THREE.SphereGeometry(dims.knobRadius * 1.004, 64, 32),
    new THREE.ShaderMaterial({
      uniforms: {
        ...shared,
        uCentre: { value: new THREE.Vector3(0, dims.knobCentre, 0) },
        uRadius: { value: dims.knobRadius },
      },
      vertexShader: VERTEX,
      fragmentShader: KNOB_FRAGMENT,
    }),
  );
  knob.name = "jar-optics-knob";
  knob.position.y = dims.knobCentre;
  knob.onBeforeRender = trackCamera;

  return {
    meshes: [column, knob],
    uniforms: shared,
    setImages(background, specimen) {
      shared.tBackground.value = background;
      shared.tSpecimen.value = specimen;
    },
    setSize(width, height) {
      shared.uSize.value.set(width, height);
    },
    setSpecimen(position) {
      column.material.uniforms.uSpecimen.value.copy(position);
    },
  };
}
