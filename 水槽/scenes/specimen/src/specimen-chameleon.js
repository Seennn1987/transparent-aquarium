import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { applyChameleonTissue, createLightbox, chameleonClock } from "./chameleon-material.js";
import { createSpecimenMotion, MOTION } from "./specimen-motion.js";

// The cleared-and-stained chameleon (chameleon.html) in the front jar, `?specimen=chameleon`.
// The mesh comes from the MorphoSource CT (non-commercial, not redistributed), so the file is
// kept out of git: blender/export_chameleon_gltf.py writes it to assets/private/.
const CHAMELEON_URL = new URL("../assets/private/specimen_chameleon.glb", import.meta.url).href;
const CLIP = "CH_Hover";

export const CHAMELEON_POSE = {
  // The plan (docs/カメレオン透明標本_計画書_v1.0.md §2): the jar is enlarged until the animal,
  // at its own size, clears the wall, the surface and the floor by 0.12; the animal is not shrunk.
  clearance: 0.12,
  // CH_Hover's breathing and heartbeat are in real seconds (chameleon-stain.js, rig_chameleon_ct.py).
  hoverRate: 1,
  // The squid's drift (specimen-motion.js) is kept, except that its turns about the jar's axis,
  // which add up without a limit, are held within ±maxYaw so the animal's side stays toward the
  // viewer (a visual choice, not measured).
  maxYawDegrees: 12,
  // Poses of CH_Hover the animal's box is taken over (the breathing moves the ribs).
  boxSamples: 6,
};

/**
 * The jar's enlargement J (§2): the smallest uniform scale of the jar at which the animal, at its
 * own size `size` (model units, in its own frame: x across the jar, z toward the viewer), clears
 * the glass by `clearance` with the drift (specimen-motion.js MOTION) on top. The half width is
 * taken at the largest turn. Everything is then drawn at 1 / J, so the jar, the room and the
 * camera stay as they are: the animal is drawn at 1 / J and the clearance and drift likewise.
 */
export function jarEnlargement(size, liquidBounds) {
  const c = CHAMELEON_POSE.clearance;
  const yaw = CHAMELEON_POSE.maxYawDegrees * Math.PI / 180;
  const radius = (liquidBounds.max.x - liquidBounds.min.x) / 2;
  const height = liquidBounds.max.y - liquidBounds.min.y;
  const halfWidth = (size.x * Math.cos(yaw) + size.z * Math.sin(yaw)) / 2;
  return Math.max(
    (halfWidth + c + MOTION.limitRadius) / radius,
    (size.y + 2 * c + 2 * (MOTION.limitHeight + MOTION.bobHeight)) / height,
  );
}

/**
 * `facing`: horizontal direction toward the viewer. The animal hangs as in photo 01 (head down,
 * its left side, the model's +Z, toward the viewer). The tissue is drawn by the lightbox passes
 * (chameleon-material.js) into the image the jar's optics look up: `renderImage` takes the place
 * of drawing the specimen scene over white. `stain`: the colour pattern (chameleon-stain.js STAINS).
 */
export async function createChameleonSpecimen({ liquidBounds, facing, stain = "06" }) {
  const gltf = await new GLTFLoader().loadAsync(CHAMELEON_URL);
  const model = gltf.scene;
  const reference = { value: 0 };
  applyChameleonTissue(model, reference);
  const clip = THREE.AnimationClip.findByName(gltf.animations, CLIP);
  if (!clip) throw new Error(`specimen_chameleon.glb に ${CLIP} がありません`);
  const mixer = new THREE.AnimationMixer(model);
  const action = mixer.clipAction(clip).play();
  action.timeScale = CHAMELEON_POSE.hoverRate;

  const body = new THREE.Group();
  body.name = "Specimen";
  body.add(model);
  // The box in the model's own frame over the loop, before the yaw.
  const box = new THREE.Box3(), pose = new THREE.Box3();
  for (let i = 0; i < CHAMELEON_POSE.boxSamples; i++) {
    mixer.setTime(clip.duration * i / CHAMELEON_POSE.boxSamples);
    body.updateMatrixWorld(true);
    box.union(pose.setFromObject(body, true));
  }
  mixer.setTime(0);
  const size = box.getSize(new THREE.Vector3());
  const jar = jarEnlargement(size, liquidBounds);
  const scale = 1 / jar;
  model.rotation.y = Math.atan2(facing.x, facing.z);
  body.scale.setScalar(scale);
  body.updateMatrixWorld(true);
  // Centred on the middle of the loop's box (turned with the model).
  const middle = box.getCenter(new THREE.Vector3()).applyAxisAngle(new THREE.Vector3(0, 1, 0), model.rotation.y);
  body.position.copy(middle).multiplyScalar(-scale);

  const pivot = new THREE.Group();
  pivot.name = "SpecimenPivot";
  pivot.add(body);
  const centre = liquidBounds.getCenter(new THREE.Vector3());
  pivot.position.copy(centre);

  const maxYaw = THREE.MathUtils.degToRad(CHAMELEON_POSE.maxYawDegrees);
  const motion = createSpecimenMotion({ rate: MOTION.driftRate });
  let lightbox = null;
  const view = new THREE.Vector3();

  return {
    object: pivot,
    model,
    mixer,
    hoverAction: action,
    motion,
    organs: null,
    /** The squid's mirror copy (gallery-jars.js) bakes squid tissue; this one is not baked. */
    bakeable: false,
    /** How much larger the jar is than the squid's, and the animal's size in it (model units). */
    jarScale: jar,
    scale,
    size,
    bounds: new THREE.Box3().setFromObject(pivot, true),
    update(dt) {
      if (dt <= 0) return;
      mixer.update(dt);
      // The drift is in the enlarged jar's units, so it is drawn at 1 / J too.
      const s = motion.update(dt);
      pivot.position.set(centre.x + scale * s.x, centre.y + scale * (s.y + s.bob), centre.z + scale * s.z);
      pivot.rotation.set(s.pitch, maxYaw * Math.tanh(s.yaw / maxYaw), s.roll, "YXZ");
    },
    /** Draws the light let through the animal (over white, linear) into `target`. */
    renderImage(renderer, target, camera, scene) {
      lightbox ??= createLightbox(renderer, { linear: true, alphaScale: 1, pathScale: jar, stain });
      if (lightbox.target.width !== target.width || lightbox.target.height !== target.height)
        lightbox.setSize(target.width, target.height);
      chameleonClock.value = action.time;
      // The plane the solid paths are measured from: through the animal's middle.
      pivot.getWorldPosition(view).applyMatrix4(camera.matrixWorldInverse);
      reference.value = -view.z;
      lightbox.render(scene, camera, target);
    },
  };
}
