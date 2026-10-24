"""
メンダコ 手順 A4: 写真・粘土色の形（前の版）・標本ページの透けた姿（今の版）を同じ向きで並べ、色の見本としてイカのページを添える（2026-10-24）。

  .venv/bin/python -I blender/mendako/b5_page_sheet.py <粘土色の版の名前（例 v12）>

入力: docs/mendako/a4_page_{front,oblique,top,oral,display}.jpg（shoot_mendako.py で撮ったページ）、b2_<名前>_*.jpg、
      page_gallery_squid_2x_2026-10-17.png（イカのページ）
出力: docs/mendako/a4_compare.jpg
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
REF = os.path.join(ROOT, "docs", "references", "mendako")
OUT = os.path.join(ROOT, "docs", "mendako")
TW, TH = 640, 480


def font(s, b=False):
    return ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc" if b else "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", s)


def fit(im, w=TW, h=TH, bg=(255, 255, 255)):
    im = im.convert("RGB")
    s = min(w / im.width, h / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    o = Image.new("RGB", (w, h), bg)
    o.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return o


def main():
    clay = sys.argv[1] if len(sys.argv) > 1 else "v12"
    rows = [
        ("前から", (os.path.join(REF, "05-sunshine2-live.jpg"), (600, 700, 3300, 2350)), "front", (250, 200, 1150, 875)),
        ("斜め前から", (os.path.join(REF, "04-sunshine1-live.jpg"), (300, 500, 3900, 2900)), "oblique", (200, 150, 1200, 900)),
        ("背中から（前が上）", (os.path.join(REF, "10-meyer1906-taf11-left.jpg"), (400, 300, 2200, 2150)), "top", (200, 75, 1200, 975)),
        ("口側から（前が上）", (os.path.join(REF, "30-verhoeff2024-fig12.png"), (200, 260, 1300, 1480)), "oral", (200, 75, 1200, 975)),
    ]
    W = 300 + 3 * (TW + 16)
    H = 160 + len(rows) * (TH + 40) + TH + 90
    out = Image.new("RGB", (W, H), (248, 247, 244))
    dr = ImageDraw.Draw(out)
    dr.text((20, 16), "メンダコ 手順 A4: 標本ページの透けた姿（2026-10-24）", font=font(38, True), fill=(20, 20, 20))
    dr.text((20, 66), f"左から: 参考の写真・図、粘土色の形（{clay}）、実際の標本ページ（mendako.html、器なし・ライトボックス）を Chrome で撮った絵。"
            "色はイカと同じ空色（計画書 第 2.4 節の目標に、ページの画素で合わせた）", font=font(20), fill=(60, 60, 60))
    for k, t in enumerate(("参考", f"粘土色の形（{clay}）", "標本ページ（今の版）")):
        dr.text((300 + k * (TW + 16), 116), t, font=font(26, True), fill=(20, 20, 20))
    y = 160
    for title, (rp, rb), view, pb in rows:
        dr.text((20, y + 10), title, font=font(26, True), fill=(20, 20, 20))
        ims = [fit(Image.open(rp).crop(rb)),
               fit(Image.open(os.path.join(OUT, f"b2_{clay}_{view}.jpg"))),
               fit(Image.open(os.path.join(OUT, f"a4_page_{view}.jpg")).crop(pb))]
        for k, im in enumerate(ims):
            out.paste(im, (300 + k * (TW + 16), y))
        y += TH + 40
    dr.text((20, y + 10), "色の見本", font=font(26, True), fill=(20, 20, 20))
    sq = Image.open(os.path.join(OUT, "page_gallery_squid_2x_2026-10-17.png")).crop((1150, 640, 1720, 1520))
    out.paste(fit(sq), (300, y))
    out.paste(fit(Image.open(os.path.join(OUT, "a4_color_points.jpg")).crop((200, 75, 1200, 975))), (300 + TW + 16, y))
    out.paste(fit(Image.open(os.path.join(OUT, "a4_page_display.jpg")).crop((150, 100, 1250, 925))), (300 + 2 * (TW + 16), y))
    dr.text((300, y + TH + 8), "左: イカのページ（色の目標）。中: 色を測った点（膜・頭の丸み・眼）。右: ページの既定の向き", font=font(18), fill=(80, 80, 80))
    path = os.path.join(OUT, "a4_compare.jpg")
    out.save(path, quality=88)
    print(path, out.size)


if __name__ == "__main__":
    main()
