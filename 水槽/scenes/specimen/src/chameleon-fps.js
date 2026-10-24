// The chameleon page's frame-rate box (C record 57, 2026-10-24, the producer: 「FPSを測定する機能を追加して（シュモクザメで実施済み）」),
// as the hammerhead page's (hammerhead-main.js createFpsBox): with ?fps=1, under the saved looks at the top left, each second the
// FPS, the frame interval over the last 2 s (median, slowest 5%), the time the drawing takes in JS (median), the passes' buffer size
// and how many are drawn, the triangles, and the GPU's name.

export function createChameleonFps(renderer, model, lightbox) {
  const el = document.createElement("div"); el.id = "ch-fps";
  el.style.cssText = "position:fixed;left:12px;top:60px;z-index:20;padding:6px 8px;background:rgba(0,0,0,.72);color:#fff;font:12px/1.45 ui-monospace,Menlo,monospace;border-radius:6px;pointer-events:none;white-space:pre";
  document.body.append(el);
  let tris = 0; model.traverse((o) => { if (o.isMesh) tris += (o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count) / 3; });
  const gl = renderer.getContext(), ext = gl.getExtension("WEBGL_debug_renderer_info");
  const gpu = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : "?";
  const times = [], work = []; let prev = 0, count = 0, since = performance.now();
  const q = (a, f) => { if (!a.length) return 0; const b = [...a].sort((x, y) => x - y); return b[Math.min(b.length - 1, Math.floor(b.length * f))]; };
  return {
    /** `now`: the frame's start (performance.now()); `ms`: how long lightbox.render took. */
    tick(now, ms) {
      if (prev) { times.push([now, now - prev]); work.push([now, ms]); }
      prev = now; count++;
      while (times.length && now - times[0][0] > 2000) times.shift();
      while (work.length && now - work[0][0] > 2000) work.shift();
      if (now - since < 1000) return;
      const fps = count * 1000 / (now - since); count = 0; since = now;
      const d = times.map((x) => x[1]), w = work.map((x) => x[1]);
      const t = lightbox.target, out = lightbox.size;
      const passes = 1 + (lightbox.organs ? 1 : 0) + (lightbox.material.uniforms.filmGain.value > 0 ? 1 : 0);
      el.textContent = `FPS ${fps.toFixed(1)}\n` +
        `コマの間隔 中央 ${q(d, 0.5).toFixed(1)} ms・遅い 5% ${q(d, 0.95).toFixed(1)} ms\n` +
        `描く処理（JS） 中央 ${q(w, 0.5).toFixed(1)} ms\n` +
        `描く先 ${t.width}×${t.height}（細かさ ${(t.width / Math.max(1, out.width)).toFixed(2)}、画素 ${(t.width * t.height / 1e6).toFixed(1)} M × ${passes} 枚、${lightbox.precision}）\n` +
        `三角形 ${(tris / 1e6).toFixed(2)} M\n${gpu}`;
    },
  };
}
