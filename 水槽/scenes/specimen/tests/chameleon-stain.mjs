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

// "01" (the jar photo 01): the four classes it was fitted on (chameleon-stain.js). Green and blue are met;
// red is not met in the blue class (0.333 against 0.477) and the pale class (0.251 against 0.213).
const ab = (t) => t.map((v) => -Math.log(v));
const nearA = (got, want, tol, what) => near(ab(got), want, tol, what);
nearA(transmitted({ film: 2.91, skin: 0.269 }, { stain: "01" }), [0.333, 0.241, 0.175], 0.02, "01 の青（輪郭）");
nearA(transmitted({ film: 2.19, skin: 0.391 }, { stain: "01" }), [0.251, 0.202, 0.175], 0.02, "01 の淡い所");
nearA(transmitted({ bone: 0.1332, film: 2.29, skin: 0.599 }, { stain: "01" }), [0.868, 1.46, 1.178], 0.05, "01 の骨（赤）");
// "01" draws the organs instead of the one mass: the patches they were fitted on (C over the liver, A and B over the contents).
nearA(transmitted({ organs: { liver_r: 0.1976 } }, { stain: "01" }), [0.182, 0.254, 0.382], 0.01, "01 の肝臓（C）");
nearA(transmitted({ organs: { contents: 0.0774 } }, { stain: "01" }), [0.571, 0.574, 0.674], 0.2, "01 の中身（A。A と B の平均なので、ずれは 0.2 まで）");
nearA(transmitted({ organs: { contents: 0.0654 } }, { stain: "01" }), [0.375, 0.514, 0.718], 0.2, "01 の中身（B）");
near(transmitted({ viscera: 0.2 }, { stain: "01" }), [1, 1, 1], 1e-12, "01 では内臓の一塊を描かない");
// The film is blue in "01" (red taken most); the skin is yellowish in "06" (blue taken most).
const s1 = transmitted({ film: 4 }, { stain: "01" }), s6 = transmitted({ skin: 0.3 });
assert.ok(s1[0] < s1[2] && s6[2] < s6[0], `皮膚の色の向きが違う: 01 ${s1}, 06 ${s6}`);
// "06" stays as it was when no stain is named.
near(transmitted({ skin: 0.56 }, { stain: "06" }), transmitted({ skin: 0.56 }), 1e-12, "06 の既定");
console.log("chameleon-stain: ok");
