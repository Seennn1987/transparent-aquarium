# A5 第 1 背びれの軟骨を、シロシュモクザメの骨格標本の写真から作る（2026-10-20 案。HH_DFIN1_PHOTO=1 のときだけ。a4e_mesh.py fins の後）
#  プロデューサー「胸びれはこの案を既定にして、次のひれ（第 1 背びれ）に進んでください」。ひれの形を見本と比べた結果（計画書「ひれの軟骨の形を見本と比べる」）:
#  いまの第 1 背びれの軟骨（CT）は、付け根の高さ 15% で膜 132 mm のうち前から 18〜87 mm だけで、前と後ろが空き、中ほどで高さ 45〜55% まで盛り上がる。
#  見本: ピサ大学自然史博物館の骨格標本 P 415（シロシュモクザメ、Stefano Puzzuoli、CC BY-SA 4.0、docs/references/hammerhead/ref1_pisa_sphyrna_zygaena_skeleton_lateral.jpg）の
#   第 1 背びれ。白い放射軟骨の帯が付け根に沿い、帯の上の境は後ろ（頂点の下）で低く（高さの約 26%）、前の低い所ではほぼ全部が棒。後端の細い所には棒が無い
#  写真 4059 × 2706 px の、2000 px に縮めたときの x 1130〜1400・y 630〜905 を元の画素で切り出し、左右を返す（頭を左に）。
#   ひれ = 明るさ > 60 のいちばん大きな塊（背骨より上）。放射軟骨 = 棒の間の黒いすき間のある帯の中の明るい所（下の 2026-10-20 の注）
#  置き方: ひれの外形（hh_fins.py の dfin1、a6a が膜の板を作る形）と写真のひれを、付け根の前の端（s 0）・後端（s 1.33）・頂点の高さ（h 1）で合わせる（前後と高さで別の倍率）。
#   軟骨は外形の 1 mm 内まで。付け根の下は体の線の 3 mm 内まで伸ばす（膜の板は体の線の 4 mm 内まで）。左右の厚さは、写真の棒の縁からの距離を半分の厚さに（上限 1.2 mm。膜の板は ±1.6 mm）
import hh_paths; hh_paths.cd_work()
import numpy as np, json, os
from scipy import ndimage as nd
from skimage.measure import marching_cubes
from PIL import Image, ImageOps
from matplotlib.path import Path as _Path
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
import hh_fins
PHOTO = os.path.join(hh_paths.ROOT, 'docs', 'references', 'hammerhead', 'ref1_pisa_sphyrna_zygaena_skeleton_lateral.jpg')
if not os.path.exists(PHOTO): raise SystemExit(f'見本の写真がありません（git に入れていない）: {PHOTO}')
im = Image.open(PHOTO).convert('RGB'); sc = im.width / 2000
im = ImageOps.mirror(im.crop(tuple(int(v * sc) for v in (1130, 630, 1400, 905))))
A = np.asarray(im).astype(float); Hh, Ww = A.shape[:2]; yy, xx = np.mgrid[0:Hh, 0:Ww]
mn = A.min(2); mx = A.max(2); sat = (mx - mn) / np.maximum(mx, 1)
col_y = int(0.86 * Hh)                                                      # 背骨（切り出しの下の 14%）より上だけ
fin = (mx > 60) & (yy < col_y); cl, n = nd.label(fin); fin = cl == (1 + np.argmax(nd.sum(fin, cl, range(1, n + 1))))
fin = nd.binary_fill_holes(fin)
# 放射軟骨の帯: 帯の上の境（放射軟骨と膜の境の明るい筋）を、左右を返した切り出し（548 × 558 px）で目で読んだ点（x, y）を結ぶ:
#  (60, 345) (100, 322) (150, 307) (200, 300) (250, 301) (300, 310) (340, 328) (380, 350) (420, 372) (460, 392) (500, 412) (520, 425)。
#  色や暗いすき間だけで帯を探す版は、照明の暗い後ろ半分が抜けたり、膜の後ろの縁の筋まで拾ったりした。
#  帯 = ひれの中で境の線より下。棒 = 帯の中で、周り（4 px でぼかした値）より明るい所（棒の間は茶色く暗い）
SEAM = np.array([(60, 345), (100, 322), (150, 307), (200, 300), (250, 301), (300, 310), (340, 328), (380, 350), (420, 372), (460, 392), (500, 412), (520, 425)], float)
band = fin & (yy >= np.interp(xx, SEAM[:, 0], SEAM[:, 1])) & (xx >= SEAM[0, 0] - 30)
rad = band & (mn > nd.gaussian_filter(mn, 4) + 2) & (yy <= 452)   # 付け根の下の破れた縁と、留めの針金（y 455 より下）は使わない
cl, n = nd.label(rad); sz = nd.sum(rad, cl, range(1, n + 1)); rad = np.isin(cl, 1 + np.nonzero(sz >= 20)[0])
fy, fx = np.nonzero(fin)
ybase = float(np.percentile(fy, 99)); apex_y = float(fy.min())
x_or = float(fx[fy > ybase - 0.10 * (ybase - apex_y)].min()); x_rear = float(fx.max())
fd = hh_fins.FINS['dfin1']; TLm = hh_fins.TL_MM; Lb = (fd['i'] - fd['o']) * TLm; Hm = fd['H'] * TLm; s_rear = max(s for s, h in fd['poly'])
sf = json.load(open('a5_side_fit.json')); top = lambda x: np.interp(x, sf['z_mm'], sf['top_target_mm'])
poly = [(fd['o'] * TLm + s * Lb, (h * Hm if h > 0 else -4.0)) for s, h in fd['poly']]     # (体軸 mm, 体の線からの高さ mm)
G = 0.25
X0, X1 = fd['o'] * TLm - 5, fd['o'] * TLm + s_rear * Lb + 5; Z0, Z1 = -6.0, Hm + 5
GX, GZ = np.meshgrid(np.arange(X0, X1, G), np.arange(Z0, Z1, G), indexing='ij')
OUT2 = _Path(poly).contains_points(np.c_[GX.ravel(), GZ.ravel()]).reshape(GX.shape)
INNER = nd.binary_erosion(OUT2, iterations=int(1.0 / G))
# 外形の点 → 写真の画素（前後: s → x、高さ: h → 付け根からの高さ）。付け根の下（h < 0）は付け根の画素の行を使う（体の線の 3 mm 内まで）
s_g = (GX - fd['o'] * TLm) / Lb; h_g = GZ / Hm
px = x_or + s_g / s_rear * (x_rear - x_or); py = ybase - np.clip(h_g, 0, None) * (ybase - apex_y)
cart2 = (nd.map_coordinates(rad.astype(np.float32), [py.ravel(), px.ravel()], order=1, cval=0).reshape(GX.shape) > 0.5)
cart2 &= INNER | ((GZ < 0.5) & (GZ > -3.0) & OUT2)
cart2 &= GZ > -3.0
dt = nd.distance_transform_edt(cart2) * G; hc = np.clip(nd.gaussian_filter(dt, 0.5), 0, 1.2); hc[~cart2] = 0
NW = int(np.ceil(1.6 / G)); gw = np.arange(-NW, NW + 1) * G
F = hc[..., None] - np.abs(gw)[None, None, :]; F[~cart2] = -1
F = nd.gaussian_filter(F.astype(np.float32), [0.6, 0.6, 0.6])
v, f, _, _ = marching_cubes(np.pad(F, 1, constant_values=-1), 0.0, allow_degenerate=False); v = v - 1
Xv = X0 + v[:, 0] * G; Zv = Z0 + v[:, 1] * G; Yv = v[:, 2] * G - NW * G
Vb = np.stack([Xv, Yv, -top(Xv) + Zv], 1) / 1000.0                          # Blender（x = 体軸、y = 左右、z = 背）。体の線は z = −top_target
vol = np.einsum('ij,ij->i', Vb[f[:, 0]], np.cross(Vb[f[:, 1]], Vb[f[:, 2]])).sum() / 6
if vol > 0: f = f[:, ::-1]                                                  # write_ply が裏返して書くので、内向きにそろえて渡す
write_ply(f'{OUT}/HH_dfin1.ply', Vb, f)
memb = OUT2 & (GZ > 0)
rep = {'photo_px': {'origin_x': x_or, 'rear_x': x_rear, 'base_y': ybase, 'apex_y': apex_y}, 'cart_area_mm2': round(float((cart2 & (GZ > 0)).sum() * G * G), 1),
       'memb_area_mm2': round(float(memb.sum() * G * G), 1), 'cart_in_memb': round(float((cart2 & memb).sum() / memb.sum()), 3), 'volume_ml': round(abs(vol) * 1e6, 3), 'faces': int(len(f))}
json.dump(rep, open('a5_dfin1photo.json', 'w'), ensure_ascii=False, indent=1); print(rep)
