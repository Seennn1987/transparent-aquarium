import { specimenLook } from "./specimen-material.js";
import { LENS } from "./postprocess.js";
import { FLOOR_LOOK, GALLERY_LOOK, GLASS_TABLE_LOOK } from "./gallery.js";
import { GALLERY_JAR_LOOK } from "./gallery-jars.js";
import { SLOTS } from "./gallery-layout.js";
import { OPTICS } from "./jar-optics.js";
import { organLook } from "./organ-motion.js";
import { labelLook } from "./jar.js";
import { MOTION } from "./specimen-motion.js";

const OPEN_KEY = "specimen-tune-open";

// Shown on this page; its close button folds it to a small button, and the page remembers
// which. Leave it out entirely with ?tune=0. Moving a slider writes the look object
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
    ["縁の光", specimenLook.rimGlow, 0, 1],
    ["液の中のつや", specimenLook.liquidSheen, 0, 1.5],
    ["筋肉の縞", specimenLook.striation, 0, 2],
    ["屈折の歪み", OPTICS.tissueBend, 0, 0.012],
  ]],
  ["組織の色", [
    ["筋肉の染まり", specimenLook.muscle, 0, 2],
    ["軟骨の染まり", specimenLook.cartilage, 0, 2],
    ["神経の濃さ", specimenLook.nerve, 0, 2],
    ["神経の白さ", specimenLook.nerveHaze, 0, 1],
    ["顎板の濃さ", specimenLook.chitin, 0, 2],
    ["色素の残り", specimenLook.pigment, 0, 1],
    ["水晶体の残り", specimenLook.lens, 0, 1],
    ["軟骨の白濁", specimenLook.cartilageHaze, 0, 0.3],
  ]],
  ["生々しさ", [
    ["まだら", specimenLook.mottle, 0, 1.5],
    ["染みの溜まり", specimenLook.pooling, 0, 1.5],
    ["青の揺らぎ", specimenLook.hue, 0, 1.5],
    ["輪郭のにじみ", specimenLook.edgeSoft, 0, 1.5],
    ["中身のかすみ", specimenLook.veil, 0, 1],
    ["消化管の粒", specimenLook.gut, 0, 1.5],
    ["脂の黄色", specimenLook.fat, 0, 1.5],
    ["墨のにじみ", specimenLook.inkBleed, 0, 1.5],
  ]],
  ["内臓の動き", [
    ["全体の速さ", organLook.speed, 0, 3],
    ["心臓", organLook.heart, 0, 2],
    ["消化管・墨", organLook.gut, 0, 2],
    ["眼", organLook.eye, 0, 2],
    ["口", organLook.mouth, 0, 2],
    ["漏斗", organLook.funnel, 0, 2],
    ["色素胞", organLook.chromatophores, 0, 1],
  ]],
  ["液と写真", [
    ["液の霞", OPTICS.haze, 0, 0.3],
    ["光の暖かみ", LENS.tint, 0, 1.5],
    ["粒状感", LENS.grain, 0, 0.06],
    ["色収差", LENS.aberration, 0, 4],
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
  ["ピントと空間", [
    ["ぼけ（絞り）", LENS.aperture, 0, 4],
    ["ピントずらし", LENS.focusShift, -3, 3],
    ["最大のぼけ", LENS.maxBlur, 4, 40],
    ["光の丸ボケ", LENS.bokeh, 0, 2],
    ["台の光", GALLERY_LOOK.glow, 0, 2.5],
    ["部屋の明るさ", GALLERY_LOOK.room, 0, 2],
    ["液の下からの光", OPTICS.underGlow, 0, 2],
    ["標本の散乱光", OPTICS.tissueGlow, 0, 2],
  ]],
  ["奥の瓶", [
    ["液の光", GALLERY_JAR_LOOK.liquid, 0, 2],
    ["蓋の光", GALLERY_JAR_LOOK.lid, 0, 1.5],
  ]],
  ["瓶・床", [
    ["周辺減光", LENS.vignette, 0, 0.6],
    ["床の影", FLOOR_LOOK.shadow, 0, 1],
    ["集光", FLOOR_LOOK.caustic, 0, 1.5],
    ["接地", FLOOR_LOOK.contact, 0, 1],
    ["天板の映り込み", GLASS_TABLE_LOOK.reflect, 0, 3],
    ["天板の黒さ", GLASS_TABLE_LOOK.base, 0, 0.08],
    ["天板のぼけ", GLASS_TABLE_LOOK.blur, 0, 5],
    ["縁の映り込み", OPTICS.mirror, 0, 1],
    ["ガラスの緑", OPTICS.glassGreen, 0, 1.5],
    ["メニスカス", OPTICS.meniscus, 0, 2],
    ["液の揺らぎ", OPTICS.swirl, 0, 3],
    ["ラベル", labelLook.opacity, 0, 1],
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

export function installTunePanel({ habitat, renderer, specimen, jarCount, setJarCount, onChange }) {
  if (new URLSearchParams(location.search).get("tune") === "0") return { visible: false };

  const defaults = {
    looks: SLIDERS.flatMap(([, rows]) => rows.map(([label, uniform]) => [uniform, uniform.value])),
    hover: specimen.hoverAction.timeScale,
    drift: MOTION.driftRate,
    exposure: renderer.toneMappingExposure,
    jars: jarCount(),
  };

  const panel = document.createElement("aside");
  panel.id = "tune";
  panel.setAttribute("aria-label", "見た目の調整");

  const header = document.createElement("div");
  header.className = "tune-header";
  const heading = document.createElement("h2");
  heading.textContent = "調整";
  const close = document.createElement("button");
  close.type = "button";
  close.className = "tune-close";
  close.textContent = "閉じる";
  header.append(heading, close);
  const note = document.createElement("p");
  note.className = "tune-note";
  note.textContent = "この画面だけ。確定したらコードに戻す。";
  panel.append(header, note);

  // Every row as [section, label, read], in the panel's order, for the copied text.
  const readings = [];
  const refreshers = [];
  for (const [title, rows] of SLIDERS) {
    const block = document.createElement("section");
    const h = document.createElement("h3");
    h.textContent = title;
    block.append(h);
    for (const [label, uniform, min, max] of rows) {
      refreshers.push(addSlider(block, label, () => uniform.value, (v) => { uniform.value = v; }, min, max, onChange));
      readings.push([title, label, () => uniform.value]);
    }
    panel.append(block);
  }

  const motion = document.createElement("section");
  const motionTitle = document.createElement("h3");
  motionTitle.textContent = "動き・画面";
  motion.append(motionTitle);
  let drift = MOTION.driftRate;
  const motionRows = [
    ["ホバリング", () => specimen.hoverAction.timeScale, (v) => { specimen.hoverAction.timeScale = v; }, 0, 1.2],
    ["漂い", () => drift, (v) => { drift = v; specimen.motion.setRate(v); }, 0, 2],
    ["明るさ", () => renderer.toneMappingExposure, (v) => { renderer.toneMappingExposure = v; }, 0.4, 1.8],
    ["奥の瓶の数", jarCount, (v) => { if (Math.round(v) !== jarCount()) setJarCount(v); }, 0, SLOTS.length],
  ];
  for (const [label, read, write, min, max] of motionRows) {
    refreshers.push(addSlider(motion, label, read, write, min, max, onChange));
    readings.push([motionTitle.textContent, label, read]);
  }
  panel.append(motion);

  const copy = document.createElement("button");
  copy.type = "button";
  copy.textContent = "設定をコピー";
  copy.addEventListener("click", async () => {
    const lines = ["標本ケースの調整値"];
    let section = "";
    for (const [title, label, read] of readings) {
      if (title !== section) {
        section = title;
        lines.push("", `【${title}】`);
      }
      lines.push(`${label}: ${Number(read()).toFixed(2)}`);
    }
    const text = lines.join("\n");
    let copied = false;
    try {
      await navigator.clipboard.writeText(text);
      copied = true;
    } catch {
      // The clipboard API needs focus and permission; the old way works without them.
      const area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      panel.append(area);
      area.select();
      copied = document.execCommand("copy");
      area.remove();
    }
    copy.textContent = copied ? "コピーしました" : "コピーできませんでした";
    setTimeout(() => { copy.textContent = "設定をコピー"; }, 1600);
  });
  panel.append(copy);

  const reset = document.createElement("button");
  reset.type = "button";
  reset.textContent = "初期値に戻す";
  reset.addEventListener("click", () => {
    for (const [uniform, value] of defaults.looks) uniform.value = value;
    specimen.hoverAction.timeScale = defaults.hover;
    drift = defaults.drift;
    specimen.motion.setRate(drift);
    renderer.toneMappingExposure = defaults.exposure;
    setJarCount(defaults.jars);
    for (const refresh of refreshers) refresh();
    onChange?.();
  });
  panel.append(reset);

  const open = document.createElement("button");
  open.type = "button";
  open.id = "tune-open";
  open.textContent = "調整";
  open.setAttribute("aria-controls", "tune");
  const setOpen = (value) => {
    panel.hidden = !value;
    open.hidden = value;
    open.setAttribute("aria-expanded", String(value));
    try { localStorage.setItem(OPEN_KEY, value ? "1" : "0"); } catch {}
  };
  close.addEventListener("click", () => { setOpen(false); open.focus(); });
  open.addEventListener("click", () => { setOpen(true); close.focus(); });
  let startOpen = true;
  try { startOpen = localStorage.getItem(OPEN_KEY) !== "0"; } catch {}

  habitat.append(panel, open);
  setOpen(startOpen);
  return {
    panel,
    get visible() { return !panel.hidden; },
  };
}
