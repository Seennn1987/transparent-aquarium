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
// Per model unit of tissue crossed (the skin's baked depth). On screen the neck behind the skull
// crosses about 0.38 units side-on; the photo's neck absorbs 0.371 in blue.
export const SKIN_GAIN = 0.98;

/** Light let through (red, green, blue) for paths through bone, cartilage and skin films. */
export function transmitted({ bone = 0, cartilage = 0, skin = 0 }, { boneScale = 1, boneT0 = BONE_T0, cartilageScale = 1, skinScale = 1 } = {}) {
  const b = BONE_GAIN * boneScale * boneT0 * (1 - Math.exp(-Math.max(bone, 0) / boneT0));
  const c = CARTILAGE_GAIN * cartilageScale * Math.max(cartilage, 0);
  const s = SKIN_GAIN * skinScale * Math.max(skin, 0);
  return [0, 1, 2].map((i) => Math.exp(-(b * BONE_SPECTRUM[i] + c * CARTILAGE_SPECTRUM[i] + s * SKIN_SPECTRUM[i])));
}
