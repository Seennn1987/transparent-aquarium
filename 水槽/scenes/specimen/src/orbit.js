import * as THREE from "three";

/** Drag to orbit, wheel/pinch to zoom. Horizontal orbit is the main gesture.
 *  2026-10-24 プロデューサー「ギャラリーのカメラの角度、ズームだけじゃなくて、カメラの高さを調整できるようにして」:
 *  高さ（height）= カメラと見る点を一緒に上下させる量。Shift を押しながら上下にドラッグで変わる。view() / setView() で角度・高さ・距離を読み書きする（camera-panel.js） */
export function createOrbit(camera, canvas, {
  target = new THREE.Vector3(0, 1.1, 0),
  minDistance = 2.2,
  maxDistance = 12,
  minPolar = 0.25,
  maxPolar = Math.PI * 0.48,
  // Horizontal limits as angles about +Y from +Z; unset, the orbit goes all the way round.
  minAzimuth = -Infinity,
  maxAzimuth = Infinity,
  rotateSpeed = 0.0055,
  zoomSpeed = 0.0014,
  minHeight = -Infinity,
  maxHeight = Infinity,
  heightSpeed = 0.006,
  onChange = () => {},
} = {}) {
  const spherical = new THREE.Spherical();
  const offset = new THREE.Vector3();
  offset.copy(camera.position).sub(target);
  spherical.setFromVector3(offset);
  const baseY = target.y;
  let height = 0;

  let dragging = false;
  let lastX = 0;
  let lastY = 0;

  function apply() {
    spherical.theta = Number.isFinite(minAzimuth) || Number.isFinite(maxAzimuth)
      ? THREE.MathUtils.clamp(spherical.theta, minAzimuth, maxAzimuth)
      : THREE.MathUtils.euclideanModulo(spherical.theta, Math.PI * 2);
    spherical.phi = THREE.MathUtils.clamp(spherical.phi, minPolar, maxPolar);
    spherical.radius = THREE.MathUtils.clamp(spherical.radius, minDistance, maxDistance);
    height = THREE.MathUtils.clamp(height, minHeight, maxHeight);
    target.y = baseY + height;
    offset.setFromSpherical(spherical);
    camera.position.copy(target).add(offset);
    camera.lookAt(target);
    onChange();
  }

  apply();

  canvas.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    dragging = true;
    lastX = event.clientX;
    lastY = event.clientY;
    canvas.setPointerCapture(event.pointerId);
  });

  canvas.addEventListener("pointermove", (event) => {
    if (!dragging) return;
    const dx = event.clientX - lastX;
    const dy = event.clientY - lastY;
    lastX = event.clientX;
    lastY = event.clientY;
    if (event.shiftKey) height += dy * heightSpeed;
    else {
      spherical.theta -= dx * rotateSpeed;
      spherical.phi -= dy * rotateSpeed;
    }
    apply();
  });

  function endDrag(event) {
    if (!dragging) return;
    dragging = false;
    try { canvas.releasePointerCapture(event.pointerId); } catch {}
  }

  canvas.addEventListener("pointerup", endDrag);
  canvas.addEventListener("pointercancel", endDrag);
  canvas.addEventListener("pointerleave", endDrag);

  canvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    spherical.radius *= Math.exp(event.deltaY * zoomSpeed);
    apply();
  }, { passive: false });

  return {
    target,
    update() { apply(); },
    /** theta: 横の角度（+Y まわり、+Z から）、phi: 真上からの角度、radius: 見る点までの距離、height: 上下の量 */
    view() { return { theta: spherical.theta, phi: spherical.phi, radius: spherical.radius, height }; },
    setView(v) {
      if (Number.isFinite(v.theta)) spherical.theta = v.theta;
      if (Number.isFinite(v.phi)) spherical.phi = v.phi;
      if (Number.isFinite(v.radius)) spherical.radius = v.radius;
      if (Number.isFinite(v.height)) height = v.height;
      apply();
    },
    limits: { minDistance, maxDistance, minPolar, maxPolar, minAzimuth, maxAzimuth, minHeight, maxHeight },
  };
}
