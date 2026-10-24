"""
標本ページの絵の点の色を測り、背景で割った通し光を出す。印を付けた図も書く。

  .venv/bin/python -I blender/mendako/measure_page.py <絵> <印の図の出力> 名前=x,y [名前=x,y ...]
背景は「bg=x,y」で指定する（7×7 の中央値）。目標（計画書 第 2.4 節）と並べて出す
"""
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

TARGET = {"web": (0.80, 0.92, 0.94), "head": (0.57, 0.72, 0.86), "eye": (0.25, 0.55, 0.60)}
src, out = sys.argv[1], sys.argv[2]
pts = {k: tuple(map(int, v.split(","))) for k, v in (a.split("=") for a in sys.argv[3:])}
im = Image.open(src).convert("RGB")
a = np.asarray(im).astype(float)
med = {k: np.median(a[y - 3:y + 4, x - 3:x + 4].reshape(-1, 3), 0) for k, (x, y) in pts.items()}
bg = med.pop("bg")
d = ImageDraw.Draw(im)
f = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 20)
for k, (x, y) in pts.items():
    d.ellipse([x - 7, y - 7, x + 7, y + 7], outline=(255, 0, 0), width=3)
    d.text((x + 10, y - 12), k, font=f, fill=(220, 0, 0))
    if k == "bg":
        continue
    t = med[k] / bg
    tg = TARGET.get(k.rstrip("0123456789"))
    print(f"{k:6s} ({x}, {y}) 色 {med[k].astype(int)} 通し光 {np.round(t, 2)}" + (f"  目標 {tg}" if tg else ""))
print("背景", bg.astype(int))
im.save(out)
