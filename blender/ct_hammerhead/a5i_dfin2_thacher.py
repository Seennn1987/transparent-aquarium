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
FRONT = float(os.environ.get('HH_DFIN2_T_FRONT', 0.0)); REAR = float(os.environ.get('HH_DFIN2_T_REAR', 2.0)); BELOW = float(os.environ.get('HH_DFIN2_T_BELOW', 10.0))   # 2026-10-24: 図のいちばん下（根元の片の下の端）を体の線の 10 mm 下へ（この CT 標本の第 2 背びれの軟骨が体の線の 9.8 mm 下まで写る。Mivart・Thacher: 根元は背骨の近くまで）
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
# 2026-10-24 直し（プロデューサー「まだヒレの一部が空白になっていますよね？ほとんどが軟骨で満たされているのが実態なのでは？また、ヒレそのものから胴体の一部にかけて軟骨が伸びているのでは？調査した上で作り直し」）:
#  - 届き: ウチワシュモクザメの胎児（Byrum ら 2024）で棒はひれの縁のすぐ内まで並ぶ。外形の高さの HH_DFIN2_T_REACH（0.97）まで、外形の内側 0.6 mm まで、前の端から（FRONT 0）
#  - 体の中: Mivart 1879（Zygaena malleus）「ひれの骨格全体は、下の背骨から繊維の膜で隔てられ、そのすき間は、いちばん短い段の深さの半分より狭い」、
#    Thacher 1877 p. 285「棒は背の正中の縦の靭帯（神経弓の上）に届かないのがふつうで、Eulamia の第 1 背びれでは前の端で 1.5 cm、後ろの端で 3.5 cm 離れる」、
#    この CT 標本の第 2 背びれも体の線の 9.8 mm 下まで写る。根元の片は体の中へ、神経弓の上の HH_DFIN2_T_GAP（2 mm）上まで伸ばす（付け根の後ろの端 658 mm から細い後端までは体の線へ戻す）
DEPTH = os.environ.get('HH_DFIN2_T_DEPTH', 'fig'); GAP = float(os.environ.get('HH_DFIN2_T_GAP', 2.0))
keep_ = np.load('tail_keep_v.npy'); off_ = np.load('tail_bend_offset_mm.npy'); vinfo = json.load(open('a8_vertebrae.json'))
vc_ = lambda z: np.interp(z * 2, np.arange(len(keep_)), keep_) - np.interp(z, np.arange(len(off_)), off_)
Rv = lambda z: np.interp(z, [float(q) for q in vinfo['radius_mm']], list(vinfo['radius_mm'].values()))
_arch_top = lambda z: -vc_(z) + 1.55 * Rv(z)                                # Blender の z（背 +）。a8c の背の弓: 椎体の中心から 0.75 r + 0.8 r（HH_VERT_ARCHH 0.8）
def depth_of(x):   # 体の線から根元の片の下の端までの深さ（mm、正）
    if DEPTH != 'arch': return np.full_like(np.asarray(x, float), BELOW)
    d = top(x) - _arch_top(x) - GAP                                        # top(x) は体の線の v（−が背）→ Blender の z は −top
    d = -top(x) * 0 + (-(top(x)) - _arch_top(x) - GAP) * -1 if False else (-top(x)) - _arch_top(x) - GAP
    ins = fd['i'] * TLm; tip = fd['o'] * TLm + s_rear * Lb
    return np.maximum(d, BELOW) * np.clip((tip - np.asarray(x, float)) / max(tip - ins, 1.0), 0, 1)
Z0 = -float(np.max(depth_of(np.arange(X0, X1, 1.0)))) - 2
if DEPTH in ('ct', 'fig'): Z0 = -BELOW - 2.0
GX, GZ = np.meshgrid(np.arange(X0, X1, G), np.arange(Z0, Z1, G), indexing='ij')
OUT2 = _Path(poly).contains_points(np.c_[GX.ravel(), GZ.ravel()]).reshape(GX.shape)
INNER = nd.binary_erosion(OUT2, iterations=max(1, int(round(float(os.environ.get('HH_DFIN2_T_EDGE', 0.6)) / G))))
inside = INNER | ((GZ < 0.5) & (GX > poly[0][0]) & (GX < max(p[0] for p in poly)) & (GZ >= -depth_of(GX[:, 0])[:, None] - 0.5))
# 高さの倍率 KV: 図の標本（Wood's Hole）と Raver の図ではひれの形が違い、縦横同じ倍率では後ろの棒（10〜14 本目）が Raver の外形の低い後ろの葉より高く、軟骨の 3 割が外形の外に出た。
#  高さだけを、外形の外に出る軟骨が HH_DFIN2_T_CLIP（既定 2%）以下になるまで縮める（棒は少し寝る）。HH_DFIN2_T_KV で直接指定もできる
def _cart(kv):
    px_ = xL + (GX - x_front) / k; py_ = yB - (GZ + BELOW) / (k * kv)
    return nd.map_coordinates(cart_px.astype(np.float32), [py_.ravel(), px_.ravel()], order=1, cval=0).reshape(GX.shape) > 0.5
# 2026-10-24 直し: 高さを全体で縮めると（0.6 倍）棒の先がひれの高さの 0.52 までしか届かず、ウチワシュモクザメの胎児（ひれの大部分まで届く）と合わなかった。
#  HH_DFIN2_T_FIT=profile（既定）で、体軸の位置ごとに、図の軟骨のいちばん上を外形の高さの HH_DFIN2_T_REACH（既定 0.9）へ合わせる（体軸の向きは図のまま）
FIT = os.environ.get('HH_DFIN2_T_FIT', 'profile'); REACHF = float(os.environ.get('HH_DFIN2_T_REACH', 0.97))
if FIT == 'profile':
    _cols = np.arange(Ww); _has = big.any(0); _td = np.where(_has, np.argmax(big, 0), yB).astype(float)
    _td = nd.gaussian_filter1d(np.interp(_cols, _cols[_has], _td[_has]), float(os.environ.get('HH_DFIN2_T_SM_FIG', 25)), mode='nearest')
    _top_m = np.array([GZ[i][OUT2[i]].max() if OUT2[i].any() else 0.0 for i in range(GX.shape[0])])
    _top_m = nd.gaussian_filter1d(np.maximum(_top_m, 0.5), float(os.environ.get('HH_DFIN2_T_SM_FIN', 6)) / G, mode='nearest')   # 図・外形の上の縁を、図 25 px・外形 6 mm でならす（ならさないと棒が頂点と切れ込みの所で波打った）
    px_ = xL + (GX - x_front) / k
    tdx = np.interp(px_, _cols, _td); tmx = np.interp(GX[:, 0], GX[:, 0], _top_m)[:, None] * np.ones_like(GZ)
    _bd = np.where(_has, Hh - 1 - np.argmax(big[::-1], 0), yB).astype(float); _bd = nd.gaussian_filter1d(np.interp(_cols, _cols[_has], _bd[_has]), float(os.environ.get('HH_DFIN2_T_SM_FIG', 25)), mode='nearest')
    #  列ごとに図の下の縁まで体の中へ写す版は、後ろの丸い板と細い後端が体の中まで大きく引き伸ばされた。図のいちばん下は体の線の BELOW mm 下のまま写し、
    #  その下（体の中）は、根元の片を棒の向きのまま神経弓の上まで伸ばす（下の EXT）
    frac = (GZ + BELOW) / np.maximum(REACHF * tmx + BELOW, 1.0)   # 0 = 図のいちばん下（体の線の BELOW mm 下）、1 = 外形の高さの REACH
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
cart_all = cart.copy(); cart &= inside & (GZ >= -BELOW)
# 根元の片を体の中へ伸ばす: 体の線の BELOW mm 下〜体の線の 1 mm 上の軟骨の画素を、そこでの棒の向き（構造テンソル、4 mm）のまま下（前・下）へ、深さ depth_of(x) まで引き延ばす
if DEPTH == 'arch':
    _f = nd.gaussian_filter(cart.astype(float), 1.0); _gx, _gz = np.gradient(_f)
    _J = [nd.gaussian_filter(q, 4.0 / G) for q in (_gx * _gx, _gz * _gz, _gx * _gz)]
    _th = 0.5 * np.arctan2(2 * _J[2], _J[0] - _J[1]) + np.pi / 2                # 棒の向き（格子の x・z）
    seed = cart & (GZ >= -BELOW) & (GZ <= 1.0)
    si, sj = np.nonzero(seed); ext = np.zeros_like(cart)
    dx_, dz_ = np.cos(_th[si, sj]), np.sin(_th[si, sj]); flip = dz_ > 0; dx_[flip] *= -1; dz_[flip] *= -1   # 下向き
    dz_ = np.minimum(dz_, -0.3); nrm_ = np.hypot(dx_, dz_); dx_ /= nrm_; dz_ /= nrm_
    for t in np.arange(0, 40, 0.5 * G):
        ii = np.round(si + t * dx_ / 1).astype(int); jj = np.round(sj + t * dz_ / 1).astype(int)
        ok = (ii >= 0) & (ii < GX.shape[0]) & (jj >= 0) & (jj < GX.shape[1])
        ii, jj = ii[ok], jj[ok]
        deep = GZ[ii, jj] >= -depth_of(GX[ii, 0])
        ext[ii[deep], jj[deep]] = True
        if not deep.any(): break
    ext = nd.binary_opening(ext, iterations=1)
    cart |= ext & (GX > poly[0][0] - 2)
dt = nd.distance_transform_edt(cart) * G; hc = np.clip(nd.gaussian_filter(dt, 0.5), 0.4, 1.2); hc[~cart] = 0
NW = int(np.ceil((6.0 if DEPTH == 'ct' else 1.4) / G)); gy = np.arange(-NW, NW + 1) * G
F = hc[..., None] - np.abs(gy)[None, None, :]; F[~cart] = -1
if DEPTH == 'ct':
    # 体の中（体の線の BELOW mm 下より下）は、この CT 標本の第 2 背びれの軟骨（a4_dfin2.npz、a4e と同じ体積。体の線の 9.8 mm 下まで写る）。a6a が CT の軟骨にしていたのと同じく
    #  体の線の動き（a5_trunk_width.json の dtop）だけ動かす。神経弓の伸ばし（'arch'）は、棒が寝ているので体の中で 40 mm 前まで伸び、根拠が無いのでやめた
    ct = np.load('a4_dfin2.npz'); fld = ct['field']; org = ct['origin']; VX_ = 0.735; U0_, V0_ = -180.0, -150.0
    _tw = json.load(open('a5_trunk_width.json')) if os.path.exists('a5_trunk_width.json') else None
    gx1 = GX[:, 0]; dtop = np.interp(gx1, _tw['z_mm'], _tw['dtop_mm']) if _tw and 'dtop_mm' in _tw else np.zeros_like(gx1)
    GX3, GZ3, GY3 = np.meshgrid(gx1, GZ[0], gy, indexing='ij')
    zf = -top(GX3) + GZ3 - np.interp(GX3, gx1, dtop)
    iz = GX3 / VX_ - org[0]; iv = (-zf - V0_) / VX_ - org[1]; iu = (GY3 - U0_) / VX_ - org[2]
    Fc = nd.map_coordinates(fld.astype(np.float32), [iz.ravel(), iv.ravel(), iu.ravel()], order=1, cval=0).reshape(GX3.shape) - 0.5
    Fc[GZ3 > -BELOW + 0.5] = -1
    F = np.maximum(F, Fc * 2.0)
    rep_ct = {'ct_below_line_mm': round(float(-GZ3[Fc > 0].min()), 1) if (Fc > 0).any() else None}
else:
    rep_ct = {}
F = nd.gaussian_filter(F.astype(np.float32), [0.4, 0.4, 0.5])
v, f, _, _ = marching_cubes(np.pad(F, 1, constant_values=-1), 0.0, allow_degenerate=False); v = v - 1
Xv = X0 + v[:, 0] * G; Zv = Z0 + v[:, 1] * G; Yv = gy[0] + v[:, 2] * G
Vb = np.stack([Xv, Yv, -top(Xv) + Zv], 1) / 1000.0
vol = np.einsum('ij,ij->i', Vb[f[:, 0]], np.cross(Vb[f[:, 1]], Vb[f[:, 2]])).sum() / 6
if vol > 0: f = f[:, ::-1]
write_ply(f'{OUT}/HH_dfin2.ply', Vb, f)
up = cart & (GZ > 0)
rep = {**rep_ct, 'figure_px': [xL, xR, yB], 'mm_per_px': round(k, 4), 'kv': round(float(KV), 2), 'fit': FIT, 'reach_target': REACHF, 'depth_mm': [round(float(depth_of(x)), 1) for x in (610, 630, 650, 670, 690)], 'fin_height_mm': round(Hm, 1),
       'clipped_area_mm2': round(float((cart_all & ~cart & (GZ > 0)).sum() * G * G), 1),
       'cart_area_mm2': round(float(up.sum() * G * G), 1), 'memb_area_mm2': round(float((OUT2 & (GZ > 0)).sum() * G * G), 1), 'faces': int(len(f))}
json.dump(rep, open('a5i_dfin2_thacher.json', 'w'), indent=1); print(rep)
np.save('a5i_dfin2_grid.npy', np.stack([OUT2, cart]))
