import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { glassSurface, meniscusMaterial, thickGlassEdge } from "./jar.js";
import { createJarOptics } from "./jar-optics.js";
import { ROOM_YAW, GALLERY_COLORS, GALLERY_LOOK, STAGE, createPedestal } from "./gallery.js";
import { SLOTS, slotsFor, pedestalRadius } from "./gallery-layout.js";

// The row of jars behind the front one, holding liquid only. Each is a copy of the front jar:
// its liquid column traced the same way (jar-optics.js), looking up an image of the room drawn
// without any jar, and its glass surfaces. The thick lid and foot are traced too at the
// highest quality. A plain version of each (the glass surfaces over a clear liquid glowing
// from below) stands in where tracing cannot be had: at the lightest quality, and in the
// black table's mirror image, which is drawn from another camera. The front jar's plain copy
// for the mirror also holds the specimen, frozen in its pose: the tissue multiplies what lies
// behind it (absorption) and adds back the light it scatters, in the colour it lets through.

export const GALLERY_JAR_LOOK = {
  scatter: { value: 0.91 },    // how much light the mirrored specimen's tissue sends back
  liquid: { value: 0.31 },     // the plain jars' liquid glow
  lid: { value: 0 },        // light caught in the lid and its knob
};

// Parts that take the second stain: cartilage, the eye and the hard mouth parts.
const ACCENT_PARTS = new Set([
  "Cartilage", "OrbitCartilage", "Iris", "Eyes", "Retina", "Beak", "Radula", "SuckerRings", "Statocysts",
]);
const REAL_MANTLE_LENGTH = 0.1;

/**
 * The specimen in its current pose as one still mesh, centred on the middle of its liquid:
 * each vertex keeps how much it absorbs (as the live material works it out) and what kind of
 * tissue it is (0 plain, 1 stained body, 2 second stain).
 */
function bakeSpecimen(specimen) {
  const pivot = specimen.object;
  pivot.updateMatrixWorld(true);
  const centre = pivot.getWorldPosition(new THREE.Vector3());
  const parts = [];
  specimen.model.traverse((mesh) => {
    const u = mesh.material?.uniforms;
    if (!mesh.isSkinnedMesh || !mesh.userData?.squid_part || !u?.absorption) return;
    const source = mesh.geometry;
    const position = source.getAttribute("position");
    const tint = source.getAttribute("tint");
    const depth = source.getAttribute("tissueDepth");
    if (!tint || !depth) return;
    const count = position.count;
    const positions = new Float32Array(count * 3);
    const absorb = new Float32Array(count * 3);
    const params = new Float32Array(count * 4);
    const part = mesh.userData.squid_part;
    const kind = u.stained.value > 0 ? 1 : ACCENT_PARTS.has(part) ? 2 : 0;
    const gain = u.absorption.value * REAL_MANTLE_LENGTH * u.stain.value * u.partStain.value * u.classGain.value;
    const v = new THREE.Vector3();
    for (let i = 0; i < count; i++) {
      v.fromBufferAttribute(position, i);
      mesh.applyBoneTransform(i, v);
      v.applyMatrix4(mesh.matrixWorld).sub(centre);
      v.toArray(positions, i * 3);
      const fade = tint.getW(i);
      absorb[i * 3] = (1 - tint.getX(i)) * gain * fade;
      absorb[i * 3 + 1] = (1 - tint.getY(i)) * gain * fade;
      absorb[i * 3 + 2] = (1 - tint.getZ(i)) * gain * fade;
      params[i * 4] = kind;
      params[i * 4 + 1] = u.film.value;
      params[i * 4 + 2] = depth.getX(i);
      params[i * 4 + 3] = fade;
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("aAbsorb", new THREE.BufferAttribute(absorb, 3));
    geometry.setAttribute("aParams", new THREE.BufferAttribute(params, 4));
    if (source.index) geometry.setIndex(source.index.clone());
    geometry.computeVertexNormals();
    parts.push(geometry);
  });
  if (!parts.length) throw new Error("奥の標本を作れません: 標本の部位が見つかりません");
  const indexed = parts.filter((g) => g.index);
  const merged = mergeGeometries(indexed.length === parts.length ? parts : parts.map((g) => g.index ? g.toNonIndexed() : g));
  for (const g of parts) g.dispose();
  merged.computeBoundingSphere();
  return merged;
}

const TISSUE_VERTEX = /* glsl */ `
  attribute vec3 aAbsorb;
  attribute vec4 aParams;
  uniform float uBase, uHeight;
  centroid varying vec3 vAbsorb;
  centroid varying vec4 vParams;
  centroid varying vec3 vNormalV;
  centroid varying vec3 vViewPos;
  varying float vLift;
  void main() {
    vAbsorb = aAbsorb;
    vParams = aParams;
    vec4 mv = modelViewMatrix * vec4(position, 1.);
    vViewPos = mv.xyz;
    vNormalV = normalMatrix * normal;
    vLift = clamp(((modelMatrix * vec4(position, 1.)).y - uBase) / uHeight, 0., 1.);
    gl_Position = projectionMatrix * mv;
  }`;

const TISSUE_ABSORBANCE = /* glsl */ `
  uniform float uFace, uRim;
  centroid varying vec3 vAbsorb;
  centroid varying vec4 vParams;
  centroid varying vec3 vNormalV;
  centroid varying vec3 vViewPos;
  varying float vLift;
  vec3 absorbance() {
    float c = abs(dot(normalize(vNormalV), normalize(-vViewPos)));
    float x = 1. / max(c, .12) - 1.;
    float path = mix(vParams.z * c, vParams.z * (uFace + uRim * x * .7), vParams.y);
    return max(vAbsorb * path, 0.);
  }`;

const MULTIPLY = {
  transparent: true,
  depthWrite: false,
  blending: THREE.CustomBlending,
  blendEquation: THREE.AddEquation,
  blendSrc: THREE.ZeroFactor,
  blendDst: THREE.SrcColorFactor,
};
const ADD = {
  transparent: true,
  depthWrite: false,
  blending: THREE.CustomBlending,
  blendEquation: THREE.AddEquation,
  blendSrc: THREE.OneFactor,
  blendDst: THREE.OneFactor,
};

// With the blocks gone the light comes from the key spot overhead: brightest high up.
const LIFT_LIGHT = "mix(exp(-(1. - vLift) * 2.), exp(-vLift * 3.), uBlocks)";

function tissueMaterials(base, height) {
  const uniforms = {
    uFace: { value: 1 },
    uRim: { value: 0.5 },
    uBase: { value: base },
    uHeight: { value: height },
    uGlow: { value: GALLERY_COLORS.glow },
    uGlowK: GALLERY_LOOK.glow,
    uScatter: GALLERY_JAR_LOOK.scatter,
    uBlocks: STAGE.blocks,
  };
  // The tissue writes depth so the lens blurs the animal at its own distance.
  const absorb = new THREE.ShaderMaterial({
    ...MULTIPLY,
    depthWrite: true,
    side: THREE.DoubleSide,
    uniforms,
    vertexShader: TISSUE_VERTEX,
    fragmentShader: /* glsl */ `
      ${TISSUE_ABSORBANCE}
      void main() {
        if (vParams.w < .02) discard;
        gl_FragColor = vec4(exp(-absorbance()), 1.);
      }`,
  });
  const glow = new THREE.ShaderMaterial({
    ...ADD,
    side: THREE.FrontSide,
    uniforms,
    vertexShader: TISSUE_VERTEX,
    fragmentShader: /* glsl */ `
      ${TISSUE_ABSORBANCE}
      uniform vec3 uGlow;
      uniform float uGlowK, uScatter, uBlocks;
      void main() {
        if (vParams.w < .02) discard;
        vec3 through = exp(-absorbance());
        float taken = 1. - dot(through, vec3(1. / 3.));
        gl_FragColor = vec4(uGlow * uGlowK * uScatter * taken * sqrt(through) * (.3 + 1.4 * ${LIFT_LIGHT}), 1.);
      }`,
  });
  return { absorb, glow };
}

// The liquid column: faintly green where the light crosses more of it, glowing from below.
function liquidMaterials(floor, top) {
  const vertexShader = /* glsl */ `
    varying vec3 vNormalV;
    varying vec3 vViewPos;
    varying float vY;
    void main() {
      vec4 mv = modelViewMatrix * vec4(position, 1.);
      vViewPos = mv.xyz;
      vNormalV = normalMatrix * normal;
      vY = position.y;
      gl_Position = projectionMatrix * mv;
    }`;
  const facing = "abs(dot(normalize(vNormalV), normalize(-vViewPos)))";
  const tint = new THREE.ShaderMaterial({
    ...MULTIPLY,
    vertexShader,
    fragmentShader: /* glsl */ `
      varying vec3 vNormalV;
      varying vec3 vViewPos;
      varying float vY;
      void main() {
        gl_FragColor = vec4(mix(vec3(1.), vec3(.95, .97, .95), ${facing}), 1.);
      }`,
  });
  const glow = new THREE.ShaderMaterial({
    ...ADD,
    uniforms: {
      uGlow: { value: GALLERY_COLORS.glow },
      uGlowK: GALLERY_LOOK.glow,
      uLiquid: GALLERY_JAR_LOOK.liquid,
      uHeight: { value: top - floor },
      uBlocks: STAGE.blocks,
    },
    vertexShader,
    fragmentShader: /* glsl */ `
      uniform vec3 uGlow;
      uniform float uGlowK, uLiquid, uHeight, uBlocks;
      varying vec3 vNormalV;
      varying vec3 vViewPos;
      varying float vY;
      void main() {
        float h = vY / uHeight + .5;
        float lift = mix(.6 * exp(-(1. - h) * 3.), exp(-h * 3.), uBlocks);
        gl_FragColor = vec4(uGlow * uGlowK * uLiquid * (.05 + .7 * lift) * ${facing}, 1.);
      }`,
  });
  return { tint, glow };
}

// The lid and knob catch the light rising through the column, brightest along their outline.
function lidGlowMaterial() {
  return new THREE.ShaderMaterial({
    ...ADD,
    uniforms: {
      uGlow: { value: GALLERY_COLORS.glow },
      uGlowK: GALLERY_LOOK.glow,
      uLid: GALLERY_JAR_LOOK.lid,
    },
    vertexShader: /* glsl */ `
      varying vec3 vNormalV;
      varying vec3 vViewPos;
      void main() {
        vec4 mv = modelViewMatrix * vec4(position, 1.);
        vViewPos = mv.xyz;
        vNormalV = normalMatrix * normal;
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uGlow;
      uniform float uGlowK, uLid;
      varying vec3 vNormalV;
      varying vec3 vViewPos;
      void main() {
        float c = abs(dot(normalize(vNormalV), normalize(-vViewPos)));
        gl_FragColor = vec4(uGlow * uGlowK * uLid * (.08 + .8 * pow(1. - c, 2.)), 1.);
      }`,
  });
}

// Depth for the glass only where it is seen edge-on: the outline is what shows of a jar, and
// the lens should blur it at the jar's distance; through the face the room keeps its own.
function edgeDepthMaterial() {
  return new THREE.ShaderMaterial({
    colorWrite: false,
    depthWrite: true,
    transparent: true,
    vertexShader: /* glsl */ `
      varying vec3 vNormalV;
      varying vec3 vViewPos;
      void main() {
        vec4 mv = modelViewMatrix * vec4(position, 1.);
        vViewPos = mv.xyz;
        vNormalV = normalMatrix * normal;
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: /* glsl */ `
      varying vec3 vNormalV;
      varying vec3 vViewPos;
      void main() {
        if (abs(dot(normalize(vNormalV), normalize(-vViewPos))) > .45) discard;
        gl_FragColor = vec4(0.);
      }`,
  });
}

function copyPart(source, material, renderOrder) {
  const mesh = new THREE.Mesh(source.geometry, material);
  mesh.matrixAutoUpdate = false;
  mesh.matrix.copy(source.matrixWorld);
  mesh.renderOrder = renderOrder;
  return mesh;
}

const UP = new THREE.Vector3(0, 1, 0);

/**
 * The jars in the slots of gallery-layout.js. `jar` and `specimen` are the front ones: their
 * shapes are reused. `lens`: the camera's, for the traced jars' blur of what lies behind.
 */
export function createGalleryJars({ jar, specimen, envMap, lens }) {
  const root = new THREE.Group();
  root.name = "gallery-jars";
  // The plain jars and the blocks, in the room frame.
  const plainRoot = new THREE.Group();
  plainRoot.rotation.y = ROOM_YAW;
  const blockRoot = new THREE.Group();
  blockRoot.rotation.y = ROOM_YAW;
  // The traced jars, in the world frame: their optics work in world positions.
  const tracedRoot = new THREE.Group();
  root.add(plainRoot, blockRoot, tracedRoot);

  jar.root.updateMatrixWorld(true);
  const { parts, dims } = jar;
  // A specimen that cannot be baked (`bakeable: false`, the chameleon) is left out of the mirror copy.
  const tissue = specimen.bakeable === false ? null : bakeSpecimen(specimen);
  const glass = glassSurface(envMap, "gallery-glass-wall");
  const meniscus = meniscusMaterial(envMap);
  // Slightly rougher than the front jar's: a pinpoint highlight would scatter into specks in
  // the wide blur, a small soft one blooms into a disc.
  glass.roughness = 0.12;
  const lidGlow = lidGlowMaterial();
  const edgeDepth = edgeDepthMaterial();
  const liquidHeight = dims.liquidTop - dims.floorHeight;
  const liquidGeometry = new THREE.CylinderGeometry(dims.innerRadius * 0.995, dims.innerRadius * 0.995, liquidHeight, 48, 1, false);
  const liquid = liquidMaterials(dims.floorHeight, dims.liquidTop);

  // Transparent layers must be drawn from the far jar to the near one, each jar's multiplied
  // layers before its added ones.
  function plainJar(order) {
    const contents = new THREE.Group();
    const liquidMesh = new THREE.Mesh(liquidGeometry, liquid.tint);
    liquidMesh.position.y = dims.floorHeight + liquidHeight / 2;
    liquidMesh.renderOrder = order;
    const liquidGlow = new THREE.Mesh(liquidGeometry, liquid.glow);
    liquidGlow.position.copy(liquidMesh.position);
    liquidGlow.renderOrder = order + 2;
    contents.add(liquidMesh, liquidGlow);
    contents.add(copyPart(parts.Jar_Lid, lidGlow, order + 4));
    contents.add(copyPart(parts.Jar_Meniscus, meniscus, order + 5));
    contents.add(copyPart(parts.Jar_Glass, glass, order + 6));
    contents.add(copyPart(parts.Jar_Lid, glass, order + 7));
    contents.add(copyPart(parts.Jar_Glass, edgeDepth, 100));
    contents.add(copyPart(parts.Jar_Lid, edgeDepth, 100));
    return contents;
  }

  // The traced copies' surfaces are the front jar's; the lid takes the thin outline only while
  // its thick glass is traced.
  const tracedGlass = glassSurface(envMap, "gallery-traced-glass");
  const tracedLid = glassSurface(envMap, "gallery-traced-lid", thickGlassEdge);
  const tracedMeniscus = meniscusMaterial(envMap);
  const depthOnly = new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: true, transparent: true });

  function tracedJar(slot) {
    const centre = new THREE.Vector3(slot.x, 0, slot.z).applyAxisAngle(UP, ROOM_YAW);
    const optics = createJarOptics({
      dims,
      lens,
      centre,
      specimen: false,
      block: { x: slot.x, z: slot.z, radius: pedestalRadius(slot) },
    });
    const group = new THREE.Group();
    const surfaces = new THREE.Group();
    surfaces.position.copy(centre);
    const lidPlain = copyPart(parts.Jar_Lid, tracedGlass, 21);
    const lidThin = copyPart(parts.Jar_Lid, tracedLid, 21);
    surfaces.add(
      copyPart(parts.Jar_Meniscus, tracedMeniscus, 19),
      copyPart(parts.Jar_Glass, tracedGlass, 20),
      lidPlain,
      lidThin,
      copyPart(parts.Jar_Glass, depthOnly, 100),
      copyPart(parts.Jar_Lid, depthOnly, 100),
    );
    group.add(surfaces, ...optics.meshes);
    return {
      group,
      optics,
      setDetail(on) {
        for (const mesh of optics.solids) mesh.visible = on;
        lidThin.visible = on;
        lidPlain.visible = !on;
      },
    };
  }

  const byDistance = SLOTS.map((slot, i) => ({ slot, i })).sort((a, b) => a.slot.z - b.slot.z || Math.abs(b.slot.x) - Math.abs(a.slot.x));
  const jars = byDistance.map(({ slot, i }, rank) => {
    const plain = new THREE.Group();
    plain.name = `gallery-jar-${i}`;
    plain.position.set(slot.x, 0, slot.z);
    plain.add(plainJar(-200 + rank * 10));
    plainRoot.add(plain);

    const traced = tracedJar(slot);
    traced.group.name = `gallery-traced-jar-${i}`;
    tracedRoot.add(traced.group);

    const block = createPedestal(slot);
    block.position.x = slot.x;
    block.position.z = slot.z;
    blockRoot.add(block);
    return { slot, plain, traced, block };
  });

  // The front jar as the black table mirrors it. Its traced optics only work from the real
  // camera, so the mirror image gets this plain copy instead, in the world frame, holding the
  // specimen frozen in its pose and following the live one's pivot.
  const front = new THREE.Group();
  front.name = "gallery-front-mirror";
  front.add(plainJar(-100));
  const materials = tissueMaterials(dims.floorHeight, liquidHeight);
  const animal = new THREE.Group();
  animal.matrixAutoUpdate = false;
  if (tissue) {
    const absorb = new THREE.Mesh(tissue, materials.absorb);
    absorb.renderOrder = -99;
    const glow = new THREE.Mesh(tissue, materials.glow);
    glow.renderOrder = -97;
    for (const mesh of [absorb, glow]) mesh.frustumCulled = false;
    animal.add(absorb, glow);
  }
  front.add(animal);
  root.add(front);

  let shown = [];
  let blocksShown = true;
  let traced = true;
  let pass = "scene";
  function refresh() {
    for (const entry of jars) {
      const on = shown.includes(entry.slot);
      entry.plain.visible = on;
      entry.traced.group.visible = on;
      entry.block.visible = on && blocksShown;
    }
    plainRoot.visible = pass === "mirror" || (pass === "scene" && !traced);
    tracedRoot.visible = pass === "scene" && traced;
    front.visible = pass === "mirror";
  }

  const api = {
    root,
    jars,
    tissue,
    /** Shows the first `count` slots (the middle of the row first); returns the slots shown. */
    setCount(count) {
      shown = slotsFor(count);
      refresh();
      return shown;
    },
    get shown() { return shown; },
    /** Whether the jars stand on their blocks (or straight on the glass table). */
    setBlocks(on) {
      blocksShown = Boolean(on);
      for (const entry of jars) entry.traced.optics.setBlocks(blocksShown);
      refresh();
    },
    /** Traced copies (true) or the plain stand-ins; `detail`: trace the thick lid and foot too. */
    setQuality({ traced: tracedOn, detail }) {
      traced = Boolean(tracedOn);
      for (const entry of jars) entry.traced.setDetail(Boolean(detail));
      refresh();
    },
    get traced() { return traced; },
    /**
     * What the next render is for: "mirror", the table's mirror image (plain jars and the front
     * copy); "room", the image the traced jars look through (no jars); "scene", the rest.
     */
    setPass(name) {
      pass = name;
      refresh();
    },
    /** The image of the room the traced jars look up, and its size in pixels. */
    setImage(texture, width, height) {
      for (const entry of jars) {
        entry.traced.optics.setImages(texture, null);
        entry.traced.optics.setSize(width, height);
      }
    },
    /** Puts the mirror copy's animal where the live specimen's `pivot` is. */
    followSpecimen(pivot) {
      animal.matrix.copy(pivot.matrixWorld);
      animal.matrixWorldNeedsUpdate = true;
    },
    advance(dt) {
      for (const entry of jars) entry.traced.optics.advance(dt);
    },
  };
  refresh();
  return api;
}
