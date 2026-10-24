// The chameleon page's rotation bars (C record 53, 2026-10-24, the producer: 「回転させるのが難しいです。画面に、調整パネルとは
// 別に３軸それぞれ変化させる３つのバーを表示して」). Three bars along the bottom turn the specimen about its own centre, about the
// screen's horizontal (X), vertical (Y) and depth (Z) axes, −180°…180°. "0" puts it back. Dragging on the page still orbits the camera.
// Not saved. ?tune=0 leaves it out (the page-checking tools hide it).
import * as THREE from "three";

const CSS = `
#ch-rot { position: fixed; z-index: 3; left: 50%; bottom: 12px; transform: translateX(-50%); display: flex; gap: 14px; align-items: center;
  padding: 8px 12px; background: rgba(250, 250, 250, 0.92); border: 1px solid #bbb; border-radius: 6px;
  font: 12px/1.4 system-ui, sans-serif; color: #222; max-width: calc(100vw - 24px); flex-wrap: wrap; justify-content: center; }
#ch-rot label { display: flex; gap: 6px; align-items: center; }
#ch-rot input[type="range"] { width: 160px; }
#ch-rot .value { width: 3.2em; text-align: right; font-variant-numeric: tabular-nums; }
#ch-rot button { min-height: 26px; padding: 0 10px; border: 1px solid #aaa; border-radius: 4px; background: #fff; cursor: pointer; }
@media (max-width: 600px) { #ch-rot input[type="range"] { width: 90px; } }
`;

/** `pivot`: a group whose position is the specimen's centre (rotating it turns the specimen in place). `camera`: to take the
 *  screen's axes from. */
export function installChameleonRotate(pivot, camera) {
  if (new URLSearchParams(location.search).get("tune") === "0") return;
  const style = document.createElement("style"); style.textContent = CSS; document.head.append(style);
  const bar = document.createElement("div"); bar.id = "ch-rot"; bar.setAttribute("aria-label", "標本の向き");
  const base = pivot.quaternion.clone();
  const angles = { x: 0, y: 0, z: 0 };
  const apply = () => {
    // Screen axes in world space, taken from the camera when the bar is moved.
    camera.updateMatrixWorld();
    const ax = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
    const ay = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 1);
    const az = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 2);
    const q = new THREE.Quaternion()
      .multiply(new THREE.Quaternion().setFromAxisAngle(az, THREE.MathUtils.degToRad(angles.z)))
      .multiply(new THREE.Quaternion().setFromAxisAngle(ay, THREE.MathUtils.degToRad(angles.y)))
      .multiply(new THREE.Quaternion().setFromAxisAngle(ax, THREE.MathUtils.degToRad(angles.x)));
    pivot.quaternion.copy(q.multiply(base));
  };
  const inputs = [];
  for (const [key, label] of [["x", "横軸 X"], ["y", "縦軸 Y"], ["z", "奥行き Z"]]) {
    const row = document.createElement("label");
    const name = document.createElement("span"); name.textContent = label;
    const input = document.createElement("input"); input.type = "range"; input.min = "-180"; input.max = "180"; input.step = "1"; input.value = "0";
    input.setAttribute("aria-label", `${label} の回転（度）`);
    const shown = document.createElement("span"); shown.className = "value"; shown.textContent = "0°";
    input.addEventListener("input", () => { angles[key] = Number(input.value); shown.textContent = `${input.value}°`; apply(); });
    row.append(name, input, shown); bar.append(row); inputs.push([input, shown, key]);
  }
  const reset = document.createElement("button"); reset.type = "button"; reset.textContent = "0 に戻す";
  reset.addEventListener("click", () => {
    for (const [input, shown, key] of inputs) { input.value = "0"; shown.textContent = "0°"; angles[key] = 0; }
    apply();
  });
  bar.append(reset);
  // Keys on the bars stay with the bars (Space pauses the page otherwise); dragging a bar does not orbit the camera.
  bar.addEventListener("keydown", (e) => e.stopPropagation());
  bar.addEventListener("pointerdown", (e) => e.stopPropagation());
  document.body.append(bar);
}
