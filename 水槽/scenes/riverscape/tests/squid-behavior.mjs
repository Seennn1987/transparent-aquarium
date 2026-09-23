import { register } from "node:module";
import assert from "node:assert/strict";

register("./three-loader.mjs", import.meta.url);
const THREE = await import("three");
const { BOUNDS } = await import("../src/fish.js");
const { createSquidPilot, jetSpeed, inside, JET_DURATION, JET_ZONE, SQUID_ML, SWIM_ZONE } =
  await import("../src/squid-behavior.js");

const STEP = 1 / 60;
// The stones and the wood as createEnvironment() lays them out (center x, y, z, radius).
// The wood crosses the middle of the open water, which is what the squid must work round.
const OBSTACLES = [
  [4.7, 0.84, 0.35, 1.39], [-4.7, 1, -0.35, 1.19], [6.7, 0.52, -0.85, 0.86], [-6.05, 0.53, 0.55, 0.86],
  [3.25, 0.39, 1.45, 0.49], [-3.05, 0.36, 0.6, 0.41], [0.55, 0.25, -2.6, 0.37], [5.35, 0.23, 1.75, 0.34],
  [6, 0.18, 1.3, 0.31], [-2.1, 0.09, 1.55, 0.25], [3.48, 0.37, -0.15, 0.8], [3.18, 0.76, -0.25, 0.76],
  [2.89, 1.16, -0.35, 0.72], [2.56, 1.65, -0.44, 0.68], [2.11, 2.38, -0.53, 0.63], [1.65, 3.16, -0.6, 0.59],
  [1.2, 3.85, -0.68, 0.55], [0.78, 4.45, -0.75, 0.51], [0.34, 5.03, -0.82, 0.47], [-0.17, 5.59, -0.9, 0.43],
  [-0.75, 6.15, -0.98, 0.39], [-1.37, 6.66, -1.04, 0.35], [-2, 7.12, -1.06, 0.31], [-2.66, 7.54, -1.06, 0.27],
  [-3.33, 7.95, -1.05, 0.22], [2.05, 2.75, -0.5, 0.38], [2.57, 3.06, -0.02, 0.32], [3.11, 3.28, 0.5, 0.26],
  [3.59, 3.47, 0.99, 0.2], [4, 3.7, 1.4, 0.15],
].map(([x, y, z, radius]) => ({ center: new THREE.Vector3(x, y, z), radius }));

// The body reaches 1 ML behind the origin (tail) and 1.3 ML ahead of it (tentacle clubs).
const TAIL = 1.0 * SQUID_ML, CLUBS = 1.3 * SQUID_ML;
function bodyInsideTank(state) {
  const head = new THREE.Vector3(Math.cos(state.yaw) * Math.cos(state.pitch), Math.sin(state.pitch),
    Math.sin(state.yaw) * Math.cos(state.pitch));
  return [head.clone().multiplyScalar(CLUBS), head.clone().multiplyScalar(-TAIL)]
    .every((offset) => inside(BOUNDS, state.position.clone().add(offset)));
}

// The jet profile is the one the Blender clip was made with: no thrust during the intake,
// a peak of 7 ML/s just after the mantle fires, then a long drag-slowed coast.
assert.equal(jetSpeed(0.2), 0);
assert.ok(jetSpeed(0.45) > 6.5 && jetSpeed(0.45) <= 7);
assert.ok(jetSpeed(1.5) < jetSpeed(0.8) && jetSpeed(1.5) > 0);
assert.ok(jetSpeed(3.9) < 0.01);
let jetRun = 0;
for (let t = 0; t < JET_DURATION; t += STEP) jetRun += jetSpeed(t) * STEP;
assert.ok(jetRun > 5 && jetRun < 7, `jet carries ${jetRun.toFixed(2)} ML`);

// Ten undisturbed minutes: it hovers, cruises and backs up, and never leaves its water or
// swims through the wood.
{
  const pilot = createSquidPilot({ obstacles: OBSTACLES });
  const time = { hover: 0, swim: 0, back: 0, jet: 0 };
  const starts = { hover: 0, swim: 0, back: 0, jet: 0 };
  let mode = pilot.state.mode, travelled = 0, closest = Infinity;
  const last = pilot.state.position.clone();
  for (let t = 0; t < 600; t += STEP) {
    const state = pilot.update(STEP, null);
    time[state.mode] += STEP;
    if (state.mode !== mode) starts[(mode = state.mode)]++;
    travelled += state.position.distanceTo(last);
    last.copy(state.position);
    assert.ok(inside(SWIM_ZONE, state.position, -0.3), `left the open water at ${state.position.toArray()}`);
    assert.ok(bodyInsideTank(state), `body through the glass at ${state.position.toArray()}`);
    for (const { center, radius } of OBSTACLES)
      closest = Math.min(closest, state.position.distanceTo(center) - radius);
  }
  assert.equal(time.jet, 0, "no jet without a scare");
  assert.ok(starts.swim >= 15, `only ${starts.swim} cruises in ten minutes`);
  assert.ok(starts.back >= 2, `only ${starts.back} backward moves in ten minutes`);
  assert.ok(time.hover > 150 && time.hover < 450, `hovered ${time.hover.toFixed(0)} s of 600`);
  assert.ok(travelled > 150, `travelled only ${travelled.toFixed(1)}`);
  assert.ok(closest > 0.8, `came within ${closest.toFixed(2)} of wood or stone`);
}

// A hand rushing at it: it jets tail first away from the hand, keeps inside the glass,
// settles back into a hover, and is not set off again by a hand that has stopped.
{
  const pilot = createSquidPilot({ obstacles: OBSTACLES, start: new THREE.Vector3(0, 5.2, 1.4) });
  for (let t = 0; t < 1; t += STEP) pilot.update(STEP, null);
  const start = pilot.state.position.clone();
  const pointer = { position: new THREE.Vector3(-2.2, 5.2, 2.6), velocity: new THREE.Vector3(8, 0, 0) };
  pilot.update(STEP, pointer);
  assert.equal(pilot.state.mode, "jet");
  let peak = 0, maxDistance = 0;
  for (let t = 0; t < JET_DURATION; t += STEP) {
    const state = pilot.update(STEP, t < 0.2 ? pointer : null);
    peak = Math.max(peak, state.velocity.length());
    maxDistance = Math.max(maxDistance, state.position.distanceTo(start));
    assert.ok(inside(JET_ZONE, state.position, -0.3), `jet left the tank at ${state.position.toArray()}`);
    assert.ok(bodyInsideTank(state), `body through the glass during the jet at ${state.position.toArray()}`);
  }
  assert.equal(pilot.state.mode, "hover");
  assert.ok(peak > 5 * SQUID_ML, `jet peaked at only ${peak.toFixed(2)}`);
  assert.ok(maxDistance > 3, `jet carried it only ${maxDistance.toFixed(2)}`);
  assert.ok(pilot.state.position.x > start.x, "it fled toward the hand");
  const still = { position: pointer.position.clone(), velocity: new THREE.Vector3() };
  pilot.update(STEP, still);
  assert.equal(pilot.state.mode, "hover", "a resting hand at a distance does not startle it");
}

console.log("squid behavior: ok");
