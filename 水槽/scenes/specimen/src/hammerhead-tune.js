import { chameleonLook } from "./chameleon-material.js";
import { HH_CHANNELS, hhColorLook } from "./hammerhead-lightbox.js";
import { hhPartLook, hhOrganColor, mottleLook, gillRayLook, visceraLook } from "./hammerhead-material.js";
import { HH_LIGHTBOX } from "./hammerhead-stain.js";

// シロシュモクザメの調整の欄（2026-10-15、プロデューサー「骨、内臓、軟骨、肉など、パーツ種別ごとに色や濃さを調整できるようにしたいです。調整パネルを作成して下さい」）。
//  種別ごとに「色」と「濃さ」。色は、その種別のふつうの厚み（hammerhead-lightbox.js の ref）を通ったライトボックスの光の色で見せ、選ぶと
//  その厚みでその色になる吸い方に置きかえる。濃さは吸い方の倍率（1 が既定）。値はこの画面の中だけで、ブラウザに覚えさせる（localStorage）。
//  決めた値は「値をコピー」で取り出して、コードの既定に入れる。
const STORE = "hh-tune-v1";
const T0 = chameleonLook.boneT0;
const eff = (c) => (c.sat ? T0.value * (1 - Math.exp(-c.ref / T0.value)) : c.ref);
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const toHex = (rgb) => "#" + rgb.map((v) => Math.round(clamp(v, 0, 1) * 255).toString(16).padStart(2, "0")).join("");
const fromHex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);

function channelColor(c) {
  const L = hhColorLook[c.key], s = L.spectrum.value, g = L.gain.value, e = eff(c);
  return toHex([s.x, s.y, s.z].map((v, i) => HH_LIGHTBOX[i] * Math.exp(-g * v * e)));
}
function setChannelColor(c, hex) {
  const T = fromHex(hex).map((v, i) => clamp(v / HH_LIGHTBOX[i], 0.003, 0.999)), A = T.map((v) => -Math.log(v)), top = Math.max(...A);
  const L = hhColorLook[c.key]; L.spectrum.value.set(...A.map((v) => v / top)); L.gain.value = top / eff(c);
}
const ORGAN_REF = 0.04;   // 内臓の色見本の厚み（m）
const organColor = (k) => { const c = hhOrganColor[k].value, a = visceraLook.amount.value * 7.5 * ORGAN_REF; return toHex([c.x, c.y, c.z].map((v, i) => HH_LIGHTBOX[i] * Math.exp(-a * v))); };
const setOrganColor = (k, hex) => { const a = visceraLook.amount.value * 7.5 * ORGAN_REF; hhOrganColor[k].value.set(...fromHex(hex).map((v, i) => -Math.log(clamp(v / HH_LIGHTBOX[i], 0.003, 0.999)) / a)); };

// 欄に出す種別（順に）。color: 色の層、part: 部品の濃さだけ、organ: 内臓、look: 模様の強さ
const GROUPS = [
  ["骨・軟骨", [
    { channel: "spine", note: "椎骨（CT の殻・椎体・弓）。石灰化してアリザリンで赤紫" },
    { part: "Centrum", label: "　椎体（背骨の中の濃さ）", max: 5 }, { part: "Arch", label: "　弓（背骨の中の濃さ）", max: 5 },
    { channel: "head", note: "頭骨（厚い軟骨、アルシアンで青）" },
    { channel: "jaw" }, { channel: "teeth" }, { channel: "gill" },
    { channel: "fin", note: "胸びれ・背びれ・尾・肩帯・腰帯の放射軟骨" },
    { channel: "pelvic" },
  ]],
  ["肉・膜", [
    { channel: "skin", note: "体の組織（胴・胸びれの膜）" },
    { part: "PelvicSkin", label: "腹びれの膜（肉の色の濃さ）", max: 30 },   // 膜は数 mm と薄く、肉の色（80 mm の胴に合わせた）では 3 倍でもほとんど見えない
  ]],
  ["内臓", [{ organ: "Liver", label: "肝臓" }, { organ: "Gut", label: "消化管" }, { organ: "Spiral", label: "らせん弁" }, { organ: "Heart", label: "心臓" }]],
  ["表面の模様", [
    { look: chameleonLook.film, key: "dent", label: "皮歯", max: 3 }, { look: mottleLook.amount, key: "mottle", label: "まだら", max: 2 },
    { look: gillRayLook.amount, key: "rays", label: "鰓条", max: 5 }, { look: visceraLook.amount, key: "visc", label: "内臓ぜんぶ", max: 5 },
  ]],
];

function snapshot() {
  return {
    channels: Object.fromEntries(HH_CHANNELS.map((c) => { const L = hhColorLook[c.key]; return [c.key, { spectrum: L.spectrum.value.toArray().map((v) => +v.toFixed(4)), gain: +L.gain.value.toFixed(3), density: +L.density.value.toFixed(3) }]; })),
    parts: Object.fromEntries(Object.entries(hhPartLook).map(([k, v]) => [k, +v.value.toFixed(3)])),
    organs: Object.fromEntries(Object.entries(hhOrganColor).map(([k, v]) => [k, v.value.toArray().map((x) => +x.toFixed(4))])),
    looks: Object.fromEntries(GROUPS.flatMap(([, rows]) => rows.filter((r) => r.look).map((r) => [r.key, +r.look.value.toFixed(3)]))),
  };
}
function restore(s) {
  for (const [k, v] of Object.entries(s.channels ?? {})) if (hhColorLook[k]) { hhColorLook[k].spectrum.value.set(...v.spectrum); hhColorLook[k].gain.value = v.gain; hhColorLook[k].density.value = v.density; }
  for (const [k, v] of Object.entries(s.parts ?? {})) if (hhPartLook[k]) hhPartLook[k].value = v;
  for (const [k, v] of Object.entries(s.organs ?? {})) if (hhOrganColor[k]) hhOrganColor[k].value.set(...v);
  for (const [, rows] of GROUPS) for (const r of rows) if (r.look && s.looks?.[r.key] != null) r.look.value = s.looks[r.key];
}
const DEFAULTS = {};   // 欄を作るときの値（既定）

export function installHammerheadTune({ open = false } = {}) {
  Object.assign(DEFAULTS, snapshot());
  try { const saved = JSON.parse(localStorage.getItem(STORE) ?? "null"); if (saved) restore(saved); } catch {}
  const save = () => { try { localStorage.setItem(STORE, JSON.stringify(snapshot())); } catch {} };

  const css = document.createElement("style");
  css.textContent = `
    #hh-tune-btn { position: fixed; z-index: 1001; right: 12px; top: 12px; font: 13px system-ui, sans-serif; padding: 6px 12px; border: 1px solid #999; border-radius: 6px; background: #fff; cursor: pointer; }
    #hh-tune { position: fixed; z-index: 1000; right: 12px; top: 48px; bottom: 12px; width: 340px; overflow-y: auto; background: rgba(255,255,255,.94);
      border-radius: 8px; box-shadow: 0 1px 6px rgba(0,0,0,.2); font: 13px/1.35 system-ui, sans-serif; color: #222; padding: 10px 12px; }
    #hh-tune h3 { font-size: 13px; margin: 12px 0 4px; border-bottom: 1px solid #ddd; padding-bottom: 2px; }
    #hh-tune .row { display: grid; grid-template-columns: 1fr 34px 110px 38px; gap: 6px; align-items: center; margin: 3px 0; }
    #hh-tune .note { grid-column: 1 / -1; font-size: 11px; color: #777; margin-top: -2px; }
    #hh-tune input[type=color] { width: 32px; height: 22px; padding: 0; border: 1px solid #aaa; }
    #hh-tune input[type=range] { width: 110px; }
    #hh-tune .val { font-variant-numeric: tabular-nums; text-align: right; }
    #hh-tune .btns { display: flex; gap: 6px; margin-top: 12px; flex-wrap: wrap; }
    #hh-tune button { font: inherit; padding: 4px 10px; border: 1px solid #999; border-radius: 6px; background: #fff; cursor: pointer; }
    #hh-tune textarea { width: 100%; height: 120px; font: 11px monospace; margin-top: 6px; display: none; }`;
  document.head.append(css);
  const btn = document.createElement("button"); btn.id = "hh-tune-btn"; btn.type = "button"; btn.textContent = "調整";
  const panel = document.createElement("aside"); panel.id = "hh-tune"; panel.setAttribute("aria-label", "色と濃さの調整");
  panel.style.display = open ? "block" : "none";
  btn.onclick = () => { panel.style.display = panel.style.display === "none" ? "block" : "none"; };
  const head = document.createElement("div");
  head.innerHTML = "<b>色と濃さの調整</b><div style='font-size:11px;color:#777'>色 = その種別のふつうの厚みを通った光の色。濃さ = 吸い方の倍率（1 が既定）。この画面だけの値で、ブラウザが覚えます。</div>";
  panel.append(head);
  const refreshers = [];
  const slider = (min, max, step, get, set) => {
    const r = document.createElement("input"); r.type = "range"; r.min = min; r.max = max; r.step = step;
    const v = document.createElement("span"); v.className = "val";
    const sync = () => { r.value = get(); v.textContent = (+get()).toFixed(2); };
    r.oninput = () => { set(+r.value); sync(); save(); refreshAll(); };
    refreshers.push(sync); sync(); return [r, v];
  };
  const colorInput = (get, set) => {
    const c = document.createElement("input"); c.type = "color";
    const sync = () => { c.value = get(); };
    c.oninput = () => { set(c.value); save(); };
    refreshers.push(sync); sync(); return c;
  };
  const refreshAll = () => refreshers.forEach((f) => f());
  for (const [title, rows] of GROUPS) {
    const h = document.createElement("h3"); h.textContent = title; panel.append(h);
    for (const r of rows) {
      const row = document.createElement("div"); row.className = "row";
      const name = document.createElement("span");
      if (r.channel) {
        const c = HH_CHANNELS.find((x) => x.key === r.channel); const L = hhColorLook[c.key];
        name.textContent = c.label;
        row.append(name, colorInput(() => channelColor(c), (hex) => setChannelColor(c, hex)), ...slider(0, 10, 0.01, () => L.density.value, (v) => { L.density.value = v; }));
      } else if (r.part) {
        if (!hhPartLook[r.part]) continue;
        name.textContent = r.label;
        row.append(name, document.createElement("span"), ...slider(0, r.max ?? 4, 0.01, () => hhPartLook[r.part].value, (v) => { hhPartLook[r.part].value = v; }));
      } else if (r.organ) {
        if (!hhOrganColor[r.organ]) continue;
        name.textContent = r.label;
        row.append(name, colorInput(() => organColor(r.organ), (hex) => setOrganColor(r.organ, hex)), ...slider(0, 5, 0.01, () => hhPartLook[r.organ].value, (v) => { hhPartLook[r.organ].value = v; }));
      } else if (r.look) {
        name.textContent = r.label;
        row.append(name, document.createElement("span"), ...slider(0, r.max ?? 3, 0.01, () => r.look.value, (v) => { r.look.value = v; }));
      }
      panel.append(row);
      if (r.note) { const n = document.createElement("div"); n.className = "row"; const t = document.createElement("span"); t.className = "note"; t.textContent = r.note; n.append(t); panel.append(n); }
    }
  }
  const btns = document.createElement("div"); btns.className = "btns";
  const out = document.createElement("textarea"); out.readOnly = true;
  const b1 = document.createElement("button"); b1.type = "button"; b1.textContent = "既定に戻す";
  b1.onclick = () => { restore(DEFAULTS); try { localStorage.removeItem(STORE); } catch {} refreshAll(); };
  const b2 = document.createElement("button"); b2.type = "button"; b2.textContent = "値をコピー";
  b2.onclick = async () => { const text = JSON.stringify(snapshot(), null, 1); out.value = text; out.style.display = "block";
    try { await navigator.clipboard.writeText(text); b2.textContent = "コピーしました"; setTimeout(() => { b2.textContent = "値をコピー"; }, 1500); } catch { out.select(); } };
  btns.append(b1, b2); panel.append(btns, out);
  document.body.append(btn, panel);
  return { panel, snapshot, restore };
}
