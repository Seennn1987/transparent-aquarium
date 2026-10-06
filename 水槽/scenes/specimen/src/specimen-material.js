import * as THREE from "three";
import { SQUID_TISSUE } from "../../riverscape/src/squid-material.js";
import { RIM_DIRECTION } from "./studio.js";

// In the white studio the backdrop is the lightbox: each tissue surface multiplies what is
// already drawn behind it by exp(-(1 - tint) * absorption * path), as Blender's volume
// absorption does, with no light added and no tank-specific stain boost.
//
// It is drawn on its own over white, so the image holds how much light each point lets
// through (plus its sheen and milkiness); jar-optics.js looks it up where the bent rays
// cross it.
const REAL_MANTLE_LENGTH = 0.1;

// The tank's squid is baked blue-green. Measured on the reference photos (white lightbox),
// the stained tissue absorbs red : green : blue ≈ 1 : 0.24 : 0.08, a sky blue; the baked
// tint absorbs 1 : 0.18 : 0.15. These weights turn one into the other on the stained body
// only; the organs keep their colours.
const SKY_WEIGHTS = new THREE.Vector3(1, 1.36, 0.4);
const STAINED_PARTS = new Set(["Mantle", "Fins", "Funnel", "Head", "Arms"]);
// Measured against the reference: the arms take the stain more deeply than the tank's
// settings give them, the fins (a thin sheet, deepened face-on below) less. The head's skin
// is the same muscle as the arms it grows into.
const PART_STAIN = { Arms: 1.2, Head: 1.2, Fins: 0.23 };
// The specimen squid (blender/generate_specimen_squid.py) replaces the tank's solid head
// with a muscular shell holding the anatomy that shows through it: eye (wall, cornea,
// iris, retina, dissolved lens), cartilage, brain, optic lobes and nerves, statocysts,
// mouth parts and oesophagus. In the mantle it adds the three hearts, their vessels and the
// membrane wrapping the gut.
const SPECIMEN_TISSUE = {
  ...SQUID_TISSUE,
  Head: { mode: "film", absorption: 550, sheen: 1 },
  Eyes: { mode: "film", absorption: 700, sheen: 0.05 },
  Cornea: { mode: "film", absorption: 150, sheen: 0.35 },
  Iris: { mode: "film", absorption: 1500, sheen: 0 },
  Retina: { mode: "film", absorption: 280, sheen: 0 },
  Lens: { mode: "solid", absorption: 600, sheen: 0 },
  OpticNerves: { mode: "solid", absorption: 900, sheen: 0 },
  OpticLobes: { mode: "solid", absorption: 900, sheen: 0 },
  Brain: { mode: "solid", absorption: 900, sheen: 0 },
  Statocysts: { mode: "solid", absorption: 600, sheen: 0 },
  Cartilage: { mode: "film", absorption: 450, sheen: 0 },
  OrbitCartilage: { mode: "film", absorption: 450, sheen: 0 },
  BuccalMass: { mode: "solid", absorption: 180, sheen: 0 },
  Beak: { mode: "film", absorption: 1300, sheen: 0.08 },
  Radula: { mode: "film", absorption: 1800, sheen: 0 },
  Esophagus: { mode: "solid", absorption: 1400, sheen: 0 },
  SystemicHeart: { mode: "solid", absorption: 500, sheen: 0 },
  BranchialHearts: { mode: "solid", absorption: 420, sheen: 0 },
  Vessels: { mode: "solid", absorption: 500, sheen: 0 },
  VisceralSac: { mode: "film", absorption: 300, sheen: 0 },
  Rachis: { mode: "film", absorption: 260, sheen: 0 },
  InkSac: { mode: "solid", absorption: 220, sheen: 0 },
  DigestiveGland: { mode: "solid", absorption: 210, sheen: 0 },
  Gladius: { mode: "film", absorption: 180, sheen: 0 },
};
// What each part is made of decides how it takes the stain (alcian blue colours cartilage
// deepest, muscle sky blue; nerve stays pale and cloudy; chitin keeps its amber).
const TISSUE_CLASS = {
  Mantle: "muscle", Fins: "muscle", Funnel: "muscle", Head: "muscle", Arms: "muscle",
  SystemicHeart: "muscle", BranchialHearts: "muscle", Vessels: "muscle",
  Cartilage: "cartilage", OrbitCartilage: "cartilage", Iris: "cartilage",
  OpticNerves: "nerve", OpticLobes: "nerve", Brain: "nerve",
  Beak: "chitin", Radula: "chitin", SuckerRings: "chitin",
  Lens: "lens",
};
// Screening pigment left after bleaching.
const PIGMENTED = new Set(["Retina", "InkSac"]);
// Parts that scatter light back milky instead of only absorbing it.
const HAZY = new Set(["OpticNerves", "OpticLobes", "Brain", "Statocysts", "Cartilage", "OrbitCartilage", "VisceralSac"]);
// Where the stain pools as it soaks in: the arm tips and the crease at the arm crown.
const PART_POOLING = { Arms: 1, Head: 1, Funnel: 0.6, Mantle: 0.4, Fins: 0.5 };
// Muscle banded across the body: the mantle most, the arms, head and funnel less.
const PART_STRIATION = { Mantle: 1, Arms: 0.5, Head: 0.4, Funnel: 0.5 };
// Spacing of the circular muscle's bands in mantle lengths (0.5 mm on a 10 cm squid).
const MUSCLE_BAND = 0.005;
// Food and fat left in the gut; the ink that leaked out around its sac.
const GUT = new Set(["DigestiveGland", "Caecum", "Esophagus"]);
const INKED = new Set(["Mantle", "Funnel", "DigestiveGland", "Gills", "InkSac"]);
// Where the chromatophores' remnants show: on the back, the head and the arms.
const PART_SPOTS = { Mantle: 1, Head: 1, Arms: 0.8, Fins: 0.4, Funnel: 0.5 };
// Spacing of the remnant dots in mantle lengths (3 mm on a 10 cm squid).
const SPOT_CELL = 0.03;
// Tissue crossed, in mantle lengths, is kept ×10 in the image's alpha: the half floats near
// the white clear's alpha of 1 are too coarse for it otherwise.
const THICKNESS_IN_ALPHA = 10;

// Targets, light let through (red/green/blue) on the white-lightbox reference: fin
// 0.58/0.86/0.98, arms 0.05–0.8 red with blue ≈ 1.5× green, mantle red 0–0.19.
export const specimenLook = {
  stain: { value: 1.79 },
  sky: { value: 0.65 },              // 0: the tank's blue-green, 1: the specimen's sky blue
  dorsal: { value: 0.45 },        // extra stain on the back
  // Thin sheets (mantle, fins): how deep face-on, and how much more along the outline.
  face: { value: 1.8 },
  rim: { value: 0.7 },
  finRim: { value: 2.84 },         // extra stain toward the fin's outer edge
  spots: { value: 0.22 },          // chromatophore remnants
  milk: { value: 0.16 },          // light scattered back by thick tissue
  milkColor: { value: new THREE.Color("#e6f3fa") },
  rimGlow: { value: 0.19 },        // the outline glowing milky against the light behind
  sheen: { value: 1 },
  liquidSheen: { value: 0.29 },    // under glycerin the surface barely reflects
  wrinkles: { value: 0.96 },       // unevenness of the sheen
  // How each kind of tissue takes the stain (1 as baked).
  muscle: { value: 1.01 },
  cartilage: { value: 1.4 },
  nerve: { value: 1.12 },
  nerveHaze: { value: 0 },     // milky white of brain, optic lobes and nerves
  chitin: { value: 0.34 },
  pigment: { value: 0 },       // 0: bleached, 1: the retina and ink as dark as in life
  lens: { value: 0.42 },           // the lens dissolves in clearing; what is left of it clouds the eye
  cartilageHaze: { value: 0.08 }, // white left in the blue cartilage
  // The stain never takes evenly.
  mottle: { value: 0.6 },         // blotchy stain, fixed to the body
  pooling: { value: 0.77 },        // stain pooled at the arm tips, the crown crease and in patches
  striation: { value: 0.51 },      // fine bands of the muscle and the crossing fibres over it
  hue: { value: 0.5 },            // the blue drifts between aqua and ultramarine
  // Tissue and fluid refract almost alike, so outlines fade instead of drawing lines.
  edgeSoft: { value: 0.73 },
  veil: { value: 0.42 },          // the head's contents seen through its muscle
  gut: { value: 0.5 },            // dark grains of food left in the gut
  fat: { value: 0.63 },            // yellow fat in the digestive gland
  inkBleed: { value: 0.49 },      // ink leaked around its sac
  // Sizes, 1 as baked. Each part grows about its own centre, the eye's parts about the eye.
  headSize: { value: 1 },         // 頭の左右・上下の大きさ
  eyeSize: { value: 1 },
  eyePop: { value: 0 },           // 目の飛び出し。正で外へ、負で頭の中へ
  eyeAspect: { value: 1 },        // 目の前後の長さ
  irisSize: { value: 0.82 },
  retinaDepth: { value: 1 },      // <1 で網膜が眼の奥へ下がる
  lobeSize: { value: 1 },
  buccalSize: { value: 1 },
  beakSize: { value: 1 },
};
const CLASS_GAIN = {
  muscle: specimenLook.muscle,
  cartilage: specimenLook.cartilage,
  nerve: specimenLook.nerve,
  chitin: specimenLook.chitin,
  lens: specimenLook.lens,
};

// The eye and what moves with it; left and right are fitted as mirror images.
const EYE_GROUP = new Set(["Eyes", "Cornea", "Iris", "Retina", "Lens", "OpticNerves", "OrbitCartilage"]);
const MIRRORED = new Set([...EYE_GROUP, "OpticLobes", "Statocysts"]);
const SIZED_AT_EYE = new Set(["Eyes", "Cornea", "Retina", "OpticNerves", "OrbitCartilage"]);
const HEAD_GROUP = new Set([...MIRRORED, "Brain", "Cartilage", "BuccalMass", "Beak", "Radula", "Esophagus"]);
const PART_SIZE = {
  Iris: specimenLook.irisSize,
  Retina: specimenLook.retinaDepth,
  OpticLobes: specimenLook.lobeSize,
  BuccalMass: specimenLook.buccalSize,
  Beak: specimenLook.beakSize,
};

// Rest-pose model axes: +X the mantle tip, −X the arms, +Y the back, ±Z left and right.
const fitVertex = `
uniform float uHeadSize;
uniform float uEyeSize;
uniform float uEyePop;
uniform float uEyeAspect;
uniform float uPartSize;
uniform vec3 uEyeCenter;
uniform vec3 uFitCenter;
uniform float uFitMirror;
uniform float uFitEye;
uniform float uFitHead;
vec3 specimenFit(vec3 p) {
  float side = uFitMirror > .5 && p.z < 0. ? -1. : 1.;
  vec3 c = uFitCenter * vec3(1., 1., side);
  p = c + (p - c) * uPartSize;
  if (uFitEye > .5) {
    vec3 e = uEyeCenter * vec3(1., 1., side);
    vec3 d = (p - e) * uEyeSize;
    d.x *= uEyeAspect;
    p = e + d + vec3(0., 0., side * uEyePop);
  }
  if (uFitHead > 1.5) p.yz += c.yz * (uHeadSize - 1.);
  else if (uFitHead > .5) p.yz *= uHeadSize;
  return p;
}
uniform float uOrganTime;
uniform float uGutWave;
uniform float uFunnelSwivel;
uniform vec4 uEyeTurn;
uniform float uMotionKind;
uniform float uMotionAmount;
uniform float uMotionGain;
uniform vec3 uMotionCentre;
uniform float uMotionRadius;
uniform float uEyeMotion;
vec2 turned(vec2 v, float a) {
  float c = cos(a), s = sin(a);
  return vec2(c * v.x - s * v.y, s * v.x + c * v.y);
}
// The organs' own motion (organ-motion.js), on the fitted body before the bones move it.
vec3 organMotion(vec3 p) {
  float side = p.z < 0. ? -1. : 1.;
  vec3 c = uMotionCentre * vec3(1., 1., side);
  float k = uMotionKind, a = uMotionAmount * uMotionGain;
  vec3 e = uEyeCenter * vec3(1., 1., side) + vec3(0., 0., side * uEyePop);
  vec3 axis = normalize(vec3(.04, .25, side));
  if (k == 1.) {
    // Beat or squeeze about a centre, strongest in the middle of the organ.
    vec3 d = p - c;
    p = c + d * (1. - a * exp(-dot(d, d) / (uMotionRadius * uMotionRadius)));
  } else if (k == 2.) {
    // A swelling pushed down the tube by the squeeze just behind it.
    float x = p.x - uGutWave;
    float w = exp(-pow((x - .025) / .03, 2.)) - .6 * exp(-pow((x + .03) / .03, 2.));
    p.yz = c.yz + (p.yz - c.yz) * (1. + a * w);
  } else if (k == 3.) {
    p.y += a * sin(p.x * 110. + p.z * 40. - uOrganTime * 6.);
  } else if (k == 4.) {
    // The iris folds in toward the pupil (positive) or draws back.
    vec3 q = p - e;
    float along = dot(q, axis);
    vec3 radial = q - axis * along;
    float w = 1. - smoothstep(.022, .036, length(radial));
    p = e + axis * along + radial * (1. - a * w);
  } else if (k == 5.) {
    p += (uEyeMotion > .5 ? axis : vec3(1., 0., 0.)) * a;
  } else if (k == 7.) {
    // The beak's two halves turn about the hinge at its back.
    vec3 d = p - c;
    d.xy = turned(d.xy, d.y > 0. ? -a : a);
    p = c + d;
  } else if (k == 8.) {
    // The funnel's mouth widens as the mantle empties, and turns slowly.
    float w = smoothstep(.02, -.086, p.x);
    p.yz = c.yz + (p.yz - c.yz) * (1. + a * w);
    p.z += .012 * uFunnelSwivel * w;
  }
  if (uEyeMotion > .5) {
    vec2 turn = side > 0. ? uEyeTurn.xy : uEyeTurn.zw;
    vec3 q = p - e;
    q.xz = turned(q.xz, turn.x);
    q.yz = turned(q.yz, turn.y);
    p = e + q;
  }
  return p;
}
`;

function centreOf(geometry, mirrored) {
  const position = geometry.getAttribute("position");
  const box = new THREE.Box3();
  const v = new THREE.Vector3();
  for (let i = 0; i < position.count; i++) {
    v.fromBufferAttribute(position, i);
    if (!mirrored || v.z >= 0) box.expandByPoint(v);
  }
  return box.getCenter(new THREE.Vector3());
}

// How each organ moves (organ-motion.js), in model units. Blender's (x, y, z) is the model's
// (x, z, −y); left and right parts are mirrored by the side a vertex is on.
const MOTION_KIND = { pulse: 1, peristalsis: 2, ripple: 3, iris: 4, slide: 5, hinge: 7, funnel: 8 };
const EYE_TURNS = new Set(["Eyes", "Cornea", "Iris", "Retina", "Lens"]);
const PART_MOTION = {
  SystemicHeart: { kind: "pulse", amount: "uBeatSystemic", gain: 0.3, centre: [0.3, -0.058, 0], radius: 0.03 },
  BranchialHearts: { kind: "pulse", amount: "uBeatBranchial", gain: 0.2, centre: [0.34, -0.052, 0.045], radius: 0.016 },
  DigestiveGland: { kind: "pulse", amount: "uGland", gain: 0.035, radius: 0.35 },
  VisceralSac: { kind: "pulse", amount: "uGland", gain: 0.03, centre: [0.4, -0.005, 0], radius: 0.35 },
  Vessels: { kind: "pulse", amount: "uBeatSystemic", gain: 0.08, centre: [0.3, -0.058, 0], radius: 0.08 },
  InkSac: { kind: "pulse", amount: "uInk", gain: 0.25, centre: [0.14, -0.035, 0], radius: 0.05 },
  BuccalMass: { kind: "pulse", amount: "uBuccal", gain: 0.06, radius: 0.05 },
  Esophagus: { kind: "peristalsis", amount: "uGut", gain: 1.2, centre: [0, 0.004, 0] },
  Caecum: { kind: "peristalsis", amount: "uGut", gain: 0.15 },
  Gills: { kind: "ripple", amount: "uBeatBranchial", gain: 0.0025 },
  Iris: { kind: "iris", amount: "uPupil", gain: 0.22 },
  Lens: { kind: "slide", amount: "uLens", gain: 0.004 },
  Radula: { kind: "slide", amount: "uRadula", gain: 0.004 },
  Beak: { kind: "hinge", amount: "uBite", gain: 0.2, centre: [-0.198, 0, 0] },
  Funnel: { kind: "funnel", amount: "uFunnelOpen", gain: 0.25, centre: [0, -0.08, 0] },
};

function motionUniforms(part, fit) {
  const o = fit.organ;
  const m = PART_MOTION[part];
  const centre = m?.centre ? new THREE.Vector3(...m.centre) : fit.centres[part];
  return {
    uOrganTime: o.uOrganTime,
    uGutWave: o.uGutWave,
    uFunnelSwivel: o.uFunnelSwivel,
    uEyeTurn: o.uEyeTurn,
    uMotionKind: { value: m ? MOTION_KIND[m.kind] : 0 },
    uMotionAmount: m ? o[m.amount] : { value: 0 },
    uMotionGain: { value: m?.gain ?? 0 },
    uMotionCentre: { value: centre },
    uMotionRadius: { value: m?.radius ?? 1 },
    uEyeMotion: { value: EYE_TURNS.has(part) ? 1 : 0 },
  };
}

function fitUniforms(part, fit) {
  return {
    ...motionUniforms(part, fit),
    uHeadSize: specimenLook.headSize,
    uEyeSize: specimenLook.eyeSize,
    uEyePop: specimenLook.eyePop,
    uEyeAspect: specimenLook.eyeAspect,
    uPartSize: PART_SIZE[part] ?? { value: 1 },
    uEyeCenter: { value: fit.eye },
    uFitCenter: { value: SIZED_AT_EYE.has(part) ? fit.eye : fit.centres[part] },
    uFitMirror: { value: MIRRORED.has(part) ? 1 : 0 },
    uFitEye: { value: EYE_GROUP.has(part) ? 1 : 0 },
    uFitHead: { value: part === "Head" ? 1 : HEAD_GROUP.has(part) ? 2 : 0 },
  };
}

export const ABSORB_ORDER = 10;
export const SURFACE_ORDER = 11;

// With multisampling a pixel centre can fall outside a thin triangle (arm tips, fin edges)
// and plain varyings are extrapolated past their range: a negative absorbance multiplies
// the light by thousands, a normal through zero turns NaN, and the arms flash white.
// Every tissue varying is sampled inside its triangle (centroid).
function centroidVaryings(shader) {
  for (const stage of ["vertex", "fragment"]) {
    const key = `${stage}Shader`;
    shader[key] = shader[key]
      .replace(`#include <normal_pars_${stage}>`, THREE.ShaderChunk[`normal_pars_${stage}`].replaceAll("varying", "centroid varying"))
      .replaceAll("\nvarying vec3 vViewPosition;", "\ncentroid varying vec3 vViewPosition;");
  }
}

const tissueVertex = `
#include <common>
#include <skinning_pars_vertex>
attribute vec4 tint;
attribute float tissueDepth;
attribute float tissueRim;
centroid varying vec4 vTint;
centroid varying float vDepth;
centroid varying float vDorsal;
centroid varying float vRim;
centroid varying vec3 vRest;
centroid varying vec3 vViewNormal;
centroid varying vec3 vViewPosition;
${fitVertex}
void main() {
  // The pattern is fixed to the body at rest, so it moves with the tissue.
  vRest = specimenFit(position);
  vec3 fitted = organMotion(vRest);
  vRim = tissueRim;
  #include <skinbase_vertex>
  #include <beginnormal_vertex>
  #include <skinnormal_vertex>
  #include <defaultnormal_vertex>
  #include <begin_vertex>
  transformed = fitted;
  #include <skinning_vertex>
  #include <project_vertex>
  vTint = tint;
  vDepth = tissueDepth;
  // The model's +Y is the animal's back.
  vDorsal = smoothstep(-.2, .8, normalize(objectNormal).y);
  vViewNormal = transformedNormal;
  vViewPosition = mvPosition.xyz;
}`;

// Absorbance along the view ray through this surface, shared by both tissue passes.
const tissueAbsorbance = `
uniform float absorption;
uniform float film;
uniform float stained;
uniform float partStain;
uniform float stain;
uniform float sky;
uniform float dorsal;
uniform float classGain;
uniform float pigment;
uniform float face;
uniform float rim;
uniform float finRim;
uniform float spots;
uniform float spotted;
uniform float mottle;
uniform float pooling;
uniform float pooled;
uniform float striation;
uniform float striated;
uniform float hue;
uniform float edgeSoft;
uniform float veil;
uniform float inner;
uniform float gut;
uniform float fat;
uniform float fatty;
uniform float gutted;
uniform float inkBleed;
uniform float inked;
uniform vec3 uInkAt;
uniform float uInk;
uniform float uOrganTime;
uniform float uChromo;
centroid varying vec4 vTint;
centroid varying float vDepth;
centroid varying float vDorsal;
centroid varying float vRim;
centroid varying vec3 vRest;
centroid varying vec3 vViewNormal;
centroid varying vec3 vViewPosition;
vec3 hash3(vec3 p) {
  p = fract(p * vec3(.1031, .1030, .0973));
  p += dot(p, p.yxz + 33.33);
  return fract((p.xxy + p.yxx) * p.zyx);
}
// Scattered dots of uneven size and strength, about half the cells holding one. With live > 0
// each dot is a chromatophore that expands and shrinks on its own beat, in clouds that pass
// along the body.
float spotField(vec3 p, float live) {
  vec3 q = p / ${SPOT_CELL.toFixed(3)};
  vec3 i = floor(q), f = fract(q);
  float s = 0.;
  float cloud = smoothstep(.2, .9, sin(p.x * 9. - uOrganTime * 1.6));
  for (int x = -1; x <= 1; x++)
    for (int y = -1; y <= 1; y++)
      for (int z = -1; z <= 1; z++) {
        vec3 o = vec3(x, y, z);
        vec3 h = hash3(i + o + 71.);
        if (h.z > .5) continue;
        float r = .16 + .2 * fract(h.x * 7.13);
        float beat = pow(.5 + .5 * sin(uOrganTime * (2. + 3. * h.y) + h.x * 40.), 3.);
        r *= mix(1., .45 + .5 * beat + .6 * cloud, live);
        s = max(s, smoothstep(r, r * .35, length(o + h - f)) * (.4 + h.y));
      }
  return s;
}
// Smooth value noise with three independent channels, and a few octaves of it (about 0.2–0.8).
vec3 noise3(vec3 p) {
  vec3 i = floor(p), f = fract(p);
  f = f * f * (3. - 2. * f);
  return mix(
    mix(mix(hash3(i), hash3(i + vec3(1, 0, 0)), f.x), mix(hash3(i + vec3(0, 1, 0)), hash3(i + vec3(1, 1, 0)), f.x), f.y),
    mix(mix(hash3(i + vec3(0, 0, 1)), hash3(i + vec3(1, 0, 1)), f.x), mix(hash3(i + vec3(0, 1, 1)), hash3(i + 1.), f.x), f.y),
    f.z);
}
vec3 fbm3(vec3 p) {
  return .5 * noise3(p) + .3 * noise3(p * 2.13 + 17.) + .2 * noise3(p * 4.37 + 31.);
}
vec3 fbm2(vec3 p) {
  return .62 * noise3(p) + .38 * noise3(p * 2.13 + 17.);
}
// wob: how far this spot's outline reaches. The grazing term is softened so an outline is a
// blurred band, the more so for the head's contents.
float tissuePath(float wob) {
  float c = abs(dot(normalize(vViewNormal), normalize(-vViewPosition)));
  float x = 1. / max(c, .12) - 1.;
  x = x * wob / (1. + x * edgeSoft * (1. + 2. * inner));
  float sheet = vDepth * (face + rim * x);
  return mix(vDepth * c, sheet, film);
}
// The mantle's circular muscle takes the stain in fine bands across the body, and the tunic
// over it in two sets of crossing fibres. Bands finer than about two pixels fade to their
// average instead of shimmering.
float muscleGrain() {
  float arc = atan(vRest.z, vRest.y) * .1;
  float band = vRest.x / ${MUSCLE_BAND.toFixed(4)};
  float f1 = (vRest.x * .89 + arc * .45) / .012;
  float f2 = (vRest.x * .89 - arc * .45) / .012;
  float bands = sin(6.2832 * band + 2. * sin(vRest.x * 40. + arc * 60.));
  float fibres = sin(6.2832 * f1) + sin(6.2832 * f2);
  float keepBands = 1. - smoothstep(.25, .5, fwidth(band));
  float keepFibres = 1. - smoothstep(.25, .5, max(fwidth(f1), fwidth(f2)));
  return .25 * bands * keepBands + .06 * fibres * keepFibres;
}
vec3 absorbance() {
  vec3 low = fbm3(vRest * 7.);
  vec3 high = fbm2(vRest * 23. + 5.);
  vec3 a = 1. - vTint.rgb;
  // Dark pigment absorbs all colours almost alike.
  a = mix(a, vec3(.78, .82, .86), pigment);
  vec3 skyWeights = vec3(${SKY_WEIGHTS.toArray().map((v) => v.toFixed(3)).join(", ")});
  float blue = stained * smoothstep(.7, .85, vTint.b);
  a *= mix(vec3(1.), skyWeights, blue * sky);
  // From aqua (less green taken) to ultramarine (more).
  float drift = (low.y - .5) * hue * blue;
  a *= vec3(1. - .4 * drift, 1. + .9 * drift, 1.);
  a *= (1. + dorsal * vDorsal * stained) * (1. + finRim * vRim);
  float blotch = 1. + mottle * (.5 + .5 * stained) * (low.x - .5) * 1.4;
  float tip = smoothstep(-.75, -1.2, vRest.x);
  float crease = exp(-pow((vRest.x + .21) / .025, 2.));
  float pool = pooled * (tip + .3 * crease) + stained * smoothstep(.6, .78, high.z);
  float gain = blotch * (1. + pooling * pool * .8) * (1. - veil * inner * .35);
  if (striated > 0.) gain *= 1. + striation * striated * muscleGrain();
  a = max(a * absorption * vTint.a * ${REAL_MANTLE_LENGTH.toFixed(3)} * stain * partStain * classGain * gain
    * tissuePath(.7 + .6 * high.x), 0.);
  // The remnants are brownish: they take more blue than red.
  float dots = spotted * mix(.25, 1., vDorsal) * vTint.a * (spotted > 0. ? spotField(vRest, uChromo) : 0.);
  a += dots * spots * vec3(.35, .6, .9);
  // Grains of food (dark brown) and fat (yellow) in the gut.
  if (gutted > 0.) {
    float grains = spotField(vRest * 2.6 + 13., 0.) * smoothstep(.45, .6, low.z);
    a += vTint.a * (gut * grains * vec3(.9, 1., 1.1) + fat * fatty * smoothstep(.52, .7, high.y) * vec3(.03, .12, .6));
  }
  // Ink leaked out of its sac: a grey cloud around it, uneven.
  if (inked > 0.) {
    vec3 k = (vRest - uInkAt) / vec3(.16, .06, .07);
    a += inkBleed * (1. + .8 * uInk) * vTint.a * exp(-dot(k, k)) * (.4 + 1.2 * low.z) * vec3(.55, .55, .5);
  }
  return a;
}`;

const absorbFragment = `
${tissueAbsorbance}
void main() {
  // At the arm crown the head's shell fades out as the arm roots fade in. What is faded to
  // nothing is not drawn; cutting off any higher leaves a visible edge.
  if (vTint.a < .02) discard;
  // Alpha adds up the tissue crossed; jar-optics.js bends the ray by how fast it changes.
  gl_FragColor = vec4(exp(-absorbance()), ${THICKNESS_IN_ALPHA.toFixed(1)} * vTint.a * tissuePath(1.));
}`;

// Preserved tissue is not glass-clear: its thick parts send some light back milky, which
// also veils the organs behind them.
const milkFragment = `
${tissueAbsorbance}
uniform float milk;
uniform vec3 milkColor;
uniform float milky;
uniform float haze;
uniform float rimGlow;
uniform vec3 uRimLight;
void main() {
  if (vTint.a < .02) discard;
  float density = dot(absorbance(), vec3(1. / 3.));
  vec3 cloud = vec3(.96, .94, .86) * haze * (1. - exp(-tissuePath(1.) * 120.));
  // Against the light behind it the cloudy tissue glows along its outline, where the light
  // crosses the most of it on its way to the camera.
  vec3 v = normalize(-vViewPosition);
  vec3 toLight = normalize((viewMatrix * vec4(uRimLight, 0.)).xyz);
  float grazing = 1. - abs(dot(normalize(vViewNormal), v));
  float glow = rimGlow * pow(grazing, 3.) * smoothstep(-.1, .7, -dot(toLight, v));
  gl_FragColor = vec4(milkColor * milky * (milk * (1. - exp(-density * .8)) + glow * vTint.a) + cloud, 1.);
}`;

function tissueUniforms({ mode, absorption }, part, fit) {
  return {
    absorption: { value: absorption },
    film: { value: mode === "film" ? 1 : 0 },
    stained: { value: STAINED_PARTS.has(part) ? 1 : 0 },
    partStain: { value: PART_STAIN[part] ?? 1 },
    classGain: CLASS_GAIN[TISSUE_CLASS[part]] ?? { value: 1 },
    pigment: PIGMENTED.has(part) ? specimenLook.pigment : { value: 0 },
    stain: specimenLook.stain,
    sky: specimenLook.sky,
    dorsal: specimenLook.dorsal,
    face: specimenLook.face,
    rim: specimenLook.rim,
    finRim: specimenLook.finRim,
    spots: specimenLook.spots,
    spotted: { value: PART_SPOTS[part] ?? 0 },
    mottle: specimenLook.mottle,
    pooling: specimenLook.pooling,
    pooled: { value: PART_POOLING[part] ?? 0 },
    striation: specimenLook.striation,
    striated: { value: PART_STRIATION[part] ?? 0 },
    hue: specimenLook.hue,
    edgeSoft: specimenLook.edgeSoft,
    veil: specimenLook.veil,
    inner: { value: HEAD_GROUP.has(part) || part === "Eyes" || part === "Lens" ? 1 : 0 },
    gut: specimenLook.gut,
    fat: specimenLook.fat,
    fatty: { value: part === "DigestiveGland" || part === "Caecum" ? 1 : 0 },
    gutted: { value: GUT.has(part) ? 1 : 0 },
    inkBleed: specimenLook.inkBleed,
    inked: { value: INKED.has(part) ? 1 : 0 },
    uInkAt: { value: fit.ink },
    uInk: fit.organ.uInk,
    uChromo: fit.organ.uChromo,
    ...fitUniforms(part, fit),
  };
}

function absorbMaterial(tissue, part, fit) {
  return new THREE.ShaderMaterial({
    uniforms: tissueUniforms(tissue, part, fit),
    vertexShader: tissueVertex,
    fragmentShader: absorbFragment,
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    blending: THREE.CustomBlending,
    blendEquation: THREE.AddEquation,
    blendSrc: THREE.ZeroFactor,
    blendDst: THREE.SrcColorFactor,
    blendSrcAlpha: THREE.OneFactor,
    blendDstAlpha: THREE.OneFactor,
  });
}

// Light added on top of the absorption; it leaves the thickness in alpha alone.
const ADD_LIGHT = {
  blending: THREE.CustomBlending,
  blendEquation: THREE.AddEquation,
  blendSrc: THREE.SrcAlphaFactor,
  blendDst: THREE.OneFactor,
  blendSrcAlpha: THREE.ZeroFactor,
  blendDstAlpha: THREE.OneFactor,
};

function milkMaterial(tissue, part, fit) {
  return new THREE.ShaderMaterial({
    uniforms: {
      ...tissueUniforms(tissue, part, fit),
      milk: specimenLook.milk,
      milkColor: specimenLook.milkColor,
      milky: { value: STAINED_PARTS.has(part) ? 1 : 0 },
      // The funnel's open ends would glow as hard lines.
      rimGlow: part === "Funnel" ? { value: 0 } : specimenLook.rimGlow,
      uRimLight: { value: RIM_DIRECTION },
      haze: !HAZY.has(part) ? { value: 0 } : TISSUE_CLASS[part] === "cartilage" ? specimenLook.cartilageHaze : specimenLook.nerveHaze,
    },
    vertexShader: tissueVertex,
    fragmentShader: milkFragment,
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    ...ADD_LIGHT,
  });
}

// The wet sheen of a preserved specimen: faint face-on, stronger along the outline.
function surfaceMaterial({ sheen }, envMap, part, fit) {
  const material = new THREE.MeshPhysicalMaterial({
    color: 0x000000,
    roughness: 0.1,
    ior: 1.38,
    envMap,
    envMapIntensity: 0.35 * sheen,
    specularIntensity: 0.3 * sheen,
    transparent: true,
    depthWrite: false,
    ...ADD_LIGHT,
  });
  material.onBeforeCompile = (shader) => {
    centroidVaryings(shader);
    shader.uniforms.uSheen = specimenLook.sheen;
    shader.uniforms.uLiquidSheen = specimenLook.liquidSheen;
    shader.uniforms.uWrinkles = specimenLook.wrinkles;
    Object.assign(shader.uniforms, fitUniforms(part, fit));
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", `#include <common>\nattribute vec4 tint;\ncentroid varying vec3 vRest;\ncentroid varying float vFade;\n${fitVertex}`)
      .replace("#include <begin_vertex>", "#include <begin_vertex>\nvRest = specimenFit(position);\ntransformed = organMotion(vRest);\nvFade = tint.a;");
    // Fine creases of the preserved skin break the highlight into uneven streaks.
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nuniform float uSheen;\nuniform float uLiquidSheen;\nuniform float uWrinkles;\ncentroid varying vec3 vRest;\ncentroid varying float vFade;")
      .replace("#include <opaque_fragment>", `
if (vFade < .02) discard;
float crease = sin(dot(vRest, vec3(160., 41., 67.)) + 3. * sin(vRest.x * 55. + vRest.z * 38.));
outgoingLight *= uSheen * uLiquidSheen * vFade * (1. + uWrinkles * crease * .5);
#include <opaque_fragment>`);
  };
  material.customProgramCacheKey = () => "specimen-squid-sheen-fit-organs";
  return material;
}

function addPass(mesh, name, material, renderOrder) {
  const pass = new THREE.SkinnedMesh(mesh.geometry, material);
  pass.name = name;
  pass.renderOrder = renderOrder;
  pass.frustumCulled = false;
  pass.position.copy(mesh.position);
  pass.quaternion.copy(mesh.quaternion);
  pass.scale.copy(mesh.scale);
  pass.bind(mesh.skeleton, mesh.bindMatrix);
  mesh.parent.add(pass);
}

/**
 * Absorption, milkiness and sheen for every part; the white studio supplies the light.
 * `organ`: createOrganMotion() from organ-motion.js, whose uniforms move the organs.
 */
export function applySpecimenTissue(model, { envMap, organ }) {
  const meshes = [];
  model.traverse((object) => { if (object.isSkinnedMesh) meshes.push(object); });
  const names = new Set(meshes.map((mesh) => mesh.userData.squid_part));
  const missing = Object.keys(SPECIMEN_TISSUE).filter((name) => !names.has(name));
  if (missing.length) throw new Error(`specimen_squid.glb に部位がありません: ${missing.join(", ")}`);
  const centres = {};
  for (const mesh of meshes) centres[mesh.userData.squid_part] = centreOf(mesh.geometry, MIRRORED.has(mesh.userData.squid_part));
  const fit = { eye: centres.Eyes, ink: centres.InkSac, centres, organ: organ.uniforms };
  for (const mesh of meshes) {
    const part = mesh.userData.squid_part;
    const tissue = SPECIMEN_TISSUE[part];
    if (!tissue) throw new Error(`specimen_squid.glb の部位 ${part ?? mesh.name} に組織の設定がありません`);
    const geometry = mesh.geometry;
    const tint = geometry.getAttribute("color");
    const depth = geometry.getAttribute("_depth");
    const rim = geometry.getAttribute("_rim");
    if (!tint || tint.itemSize !== 4 || !depth || !rim)
      throw new Error(`specimen_squid.glb の部位 ${part} に色・厚み・縁の焼き込みがありません`);
    geometry.setAttribute("tint", tint);
    geometry.setAttribute("tissueDepth", depth);
    geometry.setAttribute("tissueRim", rim);
    geometry.deleteAttribute("color");
    geometry.deleteAttribute("_depth");
    geometry.deleteAttribute("_rim");
    mesh.material = absorbMaterial(tissue, part, fit);
    mesh.renderOrder = ABSORB_ORDER;
    mesh.frustumCulled = false;
    // The arms and the head they grow from are one tissue; neither is veiled.
    const milky = STAINED_PARTS.has(part) && part !== "Arms" && part !== "Head";
    if (milky || HAZY.has(part)) addPass(mesh, `${part}Milk`, milkMaterial(tissue, part, fit), SURFACE_ORDER);
    if (tissue.sheen > 0) addPass(mesh, `${part}Surface`, surfaceMaterial(tissue, envMap, part, fit), SURFACE_ORDER);
  }
}
