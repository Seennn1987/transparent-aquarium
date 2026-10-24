# A5 第 2 背びれの軟骨を、Thacher 1877 の図 31（シロシュモクザメの第 2 背びれの骨格）から作る（2026-10-24 案。HH_DFIN2_SRC=thacher のとき。a4e・a4d3 の後、mesh/HH_dfin2.ply を書き直す）
#  プロデューサー「Thacher の図 31（14 本の 3 片の放射軟骨が強く後ろへ寝て並び、最後の棒が後端へ伸びる）と、ウチワシュモクザメの胎児の届きをもとに、
#  第 2 背びれの軟骨を作り直す案を作り、見本・前の版と並べて見せてください」
#  見本: Thacher, J. K. 1877. Median and paired fins. Trans. Connecticut Acad. 3: 281–310, 図版 LIV 図 31（パブリックドメイン、Internet Archive「transactionsconn03conn」第 657 葉）。
#   ブラウザで第 657 葉（1964 × 3385 px）を等倍で見た画面から図 31 を切り出した docs/references/hammerhead/ref_thacher1877_sphyrna_dorsal2.jpg（530 × 190 px、git に入れない。頭は左）。
#   本文 p. 289: 放射軟骨 14 本、どれも根元・中・先の 3 片、最後の棒は大きく丸い。図はひれの膜を描かない
#  軟骨 = 図の、線で囲まれた所（線より明るく、背景より暗い。線は片と片の継ぎ目として残す）。線の切れた所は、図全体の外形（線と片を閉じて穴を埋めた形）の中を軟骨とする
#  置き方: 図の体軸は水平（いちばん下の片の下の縁がほぼ水平）とみなし、縦横同じ倍率で写す（棒の傾き・太さ・間隔を図のまま保つ）。
#   図の 1 本目の根元（いちばん左）を Raver の外形の前の端（606 mm）の HH_DFIN2_T_FRONT mm 後ろ、14 本目の先（いちばん右）を細い後端の HH_DFIN2_T_REAR mm 前へ（横の長さで倍率を決める）。
#   図のいちばん下を体の線の HH_DFIN2_T_BELOW mm 下へ（根元の片は体の中に入る）。高さはこの倍率のまま。届きの確かめ: ウチワシュモクザメの胎児（Byrum ら 2024）で、
#   棒はひれの先の細い帯を除く大部分まで届く。外形の 1 mm 内まで（それより外は切る）。左右の厚さは片の縁からの距離（片側 0.4〜1.2 mm）
import hh_paths; hh_paths.cd_work()
import numpy as np, json, os
from scipy import ndimage as nd
from skimage.measure import marching_cubes
from PIL import Image
from matplotlib.path import Path as _Path
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
import hh_fins
FIG = os.path.join(hh_paths.ROOT, 'docs', 'references', 'hammerhead', 'ref_thacher1877_sphyrna_dorsal2.jpg')
if not os.path.exists(FIG): raise SystemExit(f'見本の図がありません（git に入れていない）: {FIG}')
FRONT = float(os.environ.get('HH_DFIN2_T_FRONT', 3.0)); REAR = float(os.environ.get('HH_DFIN2_T_REAR', 2.0)); BELOW = float(os.environ.get('HH_DFIN2_T_BELOW', 2.0))
A = np.asarray(Image.open(FIG).convert('RGB')).astype(float); sm = nd.gaussian_filter(A.mean(2), 0.7); Hh, Ww = sm.shape
line = nd.binary_closing(sm < 175, iterations=1)
cl, n = nd.label(~line); border = set(np.unique(np.r_[cl[0], cl[-1], cl[:, 0], cl[:, -1]]).tolist()); sz = nd.sum(~line, cl, range(1, n + 1))
pieces = np.isin(cl, [k for k in range(1, n + 1) if k not in border and sz[k - 1] >= 25])
# 図の外形（文字「Fig. 31」と番号は片から離れているので入らない）
big = nd.binary_closing(pieces | (line & nd.binary_dilation(pieces, iterations=4)), iterations=3); big = nd.binary_fill_holes(big)
cl2, n2 = nd.label(big); big = cl2 == (1 + np.argmax(nd.sum(big, cl2, range(1, n2 + 1))))
cart_px = big & ~(line & ~pieces & nd.binary_erosion(big, iterations=2)) if False else (big & ~line) | pieces
cart_px &= big
ys, xs = np.nonzero(big); xL, xR, yB = float(xs.min()), float(xs.max()), float(ys.max())
fd = hh_fins.dfin2_raver_fd(); TLm = hh_fins.TL_MM; Lb = (fd['i'] - fd['o']) * TLm; Hm = fd['H'] * TLm; s_rear = max(s for s, h in fd['poly'])
x_front = fd['o'] * TLm + FRONT; x_tip = fd['o'] * TLm + s_rear * Lb - REAR
k = (x_tip - x_front) / (xR - xL)                                           # mm / 画素（縦横同じ）
sf = json.load(open('a5_side_fit.json')); top = lambda x: np.interp(x, sf['z_mm'], sf['top_target_mm'])
poly = [(fd['o'] * TLm + s * Lb, (h * Hm if h > 0 else -4.0)) for s, h in fd['poly']]
G = 0.2
X0, X1 = fd['o'] * TLm - 5, fd['o'] * TLm + s_rear * Lb + 5; Z0, Z1 = -BELOW - 2, Hm + 3
GX, GZ = np.meshgrid(np.arange(X0, X1, G), np.arange(Z0, Z1, G), indexing='ij')
OUT2 = _Path(poly).contains_points(np.c_[GX.ravel(), GZ.ravel()]).reshape(GX.shape)
INNER = nd.binary_erosion(OUT2, iterations=int(1.0 / G))
inside = INNER | ((GZ < 0.5) & (GX > poly[0][0]) & (GX < max(p[0] for p in poly)))
# 高さの倍率 KV: 図の標本（Wood's Hole）と Raver の図ではひれの形が違い、縦横同じ倍率では後ろの棒（10〜14 本目）が Raver の外形の低い後ろの葉より高く、軟骨の 3 割が外形の外に出た。
#  高さだけを、外形の外に出る軟骨が HH_DFIN2_T_CLIP（既定 2%）以下になるまで縮める（棒は少し寝る）。HH_DFIN2_T_KV で直接指定もできる
def _cart(kv):
    px_ = xL + (GX - x_front) / k; py_ = yB - (GZ + BELOW) / (k * kv)
    return nd.map_coordinates(cart_px.astype(np.float32), [py_.ravel(), px_.ravel()], order=1, cval=0).reshape(GX.shape) > 0.5
# 2026-10-24 直し: 高さを全体で縮めると（0.6 倍）棒の先がひれの高さの 0.52 までしか届かず、ウチワシュモクザメの胎児（ひれの大部分まで届く）と合わなかった。
#  HH_DFIN2_T_FIT=profile（既定）で、体軸の位置ごとに、図の軟骨のいちばん上を外形の高さの HH_DFIN2_T_REACH（既定 0.9）へ合わせる（体軸の向きは図のまま）
FIT = os.environ.get('HH_DFIN2_T_FIT', 'profile'); REACHF = float(os.environ.get('HH_DFIN2_T_REACH', 0.9))
if FIT == 'profile':
    _cols = np.arange(Ww); _has = big.any(0); _td = np.where(_has, np.argmax(big, 0), yB).astype(float)
    _td = nd.gaussian_filter1d(np.interp(_cols, _cols[_has], _td[_has]), float(os.environ.get('HH_DFIN2_T_SM_FIG', 25)), mode='nearest')
    _top_m = np.array([GZ[i][OUT2[i]].max() if OUT2[i].any() else 0.0 for i in range(GX.shape[0])])
    _top_m = nd.gaussian_filter1d(np.maximum(_top_m, 0.5), float(os.environ.get('HH_DFIN2_T_SM_FIN', 6)) / G, mode='nearest')   # 図・外形の上の縁を、図 25 px・外形 6 mm でならす（ならさないと棒が頂点と切れ込みの所で波打った）
    px_ = xL + (GX - x_front) / k
    tdx = np.interp(px_, _cols, _td); tmx = np.interp(GX[:, 0], GX[:, 0], _top_m)[:, None] * np.ones_like(GZ)
    frac = (GZ + BELOW) / np.maximum(REACHF * tmx + BELOW, 1.0)
    py_ = yB - frac * (yB - tdx)
    cart = nd.map_coordinates(cart_px.astype(np.float32), [py_.ravel(), px_.ravel()], order=1, cval=0).reshape(GX.shape) > 0.5
    KV = float('nan')
KV = os.environ.get('HH_DFIN2_T_KV') if FIT != 'profile' else KV
if FIT == 'profile': pass
elif KV: KV = float(KV)
else:
    for KV in np.arange(1.0, 0.39, -0.02):
        c_ = _cart(KV); up_ = c_ & (GZ > 0)
        if (up_ & ~inside).sum() <= float(os.environ.get('HH_DFIN2_T_CLIP', 0.02)) * up_.sum(): break
if FIT != 'profile': cart = _cart(KV)
cart_all = cart.copy(); cart &= inside
dt = nd.distance_transform_edt(cart) * G; hc = np.clip(nd.gaussian_filter(dt, 0.5), 0.4, 1.2); hc[~cart] = 0
NW = int(np.ceil(1.4 / G)); gy = np.arange(-NW, NW + 1) * G
F = hc[..., None] - np.abs(gy)[None, None, :]; F[~cart] = -1
F = nd.gaussian_filter(F.astype(np.float32), [0.4, 0.4, 0.5])
v, f, _, _ = marching_cubes(np.pad(F, 1, constant_values=-1), 0.0, allow_degenerate=False); v = v - 1
Xv = X0 + v[:, 0] * G; Zv = Z0 + v[:, 1] * G; Yv = gy[0] + v[:, 2] * G
Vb = np.stack([Xv, Yv, -top(Xv) + Zv], 1) / 1000.0
vol = np.einsum('ij,ij->i', Vb[f[:, 0]], np.cross(Vb[f[:, 1]], Vb[f[:, 2]])).sum() / 6
if vol > 0: f = f[:, ::-1]
write_ply(f'{OUT}/HH_dfin2.ply', Vb, f)
up = cart & (GZ > 0)
rep = {'figure_px': [xL, xR, yB], 'mm_per_px': round(k, 4), 'kv': round(float(KV), 2), 'fit': FIT, 'reach_target': REACHF, 'fin_height_mm': round(Hm, 1),
       'clipped_area_mm2': round(float((cart_all & ~cart & (GZ > 0)).sum() * G * G), 1),
       'cart_area_mm2': round(float(up.sum() * G * G), 1), 'memb_area_mm2': round(float((OUT2 & (GZ > 0)).sum() * G * G), 1), 'faces': int(len(f))}
json.dump(rep, open('a5i_dfin2_thacher.json', 'w'), indent=1); print(rep)
np.save('a5i_dfin2_grid.npy', np.stack([OUT2, cart]))
