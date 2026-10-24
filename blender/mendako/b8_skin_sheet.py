"""
メンダコ 手順 A6: 皮膚の質感の前後を並べる（2026-10-24）。

  .venv/bin/python -I blender/mendako/b8_skin_sheet.py

入力: docs/mendako/a6_t0_*.jpg（質感を 0 にしたページ: ?wrinkle=0&spots=0&sheen=0&milk=0）、a6_t4_*.jpg（質感あり）、
      生体の写真 07-sunshine4-live.jpg、イカのページ page_gallery_squid_2x_2026-10-17.png
出力: docs/mendako/a6_compare.jpg
"""

import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
REF = os.path.join(ROOT, "docs", "references", "mendako")
OUT = os.path.join(ROOT, "docs", "mendako")
TW, TH = 700, 525


def font(s, b=False):
    return ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc" if b else "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", s)


def fit(im, w=TW, h=TH):
    im = im.convert("RGB")
    s = min(w / im.width, h / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    o = Image.new("RGB", (w, h), (255, 255, 255))
    o.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return o


def main():
    W = 260 + 3 * (TW + 16)
    H = 150 + 3 * (TH + 50) + 20
    out = Image.new("RGB", (W, H), (248, 247, 244))
    dr = ImageDraw.Draw(out)
    dr.text((20, 16), "メンダコ 手順 A6: 皮膚の質感（2026-10-24）", font=font(38, True), fill=(20, 20, 20))
    dr.text((20, 66), "足したもの: 周の向きに途切れながら続く溝のしわ（幅 1.6 mm・長さ 8 mm の区画の、周に沿う境目だけ）、背の 8 列の突起と色素の名残、1 mm ほどの色素の点、"
            "濡れたつや、厚い所のにごり。どれも実際の標本ページを Chrome で撮った絵", font=font(19), fill=(60, 60, 60))
    y = 110
    rows = [
        ("近くで", [fit(Image.open(os.path.join(REF, "07-sunshine4-live.jpg")).crop((1700, 1150, 2500, 1750))),
                    fit(Image.open(os.path.join(OUT, "a6_t0_front.jpg")).crop((500, 250, 800, 475))),
                    fit(Image.open(os.path.join(OUT, "a6_t4_front.jpg")).crop((500, 250, 800, 475)))],
         ["生体の皮膚（Sunshine4、x 1700〜2500、Totti, CC BY-SA 4.0）", "質感なし（前の版）", "質感あり（今の版）"]),
        ("前から", [fit(Image.open(os.path.join(OUT, "page_gallery_squid_2x_2026-10-17.png")).crop((1250, 700, 1600, 1100))),
                    fit(Image.open(os.path.join(OUT, "a6_t0_front.jpg")).crop((250, 150, 1150, 825))),
                    fit(Image.open(os.path.join(OUT, "a6_t4_front.jpg")).crop((250, 150, 1150, 825)))],
         ["色と質感の見本: イカの標本ページ", "質感なし", "質感あり"]),
        ("斜め前から", [fit(Image.open(os.path.join(REF, "04-sunshine1-live.jpg")).crop((300, 500, 3900, 2900))),
                       fit(Image.open(os.path.join(OUT, "a6_t0_oblique.jpg")).crop((200, 150, 1200, 900))),
                       fit(Image.open(os.path.join(OUT, "a6_t4_oblique.jpg")).crop((200, 150, 1200, 900)))],
         ["Sunshine1（生体、Totti, CC BY-SA 4.0）", "質感なし", "質感あり"]),
    ]
    for k, t in enumerate(("参考", "前の版", "今の版")):
        dr.text((260 + k * (TW + 16), y), t, font=font(24, True), fill=(20, 20, 20))
    y += 40
    for title, ims, caps in rows:
        dr.text((20, y + 10), title, font=font(24, True), fill=(20, 20, 20))
        for k, (im, c) in enumerate(zip(ims, caps)):
            out.paste(im, (260 + k * (TW + 16), y))
            dr.text((260 + k * (TW + 16), y + TH + 6), c, font=font(17), fill=(80, 80, 80))
        y += TH + 50
    path = os.path.join(OUT, "a6_compare.jpg")
    out.save(path, quality=88)
    print(path, out.size)


if __name__ == "__main__":
    main()
