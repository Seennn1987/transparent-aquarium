import * as THREE from "three";

export const STUDIO_BACKGROUND = "#f2f2f0";

// The key softbox stands in front of the jar to the left and above it, so the jar's shadow
// falls back to the right, beside it where the camera sees it. A second, dimmer softbox
// behind-left only rims the glass.
export const KEY_DIRECTION = new THREE.Vector3(-0.55, 0.72, 0.42).normalize();
const RIM_DIRECTION = new THREE.Vector3(-0.55, 0.5, -0.67).normalize();

/**
 * The softbox room the glass reflects, baked to a PMREM. It matches the visible lighting:
 * the big key behind-left gives the left rim its glow, a narrow strip front-right draws the
 * vertical highlight down the jar, and the dark room between them outlines the glass.
 */
export function createStudioEnvironment(renderer) {
  const room = new THREE.Scene();
  room.background = new THREE.Color("#3c3d3b");
  const panel = (w, h, intensity, position, lookAt = new THREE.Vector3(0, 1.2, 0)) => {
    const mesh = new THREE.Mesh(
      new THREE.PlaneGeometry(w, h),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(1, 1, 1).multiplyScalar(intensity), side: THREE.DoubleSide }),
    );
    mesh.position.copy(position);
    mesh.lookAt(lookAt);
    room.add(mesh);
  };
  panel(3.2, 3.2, 4, KEY_DIRECTION.clone().multiplyScalar(6).add(new THREE.Vector3(0, 1.2, 0)));
  panel(1.4, 4.5, 4.5, RIM_DIRECTION.clone().multiplyScalar(6).add(new THREE.Vector3(0, 1.2, 0)));
  panel(0.35, 4.5, 5.5, new THREE.Vector3(2.6, 2.2, 4.2));
  panel(0.6, 4, 1.8, new THREE.Vector3(-3.6, 2.0, 2.4));
  panel(3, 3, 1.4, new THREE.Vector3(0, 6.5, 0), new THREE.Vector3(0, 0, 0));
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(20, 20),
    new THREE.MeshBasicMaterial({ color: "#9a9994" }),
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

/**
 * Seamless studio sweep around the whole orbit. The wall the key faces is brighter than the
 * far side, and the floor-to-wall shading is the detail the liquid column visibly bends.
 */
export function createBackdrop(radius = 24) {
  const geometry = new THREE.SphereGeometry(radius, 96, 48);
  const colors = [];
  const top = new THREE.Color("#e9e9e6");
  const wall = new THREE.Color(STUDIO_BACKGROUND);
  const horizon = new THREE.Color("#dcdbd6");
  const low = new THREE.Color("#e2e1dd");
  const key = new THREE.Vector2(KEY_DIRECTION.x, KEY_DIRECTION.z).normalize();
  const position = geometry.attributes.position;
  const color = new THREE.Color();
  for (let i = 0; i < position.count; i++) {
    const h = position.getY(i) / radius;
    if (h > 0.12) color.copy(wall).lerp(top, THREE.MathUtils.smoothstep(h, 0.12, 0.85));
    else if (h > -0.02) color.copy(horizon).lerp(wall, THREE.MathUtils.smoothstep(h, -0.02, 0.12));
    else color.copy(low).lerp(horizon, THREE.MathUtils.smoothstep(h, -0.3, -0.02));
    const x = position.getX(i), z = position.getZ(i), r = Math.hypot(x, z) || 1;
    const facing = (x / r) * key.x + (z / r) * key.y;
    color.multiplyScalar(0.93 + 0.1 * THREE.MathUtils.smoothstep(facing, -0.6, 0.9));
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
 * The white table, lit by the key softbox. Its lighting is computed here rather than by a
 * shadow map because a glass jar does not cast an ordinary shadow: the cylinder of liquid
 * throws a soft, pale shadow that lengthens and blurs away from the jar, with a bright line
 * of focused light (the caustic) down its middle, faintly tinted by the specimen it crossed.
 * Near the foot the glass itself darkens the floor. The floor must stay opaque: it is part
 * of the image the glass refracts.
 */
export const FLOOR_LOOK = {
  shadow: { value: 0.36 },
  caustic: { value: 0.55 },
  contact: { value: 0.4 },
};

export function createStudioFloor(radius, { jarRadius, glassTop, liquidBottom, liquidTop }) {
  const toLight = new THREE.Vector2(KEY_DIRECTION.x, KEY_DIRECTION.z);
  const tanElevation = KEY_DIRECTION.y / toLight.length();
  const shadowDirection = toLight.clone().normalize().negate();
  const material = new THREE.ShaderMaterial({
    uniforms: {
      nearColor: { value: new THREE.Color("#e7e6e2") },
      farColor: { value: new THREE.Color("#dcdbd6") },
      causticTint: { value: new THREE.Color("#eaf8fb") },
      shadowDir: { value: shadowDirection },
      tanElevation: { value: tanElevation },
      jarRadius: { value: jarRadius },
      glassTop: { value: glassTop },
      liquidBottom: { value: liquidBottom },
      liquidTop: { value: liquidTop },
      shadowStrength: FLOOR_LOOK.shadow,
      causticStrength: FLOOR_LOOK.caustic,
      contactStrength: FLOOR_LOOK.contact,
    },
    vertexShader: `
      varying vec3 vWorld;
      void main() {
        vec4 world = modelMatrix * vec4(position, 1.);
        vWorld = world.xyz;
        gl_Position = projectionMatrix * viewMatrix * world;
      }`,
    fragmentShader: `
      uniform vec3 nearColor, farColor, causticTint;
      uniform vec2 shadowDir;
      uniform float tanElevation, jarRadius, glassTop, liquidBottom, liquidTop;
      uniform float shadowStrength, causticStrength, contactStrength;
      varying vec3 vWorld;
      void main() {
        vec2 p = vWorld.xz;
        float r = length(p);
        vec3 color = mix(nearColor, farColor, smoothstep(1.2, 18., r));

        // Distance along the shadow from the jar's axis, and across it.
        float along = dot(p, shadowDir);
        float across = abs(p.x * shadowDir.y - p.y * shadowDir.x);
        float shadowLength = glassTop / tanElevation;
        float t = clamp(along / shadowLength, 0., 1.);
        float halfWidth = jarRadius * (1. + .35 * t);
        float penumbra = .06 + .5 * t;
        float body = (1. - smoothstep(halfWidth - penumbra, halfWidth + penumbra, across))
          * smoothstep(-jarRadius, 0., along)
          * (1. - smoothstep(shadowLength * .85, shadowLength * 1.2, along));
        color *= 1. - body * shadowStrength * mix(1., .35, t);

        // The liquid column focuses the key into a line inside that shadow.
        float c0 = liquidBottom / tanElevation, c1 = liquidTop / tanElevation;
        float span = smoothstep(c0 - .1, c0 + .3, along) * (1. - smoothstep(c1 - .4, c1 + .2, along));
        float sigma = .035 + .16 * t;
        float line = exp(-across * across / (2. * sigma * sigma)) * (.04 / sigma);
        color += causticTint * nearColor * line * span * causticStrength;

        // Under and around the foot: the glass base and the contact with the table.
        float ring = exp(-max(r - jarRadius, 0.) / .07) * step(jarRadius * .7, r);
        color *= 1. - contactStrength * (r < jarRadius ? .35 : ring);
        gl_FragColor = vec4(color, 1.);
      }`,
  });
  const mesh = new THREE.Mesh(new THREE.CircleGeometry(radius, 128), material);
  mesh.rotation.x = -Math.PI / 2;
  mesh.name = "studio-floor";
  return mesh;
}
