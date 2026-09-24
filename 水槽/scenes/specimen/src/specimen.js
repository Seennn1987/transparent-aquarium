import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { applySpecimenTissue } from "./specimen-material.js";
import { createSpecimenMotion, MOTION } from "./specimen-motion.js";

// The tank's squid asset, read only. In the file the arms point along -X and the mantle
// tip along +X, about one mantle length from the head.
const SQUID_URL = new URL("../../riverscape/assets/squid.glb", import.meta.url).href;

// Displayed the way preserved squid usually stand in a jar: mantle up, arms hanging down.
export const SPECIMEN_POSE = {
  mantleLength: 0.7,
  clearance: 0.12,
};

export async function createSpecimen({ envMap, liquidBounds }) {
  const gltf = await new GLTFLoader().loadAsync(SQUID_URL);
  const model = gltf.scene;
  applySpecimenTissue(model, { envMap });
  model.rotation.z = Math.PI / 2;

  const body = new THREE.Group();
  body.name = "Specimen";
  body.scale.setScalar(SPECIMEN_POSE.mantleLength);
  body.add(model);

  const mixer = new THREE.AnimationMixer(model);
  const hover = THREE.AnimationClip.findByName(gltf.animations, "SQ_Hover");
  if (!hover) throw new Error("squid.glb に SQ_Hover がありません");
  const action = mixer.clipAction(hover).play();
  action.timeScale = MOTION.hoverRate;
  mixer.update(0);

  // The drift turns and tilts the animal about its own middle, so it pivots in place.
  body.updateMatrixWorld(true);
  const own = new THREE.Box3().setFromObject(body, true);
  body.position.copy(own.getCenter(new THREE.Vector3())).negate();
  const pivot = new THREE.Group();
  pivot.name = "SpecimenPivot";
  pivot.add(body);
  const centre = liquidBounds.getCenter(new THREE.Vector3());
  pivot.position.copy(centre);

  const height = own.max.y - own.min.y;
  const halfWidth = Math.max(own.max.x - own.min.x, own.max.z - own.min.z) / 2;
  const room = liquidBounds.max.y - liquidBounds.min.y - 2 * SPECIMEN_POSE.clearance;
  if (height + 2 * (MOTION.limitHeight + MOTION.bobHeight) > room)
    throw new Error(`標本が液に収まりません（高さ ${height.toFixed(2)} ＋動き / 余裕込み ${room.toFixed(2)}）`);
  const wallRoom = (liquidBounds.max.x - liquidBounds.min.x) / 2 - SPECIMEN_POSE.clearance;
  if (halfWidth + MOTION.limitRadius > wallRoom)
    throw new Error(`標本が壁に近すぎます（半幅 ${halfWidth.toFixed(2)} ＋動き / 余裕込み ${wallRoom.toFixed(2)}）`);

  const motion = createSpecimenMotion();

  return {
    object: pivot,
    model,
    mixer,
    motion,
    bounds: new THREE.Box3().setFromObject(pivot, true),
    update(dt) {
      if (dt <= 0) return;
      mixer.update(dt);
      const s = motion.update(dt);
      pivot.position.set(centre.x + s.x, centre.y + s.y + s.bob, centre.z + s.z);
      pivot.rotation.set(s.pitch, s.yaw, s.roll, "YXZ");
    },
  };
}
