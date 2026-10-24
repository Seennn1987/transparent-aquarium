"""
画像の一部に方眼（原寸の画素の座標）を引いて切り出す。参考の画像で点を読むときに使う。

  .venv/bin/python -I blender/mendako/grid.py <画像> x0 y0 x1 y1 <方眼の間隔 px> <倍率> <出力>
"""

import sys

from PIL import Image, ImageDraw

f, x0, y0, x1, y1, step, scale, out = sys.argv[1], *map(int, sys.argv[2:7]), float(sys.argv[7]), sys.argv[8]
im = Image.open(f).convert("RGB").crop((x0, y0, x1, y1))
im = im.resize((int(im.width * scale), int(im.height * scale)))
d = ImageDraw.Draw(im)
for x in range((x0 // step + 1) * step, x1, step):
    X = (x - x0) * scale
    d.line([(X, 0), (X, im.height)], fill=(0, 150, 255), width=1)
    d.text((X + 2, 2), str(x), fill=(0, 0, 255))
for y in range((y0 // step + 1) * step, y1, step):
    Y = (y - y0) * scale
    d.line([(0, Y), (im.width, Y)], fill=(255, 120, 0), width=1)
    d.text((2, Y + 2), str(y), fill=(200, 60, 0))
im.save(out)
