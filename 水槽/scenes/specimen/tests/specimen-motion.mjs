import assert from "node:assert/strict";
import { createSpecimenMotion, MOTION } from "../src/specimen-motion.js";

const STEP = 1 / 30;
const DURATION = 30 * 60;
const DEG = Math.PI / 180;

for (const seed of [1, 4127, 99991]) {
  const motion = createSpecimenMotion({ seed });
  let maxRadius = 0, maxHeight = 0, maxSpeed = 0, maxTurnRate = 0, maxTilt = 0;
  let minYaw = Infinity, maxYaw = -Infinity, turns = 0;
  let last = { ...motion.state }, lastTargetYaw = motion.target.yaw;
  for (let t = 0; t < DURATION; t += STEP) {
    const s = motion.update(STEP);
    maxRadius = Math.max(maxRadius, Math.hypot(s.x, s.z));
    maxHeight = Math.max(maxHeight, Math.abs(s.y) + Math.abs(s.bob));
    maxSpeed = Math.max(maxSpeed, Math.hypot(s.x - last.x, s.y + s.bob - last.y - last.bob, s.z - last.z) / STEP);
    maxTurnRate = Math.max(maxTurnRate, Math.abs(s.yaw - last.yaw) / STEP);
    maxTilt = Math.max(maxTilt, Math.abs(s.pitch), Math.abs(s.roll));
    minYaw = Math.min(minYaw, s.yaw);
    maxYaw = Math.max(maxYaw, s.yaw);
    if (motion.target.yaw !== lastTargetYaw) turns++;
    lastTargetYaw = motion.target.yaw;
    last = { ...s };
  }
  // It stays well inside the jar and never touches the base or the surface.
  assert.ok(maxRadius <= MOTION.limitRadius + 1e-9, `seed ${seed}: radius ${maxRadius}`);
  assert.ok(maxHeight <= MOTION.limitHeight + MOTION.bobHeight + 1e-9, `seed ${seed}: height ${maxHeight}`);
  // It drifts, it does not swim: under 3 cm/s of jar scale, and it does move.
  assert.ok(maxSpeed < 0.03, `seed ${seed}: speed ${maxSpeed}`);
  assert.ok(maxRadius > 0.01, `seed ${seed}: never drifted`);
  // Rare turns of a few degrees, each taking seconds.
  const expectedTurns = DURATION / ((MOTION.turnEvery[0] + MOTION.turnEvery[1]) / 2);
  assert.ok(turns > expectedTurns * 0.6 && turns < expectedTurns * 1.5, `seed ${seed}: turns ${turns}`);
  assert.ok(maxTurnRate < 2 * DEG, `seed ${seed}: turn rate ${maxTurnRate / DEG} deg/s`);
  assert.ok(maxYaw - minYaw > 1 * DEG, `seed ${seed}: never turned`);
  assert.ok(maxTilt <= MOTION.tiltDegrees * DEG + 1e-9, `seed ${seed}: tilt ${maxTilt / DEG}`);
}

// Paused (rate 0 or dt 0) nothing moves.
{
  const motion = createSpecimenMotion();
  for (let i = 0; i < 300; i++) motion.update(STEP);
  const before = JSON.stringify(motion.state);
  motion.update(0);
  motion.setRate(0);
  for (let i = 0; i < 100; i++) motion.update(STEP);
  assert.equal(JSON.stringify(motion.state), before);
}

console.log("specimen-motion: ok");
