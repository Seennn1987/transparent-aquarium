// 案を動かしたまま切り替えるボタンの欄（シュモクザメの標本ページとギャラリーで使う、2026-10-15）。
// rows: [見出し, [[ボタンの文字, 値], ...], 今の値を返す関数, 値を決める関数]。noteText: 下の説明
export function pickerPanel(rows, noteText) {
  const box = document.createElement("div");
  box.style.cssText = "position:fixed;left:12px;top:12px;display:flex;flex-direction:column;gap:6px;font:14px/1.3 system-ui,sans-serif;color:#333;background:rgba(255,255,255,.85);padding:10px 12px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.15)";
  for (const [title, items, get, set] of rows) {
    const r = document.createElement("div"); r.style.cssText = "display:flex;align-items:center;gap:6px;flex-wrap:wrap";
    const t = document.createElement("span"); t.textContent = title; t.style.minWidth = "5.5em"; r.append(t);
    const buttons = items.map(([label, value]) => {
      const b = document.createElement("button"); b.type = "button"; b.textContent = label;
      b.style.cssText = "font:inherit;padding:4px 10px;border:1px solid #999;border-radius:6px;cursor:pointer";
      b.onclick = () => { set(value); paint(); };
      r.append(b); return [b, value];
    });
    const paint = () => { for (const [b, v] of buttons) { const on = get() === v; b.style.background = on ? "#333" : "#fff"; b.style.color = on ? "#fff" : "#333"; } };
    paint(); box.append(r);
  }
  const note = document.createElement("div"); note.style.cssText = "font-size:12px;color:#666;max-width:28em"; note.textContent = noteText;
  box.append(note); document.body.append(box);
}
