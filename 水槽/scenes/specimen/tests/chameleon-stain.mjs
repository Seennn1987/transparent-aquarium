import assert from "node:assert/strict";
import { transmitted, BONE_SPECTRUM } from "../src/chameleon-stain.js";

// The stain against what was measured on 06-lightbox-calyptratus-2.jpg (chameleon-stain.js).
const near = (got, want, tol, what) =>
  got.forEach((v, i) => assert.ok(Math.abs(v - want[i]) <= tol, `${what}: ${got.map((x) => x.toFixed(2))} と測った値 ${want} の差が ${tol} を超える`));

// The mandible, 0.095 model units of bone side-on: the median along its band in the photo.
near(transmitted({ bone: 0.095 }), [0.34, 0.07, 0.11], 0.12, "下顎");
// Thin bone stays magenta: green taken most, then blue, then red.
const thin = transmitted({ bone: 0.015 });
assert.ok(thin[1] < thin[2] && thin[2] < thin[0], `細い骨の色が赤紫でない: ${thin}`);
// Absorbance keeps the alizarin's proportions at any depth.
for (const t of [0.005, 0.05, 0.3]) {
  const a = transmitted({ bone: t }).map((v) => -Math.log(v));
  a.forEach((v, i) => assert.ok(Math.abs(v / a[1] - BONE_SPECTRUM[i]) < 1e-9));
}
// The neck, about 0.56 model units of tissue side-on.
near(transmitted({ skin: 0.56 }), [0.90, 0.87, 0.69], 0.03, "首の組織");
// The viscera at its thickest side-on, behind the skin: the jar photo 01's brown mass, blue 0.38.
assert.ok(Math.abs(transmitted({ viscera: 0.15, skin: 0.45 })[2] - 0.38) < 0.06, "内臓の褐色が瓶写真 01 と合わない");
near(transmitted({}), [1, 1, 1], 1e-9, "空");
console.log("chameleon-stain: ok");
