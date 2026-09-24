import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

export const JAR_PARTS = ["Jar_Glass", "Jar_Lid", "Jar_Liquid", "Jar_Meniscus"];

// Soda-lime glass reads faintly green-blue through its thickest parts (base, knob).
const GLASS_ATTENUATION = new THREE.Color("#e4f0ec");

export const glassEdge = {
  darkness: { value: 0.55 },
  power: { value: 2.6 },
  tint: { value: new THREE.Color("#5f6763") },
};

// Against a white studio the refracted image is white too, so a real jar's grey outline
// (its wall seen edge-on picks up the darker room and internal reflections) is added by
// hand: light is pulled toward a grey tint at grazing view angles.
const EDGE_UNIFORMS = "uniform float uEdgeDarkness;\nuniform float uEdgePower;\nuniform vec3 uEdgeTint;";
const EDGE_FACTOR =
  "pow(1.0 - abs(dot(normalize(normal), normalize(vViewPosition))), uEdgePower) * uEdgeDarkness";

function bindEdge(shader) {
  shader.uniforms.uEdgeDarkness = glassEdge.darkness;
  shader.uniforms.uEdgePower = glassEdge.power;
  shader.uniforms.uEdgeTint = glassEdge.tint;
  shader.fragmentShader = shader.fragmentShader.replace("#include <common>", `#include <common>\n${EDGE_UNIFORMS}`);
}

/** Transmissive glass or liquid: the edge darkens what is seen through it. */
function withTransmittedEdge(material, key, strength = 1) {
  material.onBeforeCompile = (shader) => {
    bindEdge(shader);
    shader.fragmentShader = shader.fragmentShader.replace(
      "#include <transmission_fragment>",
      `#include <transmission_fragment>
      totalDiffuse = mix(totalDiffuse, totalDiffuse * uEdgeTint, ${EDGE_FACTOR} * ${strength.toFixed(3)});`,
    );
  };
  material.customProgramCacheKey = () => key;
  return material;
}

/** Thin blended wall: nearly invisible face-on, a grey line edge-on. */
function withBlendedEdge(material, key) {
  material.onBeforeCompile = (shader) => {
    bindEdge(shader);
    shader.fragmentShader = shader.fragmentShader.replace(
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

function wallMaterial(envMap) {
  return withBlendedEdge(new THREE.MeshPhysicalMaterial({
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
  }), "specimen-glass-wall");
}

function solidGlassMaterial(envMap) {
  return withTransmittedEdge(new THREE.MeshPhysicalMaterial({
    color: "#ffffff",
    metalness: 0,
    roughness: 0.01,
    transmission: 1,
    ior: 1.52,
    thickness: 0.22,
    attenuationColor: GLASS_ATTENUATION,
    attenuationDistance: 1.2,
    specularIntensity: 1,
    envMap,
    envMapIntensity: 0.85,
  }), "specimen-glass-solid");
}

// The liquid column is the jar's lens: glycerin and glass have nearly the same index, so the
// filled part magnifies and bends what is behind it, while the empty neck barely does.
function liquidMaterial(envMap, diameter) {
  return withTransmittedEdge(new THREE.MeshPhysicalMaterial({
    color: "#ffffff",
    metalness: 0,
    roughness: 0,
    transmission: 1,
    ior: 1.47,
    thickness: diameter,
    attenuationColor: new THREE.Color("#f1f6ef"),
    attenuationDistance: 6,
    specularIntensity: 0.6,
    envMap,
    envMapIntensity: 0.5,
    depthWrite: false,
  }), "specimen-liquid", 0.45);
}

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

export async function createJar({ envMap }) {
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

  const liquidBounds = new THREE.Box3().setFromObject(parts.Jar_Liquid);
  const diameter = liquidBounds.max.x - liquidBounds.min.x;

  parts.Jar_Glass.material = wallMaterial(envMap);
  parts.Jar_Lid.material = solidGlassMaterial(envMap);
  parts.Jar_Liquid.material = liquidMaterial(envMap, diameter);
  parts.Jar_Meniscus.material = meniscusMaterial(envMap);

  // Blended layers after the specimen (orders 10–11): the meniscus and the front wall lie over it.
  parts.Jar_Meniscus.renderOrder = 19;
  parts.Jar_Glass.renderOrder = 20;
  for (const mesh of Object.values(parts)) {
    mesh.castShadow = false;
    mesh.receiveShadow = false;
  }

  // Glass, liquid and specimen are blended and leave no depth, so the depth of field would
  // blur the whole jar as if it were the far wall. Drawn last, depth only, the liquid's
  // outline gives the jar its distance without hiding anything drawn before it.
  const depthProxy = new THREE.Mesh(
    parts.Jar_Liquid.geometry,
    // Transparent only to be sorted after the blended layers; it writes no colour.
    new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: true, transparent: true }),
  );
  depthProxy.name = "jar-depth";
  depthProxy.renderOrder = 100;
  depthProxy.matrix.copy(parts.Jar_Liquid.matrix);
  depthProxy.matrixAutoUpdate = false;
  parts.Jar_Liquid.parent.add(depthProxy);

  const bounds = new THREE.Box3().setFromObject(root);
  return { root, parts, bounds, liquidBounds };
}
