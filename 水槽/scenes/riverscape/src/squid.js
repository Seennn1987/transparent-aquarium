import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { applySquidTissue } from "./squid-material.js";
import { createSquidPilot, SQUID_ML } from "./squid-behavior.js";

// The squid made in blender/ (export_squid_gltf.py): its parts, its 98 bones and the four
// in-place clips. The pilot decides where it goes; this plays the matching clip.
const CLIPS = { hover: "SQ_Hover", swim: "SQ_SwimForward", back: "SQ_SwimBackward", jet: "SQ_Jet" };
// The jet starts almost at once: the clip itself opens with the intake of water.
const FADE = { hover: 0.6, swim: 0.6, back: 0.5, jet: 0.2 };

export async function createSquid(scene, { obstacles }) {
  const gltf = await new GLTFLoader().loadAsync(new URL("../assets/squid.glb", import.meta.url).href);
  const model = gltf.scene;
  applySquidTissue(model);
  // In the file the arms point along -X; the pilot's heading is +X.
  model.rotation.y = Math.PI;
  const body = new THREE.Group();
  body.name = "Squid";
  body.rotation.order = "YZX";
  body.scale.setScalar(SQUID_ML);
  body.add(model);
  scene.add(body);

  const mixer = new THREE.AnimationMixer(model);
  const actions = {};
  for (const [mode, name] of Object.entries(CLIPS)) {
    const clip = THREE.AnimationClip.findByName(gltf.animations, name);
    if (!clip) throw new Error(`squid.glb has no animation ${name}`);
    const action = mixer.clipAction(clip);
    if (mode === "jet") {
      action.setLoop(THREE.LoopOnce, 1);
      action.clampWhenFinished = true;
    }
    actions[mode] = action;
  }
  const pilot = createSquidPilot({ obstacles });
  let mode = pilot.state.mode;
  let current = actions[mode].play();

  function place(state) {
    body.position.copy(state.position);
    body.rotation.set(0, -state.yaw, state.pitch);
  }
  place(pilot.state);

  return {
    object: body,
    pilot,
    mode: () => mode,
    update(dt, time, pointer) {
      const state = pilot.update(dt, pointer);
      if (state.mode !== mode) {
        const next = actions[state.mode].reset().play();
        current.crossFadeTo(next, FADE[state.mode], false);
        current = next;
        mode = state.mode;
      }
      mixer.update(dt);
      place(state);
    },
  };
}
