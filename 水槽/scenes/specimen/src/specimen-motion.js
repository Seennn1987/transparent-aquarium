import { randomGenerator } from "../../shared/random.js";

// The specimen floats in thick preserving fluid: it barely travels. The drift is a slow
// wander toward points near the jar's centre plus a breathing bob; every so often it turns
// a few degrees about the jar's axis. A spring pulls it back well before it could reach a
// wall, the base or the surface, and the fluid's drag keeps every change unhurried.
export const MOTION = Object.freeze({
  hoverRate: 0.45,          // playback rate of SQ_Hover: fins move slowly in glycerin
  wanderRadius: 0.07,       // horizontal wander target, from the jar's axis
  wanderHeight: 0.03,
  limitRadius: 0.16,        // hard limit of the horizontal offset
  limitHeight: 0.045,       // the 1.58-tall specimen leaves ±0.07 in the liquid
  bobHeight: 0.018,
  bobPeriod: 9.5,
  wanderEvery: [9, 18],     // s between new wander targets
  turnEvery: [15, 30],      // s between small turns
  turnDegrees: 7,           // largest turn, either way
  tiltDegrees: 1.6,         // pitch/roll sway
  stiffness: 0.35,          // pull toward the current target (1/s²)
  drag: 1.4,                // fluid drag (1/s)
});

const DEG = Math.PI / 180;

function clampRadius(x, z, limit) {
  const r = Math.hypot(x, z);
  if (r <= limit) return [x, z];
  return [(x / r) * limit, (z / r) * limit];
}

export function createSpecimenMotion({ seed = 4127, rate = 1 } = {}) {
  const random = randomGenerator(seed);
  const between = ([a, b]) => a + (b - a) * random();
  const state = { x: 0, y: 0, z: 0, yaw: 0, pitch: 0, roll: 0, time: 0 };
  const velocity = { x: 0, y: 0, z: 0, yaw: 0 };
  const target = { x: 0, y: 0, z: 0, yaw: 0 };
  let nextWander = between(MOTION.wanderEvery) * 0.5;
  let nextTurn = between(MOTION.turnEvery);
  const phase = random() * Math.PI * 2;

  function sway() {
    const t = state.time + phase;
    state.bob = Math.sin((t / MOTION.bobPeriod) * Math.PI * 2) * MOTION.bobHeight;
    state.pitch = (Math.sin(t * 0.21) * 0.7 + Math.sin(t * 0.083 + 1.3) * 0.3) * MOTION.tiltDegrees * DEG;
    state.roll = (Math.sin(t * 0.17 + 2.1) * 0.7 + Math.sin(t * 0.061) * 0.3) * MOTION.tiltDegrees * DEG;
  }
  sway();

  function pickWander() {
    const angle = random() * Math.PI * 2;
    const radius = MOTION.wanderRadius * Math.sqrt(random());
    target.x = Math.cos(angle) * radius;
    target.z = Math.sin(angle) * radius;
    target.y = (random() * 2 - 1) * MOTION.wanderHeight;
  }

  function spring(key, dt, stiffness = MOTION.stiffness) {
    velocity[key] += ((target[key] - state[key]) * stiffness - velocity[key] * MOTION.drag) * dt;
    state[key] += velocity[key] * dt;
  }

  return {
    state,
    target,
    setRate(value) { rate = Math.max(0, value); },
    update(dt) {
      const step = Math.min(0.1, Math.max(0, dt)) * rate;
      if (step === 0) return state;
      state.time += step;
      nextWander -= step;
      nextTurn -= step;
      if (nextWander <= 0) {
        pickWander();
        nextWander = between(MOTION.wanderEvery);
      }
      if (nextTurn <= 0) {
        target.yaw += (random() * 2 - 1) * MOTION.turnDegrees * DEG;
        nextTurn = between(MOTION.turnEvery);
      }
      spring("x", step);
      spring("z", step);
      spring("y", step);
      spring("yaw", step, MOTION.stiffness * 0.6);

      [state.x, state.z] = clampRadius(state.x, state.z, MOTION.limitRadius);
      state.y = Math.max(-MOTION.limitHeight, Math.min(MOTION.limitHeight, state.y));

      sway();
      return state;
    },
  };
}
