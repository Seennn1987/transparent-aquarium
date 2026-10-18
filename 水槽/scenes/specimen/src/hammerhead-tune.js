import { chameleonLook } from "./chameleon-material.js";
import { HH_CHANNELS, hhColorLook, hhStainMix, stainToChannel } from "./hammerhead-lightbox.js";
import { hhPartLook, hhPartHaze, hhOrganColor, mottleLook, gillRayLook, visceraLook, HH_ORGAN_MIX, organMixToColor } from "./hammerhead-material.js";
import { HH_LIGHTBOX } from "./hammerhead-stain.js";

// シロシュモクザメの調整の欄（2026-10-15、プロデューサー「骨、内臓、軟骨、肉など、パーツ種別ごとに色や濃さを調整できるようにしたいです。調整パネルを作成して下さい」）。
//  種別ごとに「色」と「濃さ」。色は、その種別のふつうの厚み（hammerhead-lightbox.js の ref）を通ったライトボックスの光の色で見せ、選ぶと
//  その厚みでその色になる吸い方に置きかえる。濃さは吸い方の倍率（1 が既定）。値はこの画面の中だけで、ブラウザに覚えさせる（localStorage）。
//  決めた値は「値をコピー」で取り出して、コードの既定に入れる。
// 2026-10-17 直し（プロデューサー「着色剤の種類はある程度決まっているわけで、色編集パレットは完全自由な色使いではなくて、それをベースに色を選べるようにして」）:
//  色は自由に選ばず、染料の量（赤紫 = アリザリンレッド S、青 = アルシアンブルー、無色 = 染まらない組織の濁り、黄ばみ = 2026-10-17 足した組織の淡い黄。hammerhead-lightbox.js の HH_STAIN_T）を
//  動かして決める。色見本（四角）はその種別のふつうの厚みを通った光の色で、見るだけ。内臓も同じ 3 つの量（色見本の厚み 40 mm）
const STORE = "hh-tune-v4";
// 2026-10-18: 内臓の色（hhOrganColor）は glb を読んでから作られるので、ここでは HH_ORGAN_MIX の部品で作る（前は空になり、内臓の量のつまみが値を覚えなかった）
const organMix = Object.fromEntries(Object.keys(HH_ORGAN_MIX ?? {}).map((k) => [k, [...HH_ORGAN_MIX[k]]]));
const setMix = (c, m) => { hhStainMix[c.key] = [...m]; const r = stainToChannel(c, m), L = hhColorLook[c.key]; L.spectrum.value.set(...r.spectrum); L.gain.value = r.gain; L.density.value = 1; };
const setOrganMix = (k, m) => { organMix[k] = [...m]; hhOrganColor[k]?.value.set(...organMixToColor(m, visceraLook.amount.value)); };
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
    { channel: "spine", note: "椎骨（CT の殻と椎体）。石灰化している" },
    { channel: "head", note: "頭骨と顎。成魚では軟骨の表面が石灰化した小板で覆われる" },
    { channel: "teeth", note: "石灰化している" }, { channel: "gill" },
    { channel: "fin", note: "胸びれ・背びれ・臀びれ・尾・肩帯・腰帯の軟骨（CT に写る）。ひれごとの濃さは下の「部品ごと」" },
    { channel: "pelvic" },
    { channel: "uncal", note: "弓・肋骨・尾びれの鰭条（形は図と文献から）" },
  ]],
  ["肉・膜", [
    { channel: "skin", note: "体の組織（胴・ひれの膜）。透明にして染まらない。にごり度もこの色で吸う" },
  ]],
  ["内臓（透明にした組織、ふつうは染まらない）", [{ organ: "Liver", label: "肝臓" }, { organ: "Gut", label: "消化管" }, { organ: "Spiral", label: "らせん弁" }, { organ: "Heart", label: "心臓" }]],
  // 2026-10-17 プロデューサー「今、ヒレごとの色の濃さを調整できません。特に背鰭がずっと透明です。」「各パーツごとににごり度を調整できるようにして」:
  //  部品ごとに 濃さ（その層の色の吸い方の倍率）と にごり度（体の組織と同じ吸い方を、通り道 × にごり度だけ足す）
  ["部品ごとの濃さ・にごり度", [
    ...[["Bone", "背骨の殻（CT）"], ["Centrum", "椎体"], ["Arch", "弓"], ["Rib", "肋骨"], ["CaudalRay", "尾びれの鰭条"],
      ["HeadCartilage", "頭骨"], ["Jaw", "顎"], ["Teeth", "歯"], ["Gill", "エラの骨"],
      ["Cartilage", "肩帯・腰帯・尾の軟骨"], ["PectCartilage", "胸びれの軟骨"], ["Dorsal1Cartilage", "第 1 背びれの軟骨"], ["Dorsal2Cartilage", "第 2 背びれの軟骨"],
      ["AnalCartilage", "臀びれの軟骨"], ["PelvicCartilage", "腹びれの軟骨"]].map(([k, label]) => ({ partrow: k, label, max: 5 })),
    ...[["Skin", "体の膜"], ["PectSkin", "胸びれの膜"], ["Dorsal1Skin", "第 1 背びれの膜"], ["Dorsal2Skin", "第 2 背びれの膜"], ["AnalSkin", "臀びれの膜"], ["PelvicSkin", "腹びれの膜"]]
      .map(([k, label]) => ({ partrow: k, label, max: 30 })),   // 膜は数 mm と薄く、肉の色（80 mm の胴に合わせた）では 3 倍でもほとんど見えない
    ...[["Liver", "肝臓"], ["Gut", "消化管"], ["Spiral", "らせん弁"], ["Heart", "心臓"]].map(([k, label]) => ({ partrow: k, label, max: 5 })),
  ]],
  ["表面の模様", [
    { look: chameleonLook.film, key: "dent", label: "皮歯", max: 3 }, { look: mottleLook.amount, key: "mottle", label: "まだら", max: 2 },
    { look: gillRayLook.amount, key: "rays", label: "鰓条", max: 5 }, { look: visceraLook.amount, key: "visc", label: "内臓ぜんぶ", max: 5 },
  ]],
];

function snapshot() {
  return {
    channels: Object.fromEntries(HH_CHANNELS.map((c) => { const L = hhColorLook[c.key]; return [c.key, { spectrum: L.spectrum.value.toArray().map((v) => +v.toFixed(4)), gain: +L.gain.value.toFixed(3), density: +L.density.value.toFixed(3) }]; })),
    parts: Object.fromEntries(Object.entries(hhPartLook).map(([k, v]) => [k, +v.value.toFixed(3)])),
    haze: Object.fromEntries(Object.entries(hhPartHaze).map(([k, v]) => [k, +v.value.toFixed(3)])),
    organs: Object.fromEntries(Object.entries(hhOrganColor).map(([k, v]) => [k, v.value.toArray().map((x) => +x.toFixed(4))])),
    looks: Object.fromEntries(GROUPS.flatMap(([, rows]) => rows.filter((r) => r.look).map((r) => [r.key, +r.look.value.toFixed(3)]))),
    mix: Object.fromEntries(Object.entries(hhStainMix).map(([k, m]) => [k, m && m.map((v) => +v.toFixed(3))])),
    organMix: Object.fromEntries(Object.entries(organMix).map(([k, m]) => [k, m && m.map((v) => +v.toFixed(3))])),
  };
}
function restore(s) {
  for (const [k, v] of Object.entries(s.channels ?? {})) if (hhColorLook[k]) { hhColorLook[k].spectrum.value.set(...v.spectrum); hhColorLook[k].gain.value = v.gain; hhColorLook[k].density.value = v.density; }
  for (const [k, v] of Object.entries(s.parts ?? {})) if (hhPartLook[k]) hhPartLook[k].value = v;
  for (const [k, v] of Object.entries(s.haze ?? {})) if (hhPartHaze[k]) hhPartHaze[k].value = v;
  for (const [k, v] of Object.entries(s.organs ?? {})) if (hhOrganColor[k]) hhOrganColor[k].value.set(...v);
  for (const [, rows] of GROUPS) for (const r of rows) if (r.look && s.looks?.[r.key] != null) r.look.value = s.looks[r.key];
  for (const [k, m] of Object.entries(s.mix ?? {})) { const c = HH_CHANNELS.find((x) => x.key === k); if (c && m) setMix(c, m); else if (c) hhStainMix[k] = null; }
  for (const [k, m] of Object.entries(s.organMix ?? {})) { if (m && k in organMix) setOrganMix(k, m); else if (k in organMix) organMix[k] = null; }
}
const DEFAULTS = {};   // 欄を作るときの値（既定）

/** 欄を出さずに、ブラウザが覚えている値だけを当てる（ギャラリーの器の中のシュモクザメ。2026-10-17 から） */
export function applySavedHammerheadTune() {
  try { const saved = JSON.parse(localStorage.getItem(STORE) ?? "null"); if (saved) restore(saved); return Boolean(saved); } catch { return false; }
}

// 2026-10-17 直し（プロデューサー「色の調整をしたいので、以前作った色のパネルを表示して。必要であればパネルの機能改善もして」）:
//  上の帯: 「既定と見比べる」（押している間だけ既定の値で描く）、「止める／動かす」、向き（背中・横・腹・展示。欄を開いたまま読み直す）、「左へ／右へ」（欄の置き場）。
//  行: 既定から変えた行は名前の前に ● が付く。名前をダブルクリックすると、その行だけ既定に戻る。見出しをクリックすると、その組をたたむ。
//  ギャラリー（?specimen=hammerhead の前の台）も、この欄で覚えた値で描く（specimen-hammerhead.js が applySavedHammerheadTune を呼ぶ）
export function installHammerheadTune({ open = false, page = null } = {}) {
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
    #hh-tune textarea { width: 100%; height: 120px; font: 11px monospace; margin-top: 6px; display: none; }
    #hh-tune.left { right: auto; left: 12px; }
    #hh-tune .bar { position: sticky; top: -10px; background: rgba(255,255,255,.97); margin: -10px -12px 6px; padding: 8px 12px 6px; border-bottom: 1px solid #ddd; display: flex; gap: 4px; flex-wrap: wrap; z-index: 1; }
    #hh-tune .bar button { padding: 3px 8px; font-size: 12px; }
    #hh-tune .bar button.on { background: #222; color: #fff; }
    #hh-tune h3 { cursor: pointer; user-select: none; }
    #hh-tune h3::before { content: "▾ "; color: #999; }
    #hh-tune h3.folded::before { content: "▸ "; }
    #hh-tune .name { cursor: default; }
    #hh-tune .name.changed::before { content: "● "; color: #d35400; }
    #hh-tune .row.stainrow { grid-template-columns: 1fr 44px; margin-top: 8px; }
    #hh-tune .swatch { display: inline-block; width: 40px; height: 18px; border: 1px solid #aaa; border-radius: 3px; }
    #hh-tune .stains { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px 14px; margin: 1px 0 2px; }
    #hh-tune .stain { display: grid; grid-template-columns: 34px 1fr; grid-template-rows: auto auto; font-size: 11px; align-items: center; }
    #hh-tune .stain input[type=range] { width: 100%; grid-column: 1 / -1; }
    #hh-tune .stains.two { grid-template-columns: repeat(2, 1fr); }
    #hh-tune .stain .val { grid-row: 1; grid-column: 2; font-size: 11px; }
    #hh-tune .stain.r span:first-child { color: #b03060; } #hh-tune .stain.b span:first-child { color: #1f8fbf; } #hh-tune .stain.n span:first-child { color: #888; } #hh-tune .stain.y span:first-child { color: #b08a00; }`;
  document.head.append(css);
  const btn = document.createElement("button"); btn.id = "hh-tune-btn"; btn.type = "button"; btn.textContent = "調整";
  const panel = document.createElement("aside"); panel.id = "hh-tune"; panel.setAttribute("aria-label", "色と濃さの調整");
  panel.style.display = open ? "block" : "none";
  btn.onclick = () => { panel.style.display = panel.style.display === "none" ? "block" : "none"; };
  // 上の帯
  const bar = document.createElement("div"); bar.className = "bar";
  const mk = (label, title) => { const b = document.createElement("button"); b.type = "button"; b.textContent = label; if (title) b.title = title; bar.append(b); return b; };
  const cmp = mk("既定と見比べる", "押している間だけ、既定の値で描く");
  let held = null;
  const down = (e) => { e.preventDefault(); if (held) return; held = snapshot(); restore(DEFAULTS); cmp.classList.add("on"); };
  const up = () => { if (!held) return; restore(held); held = null; cmp.classList.remove("on"); };
  cmp.addEventListener("pointerdown", down); for (const ev of ["pointerup", "pointerleave", "pointercancel"]) cmp.addEventListener(ev, up);
  if (page) {
    const pz = mk(page.paused ? "動かす" : "止める", "泳ぎ・口・心臓を止める（Space でも同じ）");
    pz.onclick = () => { page.setPaused(!page.paused); pz.textContent = page.paused ? "動かす" : "止める"; };
  }
  const Q = new URLSearchParams(location.search);
  for (const [label, v] of [["背中", "top"], ["横", "side"], ["腹", "below"], ["展示", ""]]) {
    const b = mk(label, "この向きで読み直す（欄は開いたまま、値はそのまま）");
    if ((Q.get("view") ?? "") === v) b.classList.add("on");
    b.onclick = () => { const q = new URLSearchParams(location.search); if (v) q.set("view", v); else q.delete("view"); q.set("tune", "1"); location.search = q.toString(); };
  }
  const side = mk("左へ", "欄を画面の左右に移す");
  const setSide = (left) => { panel.classList.toggle("left", left); side.textContent = left ? "右へ" : "左へ"; try { localStorage.setItem(STORE + "-side", left ? "left" : "right"); } catch {} };
  side.onclick = () => setSide(!panel.classList.contains("left"));
  try { if (localStorage.getItem(STORE + "-side") === "left") setSide(true); } catch {}
  panel.append(bar);
  const head = document.createElement("div");
  head.innerHTML = "<b>色と濃さの調整</b><div style='font-size:11px;color:#777'>色は染料の量で決める: 赤紫 = アリザリンレッド S（石灰化した組織）、青 = アルシアンブルー（軟骨）、無色 = 染まらない組織の濁り、黄ばみ = 脱色の足りない組織や古くなった標本の淡い黄（染料ではない）。四角 = その種別のふつうの厚みを通った光の色。この画面だけの値で、ブラウザが覚えます（ギャラリーの器の中も同じ値）。● = 既定から変えた行。名前をダブルクリックでその行だけ既定に戻る。</div>";
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
    c.oninput = () => { set(c.value); save(); refreshAll(); };
    refreshers.push(sync); sync(); return c;
  };
  const refreshAll = () => refreshers.forEach((f) => f());
  for (const [title, rows] of GROUPS) {
    const h = document.createElement("h3"); h.textContent = title; panel.append(h);
    h.onclick = () => { const f = h.classList.toggle("folded"); panel.querySelectorAll(`.row[data-group="${title}"]`).forEach((e) => { e.style.display = f ? "none" : ""; }); };
    for (const r of rows) {
      const row = document.createElement("div"); row.className = "row"; row.dataset.group = title;
      const name = document.createElement("span"); name.className = "name"; name.title = "ダブルクリックで、この行を既定に戻す";
      const cur = () => snapshot(), key = r.channel ? ["mix", r.channel] : r.part ? ["parts", r.part] : r.partrow ? ["parts", r.partrow] : r.organ ? ["organMix", r.organ] : ["looks", r.key];
      const isChanged = () => { const c = cur(), a = c[key[0]]?.[key[1]], b = DEFAULTS[key[0]]?.[key[1]]; return JSON.stringify(a) !== JSON.stringify(b) || Boolean(r.partrow && c.haze[r.partrow] !== DEFAULTS.haze[r.partrow]); };
      refreshers.push(() => name.classList.toggle("changed", isChanged()));
      name.ondblclick = () => {
        const one = { channels: {}, parts: {}, haze: {}, organs: {}, looks: {}, mix: {}, organMix: {} };
        if (r.partrow) one.haze[r.partrow] = DEFAULTS.haze[r.partrow];
        if (r.channel) one.channels[r.channel] = DEFAULTS.channels[r.channel];
        if (r.organ) one.organs[r.organ] = DEFAULTS.organs[r.organ];
        one[key[0]][key[1]] = DEFAULTS[key[0]][key[1]];
        restore(one); save(); refreshAll();
      };
      if (r.channel || r.organ) {
        const c = r.channel && HH_CHANNELS.find((x) => x.key === r.channel);
        if (r.organ && !hhOrganColor[r.organ]) continue;
        name.textContent = r.channel ? c.label : r.label;
        const sw = document.createElement("span"); sw.className = "swatch"; sw.title = "その種別のふつうの厚みを通った光の色（見るだけ）";
        refreshers.push(() => { sw.style.background = r.channel ? channelColor(c) : organColor(r.organ); });
        row.classList.add("stainrow"); row.append(name, sw);
        const st = document.createElement("div"); st.className = "stains";
        const getM = () => (r.channel ? hhStainMix[c.key] : organMix[r.organ]) ?? [0, 0, 0, 0];
        const setM = (m) => (r.channel ? setMix(c, m) : setOrganMix(r.organ, m));
        for (const [i, lab, cls] of [[0, "赤紫", "r"], [1, "青", "b"], [2, "無色", "n"], [3, "黄ばみ", "y"]]) {
          const cell = document.createElement("label"); cell.className = "stain " + cls; cell.title = ["アリザリンレッド S（カルシウムに付く。石灰化した組織）", "アルシアンブルー（軟骨の基質に付く）", "染まらない組織の濁り", "黄ばみ（脱色の足りない組織・脂・古くなった標本。奥の青が緑寄りに見える）"][i];
          const t = document.createElement("span"); t.textContent = lab;
          const [rr, vv] = slider(0, 3, 0.05, () => getM()[i] ?? 0, (v) => { const m = [...getM()]; m[i] = v; setM(m); });
          cell.append(t, rr, vv); st.append(cell);
        }
        panel.append(row); row.dataset.group = title;
        st.dataset.group = title; st.classList.add("row"); panel.append(st);
        if (r.note) { const n = document.createElement("div"); n.className = "row"; n.dataset.group = title; const t = document.createElement("span"); t.className = "note"; t.textContent = r.note; n.append(t); panel.append(n); }
        continue;
      } else if (r.partrow) {
        if (!hhPartLook[r.partrow]) continue;
        name.textContent = r.label; row.classList.add("stainrow"); row.append(name, document.createElement("span"));
        const st = document.createElement("div"); st.className = "stains two"; st.dataset.group = title; st.classList.add("row");
        for (const [lab, max, get, set, tip] of [["濃さ", r.max, () => hhPartLook[r.partrow].value, (v) => { hhPartLook[r.partrow].value = v; }, "その層の色の吸い方の倍率（1 が既定の色見本どおり）"],
          ["にごり", 50, () => hhPartHaze[r.partrow].value, (v) => { hhPartHaze[r.partrow].value = v; }, "体の組織と同じ吸い方を、通り道 × この値だけ足す（1 で体の組織と同じ濁り。薄い部品は大きくしないと見えない）"]]) {
          const cell = document.createElement("label"); cell.className = "stain"; cell.title = tip;
          const t = document.createElement("span"); t.textContent = lab;
          const [rr, vv] = slider(0, max, 0.01, get, set); cell.append(t, rr, vv); st.append(cell);
        }
        panel.append(row, st); continue;
      } else if (r.part) {
        if (!hhPartLook[r.part]) continue;
        name.textContent = r.label;
        row.append(name, document.createElement("span"), ...slider(0, r.max ?? 4, 0.01, () => hhPartLook[r.part].value, (v) => { hhPartLook[r.part].value = v; }));
      } else if (r.look) {
        name.textContent = r.label;
        row.append(name, document.createElement("span"), ...slider(0, r.max ?? 3, 0.01, () => r.look.value, (v) => { r.look.value = v; }));
      }
      panel.append(row);
      if (r.note) { const n = document.createElement("div"); n.className = "row"; n.dataset.group = title; const t = document.createElement("span"); t.className = "note"; t.textContent = r.note; n.append(t); panel.append(n); }
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
  refreshAll();
  return { panel, snapshot, restore, defaults: DEFAULTS };
}
