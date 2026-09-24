// イカ水槽遊泳 自動検証スニペット（SQUID-TANK-001 / 色: SQUID-TANK-002）
// 使い方: http://127.0.0.1:8080/scenes/riverscape/ を開き、イカが映ったらブラウザのコンソールに貼り付けて実行（操作不要・約30秒）
// 期待結果: すべての検証項目で「✅ 成功」と表示される

(async function () {
  console.log('=== イカ水槽遊泳 自動検証開始（約30秒） ===');
  let passed = 0, failed = 0;
  const ok = (name, cond, detail = '') => {
    if (cond) { console.log(`✅ ${name} - 成功`, detail); passed++; }
    else { console.error(`❌ ${name} - 失敗`, detail); failed++; }
  };
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const stats = () => window.habitatStats();
  const TANK = { minX: -8.3, maxX: 8.3, minY: 0.7, maxY: 8.4, minZ: -4.7, maxZ: 3.2 };
  const inTank = ([x, y, z]) => x > TANK.minX && x < TANK.maxX && y > TANK.minY && y < TANK.maxY && z > TANK.minZ && z < TANK.maxZ;

  try {
    // 1. 水槽がエラーなく動いている
    const error = document.querySelector('#error');
    ok('検証1: 水槽がエラーなく起動', error && error.hidden && typeof window.habitatStats === 'function');
    window.habitatPause(false);
    await wait(500);

    // 2. イカがいる
    const s0 = stats();
    ok('検証2: イカが水槽にいる', s0.squid && ['hover', 'swim', 'back', 'jet'].includes(s0.squid.mode), s0.squid);

    // 3. 20秒間の動き: ホバリング以外の動きが出る・水槽の外に出ない
    const modes = new Set();
    let outside = null, moved = 0, prev = s0.squid.position;
    for (let i = 0; i < 80; i++) {
      await wait(250);
      const q = stats().squid;
      modes.add(q.mode);
      if (!inTank(q.position)) outside = q.position;
      moved += Math.hypot(...q.position.map((v, k) => v - prev[k]));
      prev = q.position;
    }
    ok('検証3: 20秒の間にホバリング以外の動きもする', modes.size >= 2, [...modes]);
    ok('検証4: 20秒の間に水槽の中を移動する', moved > 2, `移動距離 ${moved.toFixed(1)}`);
    ok('検証5: 水槽の外に出ない', outside === null, outside ?? '');

    // 4. ポインタを素早く近づけるとジェット噴射で逃げる
    const canvas = document.querySelector('#scene');
    const box = canvas.getBoundingClientRect();
    const q = stats().squid;
    const sx = box.left + (q.screen[0] + 1) / 2 * box.width, sy = box.top + (1 - q.screen[1]) / 2 * box.height;
    for (let i = 0; i <= 8; i++) {
      canvas.dispatchEvent(new PointerEvent('pointermove', { clientX: sx - 350 + 320 * i / 8, clientY: sy, bubbles: true, isPrimary: true }));
      await wait(16);
    }
    canvas.dispatchEvent(new PointerEvent('pointerleave', { bubbles: true }));
    let jetted = false, jetOutside = null;
    const before = stats().squid.position;
    for (let i = 0; i < 25; i++) {
      await wait(200);
      const j = stats().squid;
      if (j.mode === 'jet') jetted = true;
      if (!inTank(j.position)) jetOutside = j.position;
    }
    const after = stats().squid.position;
    const escaped = Math.hypot(...after.map((v, k) => v - before[k]));
    // 手（前面ガラス上）から 4 以上奥にいるときは、驚かないのが正しい動き
    const reachable = q.position[2] > -1.2;
    ok('検証6: 手を素早く近づけるとジェット噴射で逃げる', jetted || !reachable, `噴射 ${jetted} / 移動 ${escaped.toFixed(1)}`);
    ok('検証7: ジェット噴射でも水槽の外に出ない', jetOutside === null, jetOutside ?? '');
    // 噴射は約4.5秒続くので、終わるまで最大6秒待ってから判定する
    for (let i = 0; i < 30 && jetted && stats().squid.mode === 'jet'; i++) await wait(200);
    ok('検証8: 噴射の後はホバリングに戻る', !jetted || stats().squid.mode !== 'jet', stats().squid.mode);

    // 5. 一時停止するとイカも止まる
    window.habitatPause(true);
    await wait(300);
    const p1 = stats().squid.position;
    await wait(1500);
    const p2 = stats().squid.position;
    ok('検証9: 一時停止中はイカも止まる', p1.every((v, k) => v === p2[k]));
    window.habitatPause(false);

    // 6. 既存の操作が使える
    ok('検証10: エサ・一時停止・画質のボタンが使える',
      ['#pause', '#feed', '#quality'].every((id) => !document.querySelector(id).disabled));

    // 7. イカの色が透明標本の青緑（SQUID-TANK-002）: イカのまわりの画面の色を数える
    const grab = () => new Promise((res) => requestAnimationFrame(() => {
      const s = stats().squid;
      const W = canvas.width, H = canvas.height;
      const cx = (s.screen[0] + 1) / 2 * W, cy = (1 - s.screen[1]) / 2 * H, R = Math.round(W * 0.09);
      const box = document.createElement('canvas');
      box.width = box.height = 2 * R;
      const g = box.getContext('2d');
      g.drawImage(canvas, cx - R, cy - R, 2 * R, 2 * R, 0, 0, 2 * R, 2 * R);
      const d = g.getImageData(0, 0, 2 * R, 2 * R).data;
      let stained = 0, white = 0, sr = 0, sg = 0;
      for (let i = 0; i < d.length; i += 4) {
        const [r, gr, b] = [d[i], d[i + 1], d[i + 2]];
        if (gr - r > 45 && b - r > 25 && b > 100) { stained++; sr += r; sg += gr; }
        if (Math.min(r, gr, b) > 150 && Math.max(r, gr, b) - Math.min(r, gr, b) < 45) white++;
      }
      res({ stained, white, rg: stained ? sr / sg : 1 });
    }));
    let best = { stained: 0, white: 0, rg: 1 };
    for (let k = 0; k < 6; k++) {
      const c = await grab();
      if (c.stained > best.stained) best = c;
      await wait(500);
    }
    ok('検証11: イカが白ではなく透明標本の青緑に見える',
      // 奥にいるときは小さく映るので、画素数は少なめでも良い
      best.stained > 200 && best.stained > best.white && best.rg < 0.65,
      `青緑 ${best.stained}画素 / 白 ${best.white}画素 / 赤÷緑 ${best.rg.toFixed(2)}`);
    ok('検証12: 検証の最後までエラー表示なし', document.querySelector('#error').hidden);
  } catch (e) {
    console.error('❌ 検証中に例外が発生', e);
    failed++;
  }

  console.log(`\n=== 検証完了: ${passed}成功 / ${failed}失敗 ===`);
  if (failed === 0) console.log('✅ すべての検証に成功しました');
  else console.error('❌ 検証に失敗した項目があります');
  return { passed, failed };
})();
