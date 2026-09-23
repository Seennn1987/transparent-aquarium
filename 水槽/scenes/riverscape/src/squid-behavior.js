import * as THREE from "three";
import { randomGenerator } from "./math.js";
import { BOUNDS } from "./fish.js";

// Where the squid is and which of its four Blender clips it should be playing. The clips
// swim in place; this moves the body at the speed each clip's fin beat was tuned for.
//
// The origin of the model is the mantle opening. The tail is 1 ML behind it and the
// tentacle clubs 1.3 ML ahead, so the zones keep the origin that far off the glass.
export const SQUID_ML = 1.1;
// Open water above and in front of the planting, where it hovers and cruises.
export const SWIM_ZONE = { minX: -6.4, maxX: 6.4, minY: 3.0, maxY: 6.9, minZ: -1.2, maxZ: 1.6 };
// The escape may carry it further, but never through the glass or the surface, and not
// deep into the grass at the back.
export const JET_ZONE = {
  minX: BOUNDS.minX + 1.5, maxX: BOUNDS.maxX - 1.5,
  minY: 2.2, maxY: BOUNDS.maxY - 1.1,
  minZ: -2.2, maxZ: BOUNDS.maxZ - 1.5,
};

// Speeds in ML/s, as in blender/animate_squid.py.
const CRUISE = 0.8;
const BACK = 0.8;
const JET_PEAK = 7.0;
const JET_DRAG_TIME = 0.4;
export const JET_DURATION = 4.5;
// The jet clip hands back to hovering while it is still settling.
const JET_HANDOVER = 4.0;
const HOVER_SECONDS = [4, 10];
const BACK_CHANCE = 0.25;
const SWIM_GIVE_UP = 40;
const TURN_RATE = { hover: 0.26, swim: 0.7, back: 0, jet: 5.2 };
const MAX_PITCH = 0.3;
const OBSTACLE_CLEARANCE = 1.3;
// A hand coming fast at the glass startles it; one merely resting nearby does not.
const STARTLE = { range: 4.0, approach: 3.0, close: 1.4, cooldown: 3.0 };

const smoothstep = (e0, e1, x) => {
  const t = THREE.MathUtils.clamp((x - e0) / (e1 - e0), 0, 1);
  return t * t * (3 - 2 * t);
};

/** blender/animate_squid.py jet_speed(): thrust, then water drag, then the arms brake. */
export function jetSpeed(tau) {
  if (tau < 0.3) return 0;
  const rise = smoothstep(0.3, 0.42, tau);
  const coast = 1 / (1 + Math.max(0, tau - 0.42) / JET_DRAG_TIME);
  const brake = 1 - smoothstep(2.2, 3.8, tau);
  return JET_PEAK * rise * coast * brake;
}

export const inside = (box, p, margin = 0) =>
  p.x >= box.minX + margin && p.x <= box.maxX - margin &&
  p.y >= box.minY + margin && p.y <= box.maxY - margin &&
  p.z >= box.minZ + margin && p.z <= box.maxZ - margin;

/** Distance from p along the unit direction d before it leaves the box. */
function freeRun(box, p, d) {
  let run = Infinity;
  for (const axis of ["x", "y", "z"]) {
    const min = box[`min${axis.toUpperCase()}`], max = box[`max${axis.toUpperCase()}`];
    if (d[axis] > 1e-6) run = Math.min(run, (max - p[axis]) / d[axis]);
    else if (d[axis] < -1e-6) run = Math.min(run, (min - p[axis]) / d[axis]);
  }
  return Math.max(0, run);
}

// A route is blocked by wood or stone it would come closer to than the clearance. One the
// squid is already that close to blocks only a route that would bring it closer still, so
// a squid that has drifted near the wood can always leave it.
const segmentPoint = new THREE.Vector3();
function segmentClear(obstacles, a, b) {
  for (const { center, radius } of obstacles) {
    const ab = segmentPoint.subVectors(b, a);
    const t = THREE.MathUtils.clamp(center.clone().sub(a).dot(ab) / Math.max(ab.lengthSq(), 1e-9), 0, 1);
    const nearest = a.clone().addScaledVector(ab, t).distanceTo(center);
    if (nearest < radius + OBSTACLE_CLEARANCE && nearest < a.distanceTo(center) - 1e-3) return false;
  }
  return true;
}

const headingOf = (yaw, pitch, out) =>
  out.set(Math.cos(yaw) * Math.cos(pitch), Math.sin(pitch), Math.sin(yaw) * Math.cos(pitch));

function turnToward(from, to, maxStep) {
  const delta = Math.atan2(Math.sin(to - from), Math.cos(to - from));
  return from + THREE.MathUtils.clamp(delta, -maxStep, maxStep);
}

export function createSquidPilot({ obstacles = [], seed = 40117, start } = {}) {
  const random = randomGenerator(seed);
  const range = (a, b) => a + (b - a) * random();
  const ml = SQUID_ML;
  const state = {
    mode: "hover",
    // In the middle of the tank, in front of the wood that crosses it.
    position: start ? start.clone() : new THREE.Vector3(0, 5.2, 1.4),
    velocity: new THREE.Vector3(),
    // Heading in the horizontal plane: the head points along (cos yaw, 0, sin yaw).
    yaw: Math.PI,
    pitch: 0,
    time: 0,
    until: range(...HOVER_SECONDS),
    target: new THREE.Vector3(),
    gaze: Math.PI,
    jetYaw: 0,
    cooldown: 0,
  };
  const heading = new THREE.Vector3();
  const desired = new THREE.Vector3();
  const toTarget = new THREE.Vector3();
  const candidate = new THREE.Vector3();
  const away = new THREE.Vector3();

  function hover() {
    state.mode = "hover";
    state.time = 0;
    state.until = range(...HOVER_SECONDS);
    // While it hangs in the water it slowly turns a little to look about.
    state.gaze = state.yaw + range(-0.9, 0.9);
  }

  function pickTarget() {
    for (let i = 0; i < 40; i++) {
      candidate.set(
        range(SWIM_ZONE.minX, SWIM_ZONE.maxX),
        range(SWIM_ZONE.minY, SWIM_ZONE.maxY),
        range(SWIM_ZONE.minZ, SWIM_ZONE.maxZ),
      );
      if (candidate.distanceTo(state.position) < 3) continue;
      if (!segmentClear(obstacles, state.position, candidate)) continue;
      return candidate;
    }
    return null;
  }

  function nextAfterHover() {
    headingOf(state.yaw, 0, heading);
    const behind = heading.clone().negate();
    const room = freeRun(SWIM_ZONE, state.position, behind);
    if (random() < BACK_CHANCE && room > 2.5) {
      const distance = Math.min(room - 0.5, range(1.5, 2.5));
      const end = state.position.clone().addScaledVector(behind, distance);
      if (segmentClear(obstacles, state.position, end)) {
        state.mode = "back";
        state.time = 0;
        state.until = distance / (BACK * ml);
        return;
      }
    }
    const target = pickTarget();
    if (!target) {
      hover();
      return;
    }
    state.target.copy(target);
    state.mode = "swim";
    state.time = 0;
  }

  // The escape goes tail first, away from the hand, toward the side with the most room.
  function startJet(pointer) {
    away.subVectors(state.position, pointer.position).setY(0);
    if (away.lengthSq() < 1e-6) away.set(-Math.cos(state.yaw), 0, -Math.sin(state.yaw));
    away.normalize();
    let best = -Infinity;
    for (let i = 0; i < 16; i++) {
      const yaw = (i / 16) * Math.PI * 2;
      const tail = candidate.set(-Math.cos(yaw), 0, -Math.sin(yaw));
      const room = Math.min(freeRun(JET_ZONE, state.position, tail), 6.5) / 6.5;
      const end = state.position.clone().addScaledVector(tail, room * 6.5);
      const score = tail.dot(away) + 1.5 * room - (segmentClear(obstacles, state.position, end) ? 0 : 2);
      if (score > best) {
        best = score;
        state.jetYaw = yaw;
      }
    }
    state.mode = "jet";
    state.time = 0;
  }

  function startled(pointer) {
    if (!pointer || state.mode === "jet" || state.cooldown > 0) return false;
    toTarget.subVectors(state.position, pointer.position);
    const distance = toTarget.length();
    if (distance > STARTLE.range) return false;
    const approach = pointer.velocity.dot(toTarget) / Math.max(distance, 1e-6);
    return approach > STARTLE.approach || distance < STARTLE.close;
  }

  function update(dt, pointer) {
    state.time += dt;
    state.cooldown = Math.max(0, state.cooldown - dt);
    if (startled(pointer)) startJet(pointer);

    let speedAlong = 0, response = 0.8, pitchGoal = 0, course = null;
    if (state.mode === "hover") {
      state.yaw = turnToward(state.yaw, state.gaze, TURN_RATE.hover * dt);
      if (state.time > state.until) nextAfterHover();
    } else if (state.mode === "swim") {
      toTarget.subVectors(state.target, state.position);
      const flat = Math.hypot(toTarget.x, toTarget.z);
      state.yaw = turnToward(state.yaw, Math.atan2(toTarget.z, toTarget.x), TURN_RATE.swim * dt);
      pitchGoal = THREE.MathUtils.clamp(Math.atan2(toTarget.y, Math.max(flat, 1e-3)) * 0.6, -MAX_PITCH, MAX_PITCH);
      headingOf(state.yaw, 0, heading);
      // It swings round before it sets off, and eases off over the last body length.
      const aligned = smoothstep(0.5, 0.95, heading.dot(toTarget.clone().setY(0).normalize()));
      speedAlong = CRUISE * ml * aligned * smoothstep(0.2, 1.6, toTarget.length());
      // The fins let it slip a little sideways, so it closes on the point instead of
      // circling it at its slow turning rate.
      course = toTarget.clone().normalize();
      if (toTarget.length() < 0.5 || state.time > SWIM_GIVE_UP) hover();
    } else if (state.mode === "back") {
      speedAlong = -BACK * ml;
      if (state.time > state.until || !inside(SWIM_ZONE, state.position)) hover();
    } else if (state.mode === "jet") {
      // The clip draws water in for 0.3 s before the mantle fires; the turn happens then.
      if (state.time < 0.3) state.yaw = turnToward(state.yaw, state.jetYaw, TURN_RATE.jet * dt);
      speedAlong = -jetSpeed(state.time) * ml;
      response = 0.04;
      if (state.time > JET_HANDOVER) {
        state.cooldown = STARTLE.cooldown;
        hover();
      }
    }

    state.pitch += (pitchGoal - state.pitch) * Math.min(1, dt / 1.2);
    headingOf(state.yaw, state.pitch, heading);
    desired.copy(course ?? heading).multiplyScalar(speedAlong);
    state.velocity.lerp(desired, Math.min(1, dt / response));
    // Outside its water it brakes against the glass rather than passing through.
    const box = state.mode === "jet" ? JET_ZONE : SWIM_ZONE;
    for (const axis of ["x", "y", "z"]) {
      const min = box[`min${axis.toUpperCase()}`], max = box[`max${axis.toUpperCase()}`];
      const next = state.position[axis] + state.velocity[axis] * dt;
      if ((next < min && state.velocity[axis] < 0) || (next > max && state.velocity[axis] > 0))
        state.velocity[axis] *= Math.exp(-dt * 12);
    }
    state.position.addScaledVector(state.velocity, dt);
    return state;
  }

  return { state, update };
}
