import * as THREE from "three";

export const STUDIO_BACKGROUND = "#f2f2f0";

/**
 * A white softbox room baked to a PMREM. The tall side panels are what draw the
 * vertical highlight streaks down a cylindrical jar; the top panel lights the lid knob.
 */
export function createStudioEnvironment(renderer) {
  // A darker room than the visible backdrop: glass edges seen at grazing angles reflect it,
  // which is what outlines a clear jar against a white studio.
  const room = new THREE.Scene();
  room.background = new THREE.Color("#4a4b49");
  const panel = (w, h, intensity, position, lookAt = new THREE.Vector3(0, 1.2, 0)) => {
    const mesh = new THREE.Mesh(
      new THREE.PlaneGeometry(w, h),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(1, 1, 1).multiplyScalar(intensity), side: THREE.DoubleSide }),
    );
    mesh.position.copy(position);
    mesh.lookAt(lookAt);
    room.add(mesh);
  };
  panel(0.9, 5, 6, new THREE.Vector3(-3.2, 2.2, 2.2));
  panel(0.5, 5, 4, new THREE.Vector3(3.4, 2.2, 1.6));
  panel(3, 3, 2.2, new THREE.Vector3(0, 6, 0), new THREE.Vector3(0, 0, 0));
  panel(5, 2.5, 1.1, new THREE.Vector3(0, 1.8, -4));
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(20, 20),
    new THREE.MeshBasicMaterial({ color: "#8e8d88" }),
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.01;
  room.add(floor);

  const pmrem = new THREE.PMREMGenerator(renderer);
  const target = pmrem.fromScene(room, 0.02);
  pmrem.dispose();
  room.traverse((object) => {
    object.geometry?.dispose();
    object.material?.dispose();
  });
  return target.texture;
}

function radialTexture(stops) {
  const size = 512;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const context = canvas.getContext("2d");
  const gradient = context.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  for (const [offset, color] of stops) gradient.addColorStop(offset, color);
  context.fillStyle = gradient;
  context.fillRect(0, 0, size, size);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

/**
 * Seamless studio sweep around the whole orbit. Its soft floor-to-wall shading is the detail
 * the liquid column visibly bends; a flat backdrop would give the glass nothing to refract.
 */
export function createBackdrop(radius = 24) {
  const geometry = new THREE.SphereGeometry(radius, 64, 32);
  const colors = [];
  const top = new THREE.Color("#f6f6f4");
  const wall = new THREE.Color(STUDIO_BACKGROUND);
  const horizon = new THREE.Color("#dfded9");
  const low = new THREE.Color("#e6e5e1");
  const position = geometry.attributes.position;
  const color = new THREE.Color();
  for (let i = 0; i < position.count; i++) {
    const h = position.getY(i) / radius;
    if (h > 0.12) color.copy(wall).lerp(top, THREE.MathUtils.smoothstep(h, 0.12, 0.8));
    else if (h > -0.02) color.copy(horizon).lerp(wall, THREE.MathUtils.smoothstep(h, -0.02, 0.12));
    else color.copy(low).lerp(horizon, THREE.MathUtils.smoothstep(h, -0.3, -0.02));
    colors.push(color.r, color.g, color.b);
  }
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  const mesh = new THREE.Mesh(
    geometry,
    new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide, depthWrite: false }),
  );
  mesh.name = "studio-backdrop";
  mesh.renderOrder = -10;
  return mesh;
}

/**
 * Unlit sweep floor: slightly darker under the jar, exactly the backdrop colour at its rim,
 * so the horizon disappears without fog. It stays opaque so the glass refracts it.
 */
export function createStudioFloor(radius) {
  const mesh = new THREE.Mesh(
    new THREE.CircleGeometry(radius, 96),
    new THREE.MeshBasicMaterial({
      map: radialTexture([
        [0, "#dcdbd6"],
        [0.08, "#e0dfda"],
        [0.3, "#e4e3df"],
        [0.7, "#e2e1dc"],
        [1, "#dfded9"],
      ]),
    }),
  );
  mesh.rotation.x = -Math.PI / 2;
  mesh.name = "studio-floor";
  return mesh;
}

/**
 * Soft contact darkening under the jar: glass lets most light through, so its shadow is faint.
 * Opaque and blended into the floor's centre colour, because transparent meshes are missing
 * from the image the glass refracts.
 */
export function createContactShadow(radius) {
  const mesh = new THREE.Mesh(
    new THREE.CircleGeometry(radius, 96),
    new THREE.MeshBasicMaterial({
      map: radialTexture([
        [0, "#c9c8c2"],
        [0.5, "#cfcec8"],
        [0.66, "#d6d5d0"],
        [1, "#dcdbd6"],
      ]),
      polygonOffset: true,
      polygonOffsetFactor: -1,
      polygonOffsetUnits: -1,
    }),
  );
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.y = 0.001;
  mesh.name = "contact-shadow";
  return mesh;
}
