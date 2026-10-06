import * as THREE from "three";

// The black table's mirror image: the scene drawn from the camera reflected in the table's top
// (y = 0), with the near plane tilted onto the table so nothing below it gets in the way
// (Lengyel's oblique clipping, as three's Reflector does it). Mips stand in for the polish.

const PLANE_NORMAL = new THREE.Vector3(0, 1, 0);

/** `uniforms`: the table's, from createTableReflection in gallery.js. */
export function createMirrorPass(uniforms) {
  const camera = new THREE.PerspectiveCamera();
  const target = new THREE.WebGLRenderTarget(1, 1, {
    type: THREE.HalfFloatType,
    generateMipmaps: true,
    minFilter: THREE.LinearMipmapLinearFilter,
  });
  uniforms.tReflect.value = target.texture;
  uniforms.uHasReflect.value = 1;

  const lookAt = new THREE.Vector3();
  const up = new THREE.Vector3();
  const rotation = new THREE.Matrix4();
  const plane = new THREE.Plane();
  const clip = new THREE.Vector4();
  const q = new THREE.Vector4();

  function place(view) {
    camera.position.copy(view.position);
    camera.position.y = -view.position.y;
    rotation.extractRotation(view.matrixWorld);
    lookAt.set(0, 0, -1).applyMatrix4(rotation).add(view.position);
    lookAt.y = -lookAt.y;
    up.set(0, 1, 0).applyMatrix4(rotation);
    up.y = -up.y;
    camera.up.copy(up);
    camera.lookAt(lookAt);
    camera.far = view.far;
    camera.updateMatrixWorld();
    camera.projectionMatrix.copy(view.projectionMatrix);

    uniforms.uReflectMatrix.value.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);

    plane.setFromNormalAndCoplanarPoint(PLANE_NORMAL, lookAt.set(0, 0, 0)).applyMatrix4(camera.matrixWorldInverse);
    clip.set(plane.normal.x, plane.normal.y, plane.normal.z, plane.constant);
    const e = camera.projectionMatrix.elements;
    q.set((Math.sign(clip.x) + e[8]) / e[0], (Math.sign(clip.y) + e[9]) / e[5], -1, (1 + e[10]) / e[14]);
    clip.multiplyScalar(2 / clip.dot(q));
    e[2] = clip.x;
    e[6] = clip.y;
    e[10] = clip.z + 1;
    e[14] = clip.w;
    camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
  }

  return {
    target,
    /** Draws `scene` as the table mirrors it from `view`. */
    render(renderer, scene, view) {
      place(view);
      renderer.setRenderTarget(target);
      renderer.render(scene, camera);
    },
    setSize(width, height) {
      target.setSize(Math.max(1, width), Math.max(1, height));
    },
    dispose() {
      target.dispose();
    },
  };
}
