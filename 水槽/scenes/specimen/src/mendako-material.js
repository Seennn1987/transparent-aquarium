import * as THREE from "three";

// メンダコの透明標本をライトボックスの上に描く（2026-10-24、手順 A4）。
//  シュモクザメ（hammerhead-lightbox.js・hammerhead-material.js）と同じ考え方で、部品ごとの閉じた面の「裏の深さ − 表の深さ」
//  （視線が部品の中を通る長さ）に、その部品の 1 m あたりの赤・緑・青の吸い方を掛けて足す。さらに組織の表面を横切るたびに、
//  表面の染まりの分（1 / |cos| 倍）を足す。合わせた吸い方 a で、ライトボックスの光 × exp(−a) を描く。
//  シュモクザメ・カメレオンのファイルは変えない（CLAUDE.md）。メンダコの色は 1 系統（イカと同じ空色）なので、色の層は分けない。
//
// 色の目標（docs/メンダコ透明標本_計画書_v1.0.md 第 2.4 節。2026-10-17 プロデューサー決定「色は A（イカと同じ空色）」）:
//  イカの実際の標本ページ（docs/mendako/page_gallery_squid_2x_2026-10-17.png、背景 199 / 198.5 / 187）の通し光:
//   ひれの内側（薄い膜）(1300, 840) 0.80 / 0.92 / 0.94、外套の脇（中くらいの厚み）(1382, 960) 0.57 / 0.72 / 0.86、眼 (1374, 1120) 0.25 / 0.55 / 0.60
//  吸い方（−log 通し光）: ひれ 0.223 / 0.083 / 0.062、外套の脇 0.562 / 0.329 / 0.151、眼 1.386 / 0.598 / 0.511
//  表面の分（FILM）: 薄い膜は表と裏の 2 回横切るので、ひれの吸い方の半分を 1 回の表面の分とする: 0.112 / 0.042 / 0.031
//  中を通る分（TISSUE、1 m あたり）: 外套の脇 − 表面 2 回 = 0.339 / 0.246 / 0.089 を、メンダコの頭の丸みを背から通る長さ
//   （頭の頂の高さ 0.406 W × 横幅 138 mm ≈ 56 mm）で割る: 6.05 / 4.39 / 1.59 /m
//  眼球: 径 約 12 mm（0.9 × 0.048 W × 2 × 138 mm）を通って眼の目標になる吸い方: 1.386 / 0.598 / 0.511 ÷ 0.012 = 116 / 50 / 43 /m
//  殻（軟骨）: イカの軟骨は筋肉の 1.4 倍の染まり（specimen-material.js の cartilage 1.4・muscle 1.01）。殻は 1〜2 mm と細いので、
//   画面で見える最小として、腕の付け根の点 (1412, 1180) の吸い方 2.12 / 1.35 / 0.62 を約 6 mm で割った 350 / 225 / 100 /m から始める（手順 A4 で測って直す）
//  顎板: イカの顎板の色（琥珀）。出典の数がないので、画面で見える最小から: 25 / 55 / 120 /m
// 2026-10-24 ページで測って直した（?view=top、1400 × 1050、背景 253 / 247 / 251。計画書 第 7 節 A4）:
//  初めの値で、頭の丸み (560, 690)・(830, 690) 0.56 / 0.73 / 0.85（目標どおり）、薄い膜 (430, 740)・(980, 780) 0.76 / 0.89 / 0.92（少し暗い）、
//  眼 (555, 470)・(845, 470) 0.06 / 0.30 / 0.41（暗すぎ。背からは眼球の上に体の組織も重なる）
//  → 表面の分を 0.8 倍、中を通る分を 1.1 倍（頭の丸みを保つ）、眼を 0.42 倍（体の分 約 0.4 を引いて目標の吸い方 1.39 に）
//  直したあと: 薄い膜 0.79〜0.80 / 0.90〜0.91 / 0.94、頭の丸み 0.57〜0.58 / 0.74 / 0.86（どちらも目標と 0.02 以内）
const Q = new URLSearchParams(location.search);
export const MD_FILM = [0.112 * 0.8, 0.042 * 0.8, 0.031 * 0.8];
const T = 1.1;
export const MD_PARTS = {
  Body: { absorb: [6.05 * T, 4.39 * T, 1.59 * T], film: 1 },
  Suckers: { absorb: [6.05 * T, 4.39 * T, 1.59 * T], film: 1 },
  Cirri: { absorb: [6.05 * T, 4.39 * T, 1.59 * T], film: 1 },
  // 眼: 0.42 倍で (555, 470) 0.17 / 0.44 / 0.59。体の分（頭の丸みの点の吸い方 約 0.55 / 0.30 / 0.15）を引いた眼の分を、目標から体の分を引いた値に
  //  合わせるよう、色ごとに 0.69 / 0.58 / 0.95 倍
  Eye: { absorb: [116 * 0.42 * 0.69, 50 * 0.42 * 0.58, 43 * 0.42 * 0.95], film: 0 },
  Shell: { absorb: [350, 225, 100], film: 0 },
  Beak: { absorb: [25, 55, 120], film: 0 },
  // 中の部品（2026-10-24 手順 A5、blender/mendako/b6_organs.py）。初めの値（ページで見て直す。計画書 第 7 節 A5）:
  //  頭の軟骨: 軟骨の青（イカの腕の付け根の点の比 1 : 0.64 : 0.29）。厚み 0.004 W ≈ 0.55 mm の殻を斜めに通ると数 mm になるので 120 /m から
  //  → ページで頭の真ん中に紺の仮面のように目立ち、中の平衡石が黒く見えたので 0.35 倍、それでも濃い紺だったので 0.2 倍（2026-10-24）
  HeadCartilage: { absorb: [120 * 0.2, 77 * 0.2, 35 * 0.2], film: 0 },
  //  平衡石: 石灰質（Fuentes et al. 2000 でマダコの幼生の平衡石はアリザリンで赤く染まる）。アリザリンの色見本（hammerhead-lightbox.js の
  //   HH_STAIN_T.alizarin 0.70 / 0.33 / 0.42 → 吸い方 0.357 / 1.109 / 0.868）を、径約 1 mm で吸い方 1.5 になる強さに
  //   → 1500 /m の強さでは黒い点に見えたので、色見本の吸い方を径 約 1 mm で割った値に（2026-10-24）
  Statolith: { absorb: [360, 1100, 870], film: 0 },
  //  消化管・消化腺: イカのページの内臓 (1420, 1000) から、すぐ横の外套の壁 (1395, 1000) を引いた吸い方 0.008 / 0.051 / 0.277（黄み）。
  //   メンダコの消化腺の厚み 約 10 mm で同じ吸い方になる強さ
  Gut: { absorb: [1, 5, 28], film: 0 },
  DigestiveGland: { absorb: [1, 5, 28], film: 0 },
  //  鰓・心臓・鰓心臓: 体の組織（空色）を濃くした（イカの心臓は外套より濃い。specimen-material.js の SystemicHeart 500・BranchialHearts 420）。3 倍から
  //  → 3 倍ではほとんど見えなかったので、鰓 4.8 倍、心臓と鰓心臓 4.5 倍（2026-10-24）
  Gill: { absorb: [6.05 * T * 4.8, 4.39 * T * 4.8, 1.59 * T * 4.8], film: 0 },
  Heart: { absorb: [6.05 * T * 4.5, 4.39 * T * 4.5, 1.59 * T * 4.5], film: 0 },
  BranchialHeart: { absorb: [6.05 * T * 4.5, 4.39 * T * 4.5, 1.59 * T * 4.5], film: 0 },
};
/** 調整の値（uniform の形）。gain は部品ごとの濃さの倍率、filmGain は表面の分の倍率 */
export const mdLook = {
  gain: Object.fromEntries(Object.keys(MD_PARTS).map((k) => [k, { value: Number(Q.get(`g_${k.toLowerCase()}`) ?? 1) }])),
  filmGain: { value: Number(Q.get("film") ?? 1) },
  filmMinCos: { value: 0.25 },
};
export const MD_LIGHTBOX = [0.992, 0.969, 0.984];   // シュモクザメのページの背景 rgb(253, 247, 251) と同じ光

const vertex = `
varying vec3 vViewPosition;
varying vec3 vViewNormal;
void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.);
  vViewPosition = mv.xyz;
  vViewNormal = normalMatrix * normal;
  gl_Position = projectionMatrix * mv;
}`;
// 通り道: 表の面は −深さ、裏の面は +深さ を足すと、部品の中を通る長さになる（reference は深さの基準。値を小さく保つため）
const pathFragment = `
uniform vec3 absorb;
uniform float gain;
uniform float reference;
varying vec3 vViewPosition;
void main() {
  float d = -vViewPosition.z - reference;
  gl_FragColor = vec4(gain * absorb * (gl_FrontFacing ? -d : d), 0.);
}`;
// 表面の分: 表面を横切るたびに 1 / |cos|（斜めに見る輪郭ほど長く横切る。上限は filmMinCos で抑える）
const filmFragment = `
uniform vec3 film;
uniform float gain;
uniform float minCos;
varying vec3 vViewPosition;
varying vec3 vViewNormal;
void main() {
  float cs = abs(dot(normalize(vViewNormal), normalize(-vViewPosition)));
  gl_FragColor = vec4(gain * film / max(cs, minCos), 0.);
}`;
const ADD = {
  transparent: true, depthTest: false, depthWrite: false, side: THREE.DoubleSide,
  blending: THREE.CustomBlending, blendEquation: THREE.AddEquation,
  blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor, blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneFactor,
};

export function applyMendakoTissue(model, reference) {
  const found = new Set();
  model.traverse((o) => {
    if (!o.isMesh) return;
    const part = o.userData.md_part ?? o.parent?.userData?.md_part;
    const def = MD_PARTS[part];
    if (!def) throw new Error(`specimen_mendako.glb の部品 ${part ?? o.name} に組織の設定がありません`);
    found.add(part);
    o.frustumCulled = false;
    o.userData.pathMaterial = new THREE.ShaderMaterial({
      uniforms: { absorb: { value: new THREE.Vector3(...def.absorb) }, gain: mdLook.gain[part], reference },
      vertexShader: vertex, fragmentShader: pathFragment, ...ADD,
    });
    o.userData.filmMaterial = def.film ? new THREE.ShaderMaterial({
      uniforms: { film: { value: new THREE.Vector3(...MD_FILM) }, gain: mdLook.filmGain, minCos: mdLook.filmMinCos },
      vertexShader: vertex, fragmentShader: filmFragment, ...ADD,
    }) : null;
    o.material = o.userData.pathMaterial;
  });
  const missing = Object.keys(MD_PARTS).filter((p) => !found.has(p));
  if (missing.length) throw new Error(`specimen_mendako.glb に部品がありません: ${missing.join(", ")}`);
}

const compositeFragment = `
uniform sampler2D tPath, tFilm;
uniform vec3 lightbox;
uniform vec2 tap;
varying vec2 vUv;
vec3 at(sampler2D t) {
  return .25 * (texture2D(t, vUv + vec2(-tap.x, -tap.y)).rgb + texture2D(t, vUv + vec2(tap.x, -tap.y)).rgb
    + texture2D(t, vUv + vec2(-tap.x, tap.y)).rgb + texture2D(t, vUv + vec2(tap.x, tap.y)).rgb);
}
void main() {
  vec3 a = max(at(tPath), 0.) + max(at(tFilm), 0.);
  gl_FragColor = vec4(lightbox * exp(-a), 1.);
}`;

/** ライトボックス: 通り道と表面の分を 2 枚の小数の描く先に足し、合わせて吸わせる（hammerhead-lightbox.js と同じ使い方） */
export function createMendakoLightbox(renderer, { supersample = 2 } = {}) {
  const rt = () => new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, format: THREE.RGBAFormat, depthBuffer: false });
  const target = rt(), filmTarget = rt();
  const material = new THREE.ShaderMaterial({
    uniforms: { tPath: { value: target.texture }, tFilm: { value: filmTarget.texture }, lightbox: { value: new THREE.Vector3(...MD_LIGHTBOX) }, tap: { value: new THREE.Vector2() } },
    vertexShader: "varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0., 1.); }",
    fragmentShader: compositeFragment, depthTest: false, depthWrite: false,
  });
  const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material); quad.frustumCulled = false;
  const screen = new THREE.Scene(); screen.add(quad);
  const flat = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  return {
    target, filmTarget, precision: "float16",
    setSize(w, h) {
      const maxTex = renderer.capabilities.maxTextureSize || 8192;
      const ss = Math.max(1, Math.min(supersample, Math.sqrt(16e6 / Math.max(1, w * h)), maxTex / Math.max(w, h, 1)));
      const W = Math.round(w * ss), H = Math.round(h * ss);
      target.setSize(W, H); filmTarget.setSize(W, H);
      material.uniforms.tap.value.set(ss > 1 ? 0.75 / W : 0, ss > 1 ? 0.75 / H : 0);
    },
    render(scene, camera) {
      const clear = renderer.getClearColor(new THREE.Color()), clearAlpha = renderer.getClearAlpha();
      renderer.setClearColor(0x000000, 0);
      const pass = (key, into) => {
        const swapped = [];
        scene.traverse((o) => {
          if (!o.isMesh || !o.userData.pathMaterial) return;
          swapped.push([o, o.visible]);
          if (o.userData[key]) o.material = o.userData[key]; else o.visible = false;
        });
        renderer.setRenderTarget(into); renderer.clear(); renderer.render(scene, camera);
        for (const [o, v] of swapped) { o.material = o.userData.pathMaterial; o.visible = v; }
      };
      pass("pathMaterial", target);
      pass("filmMaterial", filmTarget);
      renderer.setClearColor(clear, clearAlpha);
      renderer.setRenderTarget(null);
      renderer.render(screen, flat);
    },
  };
}
