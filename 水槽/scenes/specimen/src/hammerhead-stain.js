// The cleared-and-stained smooth hammerhead (Sphyrna zygaena) on a lightbox (no dish yet).
//
// No photo of a cleared-and-stained hammerhead was found (docs/シュモクザメ透明標本_計画書_v1.0.md 第 8.3 節).
// The colours are borrowed from a double-stained shark embryo: Cephaloscyllium ventriosum, 15 cm,
// Eames et al. (2007) J. Anat. 210(5), Fig. 2A (dorsal view; licence not checked, kept out of git).
// In that embryo the vertebrae are strongly calcified and take the alizarin red; the cranium, jaws,
// gill arches, girdles and fin radials take the alcian blue; the body is almost clear (cream).
// Light let through, divided by the background beside it (473 × 526 px JPEG, 計画書 第 8.3 節):
//   background                       1 / 1 / 1   (253, 247, 251)
//   head cartilage   (40, 58)        0.04 / 0.47 / 0.43
//   gill arches      (72, 28)        0.50 / 0.73 / 0.83
//   pectoral radials (108, 18)       0.40 / 0.96 / 0.92
//   vertebral column (300, 27), (330, 31)  0.42–0.48 / 0.12–0.18 / 0.34–0.37
//   body tissue      (300, 24)       0.79 / 0.66 / 0.57
// This is an embryo of another species: the hammerhead's colours here are a creation that applies
// its staining to the hammerhead's shape (provisional until A6 measures the screen against these).
import { STAINS } from "./chameleon-stain.js";

export const HH_LIGHTBOX = [253 / 255, 247 / 255, 251 / 255];

// Set on screen (2026-10-14, hammerhead.html?view=top, 1400 × 800, medians over the classes below, each
// pixel's light let through divided by the lightbox). With the first guesses the screen gave:
//   vertebral column (bone path ≥ half its maximum; bone 7.2 mm, skin 92 mm)   0.41 / 0.14 / 0.26
//   fin radials (no bone, cartilage ≥ 0.8 mm, skin < 30 mm, behind the head)  0.50 / 0.89 / 0.86
//   head cartilage (the 30 % with the most cartilage in the head; 4.0 mm, skin 34 mm) 0.28 / 0.73 / 0.67
//   body tissue (skin ≥ 50 mm, no skeleton; 80 mm)                              0.83 / 0.72 / 0.64
// The gains below are solved so each class meets the embryo's value (absorbance = gain × spectrum × path,
// the tissue in front counted with its own new gain):
//   tissue: target 0.24 / 0.42 / 0.56 over 80 mm                → spectrum 0.42 : 0.74 : 1, gain 7.0
//   vertebral column: target 0.80 / 1.90 / 1.04 less the tissue (92 mm × 7.0) → 0.53 / 1.43 / 0.40
//                     → spectrum 0.37 : 1 : 0.28; gain × 239/262 of the first guess
//   fin radials: target 0.92 / 0.04 / 0.08 less the tissue → 0.90 / 0.01 / 0.04 over 2.2 mm → 408 × (1 : 0.01 : 0.04)
//   head cartilage: target 3.22 / 0.76 / 0.84 less the tissue → 3.12 / 0.58 / 0.61 over 4.0 mm
//                   → 780 × (1 : 0.19 : 0.20). One spectrum could not give both the radials and the head
//                   (the head is far darker and greener per mm), so the head is a part of its own.
// Measured again with these (2026-10-14, view=top, ss=1, 1000 × 500; the classes as above, the head class now the
// head part's own path): fin radials 0.40 / 0.96 / 0.92, head 0.04 / 0.46 / 0.42, tissue 0.79 / 0.66 / 0.57 (all at
// the embryo's values); the vertebral column 0.39 / 0.11 / 0.31 (bone 9.1 mm, skin 97 mm), darker than 0.42–0.48 /
// 0.12–0.18 / 0.34–0.37, so its gain was taken down × 0.80 (239 → 191) to put its bone absorbance at the target's.
// 2026-10-15 測り直し（顎・歯・エラの骨を頭骨から分け、エラの骨を案 B にした glb。view=top、ss=1、1000 × 500。
//  blender/ct_hammerhead/measure_colors.py の分け方。値は光の通り ÷ ライトボックス）:
//   頭の軟骨 0.08 / 0.55 / 0.51（頭の道のり 3.1 mm、膜 20 mm。顎を分けて道のりが 4.0 → 3.1 mm に減った）→ 前にある膜の分を引いて
//     目標 0.04 / 0.47 / 0.43 に要る吸い方は 1.28〜1.33 倍 → 利得 780 × 1.30 = 1014
//   椎骨の列 0.40 / 0.12 / 0.35（骨 11.1 mm、膜 75 mm）。赤が目標 0.42〜0.48 より暗い → 膜の分を引いて 0.83〜0.97 倍 → 191 × 0.87 = 166
//   ひれの放射軟骨 0.40 / 0.96 / 0.92、体の組織 0.79 / 0.66 / 0.58 は目標どおりなので変えない
export const HH_BONE_SPECTRUM = [0.37, 1, 0.28];
export const HH_CARTILAGE_SPECTRUM = [1, 0.01, 0.04];
export const HH_HEAD_SPECTRUM = [1, 0.19, 0.20];
export const HH_SKIN_SPECTRUM = [0.42, 0.74, 1];
export const HH_BONE_T0 = 0.02;      // the bone's path saturates as in the chameleon (t0, metres)
export const HH_BONE_GAIN = 166;   // 2026-10-15 191 → 166（上の注）
export const HH_CARTILAGE_GAIN = 408;
export const HH_HEAD_GAIN = 1014;  // 2026-10-15 780 → 1014（上の注）
export const HH_SKIN_GAIN = 7.0;

STAINS.hammerhead = {
  lightbox: HH_LIGHTBOX,
  bone: { spectrum: HH_BONE_SPECTRUM, gain: HH_BONE_GAIN },
  cartilage: { spectrum: HH_CARTILAGE_SPECTRUM, gain: HH_CARTILAGE_GAIN },
  skin: { spectrum: HH_SKIN_SPECTRUM, gain: HH_SKIN_GAIN },
  viscera: { spectrum: HH_HEAD_SPECTRUM, gain: HH_HEAD_GAIN },   // the head's cartilage (hammerhead-material.js)
  // A8 皮歯（hammerhead-material.js の denticleMaterial）。色は椎骨と同じアリザリンの赤紫（胚で皮歯は赤紫）。
  //  強さはページの ?dent=（chameleonLook.film に入る。既定 1（2026-10-15 決定））。利得 0.25 は「?dent=1 で点の上の吸い方が緑で約 0.25」
  film: { spectrum: HH_BONE_SPECTRUM, gain: 0.25 },
  // A8 まだら（hammerhead-material.js の mottleMaterial）: 体の組織と同じ吸い方の色。1 回横切るごとの吸い方（?mottle=1 のとき）。
  //  0.12 は「むらの濃い所で、体の組織の青の吸い方（80 mm で 0.56）が 1 割ほど増える」くらいからの出発（2026-10-15）。強さはページの ?mottle=（既定 0）
  organs: { mottle: [0.42 * 0.12, 0.74 * 0.12, 1 * 0.12] },
};
