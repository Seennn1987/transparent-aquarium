import { chameleonLook, chameleonOrgans, chameleonOrganLook, setChameleonLook } from "./chameleon-material.js";
import { LOOKS } from "./chameleon-stain.js";

// The chameleon page's adjustment panel (C record 44, 2026-10-20, the producer: 「Bで進めて規定にするが、パネルで後から調整
// できるようにして」). Moving a control writes chameleonLook in place; the next frame reads it. Nothing is saved: "設定をコピー"
// copies the values to put back in the code, "初期値に戻す" puts the shipped values back. The panel starts folded to a button;
// ?tune=0 leaves it out (the page-checking tools hide it).
// C record 54 (2026-10-24, the producer: 「各パーツごとの色は「濃さ」と「…規定パレットと色を自由に選べるもの」で構成して…「赤を
// 吸う」みたいなのか意味わからないから不要」「眼球周辺のパーツはそれ単体で色とこさが編集できるように」): each part has its
// strength and a colour, picked from the palette or freely (the system's picker, with its eyedropper).
const OPEN_KEY = "chameleon-tune-open";

// A part's colour is what it lets through at strength 1 over COLOUR_DEPTH of its absorbance: shown = exp(−COLOUR_DEPTH × a).
// Picking a colour sets a = −ln(colour) / COLOUR_DEPTH (colours darker than MIN_LIGHT are taken as MIN_LIGHT), so a pale
// colour makes a faint part, a deep one a dark part. Organs keep their own scale: a = base / unit, unit the largest of the
// shipped base (1 when it is 0).
const COLOUR_DEPTH = 1.5;
const MIN_LIGHT = 0.02;
// Colours a cleared-and-stained specimen can show (alizarin red on bone, alcian blue on cartilage, the cleared tissue, bile,
// pigment), as the light let through.
const PALETTE = [
  ["骨の赤紫", "#b83a6e"], ["濃い赤", "#8e1e3c"], ["淡い桃", "#e7a3b8"], ["アルシアンの青", "#3e8ec4"],
  ["淡い水色", "#9fd3e6"], ["紺", "#2e4a8a"], ["透けた組織の黄", "#e9dda8"], ["琥珀", "#c89a4b"],
  ["褐色", "#7b5b3e"], ["灰褐", "#5a5048"], ["黄緑（胆汁）", "#a7b45a"], ["乳白", "#eceae2"],
];

const toSrgb = (c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055);
const toLinear = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const hexOf = (a) => "#" + a.map((v) => Math.round(255 * Math.min(1, Math.max(0, toSrgb(Math.exp(-COLOUR_DEPTH * v)))))
  .toString(16).padStart(2, "0")).join("");
const absOf = (hex) => [1, 3, 5].map((i) => -Math.log(Math.max(MIN_LIGHT, toLinear(parseInt(hex.slice(i, i + 2), 16) / 255))) / COLOUR_DEPTH);

const hazeBrightness = {
  get value() { return chameleonLook.hazeColor.value.x / 0.93; },
  set value(v) { chameleonLook.hazeColor.value.set(0.93 * v, 0.92 * v, 0.88 * v); },
};
const HAZE = [
  ["曇りの強さ", chameleonLook.haze, 0, 1],
  ["曇る厚さ", chameleonLook.hazeLength, 0.3, 4],
  ["奥のぼけ", chameleonLook.blur, 0, 30],
  ["曇りの明るさ", hazeBrightness, 0.8, 1.08],
];

// A tissue drawn from the path buffer: its strength (× the fitted gain) and its spectrum (the absorbance's colour).
const tissue = (label, strength, max, spectrum) => ({
  label, strength, max,
  colour: { get value() { return spectrum.value.toArray(); }, set value(a) { spectrum.value.set(...a); } },
});
// An organ (paired ones together): the uniform is strength × base.
function organ(label, names) {
  const looks = names.map((n) => chameleonOrganLook[n]).filter(Boolean);
  if (!looks.length) return null;
  const apply = () => { for (const n of names) if (chameleonOrganLook[n]) chameleonOrgans[n].value.set(...looks[0].base).multiplyScalar(looks[0].strength); };
  const unit = Math.max(...looks[0].base) || 1;
  return {
    label, max: 3,
    strength: { get value() { return looks[0].strength; }, set value(v) { for (const o of looks) o.strength = v; apply(); } },
    colour: {
      get value() { return looks[0].base.map((v) => v / unit); },
      set value(a) { for (const o of looks) o.base = a.map((v) => v * unit); apply(); },
    },
  };
}

function groups() {
  const organs = (list) => list.map(([label, names]) => organ(label, names)).filter(Boolean);
  return [
    ["組織", [
      tissue("骨", chameleonLook.bone, 3, chameleonLook.boneSpectrum),
      tissue("軟骨（肋骨の先）", chameleonLook.cartilage, 2, chameleonLook.cartSpectrum),
      tissue("体の組織（膜の中）", chameleonLook.skin, 6, chameleonLook.skinSpectrum),
      tissue("膜の表面の層", chameleonLook.film, 6, chameleonLook.filmSpectrum),
    ]],
    ["目のまわり", [
      ...organs([["眼球", ["eye_r", "eye_l"]], ["水晶体", ["lens_r", "lens_l"]]]),
      tissue("目のまわりの骨（強膜輪・眼窩の縁）", chameleonLook.eyeRing, 3, chameleonLook.ringSpectrum),
    ]],
    ["臓器", organs([
      ["肝臓", ["liver_r", "liver_l"]], ["胆嚢", ["gallbladder"]], ["胃", ["stomach"]], ["腸", ["intestine"]], ["結腸", ["colon"]],
      ["消化管の中身", ["contents"]], ["心臓", ["heart"]], ["脂肪体", ["fat_r", "fat_l"]], ["腎臓", ["kidney_r", "kidney_l"]],
      ["舌骨の軟骨", ["hyoid_cartilage"]], ["爪の鞘", ["claw"]],
    ])],
  ];
}

const CSS = `
#ch-tune, #ch-tune-open { position: fixed; z-index: 4; top: 12px; right: 12px; font: 12px/1.4 system-ui, sans-serif; color: #222; }
#ch-tune { width: min(320px, calc(100vw - 24px)); max-height: calc(100dvh - 24px); overflow: auto; padding: 10px 12px;
  background: rgba(250, 250, 250, 0.94); border: 1px solid #bbb; border-radius: 6px; }
#ch-tune[hidden], #ch-tune-open[hidden] { display: none; }
#ch-tune .head { display: flex; justify-content: space-between; align-items: center; }
#ch-tune h2, #ch-tune h3 { margin: 0 0 6px; font-size: 12px; font-weight: 600; }
#ch-tune h3 { margin-top: 12px; color: #666; }
#ch-tune p { margin: 0 0 4px; color: #666; }
#ch-tune label { display: grid; grid-template-columns: 5.5em 1fr 2.8em; gap: 6px; align-items: center; margin: 3px 0; }
#ch-tune input[type="range"] { width: 100%; }
#ch-tune .part { margin: 4px 0 8px; padding-bottom: 6px; border-bottom: 1px solid #e2e2e2; }
#ch-tune h4 { margin: 6px 0 2px; font-size: 12px; font-weight: 600; color: #333; }
#ch-tune .value { text-align: right; font-variant-numeric: tabular-nums; }
#ch-tune .colours { display: flex; align-items: center; gap: 8px; margin-top: 2px; }
#ch-tune .now { flex: none; width: 40px; height: 40px; border: 1px solid #888; border-radius: 4px; }
#ch-tune .palette { display: grid; grid-template-columns: repeat(6, 18px); gap: 3px; }
#ch-tune .swatch { width: 18px; height: 18px; min-height: 0; padding: 0; border: 1px solid rgba(0, 0, 0, 0.25); border-radius: 3px; }
#ch-tune .swatch:hover { outline: 2px solid #555; background-clip: padding-box; }
#ch-tune .more { position: relative; display: inline-flex; align-items: center; min-height: 28px; padding: 0 8px; border: 1px solid #aaa; border-radius: 4px; background: #fff; font-size: 11px; white-space: nowrap; cursor: pointer; }
#ch-tune .more:hover { background: #eee; }
#ch-tune .more input { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
#ch-tune button, #ch-tune-open { min-height: 28px; padding: 0 10px; border: 1px solid #aaa; border-radius: 4px; background: #fff; color: #222; cursor: pointer; }
#ch-tune .wide { display: block; width: 100%; margin-top: 8px; }
#ch-tune button:hover, #ch-tune-open:hover { background: #eee; }
@media (max-width: 600px) { #ch-tune { top: auto; bottom: 40px; max-height: 45dvh; } }
#ch-look { position: fixed; z-index: 4; top: 12px; left: 12px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; max-width: calc(100vw - 110px);
  padding: 6px 8px; background: rgba(250, 250, 250, 0.92); border: 1px solid #bbb; border-radius: 6px; font: 12px/1.4 system-ui, sans-serif; color: #222; }
#ch-look button { min-height: 28px; padding: 0 10px; border: 1px solid #aaa; border-radius: 4px; background: #fff; color: #222; cursor: pointer; }
#ch-look button:hover { background: #eee; }
#ch-look button[aria-pressed="true"] { border-color: #444; background: #333; color: #fff; }
`;

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

// The part's colour now, the palette, and "その他の色…" (the system's picker).
function addColour(parent, label, holder) {
  const row = document.createElement("div"); row.className = "colours";
  const now = document.createElement("span"); now.className = "now"; now.setAttribute("role", "img");
  const more = document.createElement("label"); more.className = "more"; more.textContent = "その他の色…";
  const pick = document.createElement("input"); pick.type = "color"; pick.setAttribute("aria-label", `${label}の色を自由に選ぶ`);
  more.append(pick);
  const refresh = () => {
    const hex = hexOf(holder.value);
    now.style.background = hex; now.setAttribute("aria-label", `${label}のいまの色 ${hex}`); pick.value = hex;
  };
  const set = (hex) => { holder.value = absOf(hex); refresh(); };
  const palette = document.createElement("div"); palette.className = "palette";
  row.append(now, palette);
  for (const [name, hex] of PALETTE) {
    const b = document.createElement("button"); b.type = "button"; b.className = "swatch"; b.style.background = hex;
    b.title = name; b.setAttribute("aria-label", `${label}を${name}に`);
    b.addEventListener("click", () => set(hex));
    palette.append(b);
  }
  pick.addEventListener("input", () => set(pick.value));
  row.append(more); parent.append(row);
  refresh();
  return refresh;
}

/** `stain`: the page's colour pattern. The saved looks (chameleon-stain.js LOOKS) are for "06" and shown only there. */
export function installChameleonTune(stain = "06") {
  if (new URLSearchParams(location.search).get("tune") === "0") return;
  const style = document.createElement("style"); style.textContent = CSS; document.head.append(style);
  const parts = groups();
  const holders = [
    ...HAZE.map(([, h]) => h), chameleonLook.organs,
    ...parts.flatMap(([, list]) => list.flatMap((p) => [p.strength, p.colour])),
  ];
  const defaults = holders.map((h) => structuredClone(h.value));

  const panel = document.createElement("aside"); panel.id = "ch-tune"; panel.setAttribute("aria-label", "見た目の調整");
  const head = document.createElement("div"); head.className = "head";
  const h = document.createElement("h2"); h.textContent = "調整";
  const close = document.createElement("button"); close.type = "button"; close.textContent = "閉じる";
  head.append(h, close);
  const note = document.createElement("p"); note.textContent = "この画面だけ。決めた値はコピーしてコードに戻す。";
  panel.append(head, note);
  const refreshers = [];
  const section = (title) => { const h3 = document.createElement("h3"); h3.textContent = title; panel.append(h3); };
  section("曇り");
  for (const [label, holder, min, max] of HAZE) refreshers.push(addSlider(panel, label, holder, min, max));
  for (const [title, list] of parts) {
    section(title);
    if (title === "臓器") refreshers.push(addSlider(panel, "全体の濃さ", chameleonLook.organs, 0, 3));
    for (const p of list) {
      const box = document.createElement("div"); box.className = "part";
      const h4 = document.createElement("h4"); h4.textContent = p.label; box.append(h4);
      refreshers.push(addSlider(box, "濃さ", p.strength, 0, p.max), addColour(box, p.label, p.colour));
      panel.append(box);
    }
  }
  const copy = document.createElement("button"); copy.type = "button"; copy.className = "wide"; copy.textContent = "設定をコピー";
  copy.addEventListener("click", async () => {
    const f = (v) => Number(v).toFixed(3);
    const lines = ["カメレオンの調整値", "", "【曇り】", ...HAZE.map(([label, hd]) => `${label}: ${f(hd.value)}`),
      `臓器の全体の濃さ: ${f(chameleonLook.organs.value)}`];
    for (const [title, list] of parts) {
      lines.push("", `【${title}】`);
      for (const p of list) lines.push(`${p.label}: 濃さ ${f(p.strength.value)} 色 ${hexOf(p.colour.value)}（${p.colour.value.map(f).join(" / ")}）`);
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
  reset.addEventListener("click", () => {
    holders.forEach((hd, i) => { hd.value = structuredClone(defaults[i]); }); refreshers.forEach((r) => r());
    // The start is the first saved look ("規定1024").
    document.querySelectorAll("#ch-look button").forEach((x, i) => x.setAttribute("aria-pressed", String(i === 0)));
  });
  panel.append(copy, reset);

  // The saved looks, one click each (C record 55), along the top left.
  if (stain === "06") {
    const looks = document.createElement("div"); looks.id = "ch-look"; looks.setAttribute("aria-label", "保存した見え方");
    const label = document.createElement("span"); label.textContent = "見え方"; looks.append(label);
    const buttons = LOOKS.map(([name, look], i) => {
      const b = document.createElement("button"); b.type = "button"; b.textContent = name; b.setAttribute("aria-pressed", String(i === 0));
      b.addEventListener("click", () => {
        setChameleonLook(look); refreshers.forEach((r) => r());
        for (const other of buttons) other.setAttribute("aria-pressed", String(other === b));
      });
      looks.append(b);
      return b;
    });
    looks.addEventListener("keydown", (e) => e.stopPropagation());
    document.body.append(looks);
  }

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
