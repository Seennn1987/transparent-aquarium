import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { createLightbox, chameleonLook } from "./chameleon-material.js";
import { HH_BONE_T0 } from "./hammerhead-stain.js";   // registers STAINS.hammerhead
import { applyHammerheadTissue } from "./hammerhead-material.js";
import { createSwim } from "./hammerhead-swim.js";

// シロシュモクザメ（hammerhead.html）を、ギャラリーの前の台の低い器（dish.glb）に入れる。`?specimen=hammerhead`（C、2026-10-15）。
//  描き方はカメレオンと同じ: 透かしの通り道（chameleon-material.js の createLightbox、色は hammerhead-stain.js）を、器の屈折が引く画像に描く。
//  泳ぎは標本ページと同じ（hammerhead-swim.js: その場のうねり・口・心臓。回る道すじは C2 でまだ）。
//  大きさ: 器の液の中で、吻端〜尾（尾の振れを含む）が壁から、背〜腹が底と液面から HH_DISH.clearance 離れる、いちばん大きい縮尺
//  （器の単位 / m）。標本は縮めて描くので、組織の通り道は 1 / 縮尺 倍に数えて、本当の大きさの濃さにする（pathScale）。
const HAMMERHEAD_URL = new URL("../assets/specimen_hammerhead.glb", import.meta.url).href;
export const HH_DISH = {
  clearance: 0.12,        // 器の単位。カメレオンの瓶と同じ空き（計画書 第 4 節 C2 の目安）
  tailSwing: 0.09,        // 尾の先の片側の振れ（全長に対して、hammerhead-swim.js の既定）
};

/**
 * `facing`: 見る人への水平の向き。サメは背を上に、左の体側（glTF の +Z）を見る人へ向けて、器の真ん中に浮かぶ。
 */
export async function createHammerheadSpecimen({ liquidBounds, facing }) {
  const gltf = await new GLTFLoader().loadAsync(HAMMERHEAD_URL);
  const model = gltf.scene;
  const reference = { value: 0 };
  applyHammerheadTissue(model, reference);
  chameleonLook.boneT0.value = HH_BONE_T0;
  chameleonLook.film.value = 1;     // 皮歯（hammerhead-main.js と同じ既定）
  chameleonLook.organs.value = 1;   // まだら・鰓条・内臓の通り道

  const body = new THREE.Group();
  body.name = "Specimen";
  body.add(model);
  model.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(model, true);
  const size = box.getSize(new THREE.Vector3());
  const c = HH_DISH.clearance;
  const radius = (liquidBounds.max.x - liquidBounds.min.x) / 2;
  const depth = liquidBounds.max.y - liquidBounds.min.y;
  // 吻端〜尾は器の真ん中を通る直径に沿う。尾の振れの分だけ、体の端は真ん中から遠くなる
  const reach = Math.hypot(size.x / 2, HH_DISH.tailSwing * size.x);
  const scale = Math.min((radius - c) / reach, (depth - 2 * c) / size.y);
  model.rotation.y = Math.atan2(facing.x, facing.z);
  body.scale.setScalar(scale);
  const middle = box.getCenter(new THREE.Vector3()).applyAxisAngle(new THREE.Vector3(0, 1, 0), model.rotation.y);
  body.position.copy(middle).multiplyScalar(-scale);

  const pivot = new THREE.Group();
  pivot.name = "SpecimenPivot";
  pivot.add(body);
  pivot.position.copy(liquidBounds.getCenter(new THREE.Vector3()));
  pivot.updateMatrixWorld(true);
  const swim = createSwim(model);
  let lightbox = null;
  const view = new THREE.Vector3();
  // 調整の欄（tune-panel.js）の「泳ぎの速さ」はイカ・カメレオンの hoverAction.timeScale を動かす。シュモクザメは時計の進み方の倍率にする
  const hoverAction = { timeScale: 1 };

  return {
    object: pivot,
    model,
    swim,
    organs: null,
    hoverAction,
    /** 漂い（イカの specimen-motion.js）はまだ無い。回る道すじは C2 で作る */
    motion: { setRate() {} },
    /** 机の映り込みの写しはイカの組織を焼き付ける。シュモクザメは焼き付けない */
    bakeable: false,
    scale,
    size,
    bounds: new THREE.Box3().setFromObject(pivot, true),
    update(dt) { swim?.update(dt * hoverAction.timeScale); },
    /** 体を通った光（白の上、線形）を `target` に描く */
    renderImage(renderer, target, camera, scene) {
      lightbox ??= createLightbox(renderer, { linear: true, alphaScale: 1, pathScale: 1 / scale, stain: "hammerhead" });
      if (lightbox.size.width !== target.width || lightbox.size.height !== target.height)
        lightbox.setSize(target.width, target.height);
      pivot.getWorldPosition(view).applyMatrix4(camera.matrixWorldInverse);
      reference.value = -view.z;
      lightbox.render(scene, camera, target);
    },
  };
}
