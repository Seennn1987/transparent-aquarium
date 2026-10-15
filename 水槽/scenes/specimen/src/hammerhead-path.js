import { HH_PROFILE } from "./hammerhead-profile.js";

// シロシュモクザメの体の中心線と、器の中を回る道すじ（C2、2026-10-15）。three.js にも URL にも頼らない（tests/hammerhead-circle.mjs が node で読む）。
//  座標は glTF の標本（m）: x 吻端→尾、y 背+、z 体の左+。泳ぎの曲げは背の軸（+Y）のまわり。
//  体の向きの角 a(s)（+Y まわり、体の軸の向きは (cos a, 0, −sin a)）= うねり（B3）+ 旋回の曲げ（B4）。hammerhead-swim.js も骨をこの角で回す。
export const HH_BODY = {
  length: 1.024,       // 全長（m）、b1_rig.py の尾の骨の終わり
  neck: 0.125,         // 首（頭の骨だけの終わり、m）。旋回の曲げはここから
  turnRadius: 0.374,   // 出典のふだんの旋回の半径（全長に対して、Hoffmann & Porter 2019 のボンネットヘッド）。turn = 1 の曲がり
  // 泳ぐ速さ: 1 回の尾の振りで 0.64 L 進む（Webb & Keyes 1982 のボンネットヘッド）× 尾の振り 1.25 Hz = 0.8 L/s
  stride: 0.64,
};

/** 吻端からの長さ s（m）での体の向きの角（rad）。cycles は尾の振りの回数で数えた時刻。 */
export function bodyAngle(s, cycles, { amplitude, wavelength, turn = 0, turnBend = 0.5 }) {
  const L = HH_BODY.length, At = amplitude * L, k = 2 * Math.PI / (wavelength * L);
  const A = At * (0.15 + 0.85 * (s / L) ** 2), dA = At * 0.85 * 2 * s / (L * L);
  const ph = k * s - 2 * Math.PI * cycles;
  return Math.atan(dA * Math.sin(ph) + A * k * Math.cos(ph)) + turn * turnBend * Math.max(s - HH_BODY.neck, 0) / (HH_BODY.turnRadius * L);
}

/** 吻端の横のずれ（m、+ で体の右 = −z）。頭の付け根で回すだけだと吻端が止まるので、y(0) だけずらす（B3）。 */
export function snoutShift(cycles, { amplitude }) {
  return amplitude * HH_BODY.length * 0.15 * Math.sin(-2 * Math.PI * cycles);
}

/** 体の中心線（標本の座標、m）: 吻端から向きの角を積んだ点。{ s, x, z, a } の配列（step ごと）。 */
export function centreline(cycles, opts, step = 0.01) {
  const pts = [];
  let x = 0, z = -snoutShift(cycles, opts);
  for (let s = 0; s <= HH_BODY.length + 1e-9; s += step) {
    const a = bodyAngle(s + step / 2, cycles, opts);
    pts.push({ s, x, z, a });
    x += Math.cos(a) * step; z -= Math.sin(a) * step;
  }
  return pts;
}

const lerpProfile = (key, s) => {
  const v = HH_PROFILE[key], f = s / HH_PROFILE.step, i = Math.max(0, Math.min(v.length - 2, Math.floor(f))), t = Math.min(Math.max(f - i, 0), 1);
  return v[i] * (1 - t) + v[i + 1] * t;
};
export const halfWidthAt = (s) => lerpProfile("halfWidth", s);
export const HH_HEIGHT = { top: Math.max(...HH_PROFILE.top), bottom: Math.min(...HH_PROFILE.bottom) };

/** 水平の向き v（x, z）の角（体の向きの角と同じ数え方: v = (cos φ, −sin φ)）。 */
const angleOf = (vx, vz) => Math.atan2(-vz, vx);

/**
 * 器の中を回る道すじ: 体の真ん中（s = L/2）が、器の軸を中心とする半径 radius（器の単位）の円の上を、反時計回り（上から見て）に進む。
 * 真ん中の体の向きが道すじの向きにそろう。曲がりは道すじの円の半径から（turn = 出典の旋回の半径 / 道すじの半径、体の右へ）。
 * scale: 器の単位 / m。時刻 time（秒）→ 器の中の姿: 標本の点 p（m）は、器の座標で centre + R_yaw(scale (p − mid)) + 円の上の点。
 */
export function circlePose(time, cycles, { radius, scale, swim }) {
  const L = HH_BODY.length;
  const turn = Math.min(HH_BODY.turnRadius * L * scale / radius, 1);
  const opts = { ...swim, turn };
  const pts = centreline(cycles, opts);
  const mid = pts[Math.round(pts.length / 2)];
  const speed = HH_BODY.stride * L * scale * (swim.frequency ?? 1.25);   // 器の単位 / 秒
  const theta = speed * time / radius;
  const at = { x: radius * Math.cos(theta), z: radius * Math.sin(theta) };
  // 進む向き（反時計回り）と、標本の前（−体の軸の向き）
  const travel = angleOf(-Math.sin(theta), Math.cos(theta));
  const forward = angleOf(-Math.cos(mid.a), Math.sin(mid.a));
  return { turn, opts, pts, mid, at, yaw: travel - forward, theta };
}

/** 体の外形（中心線 ± 半幅）の点を、器の座標（水平、器の軸から）に置いたときの、軸からいちばん遠い距離。 */
export function farthestFromAxis(pose, scale) {
  const c = Math.cos(pose.yaw), s = Math.sin(pose.yaw);
  let far = 0;
  for (const p of pose.pts) {
    const w = halfWidthAt(p.s), nx = Math.sin(p.a), nz = Math.cos(p.a);   // 体の左（+z）へ向く横の向き
    for (const side of [1, -1]) {
      const lx = (p.x + side * w * nx - pose.mid.x) * scale, lz = (p.z + side * w * nz - pose.mid.z) * scale;
      const wx = pose.at.x + lx * c + lz * s, wz = pose.at.z - lx * s + lz * c;
      far = Math.max(far, Math.hypot(wx, wz));
    }
  }
  return far;
}

/**
 * 器（内側の半径 inner、器の単位）と空き clearance の中で回れる、いちばん大きい道すじの半径。
 * 1 周の尾の振りの位相をいくつか見て、体のどこも壁から clearance より近づかない。出典の旋回の半径より小さくはしない（null: 回れない）。
 */
export function fitCircle({ inner, clearance, scale, swim, phases = 64, margin = 0.002 }) {
  const L = HH_BODY.length, minR = HH_BODY.turnRadius * L * scale;
  const ok = (r) => {
    for (let i = 0; i < phases; i++) {
      const pose = circlePose(0, i / phases, { radius: r, scale, swim });
      if (farthestFromAxis(pose, scale) > inner - clearance - margin) return false;   // 位相の間の分の余裕（16 位相では 1 周の間に空きが 0.119 になった）
    }
    return true;
  };
  if (!ok(minR)) return null;
  let lo = minR, hi = inner;
  for (let k = 0; k < 40; k++) { const m = (lo + hi) / 2; if (ok(m)) lo = m; else hi = m; }
  return lo;
}

/**
 * 器（内側の半径 radius、液の深さ depth、器の単位）に、回らずに真ん中で泳ぐときに入るいちばん大きい縮尺（器の単位 / m）: 吻端〜尾（尾の振れ tailSwing L を含む）が
 * 壁から、背〜腹が底と液面から clearance 離れる（C1 の大きさ。器の直径の倍率 1）。
 */
export function dishBaseScale({ radius, depth, clearance, tailSwing = 0.09 }) {
  const L = HH_BODY.length;
  return Math.min((radius - clearance) / Math.hypot(L / 2, tailSwing * L), (depth - 2 * clearance) / (HH_HEIGHT.top - HH_HEIGHT.bottom));
}

