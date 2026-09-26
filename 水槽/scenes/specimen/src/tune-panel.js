import { specimenLook } from "./specimen-material.js";
import { LENS } from "./postprocess.js";
import { FLOOR_LOOK } from "./studio.js";
import { OPTICS } from "./jar-optics.js";

// Shown on this page. Hide with ?tune=0. Moving a slider writes the look object
// in place; the next frame reads it. Reset puts the values that shipped in the code back.
const SLIDERS = [
  ["イカ", [
    ["染まり", specimenLook.stain, 0, 2],
    ["空色", specimenLook.sky, 0, 1],
    ["背側", specimenLook.dorsal, 0, 1.2],
    ["白濁", specimenLook.milk, 0, 0.6],
    ["紋様", specimenLook.spots, 0, 2],
    ["ツヤ", specimenLook.sheen, 0, 2],
    ["しわ", specimenLook.wrinkles, 0, 2],
    ["エンペラの縁", specimenLook.finRim, 0, 4],
  ]],
  ["組織の色", [
    ["筋肉の染まり", specimenLook.muscle, 0, 2],
    ["軟骨の染まり", specimenLook.cartilage, 0, 2],
    ["神経の濃さ", specimenLook.nerve, 0, 2],
    ["神経の白さ", specimenLook.nerveHaze, 0, 1],
    ["顎板の濃さ", specimenLook.chitin, 0, 2],
    ["色素の残り", specimenLook.pigment, 0, 1],
    ["水晶体の残り", specimenLook.lens, 0, 1],
  ]],
  ["部品の大きさ", [
    ["頭の大きさ", specimenLook.headSize, 0.7, 1.35],
    ["目の大きさ", specimenLook.eyeSize, 0.7, 1.5],
    ["目の飛び出し", specimenLook.eyePop, -0.04, 0.05],
    ["目の前後の長さ", specimenLook.eyeAspect, 0.7, 1.4],
    ["虹彩の大きさ", specimenLook.irisSize, 0.6, 1.4],
    ["網膜の深さ", specimenLook.retinaDepth, 0.85, 1.05],
    ["視葉の大きさ", specimenLook.lobeSize, 0.6, 1.6],
    ["口球の大きさ", specimenLook.buccalSize, 0.6, 1.5],
    ["顎板の大きさ", specimenLook.beakSize, 0.6, 1.6],
  ]],
  ["瓶・床", [
    ["ぼけ", LENS.aperture, 0, 2.5],
    ["周辺減光", LENS.vignette, 0, 0.6],
    ["床の影", FLOOR_LOOK.shadow, 0, 1],
    ["集光", FLOOR_LOOK.caustic, 0, 1.5],
    ["接地", FLOOR_LOOK.contact, 0, 1],
    ["縁の映り込み", OPTICS.mirror, 0, 1],
  ]],
];

function addSlider(parent, label, read, write, min, max, onChange) {
  const row = document.createElement("label");
  const name = document.createElement("span");
  name.textContent = label;
  const shown = document.createElement("span");
  shown.className = "tune-value";
  const input = document.createElement("input");
  input.type = "range";
  input.min = String(min);
  input.max = String(max);
  input.step = "0.01";
  const sync = (fromInput) => {
    if (!fromInput) input.value = String(read());
    const value = Number(input.value);
    shown.textContent = value.toFixed(2);
    write(value);
    onChange?.();
  };
  input.addEventListener("input", () => sync(true));
  row.append(name, input, shown);
  parent.append(row);
  sync(false);
  return () => sync(false);
}

export function installTunePanel({ habitat, renderer, specimen, onChange }) {
  if (new URLSearchParams(location.search).get("tune") === "0") return { visible: false };

  const defaults = {
    looks: SLIDERS.flatMap(([, rows]) => rows.map(([label, uniform]) => [uniform, uniform.value])),
    hover: specimen.hoverAction.timeScale,
    drift: 1,
    exposure: renderer.toneMappingExposure,
  };

  const panel = document.createElement("aside");
  panel.id = "tune";
  panel.setAttribute("aria-label", "見た目の調整");

  const heading = document.createElement("h2");
  heading.textContent = "調整";
  const note = document.createElement("p");
  note.className = "tune-note";
  note.textContent = "この画面だけ。確定したらコードに戻す。";
  panel.append(heading, note);

  const refreshers = [];
  for (const [title, rows] of SLIDERS) {
    const block = document.createElement("section");
    const h = document.createElement("h3");
    h.textContent = title;
    block.append(h);
    for (const [label, uniform, min, max] of rows) {
      refreshers.push(addSlider(block, label, () => uniform.value, (v) => { uniform.value = v; }, min, max, onChange));
    }
    panel.append(block);
  }

  const motion = document.createElement("section");
  const motionTitle = document.createElement("h3");
  motionTitle.textContent = "動き・画面";
  motion.append(motionTitle);
  let drift = 1;
  refreshers.push(addSlider(motion, "ホバリング", () => specimen.hoverAction.timeScale, (v) => { specimen.hoverAction.timeScale = v; }, 0, 1.2, onChange));
  refreshers.push(addSlider(motion, "漂い", () => drift, (v) => { drift = v; specimen.motion.setRate(v); }, 0, 2, onChange));
  refreshers.push(addSlider(motion, "明るさ", () => renderer.toneMappingExposure, (v) => { renderer.toneMappingExposure = v; }, 0.4, 1.8, onChange));
  panel.append(motion);

  const reset = document.createElement("button");
  reset.type = "button";
  reset.textContent = "初期値に戻す";
  reset.addEventListener("click", () => {
    for (const [uniform, value] of defaults.looks) uniform.value = value;
    specimen.hoverAction.timeScale = defaults.hover;
    specimen.motion.setRate(defaults.drift);
    renderer.toneMappingExposure = defaults.exposure;
    for (const refresh of refreshers) refresh();
    onChange?.();
  });
  panel.append(reset);
  habitat.append(panel);
  return { visible: true, panel };
}
