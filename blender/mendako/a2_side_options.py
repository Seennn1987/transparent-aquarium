"""
メンダコ A2 の確認: 眼の高さの食い違い（2026-10-17）を決めるための、横の線の案を並べた 1 枚を作る。

  .venv/bin/python -I blender/mendako/a2_side_options.py

出力: docs/mendako/a2_side_options.jpg、docs/mendako/a2_side_options.json
案は、頭の頂（断面の高さの中心）を、上から見た輪郭の中心から後ろへ d ずらしたもの（a2_parts.Body の peak）。
上から見た輪郭と正面の線（A1 の決定）は変えない。眼・殻・顎板は a2_parts.py と同じ決まりで置き直す。
  A: d = 0（A1 案 a のまま）
  B: d = 0.13。頂が前の端から 0.625 = A1 の横の案 b（原記載 図 1 の厚み）の頂と同じ前後の位置
  C: d = 0.198。眼の開口の高さが、正面の写真 2 枚の平均 0.33（0.31 と 0.345）になる量
"""

import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a2_parts as A  # noqa: E402

OPTIONS = [("A", 0.0, "いまの線（A1 案 a）"), ("B", 0.13, "頂を図 1 の位置へ"), ("C", 0.198, "眼を写真に合わせる")]
EXT = 0.42   # 絵の半分の幅（W）


def measure(body, eyes, eye_open, shell):
    zz = np.linspace(body.z_back, body.z_front, 400)
    hz = body.h(np.zeros_like(zz), zz)
    peak_frac = (body.z_front - zz[np.argmax(hz)]) / (body.z_front - body.z_back)
    gaps = {}
    for name, v in (("eye", eyes[0][0]), ("shell", shell[0])):
        gaps[name] = A.clearance(body, v)[0] * A.W_MM
    return dict(eye_opening=eye_open[0]["opening"][1], peak_from_front=float(peak_frac),
                eye_gap_mm=round(gaps["eye"], 1), shell_gap_mm=round(gaps["shell"], 1))


def main():
    TW = 700
    cols = 2
    W = 300 + cols * (TW + 20) + 20
    head = 130
    row_h = int(TW * 0.62) + 20
    RT = (cols * (TW + 20) - 40) // 3
    H = head + len(OPTIONS) * row_h + RT + 150 + 60
    out = Image.new("RGB", (W, H), (248, 247, 244))
    dr = ImageDraw.Draw(out)
    dr.text((20, 16), "メンダコ: 眼の高さの食い違いと、横の線の案（2026-10-17）", font=A.font(38, True), fill=(20, 20, 20))
    dr.text((20, 66), "写真の眼の開口の高さは横幅の 0.31〜0.345。いまの線では 0.387。頭の頂を後ろへずらすと、眼が前の斜面に乗って下がる。"
            "上から見た輪郭と正面の線（A1 の決定）は変えない", font=A.font(21), fill=(60, 60, 60))
    dr.text((20, 96), "不透明の診断用の絵（正射影）。左 = 体の左から（前が左）、右 = 前から。水色 = 外形、灰 = 眼、青 = 殻、茶 = 顎板。赤の線 = 写真の眼の高さ 0.33、緑の縦線 = 頭の頂",
            font=A.font(21), fill=(60, 60, 60))
    res = {}
    y = head
    for key, d, title in OPTIONS:
        body = A.Body(peak=d)
        bv, bf = body.mesh()
        eyes, eye_open, (sv, sf, sinfo), beaks = A.build_parts(body)
        m = measure(body, eyes, eye_open, (sv, sf))
        res[key] = dict(peak_shift=d, **m)
        meshes = [(bv, bf, (0.78, 0.86, 0.9), 0.35), (eyes[0][0], eyes[0][1], (0.35, 0.35, 0.4), 1),
                  (eyes[1][0], eyes[1][1], (0.35, 0.35, 0.4), 1), (sv, sf, (0.1, 0.35, 0.85), 1)] + \
                 [(v, f, (0.75, 0.5, 0.15), 1) for _, v, f in beaks]
        dr.text((20, y + 10), f"{key}", font=A.font(60, True), fill=(20, 20, 20))
        dr.text((20, y + 90), title, font=A.font(24, True), fill=(20, 20, 20))
        lines = [f"頂のずらし d = {d:.3f}", f"頂は前の端から {m['peak_from_front']:.2f}",
                 f"眼の開口の高さ {m['eye_opening']:.3f}", f"（写真 0.31〜0.345）",
                 f"眼の表面からの出 {-m['eye_gap_mm']:.1f} mm", f"殻の上の余り {m['shell_gap_mm']:.1f} mm"]
        for i, t in enumerate(lines):
            dr.text((20, y + 135 + i * 32), t, font=A.font(21), fill=(60, 60, 60))
        for ci, view in enumerate(("side", "front")):
            im = A.render(meshes, view, size=TW, extent=EXT)
            g = ImageDraw.Draw(im)
            S = TW / (2 * EXT)
            yy = TW / 2 + 0.15 * S - 0.33 * S
            g.line([(0, yy), (TW, yy)], fill=(220, 0, 0), width=2)
            if view == "side":
                zp = body.z_front - m["peak_from_front"] * (body.z_front - body.z_back)
                xp = -zp * S + TW / 2
                g.line([(xp, 0), (xp, TW)], fill=(0, 160, 0), width=2)
            top = int(TW / 2 + 0.15 * S - 0.5 * S)
            out.paste(im.crop((0, top, TW, top + int(TW * 0.62))), (300 + ci * (TW + 20), y))
        y += row_h
    # 参考
    dr.text((300, y + 4), "参考（左から: 横 = 原記載 図 1、斜め横 = Sunshine1、正面 = Sunshine2。赤の線 = 眼の開口の高さ）", font=A.font(22, True), fill=(20, 20, 20))
    y += 40
    R = A.REF
    refs = [(os.path.join(R, "01-ijima-ikeda-1895-pl33.jpg"), (450, 120, 1450, 620), None),
            (os.path.join(R, "04-sunshine1-live.jpg"), (300, 700, 3900, 2900), None),
            (os.path.join(R, "05-sunshine2-live.jpg"), (600, 800, 3300, 2350), (1139 - 800))]
    for i, (pth, box, eye_y) in enumerate(refs):
        im = Image.open(pth).convert("RGB").crop(box)
        s = min(RT / im.width, RT / im.height)
        im = im.resize((int(im.width * s), int(im.height * s)))
        if eye_y is not None:
            ImageDraw.Draw(im).line([(0, eye_y * s), (im.width, eye_y * s)], fill=(220, 0, 0), width=2)
        o = Image.new("RGB", (RT, RT), (255, 255, 255))
        o.paste(im, ((RT - im.width) // 2, (RT - im.height) // 2))
        out.paste(o, (300 + i * (RT + 20), y))
    note = ["原記載 図 1 は固定標本で、左が前とみた（図 9 と同じ向き）。厚みのいちばん大きい所は前の端から約 0.6〜0.625。",
            "Sunshine1 は斜めから。眼のある頭の丸みが上に見えるが、真横ではないので頂の前後は測れない。",
            "Meyer 図 1 では、眼は前の端から 0.42、外套の開口は 0.83。頂を 0.69 に置くと、眼と開口のあいだの内臓の膨らみの上になる。"]
    for i, t in enumerate(note):
        dr.text((300, y + RT + 14 + i * 28), t, font=A.font(19), fill=(70, 70, 70))
    out.save(os.path.join(A.OUT, "a2_side_options.jpg"), quality=88)
    with open(os.path.join(A.OUT, "a2_side_options.json"), "w", encoding="utf-8") as fp:
        json.dump(res, fp, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
