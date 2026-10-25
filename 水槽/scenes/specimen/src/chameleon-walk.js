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
const BODY_LOW = Number(new URLSearchParams(location.search).get("low") ?? 0.6);
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
const TAIL_START = Number(_q.get("tailStart") ?? 200), TAIL_ARC = Number(_q.get("tailArc") ?? -110), TAIL_ARC_END = Number(_q.get("tailArcEnd") ?? 0.45);
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
  return { backdrop, branchFrame, update, feet, belly };
}
