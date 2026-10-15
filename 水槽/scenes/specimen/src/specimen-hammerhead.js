import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { createLightbox, chameleonLook } from "./chameleon-material.js";
import { HH_BONE_T0 } from "./hammerhead-stain.js";   // registers STAINS.hammerhead
import { applyHammerheadTissue } from "./hammerhead-material.js";
import { createSwim, swimLook } from "./hammerhead-swim.js";
import { circlePose, circleSpeed, dishBaseScale, fitCircle, HH_HEIGHT } from "./hammerhead-path.js";

// シロシュモクザメ（hammerhead.html）を、ギャラリーの前の台の低い器（dish.glb）に入れる。`?specimen=hammerhead`（C、2026-10-15）。
//  描き方はカメレオンと同じ: 透かしの通り道（chameleon-material.js の createLightbox、色は hammerhead-stain.js）を、器の屈折が引く画像に描く。
//  泳ぎは標本ページと同じ（hammerhead-swim.js: その場のうねり・口・心臓。回る道すじは C2 でまだ）。
//  大きさ: 器の液の中で、吻端〜尾（尾の振れを含む）が壁から、背〜腹が底と液面から HH_DISH.clearance 離れる、いちばん大きい縮尺
//  （器の単位 / m）。標本は縮めて描くので、組織の通り道は 1 / 縮尺 倍に数えて、本当の大きさの濃さにする（pathScale）。
const HAMMERHEAD_URL = new URL("../assets/specimen_hammerhead.glb", import.meta.url).href;
export const HH_DISH = {
  clearance: 0.12,        // 器の単位。カメレオンの瓶と同じ空き（計画書 第 4 節 C2 の目安）
  tailSwing: 0.09,        // 尾の先の片側の振れ（全長に対して、hammerhead-swim.js の既定）
  // 器の大きさの、サメに対する倍率（C1 の大きさを 1）。器の形はそのままでサメを 1 / 倍率に描くので、直径も高さもサメに対してこの倍率になる。
  //  既定 2（2026-10-15 プロデューサー「2倍、高さも2倍」）。?dish= で変える
  ratio: Number(new URLSearchParams(location.search).get("dish") ?? 2),
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
  // いまの器の大きさ（C1）: 吻端〜尾が器の真ん中を通る直径に沿い、尾の振れの分も壁から c 離れる縮尺。これを「器の直径 1 倍」とする
  const scale1 = dishBaseScale({ radius, depth, clearance: c, tailSwing: HH_DISH.tailSwing });   // hammerhead-path.js（自動テストと同じ式）
  // C2・C3（2026-10-15、プロデューサー「サメのサイズに対して水槽が小さいです。せめて直径を２倍以上にしないと周回できないのではないでしょうか？」）:
  //  器はこのまま（前の台に載る大きさ）で、サメを 1 / dishRatio に縮めて描く（＝器の直径がサメに対して dishRatio 倍）。
  //  回れるとき（hammerhead-path.js の fitCircle）は、体の真ん中が器の軸のまわりの円を反時計回りに進む。回れないときは真ん中でその場の泳ぎ
  const swimOpts = () => ({ amplitude: swimLook.amplitude, wavelength: swimLook.wavelength, turnBend: swimLook.turnBend, frequency: swimLook.frequency });
  const yMid = (HH_HEIGHT.top + HH_HEIGHT.bottom) / 2;
  const centre = liquidBounds.getCenter(new THREE.Vector3());
  const state = { ratio: 0, scale: scale1, circle: null, theta: 0, lastTime: 0 };
  const pivot = new THREE.Group();
  pivot.name = "SpecimenPivot";
  pivot.add(body);
  function setDishRatio(k) {
    state.ratio = k; state.scale = scale1 / k;
    state.circle = fitCircle({ inner: radius, clearance: c, scale: state.scale, swim: swimOpts() });
    body.scale.setScalar(state.scale);
    if (!state.circle) {   // その場: 左の体側を見る人へ
      model.rotation.y = Math.atan2(facing.x, facing.z);
      const middle = box.getCenter(new THREE.Vector3()).applyAxisAngle(new THREE.Vector3(0, 1, 0), model.rotation.y);
      body.position.copy(middle).multiplyScalar(-state.scale);
      pivot.position.copy(centre); pivot.rotation.set(0, 0, 0);
      swimLook.turn = 0;
    } else { model.rotation.y = 0; swimLook.turnBend = 1; }   // 回るときは体を道すじの円と同じ曲がりに（hammerhead-path.js の circlePose）
    lightbox?.dispose?.(); lightbox = null;   // 組織の通り道の倍率（1 / 縮尺）が変わる
  }
  function place() {
    if (!state.circle) return;
    // 円の上の角は、時計の進み（一時停止で 0）× 速さ / 半径 を足す
    const dt = swim.clock.time - state.lastTime; state.lastTime = swim.clock.time;
    state.theta += circleSpeed(state.scale, swimOpts()) * dt / state.circle;
    const pose = circlePose(state.theta, swim.clock.state.tailCycles, { radius: state.circle, scale: state.scale, swim: swimOpts() });
    swimLook.turn = pose.turn;   // 次のフレームの骨の曲げ（道すじの円の向き、体の右へ）
    body.position.set(-state.scale * pose.mid.x, -state.scale * yMid, -state.scale * pose.mid.z);
    pivot.position.set(centre.x + pose.at.x, centre.y, centre.z + pose.at.z);
    pivot.rotation.set(0, pose.yaw, 0);
  }
  const swim = createSwim(model);
  let lightbox = null;
  setDishRatio(HH_DISH.ratio);
  place();
  pivot.updateMatrixWorld(true);
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
    get scale() { return state.scale; },
    get dishRatio() { return state.ratio; },
    get circleRadius() { return state.circle; },
    setDishRatio(k) { setDishRatio(k); place(); },
    get theta() { return state.theta; },
    size,
    bounds: new THREE.Box3().setFromObject(pivot, true),
    update(dt) {
      if (state.circle) swimLook.turn = circlePose(state.theta, swim.clock.state.tailCycles, { radius: state.circle, scale: state.scale, swim: swimOpts() }).turn;
      swim?.update(dt * hoverAction.timeScale);
      place();
    },
    /** 体を通った光（白の上、線形）を `target` に描く */
    renderImage(renderer, target, camera, scene) {
      lightbox ??= createLightbox(renderer, { linear: true, alphaScale: 1, pathScale: 1 / state.scale, stain: "hammerhead" });
      if (lightbox.size.width !== target.width || lightbox.size.height !== target.height)
        lightbox.setSize(target.width, target.height);
      pivot.getWorldPosition(view).applyMatrix4(camera.matrixWorldInverse);
      reference.value = -view.z;
      lightbox.render(scene, camera, target);
    },
  };
}
