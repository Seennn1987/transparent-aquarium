"""シュモクザメの標本ページの画像を、向きごとに 1 段、版ごとに 1 列で 1 枚に並べる。

使い方（リポジトリ直下の .venv で）:
  .venv/bin/python tools/record-specimen/compare_hammerhead.py <出力.png> \
      --col "前の版 A6 (10-14 19:07)=docs/hammerhead_ct/a6_{view}.jpg" \
      --col "今の glb=out/f80fc9f_{view}.png" [--views top,side,display] [--width 800]

各列は「見出し=パス」。パスの {view} が向き（top / side / display）に置き換わる。
参考写真の列も同じ書き方で足せる（向きをそろえた画像を用意しておく）。
画像が無い向きは灰色の枠に「なし」と書く。画像は列の幅に縮めるだけで、色は変えない。
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

VIEW_NAMES = {"top": "背中から（view=top）", "side": "横から（view=side）", "display": "展示の姿勢（指定なし）",
              "below": "腹から（view=below）", "front": "前から（view=front）",
              "sidezoom": "横から・拡大（view=side）"}
FONT_PATHS = ["/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc"]


def font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--col", action="append", required=True, help="見出し=パス（{view} を含む）")
    ap.add_argument("--views", default="top,side,display")
    ap.add_argument("--width", type=int, default=800, help="1 列の幅 px")
    ap.add_argument("--title", default="")
    a = ap.parse_args()

    cols = [c.split("=", 1) for c in a.col]
    views = a.views.split(",")
    W = a.width
    H = W // 2                       # 標本ページは 2:1 で撮る（shoot-hammerhead.mjs の SIZE）
    pad, head, label_w = 12, 40, 150
    title_h = 44 if a.title else 0
    f_head, f_label = font(22), font(18)
    sheet = Image.new("RGB", (label_w + len(cols) * (W + pad) + pad, title_h + head + len(views) * (H + pad) + pad), "white")
    d = ImageDraw.Draw(sheet)
    if a.title:
        d.text((pad, 10), a.title, fill=(20, 20, 20), font=f_head)
    for i, (name, _) in enumerate(cols):
        d.text((label_w + pad + i * (W + pad), title_h + 8), name, fill=(20, 20, 20), font=f_head)
    for r, view in enumerate(views):
        y = title_h + head + r * (H + pad)
        d.multiline_text((pad, y + H // 2 - 24), VIEW_NAMES.get(view, view).replace("（", "\n（"), fill=(40, 40, 40), font=f_label)
        for i, (_, pattern) in enumerate(cols):
            x = label_w + pad + i * (W + pad)
            path = pattern.replace("{view}", view)
            if os.path.exists(path):
                im = Image.open(path).convert("RGB")
                im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
                sheet.paste(im.crop((0, 0, W, min(H, im.height))), (x, y))
                d.rectangle((x, y, x + W - 1, y + H - 1), outline=(200, 200, 200))
            else:
                d.rectangle((x, y, x + W - 1, y + H - 1), fill=(225, 225, 225))
                d.text((x + W // 2 - 20, y + H // 2 - 12), "なし", fill=(110, 110, 110), font=f_head)
    sheet.save(a.out)
    print(a.out, sheet.size)


if __name__ == "__main__":
    main()
