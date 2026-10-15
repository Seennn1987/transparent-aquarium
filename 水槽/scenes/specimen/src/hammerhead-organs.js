// B5 内臓の時計（シロシュモクザメ、2026-10-15）: 体のうねり・口・心臓・エラの時刻を 1 つの時計で進める。
//  three.js にも URL にも頼らない（tests/hammerhead-organs.mjs が node で読む）。hammerhead-swim.js が毎フレーム update(dt) を呼ぶ。
//  一時停止は dt = 0（時計が止まり、全部が止まる）。強さ hhOrganLook の 0 で、その動きだけ止まる（ほかは動き続ける）。
//  回数（計画書 第 10 節 B2・B5）:
//   尾の振り 1.25 Hz（Webb & Keyes 1982 のボンネットヘッド）
//   口 ±3°・1.25 Hz（尾と同じ、2026-10-15 プロデューサー決定。口の動きの回数の出典は無い）
//   心臓 毎分 37（ドチザメ類の安静時、Scharold et al. 1989）、山で中心へ 12% 縮む
//   エラ 止める（泳いでいる間は開いたまま、Dolce & Wilga 2013。2026-10-15 決定）。動かす案は gillHz > 0、振れ gillAmp（体の横を押し広げる割合）
export const HH_RATES = { tailHz: 1.25, mouthHz: 1.25, mouthDeg: 3, heartBpm: 37, heartSqueeze: 0.12, gillHz: 0, gillAmp: 0.06 };
// 強さ（three.js の uniform と同じ { value } の形。調整パネルや ?heartamt= などから変える）
export const hhOrganLook = { heart: { value: 1 }, mouth: { value: 1 }, gill: { value: 1 } };

/** 心臓の縮み（0〜1）: 拍の位相（回数で数えた時刻）→ 山で 1。(½ + ½ sin)⁴ で、速く縮み、休む間が長い */
export function heartbeat(beats) { return (0.5 + 0.5 * Math.sin(2 * Math.PI * beats)) ** 4; }

export function createHammerheadClock(rates = { ...HH_RATES }) {
  let time = 0;
  const state = { time: 0, tailCycles: 0, mouthDeg: 0, beat: 0, breath: 0 };
  function at(t) {
    state.time = t;
    state.tailCycles = t * rates.tailHz;
    state.mouthDeg = rates.mouthDeg * hhOrganLook.mouth.value * Math.sin(2 * Math.PI * t * rates.mouthHz);
    state.beat = rates.heartBpm > 0 ? rates.heartSqueeze * hhOrganLook.heart.value * heartbeat(t * rates.heartBpm / 60) : 0;
    state.breath = rates.gillHz > 0 ? rates.gillAmp * hhOrganLook.gill.value * Math.sin(2 * Math.PI * t * rates.gillHz) : 0;
    return state;
  }
  return {
    rates, state,
    /** dt 秒だけ進める（一時停止は 0）。 */
    update(dt) { time += dt; return at(time); },
    /** 時刻を決めて、その時刻の姿にする（撮るときの ?phase=）。 */
    at(t) { time = t; return at(t); },
    get time() { return time; },
  };
}
