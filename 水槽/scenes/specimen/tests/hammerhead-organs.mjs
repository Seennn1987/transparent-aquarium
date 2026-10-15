import assert from "node:assert/strict";
import { createHammerheadClock, heartbeat, HH_RATES, hhOrganLook } from "../src/hammerhead-organs.js";

// シロシュモクザメ B5 の内臓の時計（hammerhead-organs.js）: 回数、一時停止で全部止まる、強さ 0 でその動きだけ止まる、同じ時刻なら同じ姿。
const STEP = 1 / 60;
const close = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol, `${msg}: ${a} と ${b}`);
const snap = (s) => JSON.stringify(s);

// 拍の形: 山（拍の位相 0.25）で 1、谷（0.75）で 0
assert.equal(heartbeat(0.25), 1);
assert.equal(heartbeat(0.75), 0);
assert.ok(heartbeat(0) > 0 && heartbeat(0) < 0.1);

// 決まった回数: 120 秒で、心臓の山は毎分 37、口は ±3° を 1.25 Hz、尾は 1.25 Hz。エラは止める（決定）
{
  const clock = createHammerheadClock();
  let beats = 0, prev = 0, rising = true, mouthMax = -Infinity, mouthMin = Infinity, mouthUp = 0, lastMouth = 0, breathMax = 0;
  for (let i = 1; i <= 120 * 60; i++) {
    const s = clock.update(STEP);
    if (rising && s.beat < prev) { beats++; rising = false; }
    if (s.beat > prev) rising = true;
    prev = s.beat;
    mouthMax = Math.max(mouthMax, s.mouthDeg); mouthMin = Math.min(mouthMin, s.mouthDeg);
    if (lastMouth < 0 && s.mouthDeg >= 0) mouthUp++;
    lastMouth = s.mouthDeg;
    breathMax = Math.max(breathMax, Math.abs(s.breath));
    assert.ok(s.beat >= 0 && s.beat <= HH_RATES.heartSqueeze + 1e-12);
  }
  close(beats, 37 * 2, 1, "心臓の山の数（120 秒）");
  close(mouthMax, 3, 0.01, "口の開く向きの最大（°）"); close(mouthMin, -3, 0.01, "口の閉じる向きの最大（°）");
  close(mouthUp, 1.25 * 120, 1, "口の開け閉めの回数（120 秒）");
  close(clock.state.tailCycles, 1.25 * 120, 1e-6, "尾の振りの回数（120 秒）");
  assert.equal(breathMax, 0, "エラは止める");
}

// 一時停止（dt = 0）: 何度進めても、姿が少しも変わらない
{
  const clock = createHammerheadClock({ ...HH_RATES, gillHz: 1.25 });
  for (let i = 0; i < 600; i++) clock.update(STEP);
  const before = snap(clock.state);
  for (let i = 0; i < 300; i++) clock.update(0);
  assert.equal(snap(clock.state), before);
}

// 強さ 0: その動きだけ止まり、ほかは動き続ける
for (const k of ["heart", "mouth", "gill"]) {
  hhOrganLook[k].value = 0;
  const clock = createHammerheadClock({ ...HH_RATES, gillHz: 1.25 });
  const seen = { beat: 0, mouthDeg: 0, breath: 0 };
  for (let i = 0; i < 600; i++) {
    const s = clock.update(STEP);
    for (const f of Object.keys(seen)) seen[f] = Math.max(seen[f], Math.abs(s[f]));
  }
  const field = { heart: "beat", mouth: "mouthDeg", gill: "breath" }[k];
  assert.equal(seen[field], 0, `${k} の強さ 0 で止まらない`);
  for (const f of Object.keys(seen)) if (f !== field) assert.ok(seen[f] > 0, `${k} の強さ 0 で ${f} まで止まった`);
  hhOrganLook[k].value = 1;
}

// 同じ時刻なら同じ姿（進め方によらない）
{
  const a = createHammerheadClock(), b = createHammerheadClock();
  for (let i = 0; i < 600; i++) a.update(STEP);
  for (let i = 0; i < 100; i++) b.update(STEP * 6);
  for (const f of ["tailCycles", "mouthDeg", "beat", "breath"]) close(a.state[f], b.state[f], 1e-9, `時刻 10 秒の ${f}`);
  const c = createHammerheadClock();
  for (const f of ["tailCycles", "mouthDeg", "beat", "breath"]) close(c.at(a.time)[f], a.state[f], 1e-9, `at(10) の ${f}`);
}

console.log("hammerhead-organs: ok");
