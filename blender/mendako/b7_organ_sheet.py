"""
メンダコ 手順 A5: 中の部品を、解剖の図と同じ向きで並べる（2026-10-24）。

  .venv/bin/python -I blender/mendako/b7_organ_sheet.py

入力: docs/mendako/a5_page_*.jpg（今の版）、a4_page_*.jpg（前の版）、参考の図（docs/references/mendako/）
出力: docs/mendako/a5_compare.jpg
"""

import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
REF = os.path.join(ROOT, "docs", "references", "mendako")
OUT = os.path.join(ROOT, "docs", "mendako")
TW, TH = 640, 520


def font(s, b=False):
    return ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc" if b else "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", s)


def fit(im, w=TW, h=TH):
    im = im.convert("RGB")
    s = min(w / im.width, h / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    o = Image.new("RGB", (w, h), (255, 255, 255))
    o.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return o


def page(name, view, box):
    p = os.path.join(OUT, f"{name}_page_{view}.jpg")
    return fit(Image.open(p).crop(box)) if os.path.exists(p) else fit(Image.new("RGB", (10, 10), (240, 240, 240)))


def main():
    rows = [
        ("背中から（前が上）", fit(Image.open(os.path.join(REF, "11-meyer1906-taf11-right.jpg")).crop((0, 600, 2844, 3600))),
         "Meyer 1906 Taf. XI 図 2（皮膚を除いた背、PD）。眼・水晶体・頭の軟骨 Kk・食道の膨らみ・消化腺・第一胃・鰓・鰓心臓・精巣", "top", (250, 150, 1150, 900)),
        ("背中から（血管と神経）", fit(Image.open(os.path.join(REF, "14-meyer1906-taf13.jpg")).crop((150, 150, 1950, 1900))),
         "Meyer 1906 Taf. XIII 図 14（PD）。眼のあいだの脳と頭の軟骨、中央の赤い塊が心臓、左右の灰色が鰓心臓", "top", (400, 250, 1000, 750)),
        ("体の左から（前が左）", fit(Image.open(os.path.join(REF, "01-ijima-ikeda-1895-pl33.jpg")).crop((200, 2120, 1950, 2560))),
         "原記載 図 9（正中の断面、半ば模式、PD）。左が前。e.b. 眼、c.g. 脳、buc.b. 口球、st. 胃、d.c. 殻、tes. 精巣、an. 肛門", "side", (200, 150, 1200, 900)),
        ("前から", fit(Image.open(os.path.join(REF, "05-sunshine2-live.jpg")).crop((600, 700, 3300, 2350))),
         "Sunshine2（生体の正面、Totti, CC BY-SA 4.0）", "front", (250, 150, 1150, 900)),
    ]
    W = 300 + 3 * (TW + 16)
    H = 160 + len(rows) * (TH + 60) + 40
    out = Image.new("RGB", (W, H), (248, 247, 244))
    dr = ImageDraw.Draw(out)
    dr.text((20, 16), "メンダコ 手順 A5: 中の部品（2026-10-24）", font=font(38, True), fill=(20, 20, 20))
    dr.text((20, 66), "今の版で足した部品: 頭の軟骨（淡い青の殻）、平衡石（赤い点）、消化管と消化腺（黄み）、鰓（青い房、半分のオレンジの形）、心臓と鰓心臓（濃い空色）。"
            "どれも実際の標本ページを Chrome で撮った絵", font=font(20), fill=(60, 60, 60))
    for k, t in enumerate(("参考の図", "前の版（A4、中は殻・眼・顎板だけ）", "今の版（A5）")):
        dr.text((300 + k * (TW + 16), 116), t, font=font(26, True), fill=(20, 20, 20))
    y = 160
    for title, ref, cap, view, box in rows:
        dr.text((20, y + 10), title, font=font(24, True), fill=(20, 20, 20))
        for k, im in enumerate((ref, page("a4", view, box), page("a5", view, box))):
            out.paste(im, (300 + k * (TW + 16), y))
        dr.text((300, y + TH + 8), cap, font=font(18), fill=(80, 80, 80))
        y += TH + 60
    path = os.path.join(OUT, "a5_compare.jpg")
    out.save(path, quality=88)
    print(path, out.size)


if __name__ == "__main__":
    main()
