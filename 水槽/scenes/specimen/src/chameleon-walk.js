// The chameleon walking along a branch (C record 59, 2026-10-24, the producer: 「カメレオンの特徴は目の動き方と、移動時の手足の動かし方
// です。…画面上にカメレオンが止まる枝を一本置いてそれを手足を使って歩くような動きをつけましょう」, with a photo of a veiled chameleon
// on a twig). ?walk=1 on chameleon.html. A first trial: the bones are posed in the page each frame (no clip in the glb).
//
// Where the numbers come from:
// - Higham & Jayne 2004 (J Exp Biol 207:233–248), C. calyptratus on a 2.4 cm dowel, SVL 18.1 cm: speed 17 cm/s, duty factor 63%,
//   the foot well in front of the hip at footfall (the knee unusually extended), large pelvic rotation (57° on the level),
//   the limb widest out to the side at mid-swing.
// - Scaled to this animal: 1 model unit = 22.2 mm (chameleon-stain.js MODEL_UNITS_PER_MM), snout–vent about 5 units (11 cm), so
//   × 11 / 18.1: the dowel 1.46 cm across (0.66 units), the speed 10 cm/s (4.5 units/s).
// - The eyes: each eye turns on its own, over 180° across and 80° up and down (magnetic search coils; "Visual and vestibular
//   reflexes that stabilize gaze in the chameleon", Visual Neuroscience), in quick saccades between still spells.
// Not measured and set by eye here (to be checked against video): the order of the feet, the stride length, the swing's lift, the tail.
import * as THREE from "three";
import { MODEL_UNITS_PER_MM } from "./chameleon-stain.js";
import { chameleonEyes } from "./chameleon-material.js";

const MM = MODEL_UNITS_PER_MM;
const BRANCH_RADIUS = 14.6 / 2 * MM;
// Higham & Jayne's 17 cm/s scaled is 10 cm/s (?speed=100, in mm/s); the default is a calm 4 cm/s (set by eye, to be checked on video).
const SPEED = Number(new URLSearchParams(location.search).get("speed") ?? 40) * MM;   // model units per second
const DUTY = 0.63;
const STRIDE = 2.4;                     // model units (5.3 cm, about half the snout–vent); set by eye
// The cycle phase at which each foot lifts (a lateral-sequence walk: left hind, left fore, right hind, right fore).
const LIFT = { hL: 0, fL: 0.25, hR: 0.5, fR: 0.75 };
const BODY_LOW = Number(new URLSearchParams(location.search).get("low") ?? 0.55);   // set by eye
const SWING_LIFT = 0.35, SWING_OUT = 0.45;   // model units: how high and how far out the foot travels at mid-swing
const PELVIS_YAW = THREE.MathUtils.degToRad(20), SHOULDER_YAW = THREE.MathUtils.degToRad(12);
const _q = new URLSearchParams(location.search);
// degrees, degrees, the share of its length before it bends; set by eye (?tailStart= ?tailTurn= ?tailStraight= to try others)
const TAIL_START = Number(_q.get("tailStart") ?? 230), TAIL_TURN = Number(_q.get("tailTurn") ?? 520), TAIL_STRAIGHT = Number(_q.get("tailStraight") ?? 0.4);
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
    limbs[key] = { upper, lower, tip, a, b, hind: key[0] === "h", left: key[1] === "L" };
  }
  // Where the body sits over the branch: the hips and shoulders at BODY_LOW and BODY_LOW + 0.05 of their limbs' reach above its top
  // (the belly low over the branch, the elbows and knees well bent, as in the photo).
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
  const girdleAlong = (limb) => inHolder(limb.upper).applyQuaternion(bodyTurn).dot(FORWARD);

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
  function layTail(t) {
    model.updateMatrixWorld(true);
    let at = holder.worldToLocal(tail[0].getWorldPosition(new THREE.Vector3())), s = 0;
    const sway = 0.04 * Math.sin(t * 0.9);
    for (let i = 0; i < tailSeg.length; i++) {
      const u = (s + tailSeg[i] / 2) / tailLength;
      const k = Math.max(0, (u - TAIL_STRAIGHT) / (1 - TAIL_STRAIGHT));   // 0 → 1 along the bending part
      const theta = THREE.MathUtils.degToRad(TAIL_START + TAIL_TURN * k * k);
      const dir = FORWARD.clone().multiplyScalar(Math.cos(theta)).addScaledVector(UP, Math.sin(theta)).addScaledVector(LEFT, sway * k).normalize();
      const next = at.clone().addScaledVector(dir, tailSeg[i]);
      aim(tail[i], tail[i + 1].getWorldPosition(new THREE.Vector3()), toWorld(next));
      at = next; s += tailSeg[i];
    }
  }

  function update(t) {
    for (const [b, r] of base) b.quaternion.copy(r);
    const phase = (t * SPEED / STRIDE) % 1;
    const slide = t * SPEED;   // how far the branch has slid back
    // The body: pitched to the branch, with a small rise and fall.
    model.quaternion.copy(bodyTurn);
    model.position.set(0, 0, 0).addScaledVector(UP, 0.03 * Math.sin(4 * Math.PI * phase));
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
    // The tail: laid along a curve in the body's side plane (FORWARD, UP), from its base back and down, then coiling forward and up
    // below the branch as in the photo (the tip toward the body). Heading θ: direction = cos θ · FORWARD + sin θ · UP; it starts
    // at TAIL_START and turns ever faster toward the tip (the coil tightens), TAIL_TURN degrees in all.
    layTail(t);
    knots.position.y = (slide % KNOT_GAP);   // the branch slides back (+Y)

    for (const [key, limb] of Object.entries(limbs)) {
      // Where this foot is in its cycle: stance (planted, sliding back with the branch) or swing (to the next spot).
      let u = (phase - LIFT[key] + 1) % 1;   // 0 at lift-off
      const swing = 1 - DUTY;
      const reach = girdleAlong(limb) + STRIDE * (limb.hind ? 0.55 : 0.45);   // landing spot, ahead of the girdle
      let along, lift = 0, out = 0;
      if (u < swing) {
        const s = u / swing, e = 0.5 - 0.5 * Math.cos(Math.PI * s);
        along = reach - STRIDE + e * STRIDE;
        lift = Math.sin(Math.PI * s) * SWING_LIFT; out = Math.sin(Math.PI * s) * SWING_OUT;
      } else {
        const s = (u - swing) / DUTY;
        along = reach - s * STRIDE;
      }
      const target = plantAt(limb, along).addScaledVector(UP, lift).addScaledVector(LEFT, (limb.left ? 1 : -1) * out);
      // Two bones to the wrist/ankle, the elbow/knee out to the side and up.
      const root = holder.worldToLocal(limb.upper.getWorldPosition(new THREE.Vector3()));
      const span = target.clone().sub(root); let d = span.length();
      const { a, b } = limb; d = Math.min(d, (a + b) * 0.999); span.setLength(d);
      const end = root.clone().add(span);
      const axis = span.clone().normalize();
      const pole = new THREE.Vector3().addScaledVector(LEFT, limb.left ? 1 : -1).addScaledVector(UP, 0.6).addScaledVector(FORWARD, limb.hind ? 0.3 : -0.3);
      pole.addScaledVector(axis, -pole.dot(axis)).normalize();
      const x = (a * a - b * b + d * d) / (2 * d), h = Math.sqrt(Math.max(0, a * a - x * x));
      const joint = root.clone().addScaledVector(axis, x).addScaledVector(pole, h);
      aim(limb.upper, limb.lower.getWorldPosition(v), toWorld(joint));
      aim(limb.lower, limb.tip.getWorldPosition(w), toWorld(end));
      // The hand/foot along the branch, fingers forward, gripping its top.
      const tipNow = limb.tip.localToWorld(new THREE.Vector3(0, 0.3, 0));
      aim(limb.tip, tipNow, toWorld(end.clone().addScaledVector(FORWARD, 0.25).addScaledVector(UP, -0.12)));
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
  return { backdrop, branchFrame, update };
}
