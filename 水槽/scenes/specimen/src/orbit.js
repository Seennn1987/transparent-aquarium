import * as THREE from "three";

/** Drag to orbit, wheel/pinch to zoom. Horizontal orbit is the main gesture. */
export function createOrbit(camera, canvas, {
  target = new THREE.Vector3(0, 1.1, 0),
  minDistance = 2.2,
  maxDistance = 12,
  minPolar = 0.25,
  maxPolar = Math.PI * 0.48,
  rotateSpeed = 0.0055,
  zoomSpeed = 0.0014,
  onChange = () => {},
} = {}) {
  const spherical = new THREE.Spherical();
  const offset = new THREE.Vector3();
  offset.copy(camera.position).sub(target);
  spherical.setFromVector3(offset);

  let dragging = false;
  let lastX = 0;
  let lastY = 0;

  function apply() {
    spherical.theta = THREE.MathUtils.euclideanModulo(spherical.theta, Math.PI * 2);
    spherical.phi = THREE.MathUtils.clamp(spherical.phi, minPolar, maxPolar);
    spherical.radius = THREE.MathUtils.clamp(spherical.radius, minDistance, maxDistance);
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
    spherical.theta -= dx * rotateSpeed;
    spherical.phi -= dy * rotateSpeed;
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
  };
}
