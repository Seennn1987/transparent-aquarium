# A8 尾びれの鰭条の軟骨を、ピサの骨格標本の写真の棒の並びから作る（2026-10-22 案。HH_CAUDAL_PHOTO=1 のときだけ。a8c_vertebrae.py の後、mesh/HH_vert_radials.ply を書き直す）
#  プロデューサー「尾びれの軟骨を、ピサの骨格標本の写真と比べて直す案を作り、見本・前の版と並べて見せてください」
#  前の版（a8c の HH_VERT_RADIALS）: 737 mm より後ろの椎骨ごとに、背骨の上下へ 1 本ずつ、後ろへ 40°・体の膜の縁までの 0.7 倍の細い棒（向きは推定）。
#  ピサの骨格標本（シロシュモクザメ、Stefano Puzzuoli、CC BY-SA 4.0）の尾びれでは、背骨の上の短い棒が背の縁まで、背骨の下の長い棒が腹の縁まで、すき間なく並ぶ。
#  下の葉（前の、下へ垂れる三角）だけは棒が無い膜（鰭条）。
#  写真: 4059 × 2706 px の、2000 px に縮めたときの x 60〜640・y 690〜1090 を元の画素で切り出して左右を返した 1177 × 812 px（頭が左）。目で読んだ線:
#   背骨の中心 SPINE、下の葉の膜と棒の境 LOBE（x 440 より前。それより後ろは棒が腹の縁まで）、下の葉のいちばん下 (270, 770)、尾の先 (1090, 105)
#  写し方: 背骨に沿う長さ（下の葉のいちばん下に最も近い背骨の点 〜 尾の先を、モデルの同じ 2 点へ）と、背骨からの距離を体の縁までの距離で割った割合で、写真の点とモデルの点を対応させる。
#   モデルの体の縁は a5_S.npy（体の膜の体積）の正中（u = 0）、背骨は a8c と同じ中心の高さ（tail_keep_v − tail_bend_offset）。
#   棒 = 写真の、棒のある所で周り（3 px ぼかし）より明るい所。背骨（中心から椎体の半径 + 0.5 mm）には置かない。左右の厚さは縁からの距離（上限 1.0 mm、下限 0.5 mm、片側）
import hh_paths; hh_paths.cd_work()
import numpy as np, json, os
from scipy import ndimage as nd
from skimage.measure import marching_cubes
from PIL import Image, ImageOps
from matplotlib.path import Path as _Path
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
VX = 0.735; U0, V0 = -180.0, -150.0
PHOTO = os.path.join(hh_paths.ROOT, 'docs', 'references', 'hammerhead', 'ref1_pisa_sphyrna_zygaena_skeleton_lateral.jpg')
if not os.path.exists(PHOTO): raise SystemExit(f'見本の写真がありません（git に入れていない）: {PHOTO}')
im = Image.open(PHOTO).convert('RGB'); sc = im.width / 2000
im = ImageOps.mirror(im.crop(tuple(int(v * sc) for v in (60, 690, 640, 1090))))
A = np.asarray(im).astype(float); Hh, Ww = A.shape[:2]; yy, xx = np.mgrid[0:Hh, 0:Ww]; mn = A.min(2); mx = A.max(2)
SPINE = np.array([(0, 385), (100, 345), (200, 315), (300, 285), (400, 255), (500, 220), (600, 185), (700, 150), (800, 112), (900, 85), (1000, 75), (1090, 105)], float)
LOBE = np.array([(0, 455), (50, 470), (100, 490), (200, 492), (300, 472), (400, 440), (440, 420)], float)
LOBE_LOW = np.array([270.0, 770.0])
fin = (mx > 55) & (xx > 90); cl, n = nd.label(fin); fin = cl == (1 + np.argmax(nd.sum(fin, cl, range(1, n + 1)))); fin = nd.binary_fill_holes(fin)   # 留めの針金と台（x 90 より前）は使わない
lobe_mem = (xx < 440) & (yy > np.interp(xx, LOBE[:, 0], LOBE[:, 1]))
rodzone = fin & ~lobe_mem
rad = rodzone & (mn > nd.gaussian_filter(mn, 3))
# 写真の背骨の線: 長さ（弧長）と法線
def poly_arc(P):
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]; return d
def dense(P, step):
    d = poly_arc(P); s = np.arange(0, d[-1], step); return np.c_[np.interp(s, d, P[:, 0]), np.interp(s, d, P[:, 1])], s
SPd, sp_s = dense(SPINE, 1.0)
tan_p = np.gradient(SPd, axis=0); tan_p /= np.linalg.norm(tan_p, axis=1, keepdims=True); nor_p = np.c_[tan_p[:, 1], -tan_p[:, 0]]   # 上（y が減る）向き
if (nor_p[:, 1] > 0).mean() > 0.5: nor_p = -nor_p
def margin_photo(k, sg):   # 背骨の点 k から法線（sg = +1 上、−1 下）に、ひれの縁までの距離（px）
    p = SPd[k]; last = 0.0
    for t in np.arange(0, 400, 1.0):
        q = p + sg * t * nor_p[k]; xi, yi = int(round(q[0])), int(round(q[1]))
        if not (0 <= xi < Ww and 0 <= yi < Hh) or not fin[yi, xi]: return max(last, 1.0)
        last = t
    return last
MP = np.array([[margin_photo(k, sg) for sg in (1, -1)] for k in range(len(SPd))])
MP = nd.median_filter(MP, size=(15, 1))
k_lobe = int(np.argmin(np.linalg.norm(SPd - LOBE_LOW, axis=1))); k_tip = len(SPd) - 1
# モデルの背骨と体の縁
keep = np.load('tail_keep_v.npy'); off = np.load('tail_bend_offset_mm.npy')
vc = lambda z: np.interp(z * 2, np.arange(len(keep)), keep) - np.interp(z, np.arange(len(off)), off)
vinfo = json.load(open('a8_vertebrae.json')); zend = float(vinfo['z_mm'][1])
SK = np.load('a5_S.npy', mmap_mode='r'); iu0 = int(round((0 - U0) / VX))
Z0m = float(os.environ.get('HH_CAUDAL_Z0', 690)); zs = np.arange(Z0m, zend, 0.5)
SPm = np.c_[zs, vc(zs)]                                              # (z, v)、v は腹へ +
tan_m = np.gradient(SPm, axis=0); tan_m /= np.linalg.norm(tan_m, axis=1, keepdims=True); nor_m = np.c_[tan_m[:, 1], -tan_m[:, 0]]   # 背（v が減る）向き
if (nor_m[:, 1] > 0).mean() > 0.5: nor_m = -nor_m
def margin_model(k, sg):
    p = SPm[k]; last = 0.0
    for t in np.arange(0, 120, 0.25):
        q = p + sg * t * nor_m[k]; iz, iv = int(round(q[0] / VX)), int(round((q[1] - V0) / VX))
        if not (0 <= iz < SK.shape[0] and 0 <= iv < SK.shape[1]) or not SK[iz, iv, iu0]: return max(last, 0.5)
        last = t
    return last
MM = np.array([[margin_model(k, sg) for sg in (1, -1)] for k in range(len(SPm))]); MM = nd.median_filter(MM, size=(9, 1))
# 下の葉のいちばん下: モデルの体の縁がいちばん腹側の所（尾びれの範囲）
bot = SPm[:, 1] + MM[:, 1] * (-nor_m[:, 1])
k_lobe_m = int(np.argmax(np.where(zs < zend - 120, bot, -1e9)))
sm = np.r_[0, np.cumsum(np.hypot(*np.diff(SPm, axis=0).T))]
def to_photo_k(km):   # モデルの背骨の点 → 写真の背骨の点（長さの割合で 2 点を合わせる）
    f = (sm[km] - sm[k_lobe_m]) / (sm[-1] - sm[k_lobe_m]); s_ = sp_s[k_lobe] + f * (sp_s[k_tip] - sp_s[k_lobe]); return np.clip(np.interp(s_, sp_s, np.arange(len(sp_s))), 0, len(sp_s) - 1)
# 正中の面の格子
G = 0.25
zg = np.arange(Z0m, zend + 2, G); vmin, vmax = (SPm[:, 1] - MM[:, 0] - 3).min(), (SPm[:, 1] + MM[:, 1] + 3).max(); vg = np.arange(vmin, vmax, G)
GZ, GV = np.meshgrid(zg, vg, indexing='ij')
from scipy.spatial import cKDTree
kd = cKDTree(SPm); dist, kk = kd.query(np.c_[GZ.ravel(), GV.ravel()]); kk = kk.reshape(GZ.shape)
w = ((np.c_[GZ.ravel(), GV.ravel()] - SPm[kk.ravel()]) * nor_m[kk.ravel()]).sum(1).reshape(GZ.shape)   # 背骨からの距離（背 +）
sg = np.where(w >= 0, 0, 1); mm_ = MM[kk, sg]; tfrac = np.abs(w) / mm_
kp = to_photo_k(kk); kpi = np.round(kp).astype(int)
mp_ = MP[kpi, sg]; sgn = np.where(w >= 0, 1, -1)
PX = SPd[kpi, 0] + sgn * tfrac * mp_ * nor_p[kpi, 0]; PY = SPd[kpi, 1] + sgn * tfrac * mp_ * nor_p[kpi, 1]
inside_body = np.zeros(GZ.shape, bool)
iz = np.clip(np.round(GZ / VX).astype(int), 0, SK.shape[0] - 1); iv = np.clip(np.round((GV - V0) / VX).astype(int), 0, SK.shape[1] - 1)
inside_body = np.asarray(SK)[iz, iv, iu0] if False else np.array([[SK[a, b, iu0] for a, b in zip(ra, rb)] for ra, rb in zip(iz, iv)])
R_ = np.interp(GZ, [float(k) for k in vinfo['radius_mm'].keys()], list(vinfo['radius_mm'].values()))
cart = (nd.map_coordinates(rad.astype(np.float32), [PY.ravel(), PX.ravel()], order=1, cval=0).reshape(GZ.shape) > 0.5)
cart &= (tfrac <= 1.0) & (np.abs(w) > R_ + 0.5) & nd.binary_erosion(inside_body, iterations=int(float(os.environ.get('HH_CAUDAL_EDGE', 2.5)) / G))   # 体の膜の縁の内側 2.5 mm まで（2 mm でも 4 頂点、0.75 mm では、標本ページの体の膜（面をならした後）の外に尾の先の背の側で 405 頂点が出た） & (kk > 0)
dt = nd.distance_transform_edt(cart) * G; hc = np.clip(nd.gaussian_filter(dt, 0.5), 0.5, 1.0); hc[~cart] = 0
NW = int(np.ceil(1.2 / G)); gu = np.arange(-NW, NW + 1) * G
F = hc[..., None] - np.abs(gu)[None, None, :]; F[~cart] = -1
F = nd.gaussian_filter(F.astype(np.float32), [0.5, 0.5, 0.5])
v, f, _, _ = marching_cubes(np.pad(F, 1, constant_values=-1), 0.0, allow_degenerate=False); v = v - 1
Zv = zg[0] + v[:, 0] * G; Vv = vg[0] + v[:, 1] * G; Uv = gu[0] + v[:, 2] * G
Vb = np.stack([Zv, Uv, -Vv], 1) / 1000.0
vol = np.einsum('ij,ij->i', Vb[f[:, 0]], np.cross(Vb[f[:, 1]], Vb[f[:, 2]])).sum() / 6
if vol > 0: f = f[:, ::-1]
write_ply(f'{OUT}/HH_vert_radials.ply', Vb, f)
rep = {'z_mm': [Z0m, round(zend, 1)], 'lobe_low_model_z': round(float(zs[k_lobe_m]), 1), 'photo_lobe_k': k_lobe, 'cart_area_mm2': round(float(cart.sum() * G * G), 1),
       'volume_ml': round(abs(vol) * 1e6, 3), 'faces': int(len(f))}
json.dump(rep, open('a8d_caudal_photo.json', 'w'), indent=1); print(rep)
