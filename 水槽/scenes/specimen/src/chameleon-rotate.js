// The chameleon page's rotation bars (C record 53, 2026-10-24, the producer: 「回転させるのが難しいです。画面に、調整パネルとは
// 別に３軸それぞれ変化させる３つのバーを表示して」). Three bars along the bottom turn the specimen about its own centre, about the
// screen's horizontal (X), vertical (Y) and depth (Z) axes, −180°…180°. "0 に戻す" puts it back to the starting orientation.
// C record 55 (the producer: 「ドラッグ&ドロップで手動で回転した時もスライダーが連動するようにして」): dragging on the page turns the
// specimen too (not the camera, which stays put), and the bars follow. Not saved. ?tune=0 leaves the bars out (dragging still works).
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
const DRAG_SPEED = 0.0055;   // radians per pixel, as the camera's orbit had it

/** `pivot`: a group whose position is the specimen's centre (rotating it turns the specimen in place). The camera must look
 *  along −Z with +Y up and stay so (the screen's axes are then the world's). `canvas`: where dragging turns the specimen. */
export function installChameleonRotate(pivot, canvas) {
  const base = pivot.quaternion.clone();
  // The turn on top of the start, about the screen's axes: Rz · Ry · Rx (Euler order "ZYX"), as the bars show it.
  const turn = new THREE.Quaternion();
  const euler = new THREE.Euler(0, 0, 0, "ZYX");
  const apply = () => { pivot.quaternion.copy(turn).multiply(base); };
  const inputs = [];
  const show = () => {
    euler.setFromQuaternion(turn, "ZYX");
    for (const [input, shown, key] of inputs) {
      const v = Math.round(THREE.MathUtils.radToDeg(euler[key]));
      input.value = String(v); shown.textContent = `${v}°`;
    }
  };

  let drag = null;
  canvas.addEventListener("pointerdown", (e) => { if (e.button === 0) drag = { x: e.clientX, y: e.clientY }; });
  canvas.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    drag = { x: e.clientX, y: e.clientY };
    // Right drags the near side right (about the screen's vertical), down drags it down (about the horizontal).
    const q = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), dx * DRAG_SPEED)
      .premultiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), dy * DRAG_SPEED));
    turn.premultiply(q).normalize();
    apply(); show();
  });
  for (const type of ["pointerup", "pointercancel", "pointerleave"]) canvas.addEventListener(type, () => { drag = null; });

  if (new URLSearchParams(location.search).get("tune") === "0") return;
  const style = document.createElement("style"); style.textContent = CSS; document.head.append(style);
  const bar = document.createElement("div"); bar.id = "ch-rot"; bar.setAttribute("aria-label", "標本の向き");
  const fromBars = () => {
    const a = Object.fromEntries(inputs.map(([input, , key]) => [key, THREE.MathUtils.degToRad(Number(input.value))]));
    turn.setFromEuler(euler.set(a.x, a.y, a.z, "ZYX"));
    apply();
  };
  for (const [key, label] of [["x", "横軸 X"], ["y", "縦軸 Y"], ["z", "奥行き Z"]]) {
    const row = document.createElement("label");
    const name = document.createElement("span"); name.textContent = label;
    const input = document.createElement("input"); input.type = "range"; input.min = "-180"; input.max = "180"; input.step = "1"; input.value = "0";
    input.setAttribute("aria-label", `${label} の回転（度）`);
    const shown = document.createElement("span"); shown.className = "value"; shown.textContent = "0°";
    input.addEventListener("input", () => { shown.textContent = `${input.value}°`; fromBars(); });
    row.append(name, input, shown); bar.append(row); inputs.push([input, shown, key]);
  }
  const reset = document.createElement("button"); reset.type = "button"; reset.textContent = "0 に戻す";
  reset.addEventListener("click", () => { turn.identity(); apply(); show(); });
  bar.append(reset);
  // Keys on the bars stay with the bars (Space pauses the page otherwise).
  bar.addEventListener("keydown", (e) => e.stopPropagation());
  document.body.append(bar);
}
