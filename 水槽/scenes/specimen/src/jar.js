import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { createJarOptics } from "./jar-optics.js";

export const JAR_PARTS = ["Jar_Glass", "Jar_Lid", "Jar_Liquid", "Jar_Meniscus"];

export const glassEdge = {
  darkness: { value: 0.55 },
  power: { value: 2.6 },
  tint: { value: new THREE.Color("#5f6763") },
};

// The glass surfaces themselves: reflections of the softbox room, and a grey outline where
// the thin wall is seen edge-on. What is seen through the filled part is jar-optics.js.
const EDGE_UNIFORMS = "uniform float uEdgeDarkness;\nuniform float uEdgePower;\nuniform vec3 uEdgeTint;";
const EDGE_FACTOR =
  "pow(1.0 - abs(dot(normalize(normal), normalize(vViewPosition))), uEdgePower) * uEdgeDarkness";

function glassSurface(envMap, key) {
  const material = new THREE.MeshPhysicalMaterial({
    color: "#f7fbf9",
    metalness: 0,
    roughness: 0.01,
    ior: 1.52,
    specularIntensity: 1,
    envMap,
    envMapIntensity: 1.6,
    transparent: true,
    opacity: 0.06,
    depthWrite: false,
    premultipliedAlpha: false,
  });
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uEdgeDarkness = glassEdge.darkness;
    shader.uniforms.uEdgePower = glassEdge.power;
    shader.uniforms.uEdgeTint = glassEdge.tint;
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", `#include <common>\n${EDGE_UNIFORMS}`)
      .replace(
        "#include <opaque_fragment>",
        `{
          float edge = ${EDGE_FACTOR};
          outgoingLight = mix(outgoingLight, uEdgeTint * 0.9, edge);
          diffuseColor.a = mix(diffuseColor.a, 1.0, edge * 0.85);
        }
        #include <opaque_fragment>`,
      );
  };
  material.customProgramCacheKey = () => key;
  return material;
}

// The meniscus is the one part of the surface seen from above at a steep angle: a bright
// line of reflected room along the wall.
function meniscusMaterial(envMap) {
  return new THREE.MeshPhysicalMaterial({
    color: "#ffffff",
    roughness: 0.05,
    transparent: true,
    opacity: 0.45,
    depthWrite: false,
    envMap,
    envMapIntensity: 1.4,
    side: THREE.DoubleSide,
  });
}

function readDims(glass) {
  const extras = glass.userData;
  const dims = {
    bodyRadius: extras.jar_body_radius,
    innerRadius: extras.jar_inner_radius,
    footRadius: extras.jar_foot_radius,
    rimHeight: extras.jar_rim_height,
    floorHeight: extras.jar_floor_height,
    liquidTop: extras.jar_liquid_top,
    knobCentre: extras.jar_knob_centre,
    knobRadius: extras.jar_knob_radius,
  };
  const unknown = Object.entries(dims).filter(([, value]) => !Number.isFinite(value)).map(([key]) => key);
  if (unknown.length) throw new Error(`jar.glb に寸法がありません: ${unknown.join(", ")}（generate_specimen_jar.py で書き出し直してください）`);
  return dims;
}

export async function createJar({ envMap, lens }) {
  const gltf = await new GLTFLoader().loadAsync(new URL("../assets/jar.glb", import.meta.url).href);
  const root = gltf.scene;
  root.name = "specimen-jar";
  const parts = {};
  root.traverse((object) => {
    const name = object.userData?.jar_part;
    if (object.isMesh && name) parts[name] = object;
  });
  const missing = JAR_PARTS.filter((name) => !parts[name]);
  if (missing.length) throw new Error(`jar.glb に部位がありません: ${missing.join(", ")}`);
  const dims = readDims(parts.Jar_Glass);

  const liquidBounds = new THREE.Box3().setFromObject(parts.Jar_Liquid);
  // The liquid is traced by the optics column; its mesh only gives the bounds.
  parts.Jar_Liquid.visible = false;
  parts.Jar_Glass.material = glassSurface(envMap, "specimen-glass-wall");
  parts.Jar_Lid.material = glassSurface(envMap, "specimen-glass-wall");
  parts.Jar_Meniscus.material = meniscusMaterial(envMap);

  // Blended layers over the opaque optics: the meniscus, then the glass surfaces.
  parts.Jar_Meniscus.renderOrder = 19;
  parts.Jar_Glass.renderOrder = 20;
  parts.Jar_Lid.renderOrder = 21;
  for (const mesh of Object.values(parts)) {
    mesh.castShadow = false;
    mesh.receiveShadow = false;
  }

  const optics = createJarOptics({ dims, lens });
  for (const mesh of optics.meshes) root.add(mesh);

  // Blended glass leaves no depth, so the depth of field would blur the lid and the foot as if
  // they were the far wall. Drawn last and depth only, they keep their distance.
  const depthOnly = new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: true, transparent: true });
  for (const name of ["Jar_Glass", "Jar_Lid"]) {
    const source = parts[name];
    const proxy = new THREE.Mesh(source.geometry, depthOnly);
    proxy.name = `${name}-depth`;
    proxy.renderOrder = 100;
    source.add(proxy);
  }

  const bounds = new THREE.Box3().setFromObject(root);
  return { root, parts, bounds, liquidBounds, dims, optics };
}
