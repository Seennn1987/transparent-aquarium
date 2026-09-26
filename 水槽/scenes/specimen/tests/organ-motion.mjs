import assert from "node:assert/strict";
import { breathAt, createOrganMotion, heartbeat, ORGAN_RATES, organLook } from "../src/organ-motion.js";

const STEP = 1 / 60;
const DEG = Math.PI / 180;
const snapshot = (u) => JSON.stringify(Object.fromEntries(Object.entries(u).map(([k, v]) => [k, v.value])));

// A beat squeezes fast and relaxes slowly, and is back at rest before the next one.
assert.equal(heartbeat(0), 0);
assert.equal(heartbeat(0.12), 1);
assert.ok(heartbeat(0.06) > 0.4 && heartbeat(0.3) > heartbeat(0.5));
assert.equal(heartbeat(0.8), 0);

// Breathing follows SQ_Hover's ventilation.
for (const t of [0, 0.2, 0.9, 3.7]) assert.ok(Math.abs(breathAt(t) - Math.sin(2 * Math.PI * 0.75 * t)) < 1e-12);

for (const seed of [1, 5021, 77777]) {
  const organs = createOrganMotion({ seed });
  const u = organs.uniforms;
  const peaks = { branchial: [], systemic: [] };
  let last = { branchial: 0, systemic: 0 }, rising = { branchial: true, systemic: true };
  let maxTurn = 0, bites = 0, inked = false, minWave = Infinity, maxWave = -Infinity;
  let hover = 0;
  for (let t = 0; t < 90; t += STEP) {
    hover += STEP * 0.45;
    organs.update(STEP, hover);
    assert.ok(Math.abs(u.uBreath.value - breathAt(hover)) < 1e-12);
    for (const [name, value] of [["branchial", u.uBeatBranchial.value], ["systemic", u.uBeatSystemic.value]]) {
      if (rising[name] && value < last[name] && last[name] > 0.99) { peaks[name].push(t); rising[name] = false; }
      if (value > last[name]) rising[name] = true;
      last[name] = value;
    }
    maxTurn = Math.max(maxTurn, ...u.uEyeTurn.value.map(Math.abs));
    if (u.uBite.value > 0.99) bites++;
    if (u.uInk.value > 0.5) inked = true;
    minWave = Math.min(minWave, u.uGutWave.value);
    maxWave = Math.max(maxWave, u.uGutWave.value);
    assert.ok(Math.abs(u.uPupil.value) <= 1 && Math.abs(u.uLens.value) <= 1);
    assert.ok(u.uFunnelOpen.value >= 0 && u.uFunnelOpen.value <= 1);
  }
  // About 50 beats a minute, the branchial hearts first and the systemic heart a moment later.
  const period = 1 / ORGAN_RATES.heartHz;
  const gaps = peaks.branchial.slice(1).map((p, i) => p - peaks.branchial[i]);
  assert.ok(gaps.length > 60, `seed ${seed}: ${gaps.length} beats`);
  for (const g of gaps) assert.ok(Math.abs(g - period) < 2 * STEP, `seed ${seed}: beat gap ${g}`);
  const lag = peaks.systemic[0] - peaks.branchial[0];
  assert.ok(Math.abs(lag - ORGAN_RATES.systemicLag * period) < 2 * STEP, `seed ${seed}: lag ${lag}`);
  // Saccades stay small, the mouth bites, the ink sac squeezes, the gut wave covers the body.
  assert.ok(maxTurn <= ORGAN_RATES.saccadeDegrees * DEG + 1e-9 && maxTurn > 1 * DEG, `seed ${seed}: turn ${maxTurn / DEG}`);
  assert.ok(bites > 0, `seed ${seed}: never bit`);
  assert.ok(inked, `seed ${seed}: ink sac never squeezed`);
  assert.ok(minWave < ORGAN_RATES.gutFrom + 0.05 && maxWave > ORGAN_RATES.gutTo - 0.05);
}

// Paused (dt 0) nothing moves.
{
  const organs = createOrganMotion();
  for (let i = 0; i < 600; i++) organs.update(STEP, i * STEP);
  const before = snapshot(organs.uniforms);
  for (let i = 0; i < 100; i++) organs.update(0, 600 * STEP - STEP);
  assert.equal(snapshot(organs.uniforms), before);
}

// A strength of 0 stops that motion.
{
  organLook.heart.value = 0;
  organLook.eye.value = 0;
  const organs = createOrganMotion();
  for (let i = 0; i < 600; i++) {
    organs.update(STEP, i * STEP);
    assert.ok(organs.uniforms.uBeatSystemic.value === 0);
    assert.ok(organs.uniforms.uPupil.value === 0);
  }
  organLook.heart.value = 1;
  organLook.eye.value = 1;
}

console.log("organ-motion: ok");
