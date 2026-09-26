// 透明標本ケース 確認スニペット（SPECIMEN-JAR-001 / 002）
// 使い方: http://127.0.0.1:8080/scenes/specimen/ を開き、瓶が見えたらコンソールに貼り付けて実行
// 期待結果: すべての項目で「成功」

(async function () {
  const ok = (name, cond, detail = "") => {
    if (cond) { console.log(`成功  ${name}`, detail); passed++; }
    else { console.error(`失敗  ${name}`, detail); failed++; }
  };
  let passed = 0, failed = 0;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  const error = document.querySelector("#error");
  ok("起動してエラーがない", Boolean(window.specimenDebug) && error && error.hidden, error?.textContent);

  const d = window.specimenDebug;
  if (!d) {
    console.log(`結果: ${passed} 成功 / ${failed} 失敗`);
    return;
  }

  ok("瓶の寸法がある", Number.isFinite(d.jar?.dims?.bodyRadius) && Number.isFinite(d.jar?.dims?.footRadius), d.jar?.dims);

  const parts = [];
  d.specimen.model.traverse((o) => { if (o.userData?.squid_part) parts.push(o.userData.squid_part); });
  const anatomy = ["Cornea", "Iris", "Retina", "Lens", "OpticNerves", "OrbitCartilage", "OpticLobes", "Brain",
    "Statocysts", "Cartilage", "Radula", "Esophagus", "Rachis"];
  ok("標本用の頭と眼の部品がそろう", anatomy.every((p) => parts.includes(p)), anatomy.filter((p) => !parts.includes(p)).join(", "));
  ok("旧い目の輪は残っていない", !parts.includes("EyeRings"));

  const hover = d.specimen.hoverAction;
  ok("動いているのはホバリングだけ", Boolean(hover?.isRunning()) && hover.getClip().name === "SQ_Hover" && d.specimen.mixer._actions.length === 1, hover?.getClip().name);

  const wasPaused = document.querySelector("#pause")?.getAttribute("aria-pressed") === "true";
  window.habitatPause(true);
  await wait(80);
  ok("一時停止できる", document.querySelector("#pause")?.getAttribute("aria-pressed") === "true");
  window.habitatPause(false);
  await wait(80);
  if (wasPaused) window.habitatPause(true);

  const limitR = 0.16, limitH = 0.045;
  let out = false;
  const t0 = d.specimen.motion.state;
  for (let i = 0; i < 30; i++) {
    d.specimen.update(0.2);
    const s = d.specimen.motion.state;
    if (Math.hypot(s.x, s.z) > limitR + 1e-4 || Math.abs(s.y) > limitH + 1e-4) out = true;
  }
  ok("漂いが液の中に収まる", !out, t0);

  ok("調整パネルは ?tune=0 のときだけ隠す", location.search.includes("tune=0") ? !d.tune?.visible : Boolean(d.tune?.visible), location.search);

  const { renderer, post } = d;
  renderer.setRenderTarget(post.target);
  renderer.render(d.scene, d.camera);
  const raw = new Uint16Array(4);
  renderer.readRenderTargetPixels(post.target, Math.round(post.target.width / 2), Math.round(post.target.height / 2), 1, 1, raw);
  const exp = (raw[0] >> 10) & 31;
  ok("画面中央が壊れた値ではない", exp !== 31, raw[0]);

  console.log(`結果: ${passed} 成功 / ${failed} 失敗`);
})();
