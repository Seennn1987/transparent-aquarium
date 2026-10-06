// 透明標本ケース 確認スニペット（SPECIMEN-JAR-001 / 002、SPECIMEN-GALLERY）
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
  ok("標本は浮いてホバリングしている（泳ぎはしない）", hover?.getClip().name === "SQ_Hover" && hover.timeScale > 0 && d.specimen.mixer._actions.length === 1, hover?.timeScale);
  ok("傾けて沈めた姿勢は外してある", !d.specimen.object.getObjectByName("SpecimenLean"));
  ok("心臓が3つある（体心臓・鰓心臓）", ["SystemicHeart", "BranchialHearts"].every((p) => parts.includes(p)));

  const organs = d.specimen.organs?.uniforms;
  const clock = organs?.uOrganTime.value;
  d.specimen.update(0.5);
  ok("内臓の時計が進み、拍動と瞳が動く", organs && organs.uOrganTime.value > clock && Number.isFinite(organs.uBeatSystemic.value) && Number.isFinite(organs.uPupil.value), organs?.uOrganTime.value);

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

  const look = d.look;
  ok("生々しさの値がそろう", ["mottle", "pooling", "hue", "edgeSoft", "veil", "gut", "fat", "inkBleed"].every((k) => Number.isFinite(look[k]?.value)) && ["haze"].every((k) => Number.isFinite(d.optics.uniforms && d.scene.getObjectByName("jar-optics-column").material.uniforms[`u${k[0].toUpperCase()}${k.slice(1)}`]?.value)));

  // R18: optics, tissue and jar.
  const r18Parts = ["SuckerRings", "VisceralSac", "Vessels"];
  ok("R18 吸盤の歯・内臓の袋・血管がある", r18Parts.every((p) => parts.includes(p)), r18Parts.filter((p) => !parts.includes(p)).join(", "));
  ok("R18 縁の光・液の中のつや・筋肉の縞の値がある", ["rimGlow", "liquidSheen", "striation"].every((k) => Number.isFinite(look[k]?.value)));
  const column = d.scene.getObjectByName("jar-optics-column")?.material.uniforms;
  ok("R18 屈折の歪み・メニスカス・液の揺らぎの値がある",
    ["uTissueBend", "uMeniscus", "uSwirl", "uTime"].every((k) => Number.isFinite(column?.[k]?.value)));
  ok("R18 ガラスの緑の値がある", Number.isFinite(d.optics.uniforms.uGlassGreen?.value));
  ok("R19 標本ラベルがあり、封と傷・泡・黄ばみは外してある",
    Boolean(d.scene.getObjectByName("specimen-label")?.material.map) && !d.scene.getObjectByName("specimen-seal")
    && ["uScuff", "uSpecks", "uYellow", "uSeam"].every((k) => !(k in column)));
  ok("R19 蓋（つまみ込み）と台座は厚いガラスとして屈折で描く",
    ["jar-optics-lid", "jar-optics-foot"].every((n) => d.scene.getObjectByName(n)?.material.uniforms?.tShape?.value)
    && !d.scene.getObjectByName("jar-optics-knob"));
  window.habitatPause(true);
  await wait(150);
  const liquidTime = column?.uTime.value;
  await wait(400);
  ok("R18 一時停止中は液の揺らぎが止まる", column?.uTime.value === liquidTime, liquidTime);
  if (!wasPaused) window.habitatPause(false);

  // SPECIMEN-GALLERY: the room, the jars behind and the lens.
  ok("ギャラリーの部屋と手前の台がある", Boolean(d.scene.getObjectByName("gallery-room") && d.scene.getObjectByName("gallery-front-top")));
  const quality = document.querySelector("#quality")?.value ?? "balanced";
  const expected = { eco: 3, balanced: 5, detail: 7 }[quality];
  const shown = d.galleryJars.jars.filter((j) => d.galleryJars.shown.includes(j.slot));
  ok("奥の瓶が画質どおりの本数", shown.length === expected && d.galleryJars.shown.length === expected, `${quality}: ${shown.length}`);
  ok("奥の瓶が横一列", new Set(shown.map((j) => j.slot.z)).size <= 1, shown.map((j) => j.slot.z).join(","));
  ok("光る台なら奥の瓶ごとに台がある", d.stageLook.table !== "blocks" || shown.every((j) => j.block.visible));
  ok("奥の瓶は画質どおりの描き方（Eco だけ簡易）", d.galleryJars.traced === (quality !== "eco"));
  let edgeDepth = 0;
  const drawn = d.galleryJars.traced ? shown[0]?.traced.group : shown[0]?.plain;
  drawn?.traverse((o) => { if (o.material?.colorWrite === false && o.material.depthWrite) edgeDepth++; });
  ok("奥の瓶のガラスに縁だけの深度がある", edgeDepth === 2, edgeDepth);
  ok("奥の標本は焼き込み済みで頂点がある", d.galleryJars.tissue.attributes.position.count > 1000, d.galleryJars.tissue.attributes.position.count);
  const toOrigin = Math.atan2(d.camera.position.x, d.camera.position.z);
  ok("カメラが部屋の正面側にある（左右回転の制限内）", Math.abs(toOrigin - 0.2745) <= 0.71, toOrigin.toFixed(3));
  ok("ピントの帯と深さの値がある", d.lens.focusDepth.value > 0 && d.lens.aperture.value > 0 && Number.isFinite(d.lens.focusShift.value));

  ok("調整パネルは ?tune=0 のときだけ作らない", location.search.includes("tune=0") ? !d.tune?.panel : Boolean(d.tune?.panel), location.search);
  if (d.tune?.panel) {
    const opener = document.querySelector("#tune-open");
    const wasOpen = d.tune.visible;
    d.tune.panel.querySelector(".tune-close").click();
    const closed = d.tune.panel.hidden && !opener.hidden;
    opener.click();
    const reopened = !d.tune.panel.hidden && opener.hidden;
    if (!wasOpen) d.tune.panel.querySelector(".tune-close").click();
    ok("調整パネルを閉じて、また開ける", closed && reopened);
    ok("設定をコピーするボタンがある", [...d.tune.panel.querySelectorAll("button")].some((b) => b.textContent === "設定をコピー"));
  }

  const { renderer, post } = d;
  renderer.setRenderTarget(post.target);
  renderer.render(d.scene, d.camera);
  const raw = new Uint16Array(4);
  renderer.readRenderTargetPixels(post.target, Math.round(post.target.width / 2), Math.round(post.target.height / 2), 1, 1, raw);
  const exp = (raw[0] >> 10) & 31;
  ok("画面中央が壊れた値ではない", exp !== 31, raw[0]);

  console.log(`結果: ${passed} 成功 / ${failed} 失敗`);
})();
