// The chameleon walking along a branch (C record 59, 2026-10-24, the producer: 「カメレオンの特徴は目の動き方と、移動時の手足の動かし方
// です。…画面上にカメレオンが止まる枝を一本置いてそれを手足を使って歩くような動きをつけましょう」, with a photo of a veiled chameleon
// on a twig). ?walk=1 on chameleon.html. A first trial: the bones are posed in the page each frame (no clip in the glb).
//
// Where the numbers come from (C record 60, 2026-10-24, the producer: 「実際の動画や文献で歩き方（足を出す順・速さ・体の前後の揺れ）を
// 確かめ、試作を合わせて下さい」):
// - The order of the feet and the duty factor: Wimberly, Slater & Granatosky 2021 (Proc R Soc B 288:20210937), data on Zenodo
//   (record 5168016, CC0, non_mammal_gait.txt), Chamaeleo calyptratus: duty factor 65.55%, phase 44.07% (the forefoot lands
//   that share of a stride after the hindfoot of the same side), gait LSDC (lateral sequence, diagonal couplets): left hind 0,
//   left fore 0.44, right hind 0.5, right fore 0.94.
// - The speed: Krause & Fischer 2013 (J Exp Biol 216:1448–1457), C. calyptratus (snout–vent 19.5 and 21 cm) on a level 2 cm pole,
//   mean 6.9 cm/s (3.0–12.8). Higham & Jayne 2004 (J Exp Biol 207:233–248) had 17 cm/s on a 2.4 cm dowel, faster than the animals
//   chose for themselves on Krause & Fischer's pole.
// - The stride: Krause & Fischer's hindlimb forward reach, 5.9 cm at level; Higham & Jayne: the foot goes as far behind the hip as in
//   front (excursions nearly symmetric), the knee unusually extended at footfall, large pelvic rotation (57°), the limb widest out
//   at mid-swing. So the foot travels 2 × 5.9 cm against the hip in stance, a stride of 2 × 5.9 / 0.6555 = 18 cm.
// - Scaled to this animal: 1 model unit = 22.2 mm (chameleon-stain.js MODEL_UNITS_PER_MM), snout–vent about 11 cm, × 11 / 20.25:
//   the speed 3.75 cm/s, the stride 9.8 cm (4.4 units), one stride 2.6 s. The branch is 10 mm across (C record 63; Higham &
//   Jayne's 2.4 cm scaled would be 1.46 cm, Krause & Fischer's 2 cm 1.1 cm). In the walking videos of the same data (Gait_Videos, Chamaeleo_calyptratus.mp4 and _2.mp4) a
//   hindfoot stays down about 3 s while the animal walks on a deck, as slow as this.
// - The rocking: no measured study found. Described as rocking back and forth between spells of ordinary walking (Chameleo, ACM 2021,
//   "walk like a chameleon detection with AI"), triggered by a moving plant or wind (La Trobe animal behaviour group, 2017, one
//   veiled chameleon). Here: after every ROCK_EVERY strides it stops with all four feet gripping and rocks forward and back
//   ROCK_TIMES times over them (size and pace from a video, below; docs/カメレオン_歩き方の言語化_v1.0.md).
// - The eyes: each eye turns on its own, over 180° across and 80° up and down (magnetic search coils; "Visual and vestibular
//   reflexes that stabilize gaze in the chameleon", Visual Neuroscience), in quick saccades between still spells.
// Set by eye: the swing's lift, the tail, the body's height.
import * as THREE from "three";
import { MODEL_UNITS_PER_MM } from "./chameleon-stain.js";
import { chameleonEyes } from "./chameleon-material.js";

const MM = MODEL_UNITS_PER_MM;
// The branch: 10 mm across (C record 63, 2026-10-24, the producer: 「枝は案 B（直径 10 mm）にして」; Krause & Fischer's 2 cm pole scaled
// to this animal is 11 mm). ?branchMM= to try others.
const BRANCH_RADIUS = Number(new URLSearchParams(location.search).get("branchMM") ?? 10) / 2 * MM;
// ?speed= in mm/s (Krause & Fischer's mean 6.9 cm/s scaled: 37.5).
const SPEED = Number(new URLSearchParams(location.search).get("speed") ?? 37.5) * MM;   // model units per second
const DUTY = 0.6555;
const STRIDE = 98 * MM;                 // 9.8 cm (4.4 units)
// When each foot lands, as a share of the stride (LSDC; the touchdowns and lift-offs are the same pattern shifted by the duty factor).
const LIFT = { hL: 0, fL: 0.4407, hR: 0.5, fR: 0.9407 };
// The rocking pause: every ROCK_EVERY strides, ROCK_TIMES rocks of ±ROCK_SIZE at ROCK_HZ, all four feet gripping (the body moves over
// them; C record 61). Read off a video of a veiled chameleon swaying (YouTube Dy8AagHk-k8, Plantasia
// Tropical Zoo, 0–4 s, frames every 0.25 s read by eye against fixed lines): the eye goes forward and back by about 22% of the head's
// length (snout to the casque's back) peak to peak, about once a second (forward at 1.5, 2.75 and 3.5 s), while the forefoot on the
// twig stays put. This head is 42.5 mm long that way (the head bone's vertices along the head's forward axis), so ±4.7 mm at 0.9 Hz.
// ?rockMM= ?rockHz= ?rockTimes= to try others.
const _r = new URLSearchParams(location.search);
const ROCK_EVERY = 2, ROCK_TIMES = Number(_r.get("rockTimes") ?? 3), ROCK_HZ = Number(_r.get("rockHz") ?? 0.9);
const ROCK_SIZE = Number(_r.get("rockMM") ?? 4.7) * MM;
// The wrist/ankle behind the sole's grip (the foot's length to the grip): Higham & Jayne's heel to the base of the 4th toe, 1.1 cm, × 11 / 18.1 = 6.7 mm.
const HEEL = 6.7 * MM;
// The hips' height over the perch's top as a share of femur + tibia. Higham & Jayne Fig. 6B reads about 0.3–0.4 on the perch, but this
// body is deep (the belly deepened in C record 52): at 0.45 the trunk's skin sank 4–5 mm into the 10 mm branch (C record 67). 0.6 is
// the least that keeps it above the bark (0.8 mm). ?low= to try others; the shoulders BODY_LOW + 0.05 of the forelimb's.
// The foot's angle up from the branch: flat in the grip, the heel raised at lift-off (Higham & Jayne: the knee straightest at the
// end of stance, the foot pushing off). 90° (the foot upright on its toes at lift-off) is the least that lets the hind feet reach with
// the body high enough to clear the branch (C record 67: at 80° they fell 0.94 mm short).
const HEEL_DOWN = THREE.MathUtils.degToRad(15), HEEL_UP = THREE.MathUtils.degToRad(Number(new URLSearchParams(location.search).get("heelUp") ?? 90));
// The grip (C record 62): the bundles hug the bark GRIP_GAP above it, reach at most GRIP_MAX round from the top, lean forward by
// GRIP_AHEAD of their length, and open/close over GRIP_EASE of the swing at each end. Set by eye against photo 08 (?gripMax= in degrees).
const GRIP_GAP = 0.6 * MM, GRIP_AHEAD = 0.25, GRIP_EASE = 0.25;
const GRIP_MAX = THREE.MathUtils.degToRad(Number(new URLSearchParams(location.search).get("gripMax") ?? 150));
// The knee's path against the hip (C record 68): Higham & Jayne 2004 Fig. 5D (side) and 5A (from above), C. calyptratus on the level
// perch, read off the figure (400 dpi; points taken by eye, about evenly spaced in time) and scaled × 11 / 18.1, in mm: [forward, up,
// out]. The hind knees aim at it (the IK's pole); the knee then lies as near it as the leg's lengths allow. At footfall the knee is
// in front of the hip and near the midline; at mid-stance it sticks straight out to the side, level with the hip (their text: "at
// mid-stance the knee is nearly lateral to the hip"); at the end of stance it is behind the hip and a little below; in the swing it
// rises above the hip.
const HJ_KNEE = {
  stance: [[18.0, -0.3, 6.3], [16.4, -0.3, 6.6], [15.4, 0.7, 6.8], [14.1, 2.3, 7.1], [13.1, 2.5, 7.9], [11.9, 2.5, 8.8], [7.3, -1.4, 15.0],
    [-1.9, -2.9, 20.5], [-10.4, -6.6, 18.2], [-16.9, -8.5, 12.7], [-20.1, -9.2, 9.9], [-21.5, -7.0, 9.2], [-22.0, -4.3, 9.0]],
  swing: [[-21.8, -5.3, 9.1], [-19.4, -6.3, 10.2], [-14.8, -4.6, 14.9], [-3.8, -1.0, 19.8], [6.4, 5.3, 16.2], [10.0, 8.4, 11.8],
    [11.7, 7.3, 9.0], [14.1, 4.8, 7.1], [16.2, 4.0, 6.6], [16.7, 1.7, 6.5], [16.8, -0.3, 6.5], [18.0, -0.3, 6.3]],
};
const hjKnee = (part, s) => {
  const P = HJ_KNEE[part], x = Math.min(Math.max(s, 0), 1) * (P.length - 1), i = Math.min(Math.floor(x), P.length - 2), w = x - i;
  return P[i].map((v, k) => v + (P[i + 1][k] - v) * w);
};
// The hind ankle out to the leg's side of the grip, mm (C record 68): Higham & Jayne Fig. 5A has the ankle lateral to the hip in stance
// and the toes on the perch's top; 3 mm keeps it over this 10 mm branch and lifts the mid-stance knee by 0.5–1 mm (more and the
// feet fall short). ?ankleOut= to try others.
const ANKLE_OUT = Number(new URLSearchParams(location.search).get("ankleOut") ?? 3) * MM;
// The trunk's pose fitted to photo 08 (C record 85, 2026-10-26, the producer: 「この進め方で、手順 2 の姿勢合わせから始め、目標の線と重ねた絵とずれの mm を
// 見せて下さい。」; plan C record 84). ?fitSpine=1 lays the spine from the sacrum (v22) forward along the target spine line, and turns the head so its
// snout comes to the target's snout. Target frame (docs/chameleon_trunk/target_outline_p08_84.json, fit_plan_84.png): x 0 at the snout, 1 at the hip, y up,
// in snout–hip lengths of photo 08; scaled to this animal by its snout–hip length (121.5 mm) and anchored at v22 (target x 0.997, y 0.031).
// The spine line: the share of the skin's depth at which the spine lies in this model, kept inside photo 08's outline, smoothed (cubic).
const FIT_SPINE = new URLSearchParams(location.search).get("fitSpine") === "1";
const FIT_SKIN = FIT_SPINE && new URLSearchParams(location.search).get("fitSkin") === "1", FIT_SKIN_T = 6.5;
// The belly is lowered to photo 08's line only as far as FIT_CLEAR (mm) above the branch's top at FIT_SKIN_T (C record 86: at photo 08's depth the
// belly sank 6–7 mm into the 10 mm branch, and the legs cannot lift the body the 20 mm photo 08's gap would need). ?fitClear= to try others.
const FIT_CLEAR = Number(new URLSearchParams(location.search).get("fitClear") ?? 2);
// Photo 08's casque top (x 705 px, y 82 px) in the target frame.
const FIT_CASQUE = [(705 - 50) / 1550, (392 - 82) / 1550];
const FIT_SH_MM = 121.5, FIT_X22 = 0.9969, FIT_Y22 = 0.0310;
const FIT_SPINE_X = [0.28, 0.3, 0.32, 0.34, 0.36, 0.38, 0.4, 0.42, 0.44, 0.46, 0.48, 0.5, 0.52, 0.54, 0.56, 0.58, 0.6, 0.62, 0.64, 0.66, 0.68, 0.7, 0.72, 0.74, 0.76, 0.78, 0.8, 0.82, 0.84, 0.86, 0.88, 0.9, 0.92, 0.94, 0.96, 0.98];
const FIT_SPINE_Y = [-0.0896, -0.0665, -0.0449, -0.0249, -0.0062, 0.0109, 0.0267, 0.0412, 0.0543, 0.0662, 0.0768, 0.0861, 0.0943, 0.1014, 0.1074, 0.1122, 0.1161, 0.1189, 0.1208, 0.1218, 0.1218, 0.121, 0.1194, 0.117, 0.1138, 0.1099, 0.1053, 0.1001, 0.0942, 0.0878, 0.0808, 0.0733, 0.0654, 0.057, 0.0482, 0.039];
// Photo 08's outline in the same frame (for measuring, chameleonPage.walkOutline).
const FIT_OUT_X = [0.0, 0.02, 0.04, 0.06, 0.08, 0.1, 0.12, 0.14, 0.16, 0.18, 0.2, 0.22, 0.24, 0.26, 0.28, 0.3, 0.32, 0.34, 0.36, 0.38, 0.4, 0.42, 0.44, 0.46, 0.48, 0.5, 0.52, 0.54, 0.56, 0.58, 0.6, 0.62, 0.64, 0.66, 0.68, 0.7, 0.72, 0.74, 0.76, 0.78, 0.8, 0.82, 0.84, 0.86, 0.88, 0.9, 0.92, 0.94, 0.96, 0.98, 1.0, 1.02, 1.04, 1.06, 1.08, 1.1, 1.12, 1.14, 1.16];
const FIT_OUT_TOP = [0.0045, 0.0238, 0.0388, 0.0504, 0.0607, 0.0709, 0.0834, 0.093, 0.1007, 0.1107, 0.1201, 0.1279, 0.1374, 0.1473, 0.1551, 0.164, 0.1743, 0.183, 0.1899, 0.1948, 0.1982, 0.199, 0.1251, 0.1254, 0.1416, 0.1558, 0.168, 0.1784, 0.1858, 0.1914, 0.1973, 0.2008, 0.2022, 0.2037, 0.2045, 0.2045, 0.204, 0.2015, 0.1996, 0.1972, 0.1932, 0.1869, 0.1781, 0.1682, 0.1582, 0.1483, 0.1349, 0.121, 0.1093, 0.0962, 0.0819, 0.0687, 0.0513, 0.0276, 0.0151, 0.0064, -0.0013, -0.0109, -0.0236];
const FIT_OUT_BOT = [-0.0052, -0.028, -0.0482, -0.066, -0.0811, -0.0943, -0.1063, -0.1182, -0.1302, -0.1422, -0.1542, -0.1662, -0.1789, -0.1898, -0.1963, -0.2004, -0.203, -0.2048, -0.2063, -0.2082, -0.2109, -0.2151, -0.2281, -0.2439, -0.2584, -0.2639, -0.267, -0.2693, -0.2697, -0.2697, -0.2681, -0.2658, -0.2639, -0.2605, -0.2563, -0.2523, -0.2483, -0.2443, -0.2403, -0.2362, -0.232, -0.2296, -0.2276, -0.224, -0.2182, -0.2074, -0.1926, -0.1754, -0.1572, -0.1397, -0.1244, -0.1129, -0.1065, -0.1028, -0.099, -0.0946, -0.0879, -0.0842, -0.0826];
// The trunk's shape fitted to the young and walking animals (C record 89, 2026-10-26, the producer: 「案 1（今の個体の年齢のまま、深さ 0.31〜0.38、
// 若い個体と床を歩く成体の形）で、B〜E の修正を進めて下さい。」; plan C record 88). ?shape=88 reshapes the meshes once at load (shape88()).
// Target (docs/chameleon_trunk/target_outline_88.json): the median back and belly lines of 4 young animals and the adult walking on the floor in
// Wimberly et al. 2021's video (t 309 s), traced in the frame x 0 at the snout, 1 at the hip, y up (snout–hip lengths), x 0.3–1.25 every 0.025.
// Since C record 90 (2026-10-26, the producer: 「この形（?shape=88）を本番にして、静止の形に焼き込んで下さい。」) the shape is baked into
// specimen_chameleon.glb by page_check/bake_shape88.py, which runs ?shape=88 on the glb before baking (assets/private/proposals/pre_shape88.glb).
// A baked glb (asset.extras.chameleon_shape88) is not reshaped again.
const SHAPE88 = new URLSearchParams(location.search).get("shape") === "88";
const SHAPE_X0 = 0.3, SHAPE_DX = 0.025;
// The belly line from under the snout (x 0) to the tail (1.25), every VENT_DX: the same 5 animals' median, smoothed (C record 92).
const VENT_DX = 0.025, VENT_BOT = [-0.0443, -0.0551, -0.0695, -0.0810, -0.0887, -0.0944, -0.0991, -0.1028, -0.1057, -0.1081, -0.1100, -0.1113, -0.1115, -0.1109, -0.1092, -0.1062, -0.1031, -0.1011, -0.1016, -0.1030, -0.1038, -0.1029, -0.1009, -0.0988, -0.0968, -0.0953, -0.0938, -0.0922, -0.0903, -0.0884, -0.0866, -0.0849, -0.0835, -0.0821, -0.0806, -0.0784, -0.0754, -0.0722, -0.0699, -0.0687, -0.0672, -0.0634, -0.0561, -0.0462, -0.0352, -0.0250, -0.0164, -0.0101, -0.0058, -0.0035, -0.0027];
// The trunk's depth (back to belly) along x 0.3–1.25 every SHAPE_DX: the same 5 animals' median, smoothed (C record 94). The belly is set this far
// under the model's own back, so a back higher than theirs (the arch, the spines) no longer leaves the belly low (C record 93).
const SHAPE_DEPTH = [0.2549, 0.2608, 0.2696, 0.2778, 0.2828, 0.2850, 0.2866, 0.2888, 0.2915, 0.2938, 0.2954, 0.2962, 0.2965, 0.2963, 0.2953, 0.2932, 0.2898, 0.2851, 0.2793, 0.2729, 0.2664, 0.2598, 0.2531, 0.2457, 0.2372, 0.2264, 0.2125, 0.1957, 0.1772, 0.1585, 0.1408, 0.1233, 0.1072, 0.0932, 0.0837, 0.0776, 0.0734, 0.0691, 0.0662];
// The throat's skin this far (mm) under the lowest of the lower jaw, the hyoid and its cartilage: photo 06 (the cleared specimen) has it 0.7–1.7 mm
// under the lower jaw (C record 93).
const THROAT_MM = 1.5;
// The belly's line (C record 95, 2026-10-27, the producer: 「今度はお腹が地面に対して全体的にくぼんでいます。これはやりすぎです。限りなく水平に近いながら胴体
// として丸みは維持していないと現実的ではありません」): the back less the traced depth followed the back's arch and bowed the belly up in the middle. Now a
// gentle curve, lowest at BELLY_LOW_X, rising BELLY_RISE_MM[0] toward the chest (x 0.42) and BELLY_RISE_MM[1] toward the hip (x 1.0), squared in x;
// its height so that the mean depth over x 0.45–0.75 is the traced one, but at least GIRDLE_CLEAR_MM under the girdles (the pelvis at x 0.95–1.02 stood
// 4.7 mm under the snout–hip line: the traced animals' belly hangs 0.096 of the snout–hip length, 11.7 mm, under the hip joint; this model's back stands
// 5 mm higher over it, so the depth alone lifted the belly to the pelvis and bent it there). Behind x 1.0 it goes up to the tail's base. The traced animals: lowest at x 0.5–0.65, up 1.5–4 mm to x 0.42 and, young
// and walking, 2–6.5 mm to x 1.0 (one 10.8); 13 of 14 bulge down (quadratic term +), this model's did not (−0.24).
const BELLY_LOW_X = 0.6, BELLY_RISE_MM = [2.5, 2.0], GIRDLE_CLEAR_MM = 1.5;
const bellyBow = (x) => { const r = (x < BELLY_LOW_X ? BELLY_RISE_MM[0] / (BELLY_LOW_X - 0.42) ** 2 : BELLY_RISE_MM[1] / (1.0 - BELLY_LOW_X) ** 2) / FIT_SH_MM; return r * (x - BELLY_LOW_X) ** 2; };
const SHAPE_TOP = [0.1972, 0.1974, 0.2002, 0.2043, 0.2103, 0.2152, 0.2197, 0.2230, 0.2253, 0.2267, 0.2274, 0.2274, 0.2268, 0.2258, 0.2242, 0.2216, 0.2172, 0.2112, 0.2049, 0.1997, 0.1963, 0.1936, 0.1909, 0.1873, 0.1830, 0.1777, 0.1705, 0.1594, 0.1432, 0.1225, 0.1022, 0.0855, 0.0751, 0.0673, 0.0613, 0.0589, 0.0587, 0.0604, 0.0602];
const SHAPE_BOT = [-0.1115, -0.1108, -0.1092, -0.1062, -0.1031, -0.1011, -0.1016, -0.1030, -0.1038, -0.1029, -0.1009, -0.0988, -0.0968, -0.0953, -0.0938, -0.0922, -0.0903, -0.0884, -0.0866, -0.0849, -0.0835, -0.0821, -0.0806, -0.0784, -0.0754, -0.0722, -0.0699, -0.0687, -0.0672, -0.0634, -0.0561, -0.0462, -0.0352, -0.0250, -0.0164, -0.0101, -0.0058, -0.0035, -0.0027];
// With the trunk of C record 89 (baked into the glb since C record 90) the belly is shallower, and the hips come down to 0.4 of the leg's reach
// (14.4 mm), putting the belly 1.7–3.0 mm over the branch while walking: the adults traced in C record 88 hold it 0.02 of the snout–hip length
// (2.5 mm) above; Krause & Fischer 2013 the hip 0.114 SVL. (0.6 before, for the deeper belly; ?low= to try others.) With the arched back of C record 91
// the belly sat 0.6–1.9 mm over at 0.4, so 0.43 (1.9–3.2 mm); with the belly line of C record 92 it sits 2.9–4.3 mm over at 0.43, so 0.4 again.
// C record 94 raised the belly 6–9 mm (the traced trunk's depth under the back): the hips at 0.32 (11.5 mm, 0.112 SVL: Krause & Fischer's 0.114),
// the belly 6.3–7.8 mm over (the young animal traced over a branch, IN240: 0.05 of the snout–hip length, 6 mm). 0.25 would bring it to 3.8–5.1 mm.
const BODY_LOW = Number(new URLSearchParams(location.search).get("low") ?? 0.32);
// ?neck=<degrees>: the head pitched by this much more, shared evenly by the 5 neck vertebrae v01–v05 (Molnar & Watanabe 2023: C1–C5), + snout down.
const NECK_DEG = Number(new URLSearchParams(location.search).get("neck") ?? 0);
// The back's arch (C record 91, 2026-10-26, the producer: 「背中のアールも足りていない。」): the trunk's spine bent into an arch with level ends. The
// back of the 22 traced animals stands above its chord from x 0.4 to 1.0 by 0.078 of the snout–hip length (young and walking, median; adults 0.099),
// highest at x 0.70–0.725; this model's by 0.047 at x 0.625. ARCH_DEG tilts v21 up by that much, bends v20–v06 back down by twice it (shared as
// sin(π u)), and turns the neck (v05–v01, a fifth each) up by it again, so the shoulders keep their height and the head its direction. Measured from x 0.45 (clear of the
// casque's back edge) the young and walking animals' arch is 0.067 (adults 0.088); the model's 0.035 at 0°, 0.064 at 12°, 0.074 at 16°: 14°. ?arch=<degrees>.
const ARCH_DEG = Number(new URLSearchParams(location.search).get("arch") ?? 14);
const SWING_LIFT = 0.35, SWING_OUT = 0.45;   // model units: how high and how far out the foot travels at mid-swing
// The girdles' turn about the vertical, each way: the pelvis Higham & Jayne's 57° in all on the level (±28.5°, C record 67; it was ±20),
// largest at footfall; the shoulders set by eye.
const _y = new URLSearchParams(location.search);
const PELVIS_YAW = THREE.MathUtils.degToRad(Number(_y.get("pelvisYaw") ?? 28.5)), SHOULDER_YAW = THREE.MathUtils.degToRad(Number(_y.get("shoulderYaw") ?? 12));
const _q = new URLSearchParams(location.search);
// degrees, degrees, the share of its length before it bends; set by eye (?tailStart= ?tailTurn= ?tailStraight= to try others)
// C record 71 (2026-10-25, the producer, with frames of the walking video: 「丸々方向が逆だし、丸々量が少なすぎるし、のばしている部分も
// そんなに直線的ではないはずです」). Read off the research video (Wimberly et al. 2021, Gait_Videos/Chamaeleo_calyptratus.mp4, 272–283 s,
// a veiled chameleon walking along a door, side view): the tail leaves the rump along the back's line, a little downward, then bends
// up in a smooth arc to rise some 50° behind the body, and its last part rolls into a spiral that turns toward the belly (back, down,
// forward and up again; with the head to the right, counterclockwise), about one and a quarter turns, tighter toward the tip. The coil
// holds its shape while walking. Heading θ (direction = cos θ · FORWARD + sin θ · UP; 180° = straight back):
//   θ(u) = TAIL_START + TAIL_ARC · smooth(u / TAIL_ARC_END) + TAIL_COIL · k^1.6,  k = (u − TAIL_COIL_AT) / (1 − TAIL_COIL_AT) past TAIL_COIL_AT
// (u: share of the tail's length from the base). Set by eye against that video. ?tailStart= ?tailArc= ?tailArcEnd= ?tailCoil= ?tailCoilAt=.
// C record 70's (straight, the tip turned the other way) is tailStart=170&tailArc=0&tailCoil=-200&tailCoilAt=0.75.
// Of three tried side by side with the video frame at 280 s, this one (rising most steeply, the coil one and a third turns) is nearest.
// C record 75 (the producer: 「尻尾の付け根の方のアールが大きすぎて参考動画より尻尾が立ちすぎている」): the arc −110° over 45% → −80° over 50%
// (of three tried against the video frame at 280 s, the nearest; the tail rises at about 40–45° as in the video).
const TAIL_START = Number(_q.get("tailStart") ?? 200), TAIL_ARC = Number(_q.get("tailArc") ?? -80), TAIL_ARC_END = Number(_q.get("tailArcEnd") ?? 0.5);
const TAIL_MOTION = _q.get("tailMotion") !== "0";
// Halved (C record 74, the producer: 「今度は動きが大きすぎるのではないでしょうか？」; record 73 had 3°, 5°, 0.12, 18°).
const TAIL_SIDE_DEG = Number(_q.get("tailSide") ?? 1.5), TAIL_LAG = Number(_q.get("tailLag") ?? 0.25), TAIL_BOB_DEG = Number(_q.get("tailBob") ?? 2.5);
const TAIL_COIL_VAR = Number(_q.get("tailCoilVar") ?? 0.06), TAIL_TILT_DEG = Number(_q.get("tailTilt") ?? 9);
const TAIL_COIL = Number(_q.get("tailCoil") ?? 500), TAIL_COIL_AT = Number(_q.get("tailCoilAt") ?? 0.45);
const EYE_YAW = THREE.MathUtils.degToRad(80), EYE_PITCH = THREE.MathUtils.degToRad(35);

// Model frame (the glb's, the jar pose): dorsal −X, forward −Y (toward the head), left +Z.
const UP = new THREE.Vector3(-1, 0, 0), FORWARD = new THREE.Vector3(0, -1, 0), LEFT = new THREE.Vector3(0, 0, 1);

/**
 * `model`: the glb's scene (posed by CH_Hover at t = 0, the base for the bones not walked); `holder`: its parent, whose frame is the
 * model frame. Returns { backdrop, update(t) }: the branch scene (drawn behind the specimen) and the per-frame pose.
 */
export function createChameleonWalk(model, holder) {
  let skinned = null;
  model.traverse((o) => { if (o.isSkinnedMesh && !skinned) skinned = o; });
  const bones = Object.fromEntries(skinned.skeleton.bones.map((b) => [b.name, b]));
  const base = new Map(skinned.skeleton.bones.map((b) => [b, b.quaternion.clone()]));
  model.updateMatrixWorld(true);
  const inHolder = (b) => holder.worldToLocal(b.getWorldPosition(new THREE.Vector3()));

  // The limbs: girdle (or none) → upper → lower → hand/foot, with their lengths in the base pose.
  const limbs = {};
  for (const [key, end] of [["fL", "hand"], ["fR", "hand"], ["hL", "foot"], ["hR", "foot"]]) {
    const upper = bones[`${key}_upper`], lower = bones[`${key}_lower`], tip = bones[`${key}_${end}`];
    const a = inHolder(upper).distanceTo(inHolder(lower)), b = inHolder(lower).distanceTo(inHolder(tip));
    // The digit bundles' bones (glb with chameleon_digit_bones.py, C record 62): each bundle's two segments and its tip point.
    const bundle = (side) => {
      const b1 = bones[`${tip.name}_${side}1`], b2 = bones[`${tip.name}_${side}2`], e = bones[`${tip.name}_${side}_end`];
      return b1 && b2 && e ? { b1, b2, e, l1: inHolder(b1).distanceTo(inHolder(b2)), l2: inHolder(b2).distanceTo(inHolder(e)) } : null;
    };
    limbs[key] = { upper, lower, tip, a, b, hind: key[0] === "h", left: key[1] === "L", med: bundle("med"), lat: bundle("lat") };
  }
  // Where the body sits over the branch: the hips and shoulders at BODY_LOW and BODY_LOW + 0.05 of their limbs' reach above its top.
  const mid = (p, q) => p.clone().add(q).multiplyScalar(0.5);
  const hip = mid(inHolder(limbs.hL.upper), inHolder(limbs.hR.upper));
  const shoulder = mid(inHolder(limbs.fL.upper), inHolder(limbs.fR.upper));
  const hipH = BODY_LOW * (limbs.hL.a + limbs.hL.b), shoulderH = (BODY_LOW + 0.05) * (limbs.fL.a + limbs.fL.b);
  // Pitch the body (about LEFT) so the shoulders sit shoulderH − hipH higher than the hips.
  const along = shoulder.clone().sub(hip);
  const pitch = Math.atan2(shoulderH - hipH, along.dot(FORWARD)) - Math.atan2(along.dot(UP), along.dot(FORWARD));
  const bodyTurn = new THREE.Quaternion().setFromAxisAngle(LEFT, -pitch);
  const hipTurned = hip.clone().applyQuaternion(bodyTurn);
  // The branch's top line runs along FORWARD under the midline, hipH below the hips.
  const midZ = hip.z;
  const branchTop = hipTurned.dot(UP) - hipH;   // height (along UP) of the branch's top
  const branchCentre = new THREE.Vector3().addScaledVector(UP, branchTop - BRANCH_RADIUS);
  branchCentre.z = midZ;

  // The branch, drawn behind the specimen (chameleon-material.js render's backdrop), in the holder's frame.
  const backdrop = new THREE.Scene();
  const branchFrame = new THREE.Group(); backdrop.add(branchFrame);
  const bark = new THREE.MeshStandardMaterial({ color: 0x8a6a52, roughness: 0.9 });
  const branch = new THREE.Mesh(new THREE.CylinderGeometry(BRANCH_RADIUS, BRANCH_RADIUS * 1.1, 60, 24, 1), bark);
  branch.position.copy(branchCentre);   // CylinderGeometry runs along its Y, as FORWARD does (−Y)
  branchFrame.add(branch);
  // Knots along it, so its sliding back can be seen (the animal stays in the middle of the screen).
  const knots = new THREE.Group(); branchFrame.add(knots);
  const knotGeo = new THREE.SphereGeometry(BRANCH_RADIUS * 0.45, 12, 8), knotMat = new THREE.MeshStandardMaterial({ color: 0x5e4433, roughness: 1 });
  const KNOT_GAP = 2.3;
  for (let i = -12; i <= 12; i++) {
    const k = new THREE.Mesh(knotGeo, knotMat);
    const ang = i * 2.1;
    k.position.copy(branchCentre).addScaledVector(UP, Math.cos(ang) * BRANCH_RADIUS * 0.9).addScaledVector(LEFT, Math.sin(ang) * BRANCH_RADIUS * 0.9);
    k.position.y += i * KNOT_GAP;
    k.scale.set(1, 1.8, 1);
    knots.add(k);
  }
  backdrop.add(new THREE.HemisphereLight(0xffffff, 0x8a8478, 2.2));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(-3, 2, 5); backdrop.add(sun);

  // Where each foot lands, on top of the branch, a little to its own side of the midline.
  const plantAt = (limb, along) => {
    const side = (limb.left ? 1 : -1) * BRANCH_RADIUS * 0.35;
    return branchCentre.clone().addScaledVector(UP, BRANCH_RADIUS * 0.95).addScaledVector(LEFT, side).addScaledVector(FORWARD, along);
  };
  // Each foot's landing spot ahead of its girdle at rest (Higham & Jayne: well in front of the hip at footfall).
  function girdleAlongOf(limb) { return inHolder(limb.upper).applyQuaternion(bodyTurn).dot(FORWARD); }
  // C record 61 (the producer: 「揺れの時は足を軸にして動きます。足が木をスライドするように滑るような動きをするわけないでしょ」): this was
  // read from the girdle's position in every frame, so the landing spot — and with it every planted foot — moved with the body's
  // rocking and the girdles' turning, and the feet slid on the branch. It is the girdle's place in the base pose, fixed.
  // The trunk's span along the branch (between the hips and the shoulders), for belly().
  const trunkBack = Math.min(girdleAlongOf(limbs.hL), girdleAlongOf(limbs.hR)) + 0.3, trunkFront = Math.max(girdleAlongOf(limbs.fL), girdleAlongOf(limbs.fR)) - 0.3;
  const girdleRest = Object.fromEntries(Object.entries(limbs).map(([key, limb]) => [key, inHolder(limb.upper).applyQuaternion(bodyTurn).dot(FORWARD)]));

  // Eyes: each one's own target and saccade.
  const eyes = [0, 1].map((i) => ({ yaw: 0, pitch: 0, fromYaw: 0, fromPitch: 0, toYaw: 0, toPitch: 0, start: 0, next: 0.5 + i * 0.8 }));
  const rng = (() => { let s = 7; return () => { s = (s * 16807) % 2147483647; return s / 2147483647; }; })();

  const q = new THREE.Quaternion(), v = new THREE.Vector3(), w = new THREE.Vector3();
  // Turn `bone` (in world) so that the direction from it to `from` (a world point now) points to `to`.
  function aim(bone, from, to) {
    const p = bone.getWorldPosition(new THREE.Vector3());
    const d0 = from.clone().sub(p).normalize(), d1 = to.clone().sub(p).normalize();
    const turn = new THREE.Quaternion().setFromUnitVectors(d0, d1);
    const world = bone.getWorldQuaternion(new THREE.Quaternion()).premultiply(turn);
    const parent = bone.parent.getWorldQuaternion(new THREE.Quaternion());
    bone.quaternion.copy(parent.invert().multiply(world));
    bone.updateMatrixWorld(true);
  }
  const toWorld = (p) => holder.localToWorld(p.clone());
  const tail = [];
  for (let i = 24; bones[`v${i}`]; i++) tail.push(bones[`v${i}`]);
  const tailSeg = tail.slice(1).map((bone, i) => inHolder(bone).distanceTo(inHolder(tail[i])));
  const tailLength = tailSeg.reduce((x, y) => x + y, 0);
  // Each tail bone's rest orientation and rest direction (to the next joint) in the holder's frame, for laying it on the curve without
  // twisting (C record 69: turning each bone by the shortest turn from where it pointed rolled some 128° about their own axes where
  // the jar's coil bends the other way, and the tip looked broken off).
  const holderQ = () => holder.getWorldQuaternion(new THREE.Quaternion());
  const tailRestQ = tail.map((bone) => holderQ().invert().multiply(bone.getWorldQuaternion(new THREE.Quaternion())));
  const tailRestT = tail.map((bone, i) => (i + 1 < tail.length ? inHolder(tail[i + 1]).sub(inHolder(bone)).normalize() : null));
  tailRestT[tail.length - 1] = tailRestT[tail.length - 2];
  // A frame from a direction: the tangent, and the body's left axis made square to it (the coil lies in the body's side plane).
  const frameOf = (t) => {
    const n = LEFT.clone().addScaledVector(t, -LEFT.dot(t)).normalize(), b = t.clone().cross(n);
    return new THREE.Matrix4().makeBasis(t, n, b);
  };
  const tailRestFrame = tailRestT.map(frameOf);
  function setHolderQuat(bone, qHolder) {
    const world = holderQ().multiply(qHolder);
    bone.quaternion.copy(bone.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(world));
    bone.updateMatrixWorld(true);
  }
  // The tail's motion while walking (C record 73, from the videos of C record 72; docs/カメレオン_歩き方の言語化_v1.0.md 8.2b), on top of the shape:
  // 1. side to side with the pelvis's turn, opposite to it, starting at the base and reaching the tip TAIL_LAG of a stride later,
  //    growing toward the tip: ±TAIL_SIDE_DEG at the base … ±2 × that at the tip (the tip moves by about a centimetre);
  // 2. the arc rises and falls by ±TAIL_BOB_DEG twice a stride, highest just after each hind foot lands;
  // 3. the coil tightens/loosens by ±TAIL_COIL_VAR and tilts by ±TAIL_TILT_DEG, slowly and unevenly (three waves of 2.3, 3.7 and 5.9 s),
  //    whether walking or not. All set by eye against the videos (their numbers are read by eye). ?tailMotion=0 holds the tail still.
  function layTail(t, phase, walking) {
    model.updateMatrixWorld(true);
    let at = holder.worldToLocal(tail[0].getWorldPosition(new THREE.Vector3())), s = 0;
    const on = TAIL_MOTION ? 1 : 0, w = on * walking;
    const slow = (a, b, c) => (Math.sin(2 * Math.PI * t / 2.3 + a) + 0.7 * Math.sin(2 * Math.PI * t / 3.7 + b) + 0.5 * Math.sin(2 * Math.PI * t / 5.9 + c)) / 2.2;
    const coilScale = 1 + on * TAIL_COIL_VAR * slow(0.3, 1.9, 4.1), tilt = on * TAIL_TILT_DEG * slow(2.2, 0.4, 5.3);
    const bob = w * TAIL_BOB_DEG * Math.cos(4 * Math.PI * (phase - LIFT.hL - 0.08));
    for (let i = 0; i < tailSeg.length; i++) {
      const u = (s + tailSeg[i] / 2) / tailLength;
      const k = Math.max(0, (u - TAIL_COIL_AT) / (1 - TAIL_COIL_AT));   // 0 → 1 along the coiled part
      const a = Math.min(1, u / TAIL_ARC_END), arc = a * a * (3 - 2 * a);
      const kk = Math.min(1, k * 4), coilIn = kk * kk * (3 - 2 * kk);
      const theta = THREE.MathUtils.degToRad(TAIL_START + (TAIL_ARC - bob) * arc + TAIL_COIL * coilScale * k ** 1.6 + tilt * coilIn);
      const side = -w * THREE.MathUtils.degToRad(TAIL_SIDE_DEG) * (1 + u) * Math.sin(2 * Math.PI * (phase - LIFT.hL - 0.25 - TAIL_LAG * u));
      const dir = FORWARD.clone().multiplyScalar(Math.cos(theta)).addScaledVector(UP, Math.sin(theta)).addScaledVector(LEFT, Math.tan(side)).normalize();
      // The turn that takes the rest frame to the frame along the curve, applied to the bone's rest orientation (no roll).
      const R = frameOf(dir).multiply(tailRestFrame[i].clone().transpose());
      setHolderQuat(tail[i], new THREE.Quaternion().setFromRotationMatrix(R).multiply(tailRestQ[i]));
      at.addScaledVector(dir, tailSeg[i]); s += tailSeg[i];
      if (i === tailSeg.length - 1) setHolderQuat(tail[i + 1], new THREE.Quaternion().setFromRotationMatrix(R).multiply(tailRestQ[i + 1]));
    }
  }

  // The snout tip in the head bone's frame: the most forward point of the head's skin in the walking pose before the fit (taken once, on the first
  // fit; in the jar pose the head hangs down, and the head bone's axis is not the skull's line). For FIT_SPINE.
  let snoutLocal = null, casqueLocal = null;
  function findSnout() {
    let sk = null; model.traverse((o) => { if (o.isSkinnedMesh && o.userData.chameleon_part === "Skin") sk = o; });
    const hi = sk.skeleton.bones.indexOf(bones.head), SI = sk.geometry.getAttribute("skinIndex"), SW = sk.geometry.getAttribute("skinWeight");
    const p = new THREE.Vector3(); let best = -Infinity;
    for (let i = 0; i < SI.count; i++) {
      if (SI.getX(i) !== hi || SW.getX(i) < 0.9) continue;
      sk.getVertexPosition(i, p); sk.localToWorld(p); const f = holder.worldToLocal(p.clone()).dot(FORWARD);
      if (f > best) { best = f; snoutLocal = bones.head.worldToLocal(p.clone()); }
    }
    best = -Infinity;   // the casque's top: the highest point of the head's skin
    for (let i = 0; i < SI.count; i++) {
      if (SI.getX(i) !== hi || SW.getX(i) < 0.9) continue;
      sk.getVertexPosition(i, p); sk.localToWorld(p); const u = holder.worldToLocal(p.clone()).dot(UP);
      if (u > best) { best = u; casqueLocal = bones.head.worldToLocal(p.clone()); }
    }
  }
  const fitPoint = (anchor, x, y) => anchor.clone().addScaledVector(FORWARD, (FIT_X22 - x) * FIT_SH_MM * MM).addScaledVector(UP, (y - FIT_Y22) * FIT_SH_MM * MM);
  // Lay v22 → v01 → head along the target spine line (each joint at its bone's length along the line from the one behind), then turn the head to
  // the target's snout (x 0, y 0: where photo 08's back and belly lines meet).
  // Turn `bone` about the body's left–right axis only (no roll or yaw), so that the direction from it to `from` (holder frame) points as `to` does
  // seen from the side.
  function aimSide(bone, from, to) {
    const o = inHolder(bone), a = from.clone().sub(o), c = to.clone().sub(o);
    a.addScaledVector(LEFT, -a.dot(LEFT)); c.addScaledVector(LEFT, -c.dot(LEFT));
    if (a.lengthSq() < 1e-12 || c.lengthSq() < 1e-12) return;
    const ang = Math.atan2(a.clone().cross(c).dot(LEFT), a.dot(c));
    const local = LEFT.clone().transformDirection(holder.matrixWorld).applyQuaternion(bone.parent.getWorldQuaternion(new THREE.Quaternion()).invert());
    bone.quaternion.premultiply(new THREE.Quaternion().setFromAxisAngle(local, ang)); bone.updateMatrixWorld(true);
  }
  function laySpine() {
    model.updateMatrixWorld(true);
    if (!snoutLocal) findSnout();
    const anchor = inHolder(bones.v22);
    const line = [anchor.clone()];
    for (let i = FIT_SPINE_X.length - 1; i >= 0; i--) if (FIT_SPINE_X[i] < FIT_X22) line.push(fitPoint(anchor, FIT_SPINE_X[i], FIT_SPINE_Y[i]));
    const d0 = line[line.length - 1].clone().sub(line[line.length - 2]);
    line.push(line[line.length - 1].clone().add(d0.multiplyScalar(20)));   // run on straight past the line's front end
    let cur = anchor, seg = 0;
    const chain = []; for (let i = 21; i >= 5; i--) chain.push(bones[`v${String(i).padStart(2, "0")}`]);   // the trunk to v06, along the line; the neck below
    for (let k = 0; k + 1 < chain.length; k++) {
      const bone = chain[k], child = chain[k + 1];
      const childNow = inHolder(child), L = childNow.distanceTo(inHolder(bone));
      if (L < 1e-4) continue;   // v22 and v21 share their joint; the root v22 is not turned (it carries the pelvis and the tail)
      let target = null;
      for (; seg + 1 < line.length; seg++) {
        const A = line[seg].clone().sub(cur), B = line[seg + 1].clone().sub(cur);
        if (B.length() >= L) {   // the point between A and B at distance L from cur
          let lo = 0, hi = 1;
          for (let it = 0; it < 30; it++) { const m = (lo + hi) / 2; if (A.clone().lerp(B, m).length() < L) lo = m; else hi = m; }
          target = cur.clone().add(A.lerp(B, lo)); break;
        }
      }
      if (!target) break;
      target.addScaledVector(LEFT, childNow.dot(LEFT) - target.dot(LEFT));   // keep the joint's side-to-side place
      aimSide(bone, childNow, target);
      cur = target;
    }
    // The head and neck: the head takes photo 08's angle (snout → casque top, FIT_CASQUE), and the neck vertebrae (v05…v01) bend, half the remaining
    // miss each in turn, until the snout comes to the target's snout (x 0, y 0). 12 rounds.
    const neck = [1, 2, 3, 4, 5].map((i) => bones[`v0${i}`]);
    const snoutT = fitPoint(anchor, 0, 0), casqueT = fitPoint(anchor, FIT_CASQUE[0], FIT_CASQUE[1]);
    const sAt = (q) => holder.worldToLocal(bones.head.localToWorld(q.clone()));
    const headAngle = () => { const h0 = inHolder(bones.head); aimSide(bones.head, h0.clone().add(sAt(casqueLocal).sub(sAt(snoutLocal))), h0.clone().add(casqueT.clone().sub(snoutT))); };
    for (let round = 0; round < 12; round++) {
      headAngle();
      for (const b of neck) {
        const o = inHolder(b), a = sAt(snoutLocal).sub(o), c = snoutT.clone().sub(o);
        a.addScaledVector(LEFT, -a.dot(LEFT)); c.addScaledVector(LEFT, -c.dot(LEFT));
        const ang = Math.atan2(a.clone().cross(c).dot(LEFT), a.dot(c)) * 0.5;
        const local = LEFT.clone().transformDirection(holder.matrixWorld).applyQuaternion(b.parent.getWorldQuaternion(new THREE.Quaternion()).invert());
        b.quaternion.premultiply(new THREE.Quaternion().setFromAxisAngle(local, ang)); b.updateMatrixWorld(true);
      }
    }
    headAngle();
  }

  function update(t) {
    for (const [b, r] of base) b.quaternion.copy(r);
    // Walking time g stops during the rocking pauses.
    const T = STRIDE / SPEED, walkSpan = ROCK_EVERY * T, pause = ROCK_TIMES / ROCK_HZ;
    const n = Math.floor(t / (walkSpan + pause)), r = t - n * (walkSpan + pause);
    const g = n * walkSpan + Math.min(r, walkSpan);
    // The pause falls where all four feet grip (the swaying video YT: no foot raised): with these touchdowns and DUTY that is from the
    // right hind's touchdown (0.5) to the right fore's lift-off (0.9407 + DUTY − 1 = 0.596); its middle.
    const allDown = (LIFT.hR + (LIFT.fR + DUTY - 1)) / 2;
    const phase = (g / T + allDown) % 1;
    const slide = g * SPEED;   // how far the branch has slid back
    const rockT = Math.max(0, r - walkSpan);
    const rock = rockT > 0 ? ROCK_SIZE * Math.sin(2 * Math.PI * ROCK_HZ * rockT) * Math.sin(Math.PI * rockT / pause) : 0;
    // The body: pitched to the branch, with a small rise and fall, and the rocking forward and back.
    model.quaternion.copy(bodyTurn);
    model.position.set(0, 0, 0).addScaledVector(UP, 0.03 * Math.sin(4 * Math.PI * phase)).addScaledVector(FORWARD, rock);
    // Girdles turn about the vertical, out of phase (the pelvis with the hind feet, the shoulders with the fore feet).
    const yaw = Math.sin(2 * Math.PI * (phase - LIFT.hL - 0.25));
    model.updateMatrixWorld(true);
    // Turn a bone about an axis given in the holder's frame.
    const turnAbout = (bone, axis, angle) => {
      if (!bone) return;
      const local = axis.clone().transformDirection(holder.matrixWorld).applyQuaternion(bone.parent.getWorldQuaternion(new THREE.Quaternion()).invert());
      bone.quaternion.premultiply(q.setFromAxisAngle(local, angle));
      bone.updateMatrixWorld(true);
    };
    turnAbout(bones.v23, UP, PELVIS_YAW * yaw);
    turnAbout(bones.v24, UP, -PELVIS_YAW * yaw);   // the tail stays behind
    turnAbout(bones.v06, UP, -SHOULDER_YAW * yaw);
    if (FIT_SPINE) laySpine();
    if (NECK_DEG) for (let i = 1; i <= 5; i++) turnAbout(bones[`v0${i}`], LEFT, THREE.MathUtils.degToRad(NECK_DEG / 5));
    if (ARCH_DEG) {
      const B = THREE.MathUtils.degToRad(ARCH_DEG), mid = [];
      for (let k = 20; k >= 6; k--) mid.push(bones[`v${String(k).padStart(2, "0")}`]);
      const w = mid.map((_, j) => Math.sin(Math.PI * (j + 0.5) / mid.length)), ws = w.reduce((a, b) => a + b, 0);
      turnAbout(bones.v21, LEFT, -B);   // −LEFT turns the front up
      mid.forEach((b, j) => turnAbout(b, LEFT, 2 * B * w[j] / ws));
      for (let i = 1; i <= 5; i++) turnAbout(bones[`v0${i}`], LEFT, -B / 5);   // the head back level, shared by the 5 neck vertebrae
    }
    // The tail: laid along a curve in the body's side plane (FORWARD, UP); its shape is θ(u) above (TAIL_START …).
    // The walking part of the tail's motion fades out over 0.5 s as the rocking pause starts and back in as it ends.
    const sm = (x) => { const c = Math.min(1, Math.max(0, x)); return c * c * (3 - 2 * c); };
    layTail(t, phase, rockT > 0 ? 1 - Math.min(sm(rockT / 0.5), sm((pause - rockT) / 0.5)) : 1);
    knots.position.y = (slide % KNOT_GAP);   // the branch slides back (+Y)

    for (const [key, limb] of Object.entries(limbs)) {
      // Where this foot is in its cycle: stance (planted, sliding back with the branch) or swing (to the next spot).
      // LIFT holds the touchdown phase; the foot lifts DUTY later.
      let u = (phase - LIFT[key] - DUTY + 2) % 1;   // 0 at lift-off
      const swing = 1 - DUTY;
      // Landing spot: as far ahead of the girdle as the foot ends behind it (Higham & Jayne), half the stance's travel.
      const reach = girdleRest[key] + DUTY * STRIDE / 2;
      let along, lift = 0, out = 0, heel = HEEL_DOWN;
      const ramp = (x, lo, hi) => { const k = Math.min(1, Math.max(0, (x - lo) / (hi - lo))); return k * k * (3 - 2 * k); };
      if (u < swing) {
        const s = u / swing, e = 0.5 - 0.5 * Math.cos(Math.PI * s);
        heel = HEEL_UP + (HEEL_DOWN - HEEL_UP) * ramp(s, 0, 0.5);   // the heel, up at lift-off, comes down for the next grip
        along = reach - DUTY * STRIDE + e * DUTY * STRIDE;   // forward against the body by the stance's travel
        lift = Math.sin(Math.PI * s) * SWING_LIFT; out = Math.sin(Math.PI * s) * SWING_OUT;
      } else {
        const s = (u - swing) / DUTY;
        heel = HEEL_DOWN + (HEEL_UP - HEEL_DOWN) * ramp(s, 0.65, 1);   // late in stance the heel rises, the sole rolling onto the toes
        along = reach - s * DUTY * STRIDE;   // planted: slides back with the branch, SPEED × the stance's time
      }
      footState[key] = { stance: u >= swing, slide, u };
      // The sole's grip on the branch; the wrist/ankle sits HEEL behind it and a little above (the foot lies along the branch).
      const contact = plantAt(limb, along).addScaledVector(UP, lift).addScaledVector(LEFT, (limb.left ? 1 : -1) * out);
      const target = contact.clone().addScaledVector(FORWARD, -HEEL * Math.cos(heel)).addScaledVector(UP, HEEL * Math.sin(heel))
        .addScaledVector(LEFT, (limb.left ? 1 : -1) * (limb.hind ? ANKLE_OUT : 0));
      // Two bones to the wrist/ankle, the elbow/knee out to the side and up.
      const root = holder.worldToLocal(limb.upper.getWorldPosition(new THREE.Vector3()));
      const span = target.clone().sub(root); let d = span.length();
      const { a, b } = limb;
      footState[key].over = Math.max(0, d - (a + b) * 0.999);   // how far out of reach (the foot would leave its grip by this much)
      d = Math.min(d, (a + b) * 0.999); span.setLength(d);
      const end = root.clone().add(span);
      const axis = span.clone().normalize();
      let pole;
      if (limb.hind) {
        const [kx, ky, kz] = hjKnee(u < swing ? "swing" : "stance", u < swing ? u / swing : (u - swing) / DUTY);
        pole = new THREE.Vector3().addScaledVector(FORWARD, kx).addScaledVector(UP, ky).addScaledVector(LEFT, (limb.left ? 1 : -1) * kz);
      } else {
        pole = new THREE.Vector3().addScaledVector(LEFT, limb.left ? 1 : -1).addScaledVector(UP, 0.6).addScaledVector(FORWARD, -0.3);
      }
      pole.addScaledVector(axis, -pole.dot(axis)).normalize();
      const x = (a * a - b * b + d * d) / (2 * d), h = Math.sqrt(Math.max(0, a * a - x * x));
      const joint = root.clone().addScaledVector(axis, x).addScaledVector(pole, h);
      aim(limb.upper, limb.lower.getWorldPosition(v), toWorld(joint));
      aim(limb.lower, limb.tip.getWorldPosition(w), toWorld(end));
      // For checking: the grip in the branch's frame, and how far the wrist/ankle ended from where it was sent.
      footState[key].grip = contact.clone().addScaledVector(FORWARD, slide).toArray();
      footState[key].miss = inHolder(limb.tip).distanceTo(target);
      // The hand/foot along the branch, fingers forward, gripping its top.
      const tipNow = limb.tip.localToWorld(new THREE.Vector3(0, 0.3, 0));
      aim(limb.tip, tipNow, toWorld(contact.clone().addScaledVector(FORWARD, 0.1)));
      // The grip: in stance each bundle is laid round the branch on its own side (the lateral one to the limb's outer side), its
      // segments following the surface (arc length = the segment's length, out to GRIP_MAX from the top); they let go over the
      // first GRIP_EASE of the swing and close again over its last GRIP_EASE (in the air they keep the glb's open pose).
      const gripAmt = u < swing ? 1 - Math.min(1, Math.min(u, swing - u) / (GRIP_EASE * swing)) : 1;
      if (limb.med && limb.lat && gripAmt > 0) {
        const outward = limb.left ? 1 : -1;
        for (const [bd, sideSign] of [[limb.lat, outward], [limb.med, -outward]]) {
          const at = (bone) => holder.worldToLocal(bone.getWorldPosition(new THREE.Vector3()));
          const base = at(bd.b1);
          const rel = base.clone().sub(branchCentre); const along0 = rel.dot(FORWARD);
          const th0 = Math.atan2(rel.dot(LEFT), rel.dot(UP));
          const rr = BRANCH_RADIUS + GRIP_GAP;
          const onBranch = (th, ahead) => branchCentre.clone().addScaledVector(FORWARD, along0 + ahead)
            .addScaledVector(UP, rr * Math.cos(th)).addScaledVector(LEFT, rr * Math.sin(th));
          const clampTh = (th) => sideSign > 0 ? Math.min(th, GRIP_MAX) : Math.max(th, -GRIP_MAX);
          // The point on the surface, round from `from` on this side, that is exactly `len` (the segment, a straight bone) from `p`.
          const reachOn = (p, from, len, ahead) => {
            let lo = 0, hi = Math.PI;
            if (onBranch(from + sideSign * hi, ahead).distanceTo(p) < len) return clampTh(from + sideSign * hi);
            for (let i = 0; i < 30; i++) { const m = (lo + hi) / 2; if (onBranch(from + sideSign * m, ahead).distanceTo(p) < len) lo = m; else hi = m; }
            return clampTh(from + sideSign * lo);
          };
          const mixTo = (bone, child, target) => {
            const now = holder.worldToLocal(child.getWorldPosition(new THREE.Vector3()));
            aim(bone, toWorld(now), toWorld(now.clone().lerp(target, gripAmt)));
          };
          const th1 = reachOn(base, th0, bd.l1, bd.l1 * GRIP_AHEAD);
          mixTo(bd.b1, bd.b2, onBranch(th1, bd.l1 * GRIP_AHEAD));
          const th2 = reachOn(at(bd.b2), th1, bd.l2, (bd.l1 + bd.l2) * GRIP_AHEAD);
          mixTo(bd.b2, bd.e, onBranch(th2, (bd.l1 + bd.l2) * GRIP_AHEAD));
          const got = at(bd.e).sub(branchCentre);
          (footState[key].grip2 ??= {})[bd === limb.lat ? "lat" : "med"] = {
            th0: THREE.MathUtils.radToDeg(th0), want: THREE.MathUtils.radToDeg(th2),
            got: THREE.MathUtils.radToDeg(Math.atan2(got.dot(LEFT), got.dot(UP))),
            off: (Math.hypot(got.dot(LEFT), got.dot(UP)) - rr) / MM,   // the tip's distance from the hugging surface, mm
          };
        }
      }
    }

    // Eyes: independent saccades — a quick turn (0.12 s) to a new direction, then still for 0.4–2.2 s.
    const F = chameleonEyes.frame;
    if (F) {
      for (const [i, e] of eyes.entries()) {
        if (t >= e.next) {
          e.fromYaw = e.yaw; e.fromPitch = e.pitch;
          e.toYaw = (rng() * 2 - 1) * EYE_YAW; e.toPitch = (rng() * 2 - 1) * EYE_PITCH;
          e.start = t; e.next = t + 0.12 + 0.4 + rng() * 1.8;
        }
        const s = Math.min(1, (t - e.start) / 0.12), k = s * s * (3 - 2 * s);
        e.yaw = e.fromYaw + (e.toYaw - e.fromYaw) * k; e.pitch = e.fromPitch + (e.toPitch - e.fromPitch) * k;
        // Yaw about the head's dorsal axis (forward is +), pitch about the head's lateral axis.
        const sideSign = i === 0 ? 1 : -1;   // eye_l, eye_r: a forward look turns them opposite ways about the dorsal axis
        const r = new THREE.Quaternion().setFromAxisAngle(F.dorsal, sideSign * e.yaw)
          .multiply(new THREE.Quaternion().setFromAxisAngle(F.lateral, sideSign * e.pitch));
        (i === 0 ? chameleonEyes.turn0 : chameleonEyes.turn1).value.setFromMatrix4(new THREE.Matrix4().makeRotationFromQuaternion(r));
      }
    }
  }
  const footState = {};
  /** For checking: each foot's grip on the branch in the branch's frame, whether it is planted, and how far the wrist/ankle missed its place. */
  function feet() {
    model.updateMatrixWorld(true);
    return Object.fromEntries(Object.entries(limbs).map(([key, limb]) => {
      const f = footState[key] ?? {};
      // the knee/elbow and the ankle/wrist against the hip/shoulder, mm: x forward, y up, z out to the limb's side (Higham & Jayne Fig. 5)
      const hip = inHolder(limb.upper), side = limb.left ? 1 : -1;
      const rel = (bone) => { const r = inHolder(bone).sub(hip); return [r.dot(FORWARD) / MM, r.dot(UP) / MM, side * r.dot(LEFT) / MM]; };
      return [key, { stance: f.stance, over: f.over, u: f.u, miss: f.miss, p: f.grip, grip: f.grip2, knee: rel(limb.lower), ankle: rel(limb.tip) }];
    }));
  }
  /** For checking: how far the skin's lowest point (every `step`-th vertex, skinned) lies above the branch's top, in mm (< 0: sunk in). */
  function belly(step = 7) {
    model.updateMatrixWorld(true);
    let skin = null; model.traverse((o) => { if (o.isSkinnedMesh && o.userData.chameleon_part === "Skin") skin = o; });
    const p = new THREE.Vector3(); let lowest = Infinity, along = 0; const prof = new Array(10).fill(Infinity);
    const n = skin.geometry.getAttribute("position").count;
    const SI = skin.geometry.getAttribute("skinIndex"), SW = skin.geometry.getAttribute("skinWeight"), sb = skin.skeleton.bones;
    for (let i = 0; i < n; i += step) {
      // only the trunk's skin (its main bone a vertebra or a rib), not the legs'
      let best = 0, bi = 0;
      for (let c = 0; c < 4; c++) { const w = SW.getComponent(i, c); if (w > best) { best = w; bi = SI.getComponent(i, c); } }
      if (!/^(v\d|rib)/.test(sb[bi].name)) continue;
      skin.getVertexPosition(i, p); skin.localToWorld(p); holder.worldToLocal(p);
      const rel = p.clone().sub(branchCentre);
      // only over the branch (within its radius sideways), and not the tail, feet or legs below the body (the trunk's span)
      if (Math.abs(rel.dot(LEFT)) > BRANCH_RADIUS || rel.dot(FORWARD) < trunkBack || rel.dot(FORWARD) > trunkFront) continue;
      const h = rel.dot(UP) - BRANCH_RADIUS;
      if (h < lowest) { lowest = h; along = rel.dot(FORWARD); }
      const bin = Math.floor((rel.dot(FORWARD) - trunkBack) / (trunkFront - trunkBack) * 10);
      if (bin >= 0 && bin < 10) prof[bin] = Math.min(prof[bin], h);
    }
    return { lowestMM: lowest / MM, alongMM: along / MM, trunkMM: [trunkBack / MM, trunkFront / MM], profile: prof.map((x) => Math.round(x / MM * 10) / 10) };
  }
  // Step 3 of C record 84 (C record 86, 2026-10-26, the producer: 「手順 3 に進んで、膜を目標の線へ寄せ、胴の深さと高さを合わせた絵とずれの mm を見せて下さい。」):
  // ?fitSkin=1 (with fitSpine) reshapes the meshes once, at load, in the fitted pose at FIT_SKIN_T: at each place x along the body, the skin above the
  // spine line is stretched so its top meets photo 08's back line, and below so its bottom meets the belly line (a scale about the spine, so what lies
  // inside — ribs, rib cartilage, organs — keeps its place in the depth and the ribs reach the deeper belly). Not the head (x < 0.36, faded in to
  // 0.46), the limbs, nor the tail past the hip (faded out 1.02 → 1.12). The change is written back into the meshes' bind positions through each
  // vertex's own skinning, so it walks with the body.
  function fitSkin() {
    update(FIT_SKIN_T); model.updateMatrixWorld(true);
    const o = outline(), SH = FIT_SH_MM * MM, anchor = inHolder(bones.v22);
    const spineAt = (x) => {
      const xs = FIT_SPINE_X, ys = FIT_SPINE_Y, n = xs.length;
      if (x <= xs[0]) return ys[0] + (ys[1] - ys[0]) / (xs[1] - xs[0]) * (x - xs[0]);
      if (x >= xs[n - 1]) return ys[n - 1] + (ys[n - 1] - ys[n - 2]) / (xs[n - 1] - xs[n - 2]) * (x - xs[n - 1]);
      let i = 0; while (xs[i + 1] < x) i++; const w = (x - xs[i]) / (xs[i + 1] - xs[i]); return ys[i] + w * (ys[i + 1] - ys[i]);
    };
    const tab = (arr, x) => { const i = Math.min(arr.length - 2, Math.max(0, Math.floor(x / 0.02))), w = Math.min(1, Math.max(0, x / 0.02 - i)); const a = arr[i], b = arr[i + 1]; return Number.isFinite(a) && Number.isFinite(b) ? a + w * (b - a) : (Number.isFinite(a) ? a : b); };
    const yBranch = FIT_Y22 + (branchTop - anchor.dot(UP)) / SH + FIT_CLEAR / FIT_SH_MM;
    const sm = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
    const field = (p) => {   // holder-frame displacement for a point now at p
      const x = FIT_X22 - (p.dot(FORWARD) - anchor.dot(FORWARD)) / SH, y = FIT_Y22 + (p.dot(UP) - anchor.dot(UP)) / SH;
      const w = sm(0.36, 0.46, x) * (1 - sm(1.02, 1.12, x)); if (w <= 0) return null;
      const s = spineAt(x); let ny;
      if (y >= s) { const m = tab(o.top, x), t = tab(o.targetTop, x); if (!(m - s > 1e-3)) return null; ny = s + (y - s) * Math.min(2, Math.max(0.5, (t - s) / (m - s))); }
      else { const m = tab(o.bot, x), t = Math.max(tab(o.targetBot, x), yBranch); if (!(s - m > 1e-3)) return null; ny = s + (y - s) * Math.min(2, Math.max(0.5, (s - t) / (s - m))); }
      return UP.clone().multiplyScalar((ny - y) * SH * w);
    };
    const skipOrgan = /^(eye|lens)_[lr]$|^hyoid_cartilage$|^claw$/;
    const hq = holder.getWorldQuaternion(new THREE.Quaternion()), hs = holder.getWorldScale(new THREE.Vector3()).x;
    let moved = 0;
    model.traverse((mesh) => {
      if (!mesh.isSkinnedMesh) return;
      const part = mesh.userData.chameleon_part, organ = mesh.userData.chameleon_organ;
      if (!(part === "Skin" || part === "Bone" || part === "Cartilage" || (part === "Organ" && !skipOrgan.test(organ ?? "")))) return;
      const pos = mesh.geometry.getAttribute("position"), SI = mesh.geometry.getAttribute("skinIndex"), SW = mesh.geometry.getAttribute("skinWeight");
      const sb = mesh.skeleton.bones, bm = mesh.skeleton.boneMatrices; mesh.skeleton.update();
      const meshInv = new THREE.Matrix3().setFromMatrix4(mesh.matrixWorld).invert();
      const M = new THREE.Matrix4(), Mk = new THREE.Matrix4(), p = new THREE.Vector3();
      for (let i = 0; i < pos.count; i++) {
        let best = 0, bi = 0; for (let c = 0; c < 4; c++) { const w = SW.getComponent(i, c); if (w > best) { best = w; bi = SI.getComponent(i, c); } }
        const nm = sb[bi].name;
        if (/^(h|f)[LR]_(upper|lower|hand|foot)|_med|_lat|^head$|^hyoid$/.test(nm)) continue;
        if (part === "Bone" && !/^rib/.test(nm)) continue;   // the skeleton: only the ribs (vertebrae and girdles keep their shape)
        mesh.getVertexPosition(i, p); mesh.localToWorld(p); holder.worldToLocal(p);
        const d = field(p); if (!d) continue;
        // holder → world → mesh local → bind (the blended skinning matrix's inverse)
        d.applyQuaternion(hq).multiplyScalar(hs).applyMatrix3(meshInv);
        M.set(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
        for (let c = 0; c < 4; c++) { const w = SW.getComponent(i, c); if (w > 0) { Mk.fromArray(bm, SI.getComponent(i, c) * 16); for (let e = 0; e < 16; e++) M.elements[e] += w * Mk.elements[e]; } }
        M.premultiply(mesh.bindMatrixInverse).multiply(mesh.bindMatrix);
        const L3 = new THREE.Matrix3().setFromMatrix4(M).invert(); d.applyMatrix3(L3);
        pos.setXYZ(i, pos.getX(i) + d.x, pos.getY(i) + d.y, pos.getZ(i) + d.z); moved++;
      }
      pos.needsUpdate = true; mesh.geometry.computeBoundingSphere();
    });
    console.log(`[fitSkin] moved ${moved} vertices`);
  }
  /** For checking (C record 85): the skin's outline (trunk, head, neck and tail base; not the limbs) in photo 08's target frame, anchored at v22, and its
   *  distance from photo 08's outline at FIT_OUT_X, in mm. */
  function outline() {
    model.updateMatrixWorld(true);
    let sk = null; model.traverse((o) => { if (o.isSkinnedMesh && o.userData.chameleon_part === "Skin") sk = o; });
    const SI = sk.geometry.getAttribute("skinIndex"), SW = sk.geometry.getAttribute("skinWeight"), sb = sk.skeleton.bones;
    const anchor = inHolder(bones.v22), SH = FIT_SH_MM * MM, n = FIT_OUT_X.length;
    const top = new Array(n).fill(-Infinity), bot = new Array(n).fill(Infinity), p = new THREE.Vector3();
    for (let i = 0; i < SI.count; i += 2) {
      let best = 0, bi = 0; for (let c = 0; c < 4; c++) { const w = SW.getComponent(i, c); if (w > best) { best = w; bi = SI.getComponent(i, c); } }
      const nm = sb[bi].name; if (/^(h|f)[LR]_(upper|lower|hand|foot)|_med|_lat/.test(nm)) continue; if (/^v\d/.test(nm) && +nm.slice(1) > 32) continue;
      sk.getVertexPosition(i, p); sk.localToWorld(p); holder.worldToLocal(p);
      const x = FIT_X22 - (p.dot(FORWARD) - anchor.dot(FORWARD)) / SH, y = FIT_Y22 + (p.dot(UP) - anchor.dot(UP)) / SH;
      const b = Math.round(x / 0.02); if (b < 0 || b >= n) continue;
      top[b] = Math.max(top[b], y); bot[b] = Math.min(bot[b], y);
    }
    const dt = top.map((v, i) => (v - FIT_OUT_TOP[i]) * FIT_SH_MM), db = bot.map((v, i) => (v - FIT_OUT_BOT[i]) * FIT_SH_MM);
    return { x: FIT_OUT_X, top, bot, dTopMM: dt, dBotMM: db, targetTop: FIT_OUT_TOP, targetBot: FIT_OUT_BOT };
  }
  // ?shape=88 (C record 89): one smooth reshaping of the trunk and the tail's base, at load, in the walking pose at FIT_SKIN_T. In the snout–hip frame
  // (x 0 at the snout, 1 at the hip; y across it, the back +), each point's height from the spine line is scaled: below the spine by kb(x), above by
  // kt(x) (1 since C record 91). kb is the target's depth over the model's, both taken from smoothed outlines and then smoothed again along x (no per-place
  // ratios: C record 87). kt is kept within 0.9–1 (the back only lowered: its height is bone, not a thicker skin, C record 87). Faded in over x 0.30–0.40 and
  // out over 1.20–1.30. Each vertex moves by its skin weights on the trunk's bones (vertebrae, ribs, girdles), so the limb roots and the head blend.
  // Skin, ribs, rib cartilage and organs (not the eyes) move together, written back into the bind positions as in fitSkin().
  function shape88() {
    update(FIT_SKIN_T); model.updateMatrixWorld(true);
    let sk = null; model.traverse((o) => { if (o.isSkinnedMesh && o.userData.chameleon_part === "Skin") sk = o; });
    const two = (p) => [p.dot(FORWARD), p.dot(UP)];
    const hipP = two(inHolder(limbs.hL.upper).add(inHolder(limbs.hR.upper)).multiplyScalar(0.5));
    // the snout: the most forward point of the head's skin
    const hi = sk.skeleton.bones.indexOf(bones.head), SI0 = sk.geometry.getAttribute("skinIndex"), SW0 = sk.geometry.getAttribute("skinWeight"), p = new THREE.Vector3();
    let sn = null, ct = null;
    for (let i = 0; i < SI0.count; i++) {
      if (SI0.getX(i) !== hi || SW0.getX(i) < 0.9) continue;
      sk.getVertexPosition(i, p); sk.localToWorld(p); holder.worldToLocal(p); const q = two(p);
      if (!sn || q[0] > sn[0]) sn = q; if (!ct || q[1] > ct[1]) ct = q;
    }
    let e1 = [hipP[0] - sn[0], hipP[1] - sn[1]]; const L = Math.hypot(e1[0], e1[1]); e1 = [e1[0] / L, e1[1] / L];
    let e2 = [-e1[1], e1[0]]; if ((ct[0] - sn[0]) * e2[0] + (ct[1] - sn[1]) * e2[1] < 0) e2 = [-e2[0], -e2[1]];
    const toXY = (q) => [((q[0] - sn[0]) * e1[0] + (q[1] - sn[1]) * e1[1]) / L, ((q[0] - sn[0]) * e2[0] + (q[1] - sn[1]) * e2[1]) / L];
    const up2 = FORWARD.clone().multiplyScalar(e2[0]).addScaledVector(UP, e2[1]);   // the frame's y in the holder
    // the spine line: the vertebrae's joints
    const sp = Object.keys(bones).filter((n) => /^v\d\d$/.test(n)).map((n) => toXY(two(inHolder(bones[n])))).sort((a, b) => a[0] - b[0]);
    const spine = (x) => { if (x <= sp[0][0]) return sp[0][1]; for (let i = 0; i + 1 < sp.length; i++) if (x <= sp[i + 1][0]) { const w = (x - sp[i][0]) / Math.max(1e-9, sp[i + 1][0] - sp[i][0]); return sp[i][1] + w * (sp[i + 1][1] - sp[i][1]); } return sp[sp.length - 1][1]; };
    // the model's outline (trunk, tail base; not the limbs or the head), in bins of SHAPE_DX
    const n = SHAPE_TOP.length, top = new Array(n).fill(-Infinity), bot = new Array(n).fill(Infinity);
    const limbRe = /^(h|f)[LR]_(upper|lower|hand|foot)|_med|_lat|^head$|^hyoid/;
    const bodyW = (mesh, i, SI, SW) => { let w = 0; for (let c = 0; c < 4; c++) { const wc = SW.getComponent(i, c); if (wc > 0 && !limbRe.test(mesh.skeleton.bones[SI.getComponent(i, c)].name)) w += wc; } return w; };
    for (let i = 0; i < SI0.count; i++) {
      if (bodyW(sk, i, SI0, SW0) < 0.9) continue;
      sk.getVertexPosition(i, p); sk.localToWorld(p); holder.worldToLocal(p); const [x, y] = toXY(two(p));
      const b = Math.round((x - SHAPE_X0) / SHAPE_DX); if (b < 0 || b >= n) continue;
      top[b] = Math.max(top[b], y); bot[b] = Math.min(bot[b], y);
    }
    const fill = (a) => { for (let i = 0; i < n; i++) if (!Number.isFinite(a[i])) { let j = i; while (j < n && !Number.isFinite(a[j])) j++; a[i] = j < n ? a[j] : a[i - 1]; } return a; };
    const gauss = (a, s) => a.map((_, i) => { let su = 0, ws = 0; for (let j = 0; j < n; j++) { const w = Math.exp(-0.5 * ((i - j) / s) ** 2); su += w * a[j]; ws += w; } return su / ws; });
    const mt = gauss(fill(top), 1.6), mb = gauss(fill(bot), 1.6);
    const xs = SHAPE_TOP.map((_, i) => SHAPE_X0 + i * SHAPE_DX);
    const sm = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
    // the belly's target: the model's back less the traced trunk's depth (C record 94; it was the traced belly line SHAPE_BOT in the snout–hip frame)
    // (from x 0.55 back; in front, over the shoulders and the throat, faded to 1 from 0.45: there the back is the neck behind the casque, and the chest
    // runs down to the throat as in photo 06)
    // the belly's curve (bellyBow, C record 95) at the height that gives the traced mean depth over x 0.45–0.75; behind x 1.0 it goes over to the back
    // less the traced depth (the tail's base)
    const midK = xs.map((x, i) => [x, i]).filter(([x]) => x >= 0.45 && x <= 0.75);
    const y0d = midK.reduce((a, [x, i]) => a + mt[i] - SHAPE_DEPTH[i] - bellyBow(x), 0) / midK.length;
    // the girdles (they do not move) under the trunk, x 0.42–1.02: the curve stays GIRDLE_CLEAR_MM under them
    let y0g = Infinity;
    model.traverse((mesh) => {
      if (!mesh.isSkinnedMesh || mesh.userData.chameleon_part !== "Bone") return;
      const SI = mesh.geometry.getAttribute("skinIndex"), SW = mesh.geometry.getAttribute("skinWeight"), sb = mesh.skeleton.bones, q = new THREE.Vector3();
      for (let i = 0; i < SI.count; i++) {
        let best = 0, bi = 0; for (let c = 0; c < 4; c++) { const w = SW.getComponent(i, c); if (w > best) { best = w; bi = SI.getComponent(i, c); } }
        if (!/girdle/.test(sb[bi].name)) continue;
        mesh.getVertexPosition(i, q); mesh.localToWorld(q); holder.worldToLocal(q); const [x, y] = toXY(two(q));
        if (x >= 0.42 && x <= 1.02) y0g = Math.min(y0g, y - GIRDLE_CLEAR_MM / FIT_SH_MM - bellyBow(x));
      }
    });
    const y0k = Math.min(y0d, y0g);
    const tgtK = xs.map((x, i) => { const w = sm(1.0, 1.12, x); return (1 - w) * (y0k + bellyBow(Math.min(x, 1.0))) + w * (mt[i] - SHAPE_DEPTH[i]); });
    const kb0 = xs.map((x, i) => 1 + (Math.min(2, Math.max(0.5, (spine(x) - tgtK[i]) / Math.max(1e-3, spine(x) - mb[i]))) - 1) * sm(0.45, 0.55, x));
    // Above the spine nothing moves since C record 91: the back's height comes from the arch of the spine (ARCH_DEG); lowering the skin over the higher
    // back pressed it onto the spines' tips (0.2–0.3 mm left).
    const kt0 = xs.map(() => 1);
    const kb = gauss(kb0, 2), kt = gauss(kt0, 2);
    const at = (k, x) => { const f = (x - SHAPE_X0) / SHAPE_DX, i = Math.min(n - 2, Math.max(0, Math.floor(f))), w = Math.min(1, Math.max(0, f - i)); return k[i] + w * (k[i + 1] - k[i]); };
    const fade = (x) => sm(0.30, 0.40, x) * (1 - sm(1.20, 1.30, x));
    const skipOrgan = /^(eye|lens)_[lr]$|^claw$/;
    const hq = holder.getWorldQuaternion(new THREE.Quaternion()), hs = holder.getWorldScale(new THREE.Vector3()).x;
    // Move vertices along the frame's y by field(x, y, wBody, part, mesh, i, SI, SW, z) (snout–hip lengths; or [dy, dz], dz along LEFT), written back into
    // the bind positions through each vertex's skinning.
    const applyDy = (field, parts, withHead = false) => {
      let moved = 0;
      model.traverse((mesh) => {
        if (!mesh.isSkinnedMesh) return;
        const part = mesh.userData.chameleon_part, organ = mesh.userData.chameleon_organ;
        if (!parts.includes(part) || (part === "Organ" && skipOrgan.test(organ ?? ""))) return;
        if (withHead && organ === "hyoid_cartilage") return;   // the hyoid's cartilage is skeleton: pulled down with the throat's skin it showed under it
        const pos = mesh.geometry.getAttribute("position"), SI = mesh.geometry.getAttribute("skinIndex"), SW = mesh.geometry.getAttribute("skinWeight");
        const sb = mesh.skeleton.bones, bm = mesh.skeleton.boneMatrices; mesh.skeleton.update();
        const meshInv = new THREE.Matrix3().setFromMatrix4(mesh.matrixWorld).invert();
        const M = new THREE.Matrix4(), Mk = new THREE.Matrix4();
        for (let i = 0; i < pos.count; i++) {
          let best = 0, bi = 0; for (let c = 0; c < 4; c++) { const w = SW.getComponent(i, c); if (w > best) { best = w; bi = SI.getComponent(i, c); } }
          if (part === "Bone" && !/^rib/.test(sb[bi].name)) continue;   // of the skeleton only the ribs: vertebrae, girdles and limbs keep their shape
          const wBody = bodyW(mesh, i, SI, SW); if (wBody <= 0 && !withHead) continue;
          mesh.getVertexPosition(i, p); mesh.localToWorld(p); holder.worldToLocal(p);
          const [x, y] = toXY(two(p)), r = field(x, y, wBody, part, mesh, i, SI, SW, p.dot(LEFT) / L);
          const dy = Array.isArray(r) ? r[0] : r, dz = Array.isArray(r) ? r[1] : 0;
          if (!(Math.abs(dy) >= 1e-7 || Math.abs(dz) >= 1e-7)) continue;
          const d = up2.clone().multiplyScalar(dy * L).addScaledVector(LEFT, dz * L);
          d.applyQuaternion(hq).multiplyScalar(hs).applyMatrix3(meshInv);
          M.set(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
          for (let c = 0; c < 4; c++) { const w = SW.getComponent(i, c); if (w > 0) { Mk.fromArray(bm, SI.getComponent(i, c) * 16); for (let e = 0; e < 16; e++) M.elements[e] += w * Mk.elements[e]; } }
          M.premultiply(mesh.bindMatrixInverse).multiply(mesh.bindMatrix);
          d.applyMatrix3(new THREE.Matrix3().setFromMatrix4(M).invert());
          pos.setXYZ(i, pos.getX(i) + d.x, pos.getY(i) + d.y, pos.getZ(i) + d.z); moved++;
        }
        pos.needsUpdate = true; mesh.geometry.computeBoundingSphere();
      });
      return moved;
    };
    const moved = applyDy((x, y, wBody) => {
      const f = fade(x); if (f <= 0) return 0;
      const s0 = spine(x), k = y >= s0 ? at(kt, x) : at(kb, x);
      return (s0 + (y - s0) * (1 + (k - 1) * f) - y) * wBody;
    }, ["Skin", "Bone", "Cartilage", "Organ"]);
    // The belly line, chin to tail, as one smooth line (C record 92, 2026-10-26, the producer: 「お腹側が顎から胴体まで、および胴体から尻尾までがほぼ一直線（もちろん
    // 丸みはある）の綺麗なラインで繋がっていなきゃおかしいです。」; before it, C record 91: the small waves over the rib ends). The skin is built around the
    // bones (skinbody.py), so its bottom line steps up under the throat (behind the jaw, 2.5–5.7 mm above the traced animals' line) and at the tail's base
    // (2 mm), and stands proud over every rib end. Along x 0–1.30 in 1 mm bins the bottom of the skin (head and trunk; not the limbs) is taken, its low
    // the new bottom is the target below (since C record 94; the traced line VENT_BOT in C record 92), kept 0.8 mm under the lowest bone (not the
    // limbs'), rib cartilage or the hyoid's cartilage there, smoothed (about 4 mm)
    // and kept under that. The skin goes to it, down or up (up only where nothing inside is near: C record 92, the shelf behind the hip stood
    // 2 mm under the line and stepped up to the tail): the vertices within the lowest 30% of the depth (at least 6 mm, at most 12 mm) by how near they are
    // to the bottom, by their weight on the head's and trunk's bones. The skin and the organs (not the eyes).
    const nonLimbRe = /^(h|f)[LR]_(upper|lower|hand|foot)|_med|_lat/;
    const bodyWh = (mesh, i, SI, SW) => { let w = 0; for (let c = 0; c < 4; c++) { const wc = SW.getComponent(i, c); if (wc > 0 && !nonLimbRe.test(mesh.skeleton.bones[SI.getComponent(i, c)].name)) w += wc; } return w; };
    const FX0 = 0, FX1 = 1.30, FDX = 1 / FIT_SH_MM, fn = Math.ceil((FX1 - FX0) / FDX) + 1, fb = new Array(fn).fill(Infinity), ft = new Array(fn).fill(-Infinity);
    for (let i = 0; i < SI0.count; i++) {
      if (bodyWh(sk, i, SI0, SW0) < 0.9) continue;
      sk.getVertexPosition(i, p); sk.localToWorld(p); holder.worldToLocal(p); const [x, y] = toXY(two(p));
      const b = Math.round((x - FX0) / FDX); if (b >= 0 && b < fn) { fb[b] = Math.min(fb[b], y); ft[b] = Math.max(ft[b], y); }
    }
    for (const a of [fb, ft]) for (let i = 0; i < fn; i++) if (!Number.isFinite(a[i])) a[i] = i ? a[i - 1] : a.find(Number.isFinite);
    // What must stay inside: the lowest point of the bones (not the limbs') and rib cartilage in each bin, less 0.8 mm. The organs move with the skin
    // (C record 92: the right kidney's end, 23 mm behind the hip and 4 mm under it, held the skin there 4 mm under the traced line).
    const inner = new Array(fn).fill(Infinity), jaw = new Array(fn).fill(Infinity);
    model.traverse((mesh) => {
      const hyoidCart = mesh.userData.chameleon_organ === "hyoid_cartilage";
      if (!mesh.isSkinnedMesh || !(["Bone", "Cartilage"].includes(mesh.userData.chameleon_part) || hyoidCart)) return;
      const SI = mesh.geometry.getAttribute("skinIndex"), SW = mesh.geometry.getAttribute("skinWeight"), sb = mesh.skeleton.bones, q = new THREE.Vector3();
      for (let i = 0; i < SI.count; i++) {
        if (bodyWh(mesh, i, SI, SW) < 0.5) continue;
        mesh.getVertexPosition(i, q); mesh.localToWorld(q); holder.worldToLocal(q); const [x, y] = toXY(two(q));
        const b = Math.round((x - FX0) / FDX); if (b < 0 || b >= fn) continue;
        let best = 0, bi = 0; for (let c = 0; c < 4; c++) { const w = SW.getComponent(i, c); if (w > best) { best = w; bi = SI.getComponent(i, c); } }
        // the ribs' ends and their cartilage move with the skin (since C record 95: one pair, at x 0.7, hung 1.5 mm under its neighbours and dented the
        // line); what holds the line is the rest: the girdles, the vertebrae, the head, the hyoid and its cartilage
        if (mesh.userData.chameleon_part === "Cartilage" || /^rib/.test(sb[bi].name)) continue;
        inner[b] = Math.min(inner[b], y - 0.8 / FIT_SH_MM);
        if (x <= 0.31 && (hyoidCart || /^(head|hyoid)$/.test(sb[bi].name))) jaw[b] = Math.min(jaw[b], y);   // the lower jaw, hyoid and its cartilage (behind 0.31 the skull's back)
      }
    });
    // The new bottom: the traced line, but under what must stay inside; smoothed (1 mm, 16 rounds: about 4 mm in all) and kept under it each round.
    const cap = inner.map((v, i) => Math.min(v, fb[i] + 12 / FIT_SH_MM));   // where nothing is inside, at most 12 mm up
    // The target (C record 94): under the trunk (x ≥ 0.58) the belly's curve (bellyBow, since C record 95; the back less the traced depth in C record 94); under the head (x ≤ 0.28) THROAT_MM under the lower jaw and
    // hyoid; between, the two blended (smoothstep; over 0.30–0.42 the throat, 5 mm under the raised chest, met it in a step). Where there is no jaw
    // (in front of it, behind the hyoid) its nearest value is held.
    let jl = jaw.findIndex(Number.isFinite); const jawF = jaw.slice();
    for (let i = 0; i < fn; i++) { if (Number.isFinite(jawF[i])) jl = i; else if (jl >= 0) jawF[i] = jawF[jl]; }
    const j0 = jaw.findIndex(Number.isFinite); for (let i = 0; i < j0; i++) jawF[i] = jaw[j0];
    const depthAt = (x) => { const f = (x - SHAPE_X0) / SHAPE_DX, i = Math.min(SHAPE_DEPTH.length - 2, Math.max(0, Math.floor(f))), w = Math.min(1, Math.max(0, f - i)); return SHAPE_DEPTH[i] + w * (SHAPE_DEPTH[i + 1] - SHAPE_DEPTH[i]); };
    // the back's line without the spines' tips: the highest within ±3 mm, then a Gaussian of 4 mm
    const ftM = ft.map((_, i) => { let m = -Infinity; for (let j = Math.max(0, i - 3); j <= Math.min(fn - 1, i + 3); j++) m = Math.max(m, ft[j]); return m; });
    const ftS = ftM.map((_, i) => { let su = 0, ws = 0; for (let j = Math.max(0, i - 12); j <= Math.min(fn - 1, i + 12); j++) { const w = Math.exp(-0.5 * ((i - j) / 4) ** 2); su += w * ftM[j]; ws += w; } return su / ws; });
    const trunkWant = (x, i) => { const w = sm(1.0, 1.12, x); return (1 - w) * (y0k + bellyBow(Math.min(x, 1.0))) + w * (ftS[i] - depthAt(x)); };
    const want = fb.map((_, i) => { const x = FX0 + i * FDX, w = sm(0.28, 0.58, x); return (1 - w) * (jawF[i] - THROAT_MM / FIT_SH_MM) + w * trunkWant(x, i); });
    let line = cap.map((v, i) => Math.min(v, want[i]));
    for (let r = 0; r < 16; r++) line = line.map((_, i) => { let su = 0, ws = 0; for (let j = Math.max(0, i - 3); j <= Math.min(fn - 1, i + 3); j++) { const w = Math.exp(-0.5 * (i - j) ** 2); su += w * line[j]; ws += w; } return Math.min(cap[i], su / ws); });
    const tab = (a, x) => { const f = (x - FX0) / FDX, i = Math.min(fn - 2, Math.max(0, Math.floor(f))), w = Math.min(1, Math.max(0, f - i)); return a[i] + w * (a[i + 1] - a[i]); };
    const fillFade = (x) => sm(0.0, 0.04, x) * (1 - sm(1.22, 1.30, x));
    const filled = applyDy((x, y, wBody, part, mesh, i, SI, SW) => {
      const f = fillFade(x); if (f <= 0) return 0;
      const b = tab(fb, x), c = tab(line, x), band = Math.min(12 / FIT_SH_MM, Math.max(6 / FIT_SH_MM, 0.3 * (tab(ft, x) - b)));
      const wv = 1 - Math.min(1, Math.max(0, (y - b) / band)); if (wv <= 0) return 0;
      return (c - b) * wv * wv * (3 - 2 * wv) * f * bodyWh(mesh, i, SI, SW);
    }, ["Skin", "Organ", "Bone", "Cartilage"], true);
    model.userData.shape88Line = { x0: FX0, dx: FDX, bottom: fb, inner, line, jaw, want };   // for checking
    // The belly's sides (C record 94, from C record 93: along the body, 45–75° below the level the skin waved 1.0–1.4 mm with the rib ends): around each
    // 1 mm section (centre midway between the spine and the new bottom, on the spine's side line), the outermost skin per 7.5° below the level is taken,
    // smoothed along x (Gaussian 3 mm) and a little round (7.5°), and the skin brought out to it where it lies inside (troughs filled only, so nothing
    // inside comes out). The trunk only, x 0.40–1.12, fading out toward the spine's level.
    const spZ = (() => { const v = Object.keys(bones).filter((n) => /^v\d\d$/.test(n)).map((n) => { const q = inHolder(bones[n]); return [toXY(two(q))[0], q.dot(LEFT) / L]; }).sort((a, b) => a[0] - b[0]);
      return (x) => { if (x <= v[0][0]) return v[0][1]; for (let i = 0; i + 1 < v.length; i++) if (x <= v[i + 1][0]) { const w = (x - v[i][0]) / Math.max(1e-9, v[i + 1][0] - v[i][0]); return v[i][1] + w * (v[i + 1][1] - v[i][1]); } return v[v.length - 1][1]; }; })();
    const CX0 = 0.40, CX1 = 1.12, cn = Math.ceil((CX1 - CX0) / FDX) + 1, NT = 24;
    let sides = 0, liftMax = 0;
    for (let round = 0; round < 2; round++) {   // twice: the first round's fill leaves a little of the waves (C record 94)
    const outer = Array.from({ length: cn }, () => new Array(NT).fill(0)), bot2 = new Array(cn).fill(Infinity);
    for (let i = 0; i < SI0.count; i++) {
      if (bodyW(sk, i, SI0, SW0) < 0.9) continue;
      sk.getVertexPosition(i, p); sk.localToWorld(p); holder.worldToLocal(p); const [x, y] = toXY(two(p));
      const b = Math.round((x - CX0) / FDX); if (b >= 0 && b < cn) bot2[b] = Math.min(bot2[b], y);
    }
    const centre = (x, b) => [(spine(x) + bot2[Math.min(cn - 1, Math.max(0, b))]) / 2, spZ(x)];
    for (let i = 0; i < SI0.count; i++) {
      if (bodyW(sk, i, SI0, SW0) < 0.9) continue;
      sk.getVertexPosition(i, p); sk.localToWorld(p); holder.worldToLocal(p); const [x, y] = toXY(two(p)), z = p.dot(LEFT) / L;
      const b = Math.round((x - CX0) / FDX); if (b < 0 || b >= cn || y >= spine(x)) continue;
      const [yc, zc] = centre(x, b), t = Math.atan2(y - yc, z - zc); if (t > 0) continue;
      const k = Math.min(NT - 1, Math.floor((t + Math.PI) / Math.PI * NT)); outer[b][k] = Math.max(outer[b][k], Math.hypot(y - yc, z - zc));
    }
    for (let k = 0; k < NT; k++) for (let b = 0; b < cn; b++) if (!(outer[b][k] > 0)) { let j = b; while (j < cn && !(outer[j][k] > 0)) j++; outer[b][k] = j < cn ? outer[j][k] : (b ? outer[b - 1][k] : 0); }
    const smoothR = outer.map((row, b) => row.map((_, k) => { let su = 0, ws = 0;
      for (let bb = Math.max(0, b - 9); bb <= Math.min(cn - 1, b + 9); bb++) for (let kk = Math.max(0, k - 2); kk <= Math.min(NT - 1, k + 2); kk++) { const w = Math.exp(-0.5 * ((b - bb) / 3) ** 2 - 0.5 * (k - kk) ** 2); su += w * outer[bb][kk]; ws += w; }
      return su / ws; }));
    const lift = outer.map((row, b) => row.map((r, k) => Math.max(0, smoothR[b][k] - r)));
    const sideFade = (x) => sm(0.40, 0.46, x) * (1 - sm(1.05, 1.12, x));
    sides += applyDy((x, y, wBody, part, mesh, i, SI, SW, z) => {
      const f = sideFade(x); if (f <= 0) return 0;
      const s0 = spine(x); if (y >= s0) return 0;
      const fb2 = (x - CX0) / FDX, b = Math.min(cn - 2, Math.max(0, Math.floor(fb2))), wb = Math.min(1, Math.max(0, fb2 - b));
      const [yc, zc] = centre(x, b), t = Math.atan2(y - yc, z - zc); if (t > 0) return 0;
      const fk = (t + Math.PI) / Math.PI * NT - 0.5, k = Math.min(NT - 2, Math.max(0, Math.floor(fk))), wk = Math.min(1, Math.max(0, fk - k));
      const dl = (1 - wb) * ((1 - wk) * lift[b][k] + wk * lift[b][k + 1]) + wb * ((1 - wk) * lift[b + 1][k] + wk * lift[b + 1][k + 1]);
      const r = Math.hypot(y - yc, z - zc); if (r < 1e-6 || dl <= 0) return 0;
      const g = f * wBody * sm(0, 0.25, (s0 - y) / Math.max(1e-3, s0 - bot2[b]));
      return [dl * g * (y - yc) / r, dl * g * (z - zc) / r];
    }, ["Skin"]);
    liftMax = Math.max(liftMax, Math.max(...lift.map((row) => Math.max(...row))) * FIT_SH_MM);
    }
    const dev = fb.map((v, i) => Math.abs(v - line[i])).filter((v, i) => fillFade(FX0 + i * FDX) > 0.5);
    console.log(`[shape88] belly curve's lowest ${(y0k * FIT_SH_MM).toFixed(1)} mm (by the depth ${(y0d * FIT_SH_MM).toFixed(1)}, under the girdles ${(y0g * FIT_SH_MM).toFixed(1)}); moved ${moved} vertices; kb ${kb.map((v) => v.toFixed(2)).join(" ")}; kt ${kt.map((v) => v.toFixed(2)).join(" ")}; belly line: ${filled} skin vertices moved, at most ${(Math.max(...dev) * FIT_SH_MM).toFixed(2)} mm; sides: ${sides} skin vertices, troughs filled up to ${liftMax.toFixed(2)} mm`);
  }
  if (FIT_SKIN) fitSkin();
  if (SHAPE88 && model.userData.shape88Baked) console.warn("[shape88] この glb は焼き込み済みなので、?shape=88 をかけない");
  else if (SHAPE88) shape88();
  return { backdrop, branchFrame, update, feet, belly, outline };
}
