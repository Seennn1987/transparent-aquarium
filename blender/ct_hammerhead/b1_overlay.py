# B1 休みの姿勢と曲げた姿勢を、背から見た投影で色を変えて重ねる（b1_rig.py の HH_RIG_TEST=1 が書く b1_rig_proj*.npz から）
#  灰 = 休み（膜は薄い灰、骨は濃い灰）、青 = 曲げた膜、赤 = 曲げた骨。上が吻端（左）、尾（右）。y は体の右が下
#  使い方: python b1_overlay.py 出力.png 見出し npz [npz ...]（npz ごとに 1 段、位相 0 / 0.25 / 0.5 / 0.75 の 4 列）
import sys, numpy as np, hh_paths
from PIL import Image, ImageDraw
out, title, files = sys.argv[1], sys.argv[2], sys.argv[3:]
PH = ["0.0", "0.25", "0.5", "0.75"]; S = 0.62            # 1 px = 1/S mm
W, H = int(1120 * S) + 20, int(420 * S) + 40
def panel(d, ph, label):
    img = np.full((H, W, 3), 255, np.uint8)
    def dots(P, col, a):
        x = ((P[:, 0] * 1000 + 40) * S).astype(int); y = ((P[:, 1] * 1000 + 210) * S).astype(int) + 30
        ok = (x >= 0) & (x < W) & (y >= 0) & (y < H); x, y = x[ok], y[ok]
        img[y, x] = (img[y, x] * (1 - a) + np.array(col) * a).astype(np.uint8)
    dots(d["skin_rest"], (200, 200, 200), 0.5); dots(d["bone_rest"], (110, 110, 110), 0.6)
    dots(d[f"skin_{ph}"], (60, 120, 230), 0.35); dots(d[f"bone_{ph}"], (220, 40, 40), 0.6)
    im = Image.fromarray(img); dr = ImageDraw.Draw(im); dr.text((8, 4), label, fill=(0, 0, 0), font=hh_paths.font(16))
    for mm in range(0, 1001, 100): dr.line([((mm + 40) * S, H - 6), ((mm + 40) * S, H - 1)], fill=(0, 0, 0))
    return im
rows = []
for f in files:
    d = np.load(f); tag = f.split("proj_")[-1].replace(".npz", "")
    rows.append([panel(d, ph, f"{tag}  位相 {ph}") for ph in PH])
grid = Image.new("RGB", (W * 2, H * 2 * len(rows) + 64), "white")
for r, row in enumerate(rows):
    for i, im in enumerate(row): grid.paste(im, ((i % 2) * W, 64 + (r * 2 + i // 2) * H))
ImageDraw.Draw(grid).multiline_text((10, 6), title.replace("|", "\n"), fill=(0, 0, 0), font=hh_paths.font(20))
grid.save(out); print(out, grid.size)
