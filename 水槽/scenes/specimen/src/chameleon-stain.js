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
// Measured again on the skin built from the bones (ct_body_pipeline/skinbody.py 7, after the hyoid rebuild, 2026-10-15):
// below the neck vertebrae v02–v04, off the bone, the skin crosses 0.627 units (median of 1328 screen pixels,
// quartile 0.687), so 0.371 / 0.627. (Was 0.66 over 0.56.)
// After the head was made 1.45 times, the ribcage widened and the skin smoothed (plan, C record 21, 2026-10-17): the
// same pixels cross 0.900 units on the Mac's screen against 0.630 for the glb before (whose gain came out 0.589 there,
// against 0.592 here), so 0.592 × 0.630 / 0.900 = 0.414 (ct_body_pipeline/fit_skin06.py on both glbs).
// Again after the limbs were set to the literature's stance and the rib heads put into the vertebrae (C records 23–24,
// 2026-10-17), always against the glb before C record 21: 0.918 against 0.630, so 0.592 × 0.630 / 0.918 = 0.406.
export const SKIN_GAIN = 0.406;

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
/** The hyoid cartilage's absorbance per model unit (photo 06's throat, fitted; see "06" below). */
// After the head was made 1.45 times (C record 21, 2026-10-17) the median hyoid path there went 0.0344 → 0.0485 on the
// Mac's screen, so × 0.709 (was 11.98 / 4.11 / 1.65). After C records 23–24: 0.0344 → 0.0480, × 0.717.
export const HYOID_CARTILAGE = [8.59, 2.95, 1.18];

export const STAINS = {
  "06": {
    lightbox: LIGHTBOX,
    bone: { spectrum: BONE_SPECTRUM, gain: BONE_GAIN },
    cartilage: { spectrum: CARTILAGE_SPECTRUM, gain: CARTILAGE_GAIN },
    skin: { spectrum: SKIN_SPECTRUM, gain: SKIN_GAIN },
    viscera: { spectrum: VISCERA_SPECTRUM, gain: VISCERA_GAIN },
    film: { spectrum: [0, 0, 0], gain: 0 },
    // The hyoid's cartilage (entoglossal process, basihyal, ceratohyals; blender/ct_body_pipeline/hyoid_rebuild.py) is drawn
    // as the organ hyoid_cartilage, so that it can have its own strength: with the rib-gap cartilage's (above) it came out
    // about 4 times darker than the pale blue at photo 06's throat (red absorbance 1.9 against 0.46). Fitted to that patch
    // (x 955–1005, y 480–525 px: 0.462 / 0.231 / 0.323 over the background), less the screen's own tissue there, by the
    // median hyoid path off the bone (0.0328; ct_body_pipeline/fit_hyoidcart06.py, 2026-10-15, with the skin at 0.592;
    // 11.71 / 3.77 / 0.71 with the skin at 0.66). The patch lies behind the
    // jaw, the modelled entoglossal process along it, so matched by strength, not by place: provisional.
    organs: { hyoid_cartilage: HYOID_CARTILAGE },
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
  // Refitted the same way on the rebuilt skin (ct_body_pipeline/skinloft3.py, 2026-10-14; screen rows: blue film 2.83,
  // skin 0.270; pale 2.13, 0.386; red bone 0.0402 after the saturation, film 2.26, skin 0.615):
  //   film 0.118 / 0.0744 / 0.0393, skin 0 / 0.1139 / 0.2374, bone 15.0 / 30.4 / 23.5
  // Refitted again after the skin was built from the bones (ct_body_pipeline/skinbody.py, 2026-10-14: the body is
  // deeper, so more skin is crossed; screen rows: blue film 2.76, skin 0.311; pale 2.16, 0.687; red bone 0.0402
  // after the saturation, film 2.26, skin 0.733):
  //   film 0.1168 / 0.0840 / 0.0539, skin 0 / 0.0298 / 0.0854, bone 15.0 / 31.1 / 24.7
  // And again after the head was given a skin of its own, eyes, coiled gut and red ventral ribs (skinbody.py 6,
  // 2026-10-14). The one viscera mass is no longer drawn, so three classes: blue film 2.96, skin 0.309; pale 2.13,
  // 0.701; red bone 0.0403 after the saturation, film 2.32, skin 0.685:
  //   film 0.1173 / 0.0751 / 0.0484, skin 0 / 0.0606 / 0.1031, bone 14.8 / 30.9 / 24.7
  // And again after the hyoid was rebuilt (blender/ct_body_pipeline/hyoid_rebuild.py, 2026-10-15: the five rods in the
  // chest were taken out, the entoglossal process, basihyal and ceratohyals added as cartilage, and the head skin
  // reaches the throat). Blue film 2.83, skin 0.354; pale 2.11, 0.708; red bone 0.0403, film 2.27, skin 0.627:
  //   film 0.1189 / 0.0791 / 0.0495, skin 0 / 0.0496 / 0.1000, bone 14.9 / 31.0 / 24.9
  // And after the head was made 1.45 times, the ribcage widened and the skin smoothed (C record 21, 2026-10-17). Fitted
  // on the Mac's screen (Chrome, not the cloud's SwiftShader) for both the glb before and after; the glb before gives
  // film 0.1164 / 0.0749 / 0.0481, skin 0 / 0.0591 / 0.1023, bone 15.0 / 31.1 / 24.9 there (not the values above:
  // the screens differ and the skin had changed since 10-15), the glb after film 0.1136 / 0.0752 / 0.0470,
  // skin 0 / 0.0390 / 0.0768, bone 14.9 / 30.3 / 24.2. The values above times after / before, channel by channel:
  //   film 0.1161 / 0.0794 / 0.0483, skin 0 / 0.0327 / 0.0751, bone 14.79 / 30.26 / 24.17
  // And after the limbs were set to the literature's stance and the rib heads put into the vertebrae (C records 23–24,
  // 2026-10-17). The glb after gives film 0.1147 / 0.0781 / 0.0449, skin 0 / 0.0326 / 0.0819, bone 14.8 / 30.3 / 24.2 on the
  // Mac's screen; the 10-15 values times after / before (the glb before C record 21, as above), channel by channel:
  //   film 0.1172 / 0.0825 / 0.0462, skin 0 / 0.0273 / 0.0800, bone 14.72 / 30.22 / 24.13 (used below)
  // Green and blue meet all three. Red cannot: the blue class comes out 0.347 against 0.477 (paler than
  // the photo's outline) and the pale class 0.249 against 0.213; bone and viscera are met. The shares matched between photo and screen stand in for
  // matching the same places (01's trunk bends unlike the model's), so these are fitted, provisional.
  "01": {
    lightbox: [224 / 255, 224 / 255, 224 / 255],
    bone: { spectrum: [0.487, 1, 0.798], gain: 30.22 },
    // Not measured on 01: the rib-gap cartilage is too small to find there. Kept as "06".
    cartilage: { spectrum: CARTILAGE_SPECTRUM, gain: CARTILAGE_GAIN },
    skin: { spectrum: [0, 0.342, 1], gain: 0.0800 },
    // The one brown mass is not drawn in "01" (the organs below take its place). Its fit, kept for reference:
    // spectrum 0.571 / 0.861 / 1, gain 4.32.
    viscera: { spectrum: [0.571, 0.861, 1], gain: 0 },
    film: { spectrum: [1, 0.704, 0.394], gain: 0.1172 },
    // The organs of the body cavity (blender/ct_body_pipeline/organs.py). Order head → tail and the sizes of heart,
    // liver, gallbladder, fat bodies and kidneys after Melero et al. 2023 (Open Vet J 13:1071, the CT of 17 living
    // veiled chameleons). The living animals' lungs fill > 2/3 of the dorsal coelom (ibid.); in preserved chameleons
    // the lungs are often contracted (Klaver 1973, Beaufortia 20: 164–169), and in five photos of cleared-and-stained
    // chameleons (docs/chameleon_ct_body/organs_ref_compare, sources in docs/references/chameleon/SOURCES.md) the
    // visible mass lies at shoulder → hip t 0.20–0.95 and back → belly 0–0.86 (medians). So the gut (no size in the
    // source) fills that range from behind the liver to the kidneys (provisional). They replace the one brown mass
    // ("06" keeps it). Absorbance per model unit of organ crossed, added to the tissue around it, fitted on photo 01
    // (ct_body_pipeline/fit_organs01.py), each patch less the screen's skin, film and bone there:
    //   C (t 0.35, brown mottle) 0.172 / 0.271 / 0.442 over the liver's median path in that band (0.231)
    //                                                                            → liver 0.75 / 1.17 / 1.91
    //     (after the hyoid rebuild, 2026-10-15: 0.150 / 0.231 / 0.415 over 0.226 → liver 0.66 / 1.02 / 1.84, used)
    //   A (t 0.85, dark grey) 0.567 / 0.593 / 0.695 and B (t 0.60, brown mottle) 0.440 / 0.629 / 0.806; mean
    //     0.503 / 0.611 / 0.750. 01's trunk bends unlike the model's, so the same places on screen do not catch the
    //     gut; matched by share instead, as for the film and bone above: over the median gut path of the screen's
    //     gut pixels (0.165)                                                     → gut 3.06 / 3.71 / 4.55
    //     (after the hyoid rebuild: 0.494 / 0.599 / 0.746 over 0.156 → gut 3.16 / 3.84 / 4.79, used)
    //   (values after the head skin, eyes and coiled gut, skinbody.py 6, 2026-10-14)
    // The eyes (blender/ct_body_pipeline/eyes.py: a ball in each orbit, centred on the scleral ring, radius the
    // orbit's 2.94 mm; the lens a ball of 0.45 of that inside): photo 01's eye (centre x 243, y 368) lets through a
    // ring (r 7–10 px) of absorbance 1.135 / 1.48 / 1.48 and a darker middle (r < 4 px) 1.24 / 1.70 / 1.89. Over the
    // screen's eye-only pixels, less the skin, film and bone there, by the median eye path (0.172)
    //                                                                            → eye 3.82 / 4.19 / 5.16
    //     (after the hyoid rebuild: base 0.377 / 0.460 / 0.380, eye path 0.166 → eye 4.08 / 4.63 / 5.64, used)
    // After the head was made 1.45 times, the ribcage widened and the skin smoothed (C record 21, 2026-10-17), each
    // organ's absorbance per unit is scaled by its median path before / after on the Mac's screen, so the light let
    // through stays as fitted: liver path 0.2928 → 0.3061 (× 0.957), gut 0.1580 → 0.1454 (× 1.087), eye-only pixels'
    // eye path 0.1706 → 0.2494 (× 0.684). The skin around them is not refitted for this (provisional).
    // After C records 23–24 (limbs, rib heads), against the same glb before: liver 0.2928 → 0.3075 (× 0.952), gut
    // 0.1580 → 0.1958 (× 0.807), eye 0.1706 → 0.2506 (× 0.681).
    // The middle comes out darker from the longer path through the ball alone, so the lens adds nothing (0, fitted:
    // ct_body_pipeline/fit_eyes01.py).
    // The gut's value is given to the stomach, intestine and colon alike. The contents are not told apart from the
    // gut in 01, so they add nothing beyond it (provisional).
    // The organs 01 shows nothing of (heart, gallbladder, fat bodies, kidneys) are given the cleared tissue's own
    // absorbance (the skin's volume above, 0 / 0.0273 / 0.0800) once more: faint, provisional.
    organs: {
      liver_r: [0.63, 0.97, 1.75], liver_l: [0.63, 0.97, 1.75],
      contents: [0, 0, 0],
      heart: [0, 0.0273, 0.0800], gallbladder: [0, 0.0273, 0.0800], fat_r: [0, 0.0273, 0.0800], fat_l: [0, 0.0273, 0.0800],
      kidney_r: [0, 0.0273, 0.0800], kidney_l: [0, 0.0273, 0.0800],
      stomach: [2.55, 3.10, 3.87], intestine: [2.55, 3.10, 3.87], colon: [2.55, 3.10, 3.87],
      eye_r: [2.78, 3.15, 3.84], eye_l: [2.78, 3.15, 3.84], lens_r: [0, 0, 0], lens_l: [0, 0, 0],
      // Not measured on 01 (its throat is under the blue film): kept as "06", like the rib-gap cartilage.
      hyoid_cartilage: HYOID_CARTILAGE,
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
