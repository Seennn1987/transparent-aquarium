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
// The neck, about 0.798 model units of tissue side-on (skinbody.py after C records 21–29, 2026-10-18; was 0.627).
near(transmitted({ skin: 0.798 }), [0.90, 0.87, 0.69], 0.03, "首の組織");
// The viscera at its thickest side-on, behind the skin: the jar photo 01's brown mass, blue 0.38.
assert.ok(Math.abs(transmitted({ viscera: 0.15, skin: 0.45 })[2] - 0.38) < 0.06, "内臓の褐色が瓶写真 01 と合わない");
near(transmitted({}), [1, 1, 1], 1e-9, "空");

// "01" (the jar photo 01): the four classes it was fitted on (chameleon-stain.js). Green and blue are met;
// red is not met in the blue class (0.336 against 0.477) and the pale class (0.251 against 0.213). The blue class's red
// is the fit's own prediction, not the photo; after C record 26 it comes out 0.315 (the shares changed with the shape).
// Rows after the hyoid rebuild (2026-10-15), times the Mac screen's after / before for the head 1.45 times, the wider
// ribcage and the smoothed skin, the limbs' stance, the rib heads, the hyoid 1.2 times, the eyes and the opened hands (C records 21–29, 2026-10-18).
const ab = (t) => t.map((v) => -Math.log(v));
const nearA = (got, want, tol, what) => near(ab(got), want, tol, what);
nearA(transmitted({ film: 2.7015, skin: 0.6394 }, { stain: "01" }), [0.315, 0.241, 0.175], 0.02, "01 の青（輪郭）");
nearA(transmitted({ film: 2.1771, skin: 0.9283 }, { stain: "01" }), [0.251, 0.202, 0.175], 0.02, "01 の淡い所");
nearA(transmitted({ bone: 0.1366, film: 2.2301, skin: 0.8999 }, { stain: "01" }), [0.868, 1.46, 1.178], 0.05, "01 の骨（赤）");
// "01" draws the organs instead of the one mass: the patches they were fitted on (C over the liver, A and B over the gut).
nearA(transmitted({ organs: { liver_r: 0.2385 } }, { stain: "01" }), [0.150, 0.231, 0.415], 0.01, "01 の肝臓（C）");
nearA(transmitted({ organs: { intestine: 0.1575 } }, { stain: "01" }), [0.494, 0.599, 0.746], 0.01, "01 の腸（A と B の平均を、画面の腸の通り道の中央値で）");
// The eye: half photo 01's ring (0.677 / 0.769 / 0.936) over the median eye path, as the producer chose (C record 26,
// "眼窩を埋めて淡く").
nearA(transmitted({ organs: { eye_r: 0.2863 } }, { stain: "01" }), [0.339, 0.385, 0.468], 0.01, "01 の目（写真 01 の輪の半分の濃さ）");
near(transmitted({ viscera: 0.2 }, { stain: "01" }), [1, 1, 1], 1e-12, "01 では内臓の一塊を描かない");
// The film is blue in "01" (red taken most); the skin is yellowish in "06" (blue taken most).
const s1 = transmitted({ film: 4 }, { stain: "01" }), s6 = transmitted({ skin: 0.3 });
assert.ok(s1[0] < s1[2] && s6[2] < s6[0], `皮膚の色の向きが違う: 01 ${s1}, 06 ${s6}`);
// The hyoid cartilage (an organ, so that it has its own strength): photo 06's throat patch less the screen's tissue there,
// over the median hyoid path (0.0328; 0.0379 after C records 21–29), and lighter in red than the rib-gap cartilage over the same path.
nearA(transmitted({ organs: { hyoid_cartilage: 0.0379 } }), [0.393, 0.135, 0.054], 0.005, "06 の舌骨の軟骨");
assert.ok(transmitted({ organs: { hyoid_cartilage: 0.0379 } })[0] > transmitted({ cartilage: 0.0379 })[0], "舌骨の軟骨が肋骨の軟骨より薄くない");
// "06" stays as it was when no stain is named.
near(transmitted({ skin: 0.627 }, { stain: "06" }), transmitted({ skin: 0.627 }), 1e-12, "06 の既定");
console.log("chameleon-stain: ok");
