// ギャラリーのカメラの欄（2026-10-24、プロデューサー「カメラも規定値を設定したいので別パネルを作って、角度・高さ・ズーム具合を設定できるようにして」）。
//  左上の「カメラ」で開く。横の角度（既定の向きから、度）、見下ろす角度（水平から、度）、高さ（カメラと見る点を一緒に上げ下げ）、距離（ズーム）。
//  ドラッグ・ホイール・Shift＋ドラッグ（高さ）で動かしても、欄の値が追いかける。
//  「この位置を既定にする」でブラウザが覚え、次に開いたときからその位置で始まる（標本ごと）。「値をコピー」で取り出してコードの既定（CAMERA_DEFAULTS）に入れる
import * as THREE from "three";

const deg = THREE.MathUtils.radToDeg, rad = THREE.MathUtils.degToRad;
/** コードの既定（標本ごと。無い標本は部屋の既定の視点 DEFAULT_VIEW のまま）。値は { yaw, pitch, height, distance }（度・度・部屋の単位・部屋の単位） */
export const CAMERA_DEFAULTS = {};

const storeKey = (kind) => `gallery-camera-default-${kind}`;
function savedDefault(kind) {
  try { return JSON.parse(localStorage.getItem(storeKey(kind)) ?? "null"); } catch { return null; }
}

/** orbit（orbit.js）の値 ⇔ 欄の値。roomYaw: 既定の横の向き */
const toPanel = (v, roomYaw) => ({ yaw: deg(v.theta - roomYaw), pitch: 90 - deg(v.phi), height: v.height, distance: v.radius });
const toOrbit = (p, roomYaw) => ({ theta: roomYaw + rad(p.yaw), phi: rad(90 - p.pitch), height: p.height, radius: p.distance });

export function installCameraPanel({ habitat, orbit, roomYaw, kind, onChange }) {
  const first = toPanel(orbit.view(), roomYaw);   // 部屋の既定の視点
  const codeDefault = { ...first, ...(CAMERA_DEFAULTS[kind] ?? {}) };
  const current = () => toPanel(orbit.view(), roomYaw);
  const apply = (p) => { orbit.setView(toOrbit(p, roomYaw)); onChange?.(); refresh(); };
  const start = savedDefault(kind) ?? codeDefault;
  orbit.setView(toOrbit(start, roomYaw));

  const L = orbit.limits;
  const fin = (v, fallback) => (Number.isFinite(v) ? v : fallback);
  const rows = [
    ["横の角度", "yaw", "°", deg(fin(L.minAzimuth, roomYaw - Math.PI) - roomYaw), deg(fin(L.maxAzimuth, roomYaw + Math.PI) - roomYaw), 0.5, "既定の向き（部屋の奥の壁に正対）から。＋で左から回り込む"],
    ["見下ろす角度", "pitch", "°", 90 - deg(L.maxPolar), 90 - deg(L.minPolar), 0.5, "水平から下へ見る角度"],
    ["高さ", "height", "", fin(L.minHeight, -2), fin(L.maxHeight, 3), 0.01, "カメラと見る点を一緒に上げ下げする（Shift を押しながら上下にドラッグでも）"],
    ["距離（ズーム）", "distance", "", L.minDistance, L.maxDistance, 0.05, "見る点までの距離。小さいほど寄る（ホイールでも）"],
  ];

  const panel = document.createElement("aside");
  panel.id = "camera-panel";
  panel.setAttribute("aria-label", "カメラ");
  panel.hidden = true;
  const head = document.createElement("div"); head.className = "camera-head";
  const title = document.createElement("h2"); title.textContent = "カメラ";
  const close = document.createElement("button"); close.type = "button"; close.textContent = "閉じる";
  head.append(title, close); panel.append(head);
  const refreshers = [];
  for (const [label, key, unit, min, max, step, tip] of rows) {
    const row = document.createElement("label"); row.className = "camera-row"; row.title = tip;
    const name = document.createElement("span"); name.textContent = label;
    const value = document.createElement("input"); value.type = "number"; value.step = String(step); value.min = String(min); value.max = String(max);
    const range = document.createElement("input"); range.type = "range"; range.min = String(min); range.max = String(max); range.step = String(step);
    const set = (v) => { const p = current(); p[key] = THREE.MathUtils.clamp(+v, min, max); apply(p); };
    range.oninput = () => set(range.value);
    value.onchange = () => set(value.value);
    refreshers.push(() => { const v = current()[key]; range.value = String(v); if (document.activeElement !== value) value.value = v.toFixed(step < 0.1 ? 2 : 1); });
    const top = document.createElement("div"); top.className = "camera-top"; top.append(name, value, document.createTextNode(unit));
    row.append(top, range); panel.append(row);
  }
  const note = document.createElement("p"); note.className = "camera-note"; panel.append(note);
  const showNote = () => { note.textContent = savedDefault(kind) ? "既定: この画面で決めた位置（ブラウザが覚えている）" : "既定: コードの位置"; };
  const btns = document.createElement("div"); btns.className = "camera-buttons";
  const mk = (label, fn) => { const b = document.createElement("button"); b.type = "button"; b.textContent = label; b.onclick = () => fn(b); btns.append(b); return b; };
  mk("この位置を既定にする", (b) => { try { localStorage.setItem(storeKey(kind), JSON.stringify(round(current()))); } catch {} showNote(); flash(b, "既定にしました"); });
  mk("既定に戻す", () => apply(savedDefault(kind) ?? codeDefault));
  mk("コードの既定に戻す", () => { try { localStorage.removeItem(storeKey(kind)); } catch {} showNote(); apply(codeDefault); });
  const out = document.createElement("textarea"); out.readOnly = true; out.hidden = true;
  mk("値をコピー", async (b) => {
    const text = JSON.stringify({ [kind]: round(current()) });
    out.value = text; out.hidden = false;
    try { await navigator.clipboard.writeText(text); flash(b, "コピーしました"); } catch { out.select(); }
  });
  panel.append(btns, out);

  const open = document.createElement("button"); open.type = "button"; open.id = "camera-open"; open.textContent = "カメラ";
  const setOpen = (v) => { panel.hidden = !v; open.hidden = v; if (v) refresh(); };
  open.onclick = () => setOpen(true);
  close.onclick = () => setOpen(false);
  habitat.append(panel, open);

  function refresh() { if (!panel.hidden) for (const f of refreshers) f(); }
  showNote();
  return { refresh, panel };
}

function round(p) { return { yaw: +p.yaw.toFixed(1), pitch: +p.pitch.toFixed(1), height: +p.height.toFixed(2), distance: +p.distance.toFixed(2) }; }
function flash(b, text) { const t = b.textContent; b.textContent = text; setTimeout(() => { b.textContent = t; }, 1500); }
