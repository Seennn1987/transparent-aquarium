import { chameleonLook, chameleonOrgans } from "./chameleon-material.js";

// The chameleon page's adjustment panel (C record 44, 2026-10-20, the producer: 「Bで進めて規定にするが、パネルで後から調整
// できるようにして」). Moving a slider writes chameleonLook in place; the next frame reads it. Nothing is saved: "設定をコピー"
// copies the values to put back in the code, "初期値に戻す" puts the shipped values back. The panel starts folded to a button;
// ?tune=0 leaves it out (the page-checking tools hide it).
const OPEN_KEY = "chameleon-tune-open";
const hazeBrightness = {
  get value() { return chameleonLook.hazeColor.value.x / 0.93; },
  set value(v) { chameleonLook.hazeColor.value.set(0.93 * v, 0.92 * v, 0.88 * v); },
};
const SLIDERS = [
  ["曇り", [
    ["曇りの強さ", chameleonLook.haze, 0, 1],
    ["曇る厚さ", chameleonLook.hazeLength, 0.3, 4],
    ["奥のぼけ", chameleonLook.blur, 0, 30],
    ["曇りの明るさ", hazeBrightness, 0.8, 1.08],
  ]],
  // The strengths together at the top, as the panel had them (C record 47, the producer: 「なんでさっきのパネルを消したの？
  // 全部を１つのパネルに統合してよ」). Colours are below, every section open in the one panel.
  ["濃さ", [
    ["体の組織（膜の中）", chameleonLook.skin, 0, 6],
    ["膜の表面の層", chameleonLook.film, 0, 6],
    ["骨", chameleonLook.bone, 0, 3],
    ["軟骨（肋骨の先）", chameleonLook.cartilage, 0, 2],
    ["臓器（全体）", chameleonLook.organs, 0, 3],
  ]],
];
// Each tissue (C record 46, the producer: 「パネルについて骨や全ての組織について色や濃さを編集できるようにして」): its strength
// (× the shipped value; the rib-gap cartilage and, in "06", the surface layer start at 0 = not drawn) and its colour (the share of
// red, green and blue it takes away).
const TISSUES = [
  ["骨", chameleonLook.bone, 3, chameleonLook.boneSpectrum],
  ["軟骨（肋骨の先）", chameleonLook.cartilage, 2, chameleonLook.cartSpectrum],
  ["体の組織（膜の中）", chameleonLook.skin, 6, chameleonLook.skinSpectrum],
  ["膜の表面の層", chameleonLook.film, 6, chameleonLook.filmSpectrum],
];
function tissueRows() {
  return TISSUES.map(([label, strength, maxStrength, spectrum]) => {
    const top = Math.max(1.5, 2 * Math.max(...spectrum.value.toArray()));
    const comp = (i) => ({ get value() { return spectrum.value.getComponent(i); }, set value(v) { spectrum.value.setComponent(i, v); } });
    return [label, [["赤を吸う割合", comp(0), 0, top], ["緑を吸う割合", comp(1), 0, top], ["青を吸う割合", comp(2), 0, top]]];
  });
}

const CSS = `
#ch-tune, #ch-tune-open { position: fixed; z-index: 3; top: 12px; right: 12px; font: 12px/1.4 system-ui, sans-serif; color: #222; }
#ch-tune { width: min(320px, calc(100vw - 24px)); max-height: calc(100dvh - 24px); overflow: auto; padding: 10px 12px;
  background: rgba(250, 250, 250, 0.92); border: 1px solid #bbb; border-radius: 6px; }
#ch-tune[hidden], #ch-tune-open[hidden] { display: none; }
#ch-tune .head { display: flex; justify-content: space-between; align-items: center; }
#ch-tune h2, #ch-tune h3 { margin: 0 0 6px; font-size: 12px; font-weight: 600; }
#ch-tune h3 { margin-top: 10px; color: #666; }
#ch-tune p { margin: 0 0 4px; color: #666; }
#ch-tune label { display: grid; grid-template-columns: 9.5em 1fr 2.8em; gap: 6px; align-items: center; margin: 3px 0; }
#ch-tune input[type="range"] { width: 100%; }
#ch-tune .group { margin: 4px 0 6px 6px; } #ch-tune h4 { margin: 6px 0 2px; font-size: 12px; font-weight: 600; color: #333; }
#ch-tune .value { text-align: right; font-variant-numeric: tabular-nums; }
#ch-tune button, #ch-tune-open { min-height: 28px; padding: 0 10px; border: 1px solid #aaa; border-radius: 4px; background: #fff; color: #222; cursor: pointer; }
#ch-tune .wide { display: block; width: 100%; margin-top: 8px; }
#ch-tune button:hover, #ch-tune-open:hover { background: #eee; }
@media (max-width: 600px) { #ch-tune { top: auto; bottom: 40px; max-height: 45dvh; } }
`;

// Each organ (paired ones together): its strength (× the shipped absorbance) and its colour (the absorbance of red, green and
// blue light per model unit; higher = that colour taken away more, so a high red reads blue-green). C record 45.
const ORGANS = [
  ["肝臓", ["liver_r", "liver_l"]], ["胆嚢", ["gallbladder"]], ["胃", ["stomach"]], ["腸", ["intestine"]], ["結腸", ["colon"]],
  ["消化管の中身", ["contents"]], ["心臓", ["heart"]], ["脂肪体", ["fat_r", "fat_l"]], ["腎臓", ["kidney_r", "kidney_l"]],
  ["目", ["eye_r", "eye_l"]], ["水晶体", ["lens_r", "lens_l"]], ["舌骨の軟骨", ["hyoid_cartilage"]], ["爪の鞘", ["claw"]],
];
function organRows() {
  const out = [];
  for (const [label, names] of ORGANS) {
    const us = names.map((n) => chameleonOrgans[n]).filter(Boolean);
    if (!us.length) continue;
    const base = us[0].value.toArray(); let strength = 1;
    const apply = () => { for (const u of us) u.value.set(base[0] * strength, base[1] * strength, base[2] * strength); };
    const top = Math.max(0.5, 3 * Math.max(...base));
    const comp = (i) => ({ get value() { return base[i]; }, set value(v) { base[i] = v; apply(); } });
    out.push([label, [
      ["濃さ", { get value() { return strength; }, set value(v) { strength = v; apply(); } }, 0, 3],
      ["赤を吸う", comp(0), 0, top], ["緑を吸う", comp(1), 0, top], ["青を吸う", comp(2), 0, top],
    ]]);
  }
  return out;
}

function addSlider(parent, label, holder, min, max) {
  const row = document.createElement("label");
  const name = document.createElement("span"); name.textContent = label;
  const input = document.createElement("input");
  input.type = "range"; input.min = String(min); input.max = String(max); input.step = String((max - min) / 200);
  const shown = document.createElement("span"); shown.className = "value";
  const show = () => { shown.textContent = Number(holder.value).toFixed(2); };
  input.addEventListener("input", () => { holder.value = Number(input.value); show(); });
  row.append(name, input, shown); parent.append(row);
  const refresh = () => { input.value = String(holder.value); show(); };
  refresh();
  return refresh;
}

export function installChameleonTune() {
  if (new URLSearchParams(location.search).get("tune") === "0") return;
  const style = document.createElement("style"); style.textContent = CSS; document.head.append(style);
  const organs = organRows();
  const tissues = tissueRows();
  const rows = [...SLIDERS, ...tissues.map(([t, list]) => ["色 " + t, list]), ...organs.map(([t, list]) => ["臓器 " + t, list])]
    .flatMap(([title, list]) => list.map(([label, holder, min, max]) => ({ title, label, holder, min, max })));
  const defaults = rows.map((r) => r.holder.value);

  const panel = document.createElement("aside"); panel.id = "ch-tune"; panel.setAttribute("aria-label", "見た目の調整");
  const head = document.createElement("div"); head.className = "head";
  const h = document.createElement("h2"); h.textContent = "調整";
  const close = document.createElement("button"); close.type = "button"; close.textContent = "閉じる";
  head.append(h, close);
  const note = document.createElement("p"); note.textContent = "この画面だけ。決めた値はコピーしてコードに戻す。";
  panel.append(head, note);
  const refreshers = [];
  for (const [title, list] of SLIDERS) {
    const block = document.createElement("section");
    const h3 = document.createElement("h3"); h3.textContent = title; block.append(h3);
    for (const [label, holder, min, max] of list) refreshers.push(addSlider(block, label, holder, min, max));
    panel.append(block);
  }
  const tissueHead = document.createElement("h3"); tissueHead.textContent = "組織の色"; panel.append(tissueHead);
  for (const [title, list] of tissues) {
    const box = document.createElement("div"); box.className = "group";
    const sum = document.createElement("h4"); sum.textContent = title; box.append(sum);
    for (const [label, holder, min, max] of list) refreshers.push(addSlider(box, label, holder, min, max));
    panel.append(box);
  }
  const organHead = document.createElement("h3"); organHead.textContent = "臓器ごとの濃さと色"; panel.append(organHead);
  for (const [title, list] of organs) {
    const box = document.createElement("div"); box.className = "group";
    const sum = document.createElement("h4"); sum.textContent = title; box.append(sum);
    for (const [label, holder, min, max] of list) refreshers.push(addSlider(box, label, holder, min, max));
    panel.append(box);
  }
  const copy = document.createElement("button"); copy.type = "button"; copy.className = "wide"; copy.textContent = "設定をコピー";
  copy.addEventListener("click", async () => {
    const lines = ["カメレオンの調整値"]; let section = "";
    for (const r of rows) {
      if (r.title !== section) { section = r.title; lines.push("", `【${section}】`); }
      lines.push(`${r.label}: ${Number(r.holder.value).toFixed(3)}`);
    }
    let ok = false;
    try { await navigator.clipboard.writeText(lines.join("\n")); ok = true; } catch {
      const area = document.createElement("textarea"); area.value = lines.join("\n"); area.style.position = "fixed"; area.style.opacity = "0";
      panel.append(area); area.select(); ok = document.execCommand("copy"); area.remove();
    }
    copy.textContent = ok ? "コピーしました" : "コピーできませんでした";
    setTimeout(() => { copy.textContent = "設定をコピー"; }, 1600);
  });
  const reset = document.createElement("button"); reset.type = "button"; reset.className = "wide"; reset.textContent = "初期値に戻す";
  reset.addEventListener("click", () => { rows.forEach((r, i) => { r.holder.value = defaults[i]; }); refreshers.forEach((f) => f()); });
  panel.append(copy, reset);

  const open = document.createElement("button"); open.type = "button"; open.id = "ch-tune-open"; open.textContent = "調整";
  open.setAttribute("aria-controls", "ch-tune");
  const setOpen = (v) => {
    panel.hidden = !v; open.hidden = v; open.setAttribute("aria-expanded", String(v));
    try { localStorage.setItem(OPEN_KEY, v ? "1" : "0"); } catch {}
  };
  close.addEventListener("click", () => { setOpen(false); open.focus(); });
  open.addEventListener("click", () => { setOpen(true); });
  let was = "0";
  try { was = localStorage.getItem(OPEN_KEY) ?? "0"; } catch {}
  document.body.append(panel, open);
  setOpen(was === "1");
  // Keyboard on the panel stays with the panel (Space pauses the page otherwise).
  panel.addEventListener("keydown", (e) => e.stopPropagation());
}
