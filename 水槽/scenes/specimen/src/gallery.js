import * as THREE from "three";
import { ROOM, PEDESTAL, SLOTS, pedestalRadius } from "./gallery-layout.js";

// A small gallery of cleared specimens: warm plank walls, a pale table, and each jar on an
// acrylic block lit from inside. The blocks are the main light: they glow up through the
// jars and pool on the table and the wall behind them.

// Product-shot framing: a long lens from slightly above the jar's middle.
export const DEFAULT_VIEW = {
  fov: 20,
  position: new THREE.Vector3(3.1, 3.2, 11.0),
  target: new THREE.Vector3(0, 1.4, 0),
};
// The room is turned so its back wall faces the default camera.
export const ROOM_YAW = Math.atan2(
  DEFAULT_VIEW.position.x - DEFAULT_VIEW.target.x,
  DEFAULT_VIEW.position.z - DEFAULT_VIEW.target.z,
);
const Y = new THREE.Vector3(0, 1, 0);
const toWorld = (x, y, z) => new THREE.Vector3(x, y, z).applyAxisAngle(Y, ROOM_YAW);

// A warm spot overhead and slightly in front, and one behind the jar that rims the glass.
export const KEY_DIRECTION = toWorld(-0.35, 0.86, 0.38).normalize();
export const RIM_DIRECTION = toWorld(-0.45, 0.42, -0.79).normalize();

export const GALLERY_COLORS = {
  glow: new THREE.Color(1.0, 0.84, 0.64),   // the lit acrylic, linear
  key: new THREE.Color(1.0, 0.9, 0.76),
  wall: new THREE.Color("#b99b7a"),
  table: new THREE.Color("#a49c92"),
  dark: new THREE.Color("#2b231d"),       // the room in the dark, behind the camera
};
export const ROOM_DARK = GALLERY_COLORS.dark;

export const GALLERY_LOOK = {
  glow: { value: 1.28 },       // how bright the acrylic blocks shine
  room: { value: 1 },       // walls and table
};

// What the jars stand on and what the walls are. `blocks`: 1, each jar on its lit acrylic
// block; 0, straight on a glass table, whose colour is `tableTint` (0 black, 1 white). Light
// that came up from the blocks is multiplied or blended by `blocks`. `wallStyle`: 0 the plank
// walls, 1 plain painted ones. `floorLight`: how bright the glass sees what lies below it.
// `spot`: how much of the key spot the specimen's tissue catches where the room gives it no
// light from behind (the black room).
export const STAGE = {
  blocks: { value: 1 },
  tableTint: { value: 0 },
  wallStyle: { value: 0 },
  floorLight: { value: 0.5 },
  spot: { value: 0 },
};
export const STAGE_NAMES = ["blocks", "white", "black"];
export const WALL_NAMES = ["wood", "white", "black"];
export const DEFAULT_STAGE = "white";
export const DEFAULT_WALL = "white";
export const stageName = (name) => (name === "glass" ? "black" : STAGE_NAMES.includes(name) ? name : DEFAULT_STAGE);
export const wallName = (name) => (WALL_NAMES.includes(name) ? name : DEFAULT_WALL);

// `edge`: the grey the thin glass shows edge-on, which is the room seen along the wall.
// `glass`, `meniscus`: the colour the glass surfaces take from the lamps; in the black room
// there is nothing for the glass to glow with but its highlights.
const WALLS = {
  wood: { wall: "#b99b7a", floor: "#a49c92", dark: "#2b231d", edge: "#5f6763", glass: "#f7fbf9", meniscus: "#ffffff", style: 0, spot: 0 },
  white: { wall: "#e4e1db", floor: "#c9c5be", dark: "#6e6b66", edge: "#8c928e", glass: "#f7fbf9", meniscus: "#ffffff", style: 1, spot: 0 },
  black: { wall: "#1c1b1a", floor: "#161514", dark: "#060606", edge: "#181a19", glass: "#161818", meniscus: "#3a3c3c", style: 1, spot: 0.4 },
};
// The wall as the jars' glass sees it, kept with the wall's colour.
export const WALL_LIGHT = new THREE.Color();
export const GLASS_EDGE = new THREE.Color();
export const GLASS_DIFFUSE = new THREE.Color();
export const MENISCUS_DIFFUSE = new THREE.Color();

export const GLASS_TABLE_LOOK = {
  reflect: { value: 0.55 },   // how strongly the table mirrors the room
  base: { value: 0.012 },     // the glass's own dark colour
  blur: { value: 1.2 },       // mip level of the mirrored image: the polish
};
// The table's front edge, in the room frame, clear in front of the front jar.
const TABLE_FRONT = 2.3;

const TABLE_WHITE = new THREE.Color("#f1efea");

/**
 * Sets every uniform and colour the table and walls are drawn with. Returns the look that was
 * in place, so a bake can put it back.
 */
let currentLook = { table: "blocks", wall: "wood" };
export function applyLook({ table, wall }) {
  const before = currentLook;
  const t = stageName(table);
  const w = WALLS[wallName(wall)];
  STAGE.blocks.value = t === "blocks" ? 1 : 0;
  STAGE.tableTint.value = t === "white" ? 1 : 0;
  STAGE.floorLight.value = { blocks: 0.5, white: 0.8, black: 0.12 }[t];
  STAGE.wallStyle.value = w.style;
  STAGE.spot.value = w.spot;
  GLASS_EDGE.set(w.edge);
  GLASS_DIFFUSE.set(w.glass);
  MENISCUS_DIFFUSE.set(w.meniscus);
  GALLERY_COLORS.wall.set(w.wall);
  GALLERY_COLORS.table.set(w.floor);
  GALLERY_COLORS.dark.set(w.dark);
  WALL_LIGHT.copy(GALLERY_COLORS.wall).multiplyScalar(0.35);
  currentLook = { table: t, wall: wallName(wall) };
  return before;
}
applyLook(currentLook);

/** The glow of the blocks as one colour, for shaders that are lit by it. */
export function glowLight(strength = 1) {
  return GALLERY_COLORS.glow.clone().multiplyScalar(GALLERY_LOOK.glow.value * strength);
}

const MAX_BLOCKS = 9;

// Blocks the room shader lights the table and walls with: x, z, radius, on (room frame).
const blocks = { value: Array.from({ length: MAX_BLOCKS }, () => new THREE.Vector4()) };

function setBlocks(slots) {
  blocks.value[0].set(0, 0, PEDESTAL.frontRadius, 1);
  for (let i = 1; i < MAX_BLOCKS; i++) {
    const slot = slots[i - 1];
    if (slot) blocks.value[i].set(slot.x, slot.z, pedestalRadius(slot), 1);
    else blocks.value[i].set(0, 0, 0, 0);
  }
}
setBlocks([]);

const NOISE = /* glsl */ `
  float hash1(float n) { return fract(sin(n * 12.9898) * 43758.5453); }
  float hash2(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float noise2(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3. - 2. * f);
    return mix(mix(hash2(i), hash2(i + vec2(1, 0)), f.x), mix(hash2(i + vec2(0, 1)), hash2(i + 1.), f.x), f.y);
  }
`;

function roomMaterial() {
  const offset = new THREE.Vector3(0, (ROOM.ceiling - PEDESTAL.height) / 2, (ROOM.front - ROOM.back) / 2);
  const material = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    uniforms: {
      uOffset: { value: offset },
      uWall: { value: GALLERY_COLORS.wall },
      uTable: { value: GALLERY_COLORS.table },
      uGlow: { value: GALLERY_COLORS.glow },
      uGlowK: GALLERY_LOOK.glow,
      uRoomK: GALLERY_LOOK.room,
      uTableY: { value: -PEDESTAL.height },
      uHalfWidth: { value: ROOM.halfWidth },
      uBack: { value: ROOM.back },
      uBlocks: blocks,
      uStageBlocks: STAGE.blocks,
      uWallStyle: STAGE.wallStyle,
    },
    vertexShader: /* glsl */ `
      uniform vec3 uOffset;
      varying vec3 vRoom;
      varying vec3 vFace;
      varying vec3 vWorld;
      void main() {
        vRoom = position + uOffset;
        vFace = normal;
        vec4 world = modelMatrix * vec4(position, 1.);
        vWorld = world.xyz;
        gl_Position = projectionMatrix * viewMatrix * world;
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uWall, uTable, uGlow;
      uniform float uGlowK, uRoomK, uTableY, uHalfWidth, uBack, uStageBlocks, uWallStyle;
      uniform vec4 uBlocks[${MAX_BLOCKS}];
      varying vec3 vRoom;
      varying vec3 vFace;
      varying vec3 vWorld;
      ${NOISE}

      // Light from the blocks reaching a point: brighter near a block, falling off with distance.
      float blockLight(vec3 p, float reach) {
        float s = 0.;
        for (int i = 0; i < ${MAX_BLOCKS}; i++) {
          vec4 b = uBlocks[i];
          if (b.w < .5) continue;
          vec3 d = p - vec3(b.x, 0., b.y);
          s += b.z * b.z / (1. + dot(d, d) / (reach * reach));
        }
        return s;
      }

      void main() {
        vec3 p = vRoom;
        vec3 color;
        if (vFace.y < -.5) {
          // The table: pale, faintly glossy, lit in pools around each block.
          float pool = 0.;
          for (int i = 0; i < ${MAX_BLOCKS}; i++) {
            vec4 b = uBlocks[i];
            if (b.w < .5) continue;
            float d = max(length(p.xz - b.xy) - b.z, 0.);
            pool += exp(-d / .45) * .9 + exp(-d / 1.8) * .25;
          }
          pool *= uStageBlocks;
          vec3 v = normalize(cameraPosition - vWorld);
          float gloss = pow(1. - abs(v.y), 5.);
          float back = smoothstep(-uBack, -uBack + 4., p.z);
          color = uTable * (.26 + .12 * back) + uTable * uGlow * uGlowK * pool * .45 + uWall * gloss * .25;
        } else if (vFace.y > .5) {
          color = uWall * .04;
        } else {
          // Vertical planks: seams, a tone per board and a grain running up it.
          bool backWall = abs(vFace.z) > .5;
          float u = backWall ? p.x : p.z;
          float board = floor(u / .56);
          float f = fract(u / .56);
          float tone = .82 + .32 * hash1(board + (backWall ? 0. : 40.));
          float grain = noise2(vec2(u * 34., p.y * 1.1 + board * 13.));
          float streak = noise2(vec2(u * 7., p.y * .22 + board * 5.));
          float seam = smoothstep(0., .014, f) * smoothstep(1., .986, f);
          vec3 wood = uWall * tone * (.8 + .2 * grain) * (.88 + .24 * streak) * (.5 + .5 * seam);
          // Painted plaster: one colour, only the faint unevenness of the trowel.
          vec3 paint = uWall * (.96 + .05 * noise2(vec2(u * 1.3, p.y * 1.3)) + .02 * noise2(vec2(u * 9., p.y * 9.)));
          wood = mix(wood, paint, uWallStyle);
          // Lit from below by the blocks and the table, and by three soft spots on the back wall.
          float y = p.y - uTableY;
          float lift = .22 + .38 * exp(-y / 2.4);
          float spots = 0.;
          if (backWall) for (int k = -1; k <= 1; k++) {
            float dx = u - float(k) * 5.;
            spots += exp(-dx * dx / 5. - (y - 3.4) * (y - 3.4) / 7.);
          }
          float glow = blockLight(p, 1.4) * exp(-y / 3.) * uStageBlocks;
          float side = backWall ? mix(.6, 1., smoothstep(uHalfWidth, 5., abs(p.x))) : .7;
          color = wood * side * (vec3(lift + .3 * spots) + uGlow * uGlowK * glow * .35);
        }
        gl_FragColor = vec4(color * uRoomK, 1.);
      }`,
  });
  return material;
}

/** The walls, ceiling and table, as one box seen from inside. */
function createRoom() {
  const geometry = new THREE.BoxGeometry(
    ROOM.halfWidth * 2,
    ROOM.ceiling + PEDESTAL.height,
    ROOM.back + ROOM.front,
  );
  const mesh = new THREE.Mesh(geometry, roomMaterial());
  mesh.position.set(0, (ROOM.ceiling - PEDESTAL.height) / 2, (ROOM.front - ROOM.back) / 2);
  mesh.name = "gallery-room";
  mesh.renderOrder = -10;
  return mesh;
}

// Clear acrylic lit from inside: the light is trapped in the block and escapes at its edges,
// so the top rim shines brightest, the bottom rim less, and the faces between stay dim and
// show the warm table through. The rims run past 1 so the lens blurs them into highlights.
function blockMaterial() {
  return new THREE.ShaderMaterial({
    uniforms: {
      uGlow: { value: GALLERY_COLORS.glow },
      uGlowK: GALLERY_LOOK.glow,
      uHeight: { value: PEDESTAL.height },
    },
    vertexShader: /* glsl */ `
      varying vec3 vWorld;
      varying vec3 vNormalW;
      void main() {
        vec4 world = modelMatrix * vec4(position, 1.);
        vWorld = world.xyz;
        vNormalW = normalize(mat3(modelMatrix) * normal);
        gl_Position = projectionMatrix * viewMatrix * world;
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uGlow;
      uniform float uGlowK, uHeight;
      varying vec3 vWorld;
      varying vec3 vNormalW;
      void main() {
        vec3 n = normalize(vNormalW);
        vec3 v = normalize(cameraPosition - vWorld);
        float up = clamp((vWorld.y + uHeight) / uHeight, 0., 1.);
        float slant = pow(1. - abs(dot(n, v)), 2.);
        float topRim = smoothstep(.8, .97, up);
        float bottomRim = smoothstep(.12, .02, up);
        float shine = n.y > .5 ? 1.1 : .22 + .35 * up + 2.2 * topRim + .7 * bottomRim + .8 * slant;
        gl_FragColor = vec4(uGlow * uGlowK * shine, 1.);
      }`,
  });
}

function octagonalBlock(radius, height, material) {
  const geometry = new THREE.CylinderGeometry(radius, radius, height, 8, 1, false).toNonIndexed();
  geometry.computeVertexNormals();
  const mesh = new THREE.Mesh(geometry, material);
  // A flat face toward the camera.
  mesh.rotation.y = Math.PI / 8;
  mesh.position.y = -height / 2;
  return mesh;
}

/** An acrylic block for a jar behind, at `slot` in the room frame. */
export function createPedestal(slot) {
  const mesh = octagonalBlock(pedestalRadius(slot), PEDESTAL.height, blockMaterial());
  mesh.name = "gallery-block";
  return mesh;
}

/**
 * The top of the front jar's block, lit by the key spot. Its lighting is computed here rather
 * than by a shadow map because a glass jar does not cast an ordinary shadow: the cylinder of
 * liquid throws a soft, pale shadow that lengthens and blurs away from the jar, with a bright
 * line of focused light (the caustic) down its middle. Near the foot the glass itself darkens
 * the top. It must stay opaque: it is part of the image the glass refracts.
 */
export const FLOOR_LOOK = {
  shadow: { value: 1 },
  caustic: { value: 0.96 },
  contact: { value: 0.43 },
};

function createBlockTop(radius, { jarRadius, footRadius, glassTop, liquidBottom, liquidTop }) {
  const toLight = new THREE.Vector2(KEY_DIRECTION.x, KEY_DIRECTION.z);
  const tanElevation = KEY_DIRECTION.y / toLight.length();
  const shadowDirection = toLight.clone().normalize().negate();
  const material = new THREE.ShaderMaterial({
    uniforms: {
      uGlow: { value: GALLERY_COLORS.glow },
      uGlowK: GALLERY_LOOK.glow,
      causticTint: { value: new THREE.Color("#fff6e8") },
      shadowDir: { value: shadowDirection },
      tanElevation: { value: tanElevation },
      jarRadius: { value: jarRadius },
      footRadius: { value: footRadius },
      glassTop: { value: glassTop },
      liquidBottom: { value: liquidBottom },
      liquidTop: { value: liquidTop },
      topRadius: { value: radius },
      shadowStrength: FLOOR_LOOK.shadow,
      causticStrength: FLOOR_LOOK.caustic,
      contactStrength: FLOOR_LOOK.contact,
    },
    vertexShader: /* glsl */ `
      varying vec3 vWorld;
      void main() {
        vec4 world = modelMatrix * vec4(position, 1.);
        vWorld = world.xyz;
        gl_Position = projectionMatrix * viewMatrix * world;
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uGlow, causticTint;
      uniform float uGlowK;
      uniform vec2 shadowDir;
      uniform float tanElevation, jarRadius, footRadius, glassTop, liquidBottom, liquidTop, topRadius;
      uniform float shadowStrength, causticStrength, contactStrength;
      varying vec3 vWorld;
      void main() {
        vec2 p = vWorld.xz;
        float r = length(p);
        // Frosted acrylic lit from inside, a little brighter toward its rim.
        vec3 color = uGlow * uGlowK * (.95 + .9 * smoothstep(topRadius * .8, topRadius, r));

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

        float c0 = liquidBottom / tanElevation, c1 = liquidTop / tanElevation;
        float span = smoothstep(c0 - .1, c0 + .3, along) * (1. - smoothstep(c1 - .4, c1 + .2, along));
        float sigma = .035 + .16 * t;
        float line = exp(-across * across / (2. * sigma * sigma)) * (.04 / sigma);
        color += causticTint * line * span * causticStrength;

        float ring = exp(-max(r - footRadius, 0.) / .07) * step(footRadius * .7, r);
        color *= 1. - contactStrength * (r < footRadius ? .35 : ring);
        gl_FragColor = vec4(color, 1.);
      }`,
  });
  const mesh = new THREE.Mesh(new THREE.CircleGeometry(radius, 8), material);
  mesh.rotation.set(-Math.PI / 2, 0, Math.PI / 8);
  mesh.position.y = 0.0005;
  mesh.name = "gallery-front-top";
  return mesh;
}

// The front block's sides; its top is drawn by createBlockTop.
function createFrontBlock(jarShape) {
  const group = new THREE.Group();
  group.name = "gallery-front-block";
  const sides = octagonalBlock(PEDESTAL.frontRadius, PEDESTAL.height, blockMaterial());
  sides.scale.y = 0.998;
  group.add(sides);
  group.add(createBlockTop(PEDESTAL.frontRadius, jarShape));
  return group;
}

/** Uniforms the table reads its mirror image from; filled by table-reflection.js. */
export function createTableReflection() {
  return {
    tReflect: { value: null },
    uReflectMatrix: { value: new THREE.Matrix4() },
    uHasReflect: { value: 0 },
  };
}

/**
 * A slab of polished glass whose top is y = 0, filling the room from the back wall to a front
 * edge before the front jar, so every jar stands straight on it. Black glass sends back almost
 * nothing of its own: what shows is the room mirrored in it, stronger the more glancing the
 * view. White (back-painted) glass is lit by the key spot and mirrors less; the jars' shadows
 * and the line of light focused through the front jar show on it. Around each foot the table
 * darkens where the jar crowds out the light.
 */
export function createGlassTable(jarShape, reflection = createTableReflection()) {
  const depth = ROOM.back - 0.01 + TABLE_FRONT;
  const geometry = new THREE.BoxGeometry((ROOM.halfWidth - 0.01) * 2, PEDESTAL.height, depth);
  geometry.translate(0, -PEDESTAL.height / 2, TABLE_FRONT - depth / 2);
  const toLight = new THREE.Vector2(KEY_DIRECTION.x, KEY_DIRECTION.z);
  const material = new THREE.ShaderMaterial({
    uniforms: {
      ...reflection,
      uReflect: GLASS_TABLE_LOOK.reflect,
      uBase: GLASS_TABLE_LOOK.base,
      uBlur: GLASS_TABLE_LOOK.blur,
      uKeyColor: { value: GALLERY_COLORS.key },
      uGlow: { value: GALLERY_COLORS.glow },
      uGlowK: GALLERY_LOOK.glow,
      uRim: { value: RIM_DIRECTION.clone() },
      causticTint: { value: new THREE.Color("#fff6e8") },
      shadowDir: { value: toLight.clone().normalize().negate() },
      tanElevation: { value: KEY_DIRECTION.y / toLight.length() },
      jarRadius: { value: jarShape.jarRadius },
      footRadius: { value: jarShape.footRadius },
      glassTop: { value: jarShape.glassTop },
      liquidBottom: { value: jarShape.liquidBottom },
      liquidTop: { value: jarShape.liquidTop },
      causticStrength: FLOOR_LOOK.caustic,
      contactStrength: FLOOR_LOOK.contact,
      shadowStrength: FLOOR_LOOK.shadow,
      uHeight: { value: PEDESTAL.height },
      uTint: STAGE.tableTint,
      uWhite: { value: TABLE_WHITE },
      uBlocks: blocks,
    },
    vertexShader: /* glsl */ `
      varying vec3 vWorld;
      varying vec3 vRoom;
      varying vec3 vNormalW;
      void main() {
        vec4 world = modelMatrix * vec4(position, 1.);
        vWorld = world.xyz;
        vRoom = position;
        vNormalW = normalize(mat3(modelMatrix) * normal);
        gl_Position = projectionMatrix * viewMatrix * world;
      }`,
    fragmentShader: /* glsl */ `
      uniform sampler2D tReflect;
      uniform mat4 uReflectMatrix;
      uniform float uHasReflect, uReflect, uBase, uBlur, uGlowK, uHeight, uTint;
      uniform vec3 uKeyColor, uGlow, uRim, causticTint, uWhite;
      uniform vec2 shadowDir;
      uniform float tanElevation, jarRadius, footRadius, glassTop, liquidBottom, liquidTop;
      uniform float causticStrength, contactStrength, shadowStrength;
      uniform vec4 uBlocks[${MAX_BLOCKS}];
      varying vec3 vWorld;
      varying vec3 vRoom;
      varying vec3 vNormalW;

      // The light a jar standing at jar (room frame) keeps from the table near it: a tight
      // dark ring at the foot and a wide soft falloff.
      float crowd(vec2 p, vec2 jar) {
        float r = length(p - jar);
        float out_ = max(r - footRadius, 0.);
        return step(footRadius * .92, r) * (.6 * exp(-out_ / .03) + .4 * exp(-out_ / .35));
      }

      void main() {
        vec3 n = normalize(vNormalW);
        vec3 v = normalize(cameraPosition - vWorld);
        float c = clamp(dot(n, v), 0., 1.);
        float fresnel = .04 + .96 * pow(1. - c, 5.);
        // White glass: the painted back lit by the key spot, a touch brighter away from the eye.
        vec3 white = uWhite * (.5 + .12 * (1. - c));
        vec3 color;
        if (n.y > .5) {
          vec4 clip = uReflectMatrix * vec4(vWorld, 1.);
          vec2 uv = clamp(clip.xy / clip.w * .5 + .5, vec2(.001), vec2(.999));
          vec3 mirror = textureLod(tReflect, uv, uBlur).rgb * uHasReflect;

          float ao = 0.;
          for (int i = 0; i < ${MAX_BLOCKS}; i++) {
            vec4 b = uBlocks[i];
            if (b.w > .5) ao = max(ao, crowd(vRoom.xz, b.xy));
          }

          // The front jar's shadow from the key spot: the cylinder of liquid throws a soft, pale
          // shadow that lengthens and blurs away from the jar.
          vec2 p = vWorld.xz;
          float along = dot(p, shadowDir);
          float across = abs(p.x * shadowDir.y - p.y * shadowDir.x);
          float shadowLength = glassTop / tanElevation;
          float t = clamp(along / shadowLength, 0., 1.);
          float halfWidth = jarRadius * (1. + .35 * t);
          float penumbra = .06 + .5 * t;
          float body = (1. - smoothstep(halfWidth - penumbra, halfWidth + penumbra, across))
            * smoothstep(-jarRadius, 0., along)
            * (1. - smoothstep(shadowLength * .85, shadowLength * 1.2, along));

          vec3 own = mix(vec3(uBase), white * (1. - body * shadowStrength * .45 * mix(1., .35, t)), uTint);
          color = own * (1. - contactStrength * mix(.3, .75, uTint) * ao);
          color += mirror * fresnel * uReflect * mix(1., .4, uTint) * (1. - contactStrength * .6 * ao);
          // The rim light behind, a broad sheen on the polish.
          vec3 toEye = reflect(-v, n);
          color += uKeyColor * pow(max(dot(toEye, uRim), 0.), 18.) * .22 * fresnel;

          // Key light focused by the front jar's liquid into a line on the glass.
          float c0 = liquidBottom / tanElevation, c1 = liquidTop / tanElevation;
          float span = smoothstep(c0 - .1, c0 + .3, along) * (1. - smoothstep(c1 - .4, c1 + .2, along));
          float sigma = .035 + .16 * t;
          float line = exp(-across * across / (2. * sigma * sigma)) * (.04 / sigma);
          color += causticTint * line * span * causticStrength * mix(.12, .5, uTint);
        } else {
          // The ground edge of the slab, with a bright line where the polished top turns.
          float up = clamp((vWorld.y + uHeight) / uHeight, 0., 1.);
          vec3 own = mix(vec3(uBase * .7), white * .75, uTint);
          color = own + uKeyColor * (.9 * smoothstep(.93, .99, up) + .05 * up) * (.3 + fresnel);
        }
        gl_FragColor = vec4(color, 1.);
      }`,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = "gallery-glass-table";
  return mesh;
}

/**
 * The room, its lights' stand-ins for the glass to reflect, and what the jars stand on: the
 * front jar's block, or the black glass table. `jarShape`: the front jar's radii and heights,
 * for the shadow on its block and the light it focuses.
 */
export function createGallery(jarShape) {
  const root = new THREE.Group();
  root.name = "gallery";
  root.rotation.y = ROOM_YAW;
  root.add(createRoom());
  const front = createFrontBlock(jarShape);
  // The shadow is computed in world space; undo the room's turn for the top.
  front.rotation.y = -ROOM_YAW;
  front.children[0].rotation.y = Math.PI / 8 + ROOM_YAW;
  front.children[1].rotation.z = Math.PI / 8 + ROOM_YAW;
  root.add(front);
  const reflection = createTableReflection();
  const table = createGlassTable(jarShape, reflection);
  root.add(table);

  /** `table`: blocks, white or black; `wall`: wood, white or black. */
  function setLook(look) {
    applyLook(look);
    const glass = STAGE.blocks.value < 0.5;
    front.visible = !glass;
    table.visible = glass;
  }
  setLook(currentLook);
  return {
    root,
    table,
    reflection,
    /** The blocks that light the room: the front one and those of `slots`. */
    setBlocks,
    setLook,
  };
}

/**
 * The room as the glass reflects it, baked to a PMREM from the jar's middle: the walls and
 * table, every block (or the glass table), the key spot overhead and the rim light behind.
 * `look`: the table and walls, as for createGallery's setLook.
 */
export function createGalleryEnvironment(renderer, look = currentLook) {
  const saved = blocks.value.map((b) => b.clone());
  const savedLook = applyLook(look);
  const glass = STAGE.blocks.value < 0.5;
  const room = new THREE.Scene();
  room.background = ROOM_DARK.clone();
  const turned = new THREE.Group();
  turned.rotation.y = ROOM_YAW;
  room.add(turned);
  setBlocks(SLOTS);
  turned.add(createRoom());
  const jarShape = { jarRadius: 0.62, footRadius: 0.73, glassTop: 3, liquidBottom: 0.26, liquidTop: 2.3 };
  if (glass) {
    turned.add(createGlassTable(jarShape));
  } else {
    for (const slot of SLOTS) {
      const block = createPedestal(slot);
      block.position.x = slot.x;
      block.position.z = slot.z;
      turned.add(block);
    }
    turned.add(createFrontBlock(jarShape));
  }

  const panel = (w, h, color, intensity, position) => {
    const mesh = new THREE.Mesh(
      new THREE.PlaneGeometry(w, h),
      new THREE.MeshBasicMaterial({ color: color.clone().multiplyScalar(intensity), side: THREE.DoubleSide }),
    );
    mesh.position.copy(position);
    mesh.lookAt(0, 1.2, 0);
    room.add(mesh);
  };
  panel(2.2, 2.2, GALLERY_COLORS.key, 6, KEY_DIRECTION.clone().multiplyScalar(6).add(new THREE.Vector3(0, 1.2, 0)));
  panel(1.0, 3.5, GALLERY_COLORS.key, 3, RIM_DIRECTION.clone().multiplyScalar(6).add(new THREE.Vector3(0, 1.2, 0)));
  // A narrow strip front-right draws the vertical highlight down the jar.
  panel(0.3, 3.6, GALLERY_COLORS.key, 3.5, toWorld(2.6, 2.2, 4.2));

  const pmrem = new THREE.PMREMGenerator(renderer);
  const target = pmrem.fromScene(room, 0.02, 0.1, 60, { position: new THREE.Vector3(0, 1.3, 0) });
  pmrem.dispose();
  room.traverse((object) => {
    object.geometry?.dispose();
    object.material?.dispose();
  });
  saved.forEach((b, i) => blocks.value[i].copy(b));
  applyLook(savedLook);
  return target.texture;
}
