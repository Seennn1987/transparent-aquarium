"""
メンダコ: 参考の写真・前の版（A3 の単純な部品）・今の版（Blender で融合した形）を同じ向きで 1 枚に並べる（2026-10-24）。

  .venv/bin/python -I blender/mendako/b3_sheet.py <今の版の名前（例 v10）>

出力: docs/mendako/b3_compare_<名前>.jpg
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
REF = os.path.join(ROOT, "docs", "references", "mendako")
OUT = os.path.join(ROOT, "docs", "mendako")
FONT = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
FONT_B = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
TW, TH = 640, 480

# a3_parts.jpg の中の絵の位置（a3_membrane_arms.py の sheet: 絵 560 px、行は 130 + 680 k）
A3 = {"front": (20, 1490), "oblique": (1180, 1490), "top": (1760, 1490), "oral": (1180, 130)}
ROWS = [
    ("前から（生体の正面）", ("05-sunshine2-live.jpg", (600, 700, 3300, 2350)), "Sunshine2、Totti, CC BY-SA 4.0", "front"),
    ("斜め前から", ("04-sunshine1-live.jpg", (300, 500, 3900, 2900)), "Sunshine1、Totti, CC BY-SA 4.0（左前の低い所から）", "oblique"),
    ("背中から（前が上）", ("10-meyer1906-taf11-left.jpg", (400, 300, 2200, 2150)), "Meyer 1906 図 1、成熟した雄（固定）、PD", "top"),
    ("口側から（前が上）", ("30-verhoeff2024-fig12.png", (200, 260, 1300, 1480)), "Sasaki 1929 の雄の口側、Verhoeff 2024 図 12 A、CC BY 4.0", "oral"),
]


def font(s, b=False):
    return ImageFont.truetype(FONT_B if b else FONT, s)


def fit(im, w=TW, h=TH, bg=(255, 255, 255)):
    im = im.convert("RGB")
    s = min(w / im.width, h / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    o = Image.new("RGB", (w, h), bg)
    o.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return o


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "v10"
    a3 = Image.open(os.path.join(OUT, "a3_parts.jpg")).convert("RGB")
    W = 300 + 3 * (TW + 16)
    H = 150 + len(ROWS) * (TH + 70)
    out = Image.new("RGB", (W, H), (248, 247, 244))
    dr = ImageDraw.Draw(out)
    dr.text((20, 16), f"メンダコ 外の形: 写真・前の版・今の版（2026-10-24、{name}）", font=font(38, True), fill=(20, 20, 20))
    dr.text((20, 66), "前の版 = A3 の単純な部品（管・杯・板・球）を自作の描き方で描いた絵。今の版 = Blender で傘・頭・眼・ひれ・腕を 1 つの体に融合して"
            "ならした形を、粘土色で描いた絵（色と透けはまだ）", font=font(20), fill=(60, 60, 60))
    for k, t in enumerate(("参考", "前の版（A3）", f"今の版（{name}）")):
        dr.text((300 + k * (TW + 16), 110), t, font=font(26, True), fill=(20, 20, 20))
    y = 150
    for title, (ref, box), cap, view in ROWS:
        dr.text((20, y + 10), title, font=font(26, True), fill=(20, 20, 20))
        r = fit(Image.open(os.path.join(REF, ref)).crop(box))
        x0, y0 = A3[view]
        p = fit(a3.crop((x0, y0, x0 + 560, y0 + 560)))
        cp = os.path.join(OUT, f"b2_{name}_{view}.png")
        c = fit(Image.open(cp if os.path.exists(cp) else cp[:-4] + ".jpg"))
        for k, im in enumerate((r, p, c)):
            out.paste(im, (300 + k * (TW + 16), y))
        dr.text((300, y + TH + 8), cap, font=font(18), fill=(80, 80, 80))
        y += TH + 70
    path = os.path.join(OUT, f"b3_compare_{name}.jpg")
    out.save(path, quality=88)
    print(path, out.size)


if __name__ == "__main__":
    main()
