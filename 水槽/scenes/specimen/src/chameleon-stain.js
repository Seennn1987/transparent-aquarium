// The cleared-and-stained chameleon on a lightbox (no jar yet).
//
// Each tissue takes away light along the view ray as exp(-absorbance), in the colour the
// reference photo shows: the light let through divided by the lightbox beside it, read in
// the photo's own (sRGB) values. The page reproduces those values directly, so a pixel on
// screen is the lightbox colour times the light let through, with no lighting or tone mapping.
//
// Measured on 06-lightbox-calyptratus-2.jpg (C. calyptratus, Field Museum 66198, Brianwray26,
// CC BY-SA 4.0, docs/references/chameleon/SOURCES.md), 5184 px original, median of 13 × 13 px
// divided by the clear lightbox next to it (docs/カメレオン透明標本_計画書_v1.0.md 第5節, 2026-10-13):
//   neural spine (thin bone)   0.69 / 0.27 / 0.48   (two spines: 0.72/0.31/0.49, 0.66/0.22/0.46)
//   mandible (thick bone)      0.30 / 0.02 / 0.06
//   cyan at the throat         0.61 / 0.84 / 0.79   (brightest 5 % of the cyan patch)
//   cleared tissue, neck       0.90 / 0.87 / 0.69
//   cleared tissue, crest      0.94 / 0.91 / 0.81
export const LIGHTBOX = [222 / 255, 224 / 255, 226 / 255]; // the photo's clear lightbox, sRGB

// Alizarin on bone. Absorbance −ln(T) of the spine is 0.37 : 1.31 : 0.73, of the mandible
// 1.20 : 3.9 : 2.8; per unit of green that is 0.28 : 1 : 0.56 and 0.31 : 1 : 0.72. Their mean:
export const BONE_SPECTRUM = [0.3, 1, 0.64];
// How deep: the CT bone is thicker side-on than a straight Beer–Lambert law allows. Ray-traced
// side-on through the CT skeleton, a neural spine is 0.015 model units across and the mandible
// 0.095: six times the bone, but in the photo three times the absorbance (green 1.31 and 3.9).
// So the bone's path is counted as t0 · (1 − exp(−t / t0)), t0 = 0.042 from those two points.
// The gain was then set so the bone's colours over the head and along the back spread like the
// photo's (median green let through, bone pixels over the clear lightbox; browser, view=photo06):
//   head:   photo 0.40 / 0.11 / 0.18, screen 0.42 / 0.10 / 0.16
//   back:   photo 0.70 / 0.31 / 0.46, screen 0.58 / 0.27 / 0.32 (the screen's crest is yellower)
// With the two-point gain (104) the screen was darker than the photo all over (head 0.04 green);
// ×0.67 brings both medians in. Why thick bone takes less stain per length is not settled here:
// the curve is a fit, not a mechanism.
export const BONE_T0 = 0.042;
export const BONE_GAIN = 70;
// Alcian blue on cartilage: the throat's cyan with the tissue around it taken away absorbs
// about 0.39 : 0.03 : 0 (red only). Provisional: the cartilage built so far (rib gaps) is not
// the throat's, and the jar photo 01 shows a greyer blue (0.56/0.58/0.63).
export const CARTILAGE_SPECTRUM = [1, 0.1, 0.05];
// About 0.4 red absorbance across a rib-thick bar (0.015).
export const CARTILAGE_GAIN = 27;
// Cleared tissue, yellowish: the neck absorbs 0.105 : 0.139 : 0.371 (0.28 : 0.37 : 1).
export const SKIN_SPECTRUM = [0.28, 0.37, 1];
// Per model unit of tissue crossed side-on. The skin is a closed shell (ct_body_pipeline/skinloft2.py);
// on screen the neck behind the skull crosses about 0.56 units side-on (view=photo06), and the photo's
// neck absorbs 0.371 in blue. (Before the skin was rebuilt from the thickness tables, 0.38 and 0.98.)
export const SKIN_GAIN = 0.66;

// The viscera, one brown mass in the body cavity (ct_body_pipeline/visceramesh.py). Provisional: the
// only measure is the user's jar photo 01 (447 px a side, divided by the liquid 217): 0.50 / 0.42 / 0.38,
// absorbance 0.69 : 0.87 : 0.97. Photo 06 shows no brown mass (that specimen may have been gutted; Davis &
// Gore 1936 make removing the viscera necessary when the gut is full). The gain is set on screen: where
// the mass is thickest side-on (0.13 model units or more, no bone in front), blue lets through 0.38 with
// the skin in front counted (median of the gains each pixel needs, 4.8; quartiles 3.8–5.8).
export const VISCERA_SPECTRUM = [0.71, 0.9, 1];
export const VISCERA_GAIN = 4.8;

// The colour patterns. "06" is the one above (photo 06); "01" is the user's jar photo, below.
// Pages pick one with `?stain=01` (chameleon.html and the jar page); without it, "06".
export const STAINS = {
  "06": {
    lightbox: LIGHTBOX,
    bone: { spectrum: BONE_SPECTRUM, gain: BONE_GAIN },
    cartilage: { spectrum: CARTILAGE_SPECTRUM, gain: CARTILAGE_GAIN },
    skin: { spectrum: SKIN_SPECTRUM, gain: SKIN_GAIN },
    viscera: { spectrum: VISCERA_SPECTRUM, gain: VISCERA_GAIN },
    film: { spectrum: [0, 0, 0], gain: 0 },
    organs: {},
  },
  // Measured on 01-user-jar-diaphonized.jpg (the user's jar photo, 447 px a side; watermarked, not
  // redistributed, docs/references/chameleon/SOURCES.md), 2026-10-13. Light let through = pixel / the
  // clear liquid beside the animal (224, neutral grey: median of three clear patches 223–227).
  // In 01 the blue lies at the outline (throat, back, limbs, tail) and the middle of the trunk is pale,
  // so the blue is drawn as a thin stained layer at the skin's surface (the film, chameleon-material.js:
  // each crossing of the surface adds 1 / |cos|, kept under 5), over a faint cleared tissue (the skin's
  // volume, as for "06"). The photo's pixels were sorted by colour (inside the jar, off the grey liquid):
  //   blue (b > r + 20 and g > r + 5), 38.8 % of the animal: absorbance median 0.477 / 0.241 / 0.175
  //   pale (neither, mean above 150),      17.6 %:            0.213 / 0.202 / 0.175
  //   red  (r > b + 15 and r > g + 30),    3.7 %:             0.868 / 1.46 / 1.178
  //   the brown mass (as for "06" above):                      0.693 / 0.868 / 0.968
  // On screen (chameleon.html?stain=01, the default head-down view, the same side as 01) the same shares
  // of the animal were taken from the path and film buffers: of the pixels with no bone, the 38.8 % with
  // the most film (film 2.91, skin 0.269) and the 17.6 % with the least (film 2.19, skin 0.391); the 3.7 %
  // with the most bone (bone 0.040 after the saturation, film 2.29, skin 0.599); the viscera at its
  // thickest (0.159; film 2.62, skin 0.769). Per colour, each tissue's absorbance per unit was solved from
  // those four (non-negative least squares, relative errors):
  //   film 0.1145 / 0.0728 / 0.0389, skin 0 / 0.109 / 0.230, bone 15.1 / 30.5 / 23.6, viscera 2.47 / 3.72 / 4.32
  // Green and blue meet all four. Red cannot: the blue class comes out 0.333 against 0.477 (paler than
  // the photo's outline) and the pale class 0.251 against 0.213; bone and viscera are met. The shares matched between photo and screen stand in for
  // matching the same places (01's trunk bends unlike the model's), so these are fitted, provisional.
  "01": {
    lightbox: [224 / 255, 224 / 255, 224 / 255],
    bone: { spectrum: [0.493, 1, 0.774], gain: 30.54 },
    // Not measured on 01: the rib-gap cartilage is too small to find there. Kept as "06".
    cartilage: { spectrum: CARTILAGE_SPECTRUM, gain: CARTILAGE_GAIN },
    skin: { spectrum: [0, 0.474, 1], gain: 0.2298 },
    // The one brown mass is not drawn in "01" (the organs below take its place). Its fit, kept for reference:
    // spectrum 0.571 / 0.861 / 1, gain 4.32.
    viscera: { spectrum: [0.571, 0.861, 1], gain: 0 },
    film: { spectrum: [1, 0.636, 0.34], gain: 0.1145 },
    // The organs of the body cavity (blender/ct_body_pipeline/organs.py: placed and sized after Melero et al. 2023,
    // Open Vet J 13:1071, the CT of 17 living veiled chameleons). They replace the one brown mass ("06" keeps it).
    // Absorbance per model unit of organ crossed, added to the tissue around it. Fitted on photo 01's patches inside
    // the trunk, by where along the trunk they lie (shoulder → hip = 0 → 1; ct_body_pipeline/fit_organs01.py):
    //   C (t 0.35, brown mottle) less the screen's skin, film and bone there: 0.182 / 0.254 / 0.382, over the liver's
    //     median path in that band (0.198)                                      → liver 0.92 / 1.29 / 1.93
    //   B (t 0.60, brown mottle) 0.375 / 0.514 / 0.718 over the gut contents' path (0.065), A (t 0.85, dark grey)
    //     0.571 / 0.574 / 0.674 over 0.077; their mean                            → contents 6.56 / 7.64 / 9.84
    // By where across the trunk they lie the patches do not match: in 01 they sit nearer the spine, where the
    // living animals' CT has the lungs (> 2/3 of the dorsal coelom, Melero 2023). Not settled.
    // The organs 01 shows nothing of (heart, gallbladder, fat bodies, kidneys, the gut's wall) are given the cleared
    // tissue's own absorbance (the skin's volume above, 0 / 0.109 / 0.230) once more: faint, provisional.
    organs: {
      liver_r: [0.92, 1.29, 1.93], liver_l: [0.92, 1.29, 1.93],
      contents: [6.56, 7.64, 9.84],
      heart: [0, 0.109, 0.23], gallbladder: [0, 0.109, 0.23], fat_r: [0, 0.109, 0.23], fat_l: [0, 0.109, 0.23],
      kidney_r: [0, 0.109, 0.23], kidney_l: [0, 0.109, 0.23],
      stomach: [0, 0.109, 0.23], intestine: [0, 0.109, 0.23], colon: [0, 0.109, 0.23],
    },
  },
};
export const stainOf = (name) => STAINS[name] ?? STAINS["06"];

/** Light let through (red, green, blue) for paths through bone, cartilage and skin films. */
export function transmitted({ bone = 0, cartilage = 0, skin = 0, viscera = 0, film = 0, organs = {} }, { boneScale = 1, boneT0 = BONE_T0, cartilageScale = 1, skinScale = 1, visceraScale = 1, stain = "06" } = {}) {
  const k = stainOf(stain);
  const b = k.bone.gain * boneScale * boneT0 * (1 - Math.exp(-Math.max(bone, 0) / boneT0));
  const c = k.cartilage.gain * cartilageScale * Math.max(cartilage, 0);
  const s = k.skin.gain * skinScale * Math.max(skin, 0);
  const v = k.viscera.gain * visceraScale * Math.max(viscera, 0);
  const f = k.film.gain * Math.max(film, 0);
  const o = [0, 1, 2].map((i) => Object.entries(organs).reduce((sum, [n, t]) => sum + (k.organs[n]?.[i] ?? 0) * Math.max(t, 0), 0));
  return [0, 1, 2].map((i) => Math.exp(-(b * k.bone.spectrum[i] + c * k.cartilage.spectrum[i] + s * k.skin.spectrum[i] + v * k.viscera.spectrum[i] + f * k.film.spectrum[i] + o[i])));
}

// The heart (chameleon-material.js). No resting heart rate for chameleons was found in the literature
// (2026-10-13). Used instead, with the producer's agreement: the agamid Uromastyx microlipes at 30 °C,
// 40.57 ± 5.68 beats/min (Al-Ghamdi 2005, JKAU Sci 17:21–33, Table 1A; 350–1033 g, heavier than a chameleon).
// 8 beats in the 12 s loop (CH_Hover) = 40 beats/min. The heart's size and how far it squeezes are not
// measured: provisional, chosen to be seen.
export const HEART_PERIOD = 12 / 8;
export const HEART_RADIUS_MM = 2;
export const HEART_AMP = 0.12;
// Model units: the skull, 23.1 mm in the CT, is 1.04 units.
export const MODEL_UNITS_PER_MM = 1.04 / 23.1;
